import hmac
import json
import logging
import os
import re
from collections.abc import Iterator
from enum import Enum
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator

from src.security.resource_controls import resource_guard

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)
_MIN_API_KEY_LENGTH = 32
_ALLOWED_SCOPES = frozenset({"read", "write", "tools:invoke"})
_SUBJECT_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")


class ApiScope(str, Enum):
    READ = "read"
    WRITE = "write"
    TOOLS_INVOKE = "tools:invoke"


class AuthenticatedPrincipal(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    scopes: frozenset[ApiScope]


class ApiKeyRecord(BaseModel):
    api_key: SecretStr
    subject: str = Field(min_length=1, max_length=64)
    scopes: frozenset[ApiScope]

    @model_validator(mode="after")
    def validate_record(self) -> "ApiKeyRecord":
        if len(self.api_key.get_secret_value()) < _MIN_API_KEY_LENGTH:
            raise ValueError("API keys must contain at least 32 characters.")
        if not _SUBJECT_PATTERN.fullmatch(self.subject):
            raise ValueError("API key subject must be a safe 1-64 character identifier.")
        if not self.scopes:
            raise ValueError("API keys must have at least one scope.")
        return self


def _load_api_keys() -> list[ApiKeyRecord]:
    multi_user_config = os.getenv("ECORAG_API_KEYS_JSON", "").strip()
    legacy_key = os.getenv("ECORAG_API_KEY", "")
    if multi_user_config and legacy_key:
        raise ValueError("Configure either ECORAG_API_KEYS_JSON or ECORAG_API_KEY, not both.")

    if multi_user_config:
        try:
            records = [ApiKeyRecord.model_validate(item) for item in json.loads(multi_user_config)]
        except (json.JSONDecodeError, TypeError, ValidationError) as exc:
            raise ValueError("ECORAG_API_KEYS_JSON must be a valid array of API key records.") from exc
        if not records or len(records) > 100:
            raise ValueError("ECORAG_API_KEYS_JSON must contain between 1 and 100 keys.")
        raw_keys = [record.api_key.get_secret_value() for record in records]
        if len(raw_keys) != len(set(raw_keys)):
            raise ValueError("ECORAG_API_KEYS_JSON must not contain duplicate keys.")
        return records

    raw_scopes = os.getenv("ECORAG_API_SCOPES", "read,write")
    configured_scopes = frozenset(scope.strip() for scope in raw_scopes.split(",") if scope.strip())
    if not legacy_key or len(legacy_key) < _MIN_API_KEY_LENGTH:
        raise ValueError("ECORAG_API_KEY is unset or shorter than 32 characters.")
    if not configured_scopes or not configured_scopes.issubset(_ALLOWED_SCOPES):
        raise ValueError("ECORAG_API_SCOPES contains invalid values.")

    try:
        return [
            ApiKeyRecord(
                api_key=SecretStr(legacy_key),
                subject=os.getenv("ECORAG_API_USER_ID", "local-user"),
                scopes=frozenset(ApiScope(scope) for scope in configured_scopes),
            )
        ]
    except ValidationError as exc:
        raise ValueError("Legacy API key identity or scopes are invalid.") from exc


async def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedPrincipal:
    try:
        api_keys = _load_api_keys()
    except ValueError as exc:
        logger.error("API authentication configuration is invalid.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured correctly.",
        ) from exc

    client_host = request.client.host if request.client else "unknown"
    auth_rate_subject = f"unauthenticated:{client_host}"
    if credentials is None:
        resource_guard.check_rate_limit(auth_rate_subject, "auth")
        logger.warning("api_authentication_denied reason=missing_bearer")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid bearer API key is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    presented_key = credentials.credentials.encode("utf-8")
    matched_record: ApiKeyRecord | None = None
    for record in api_keys:
        expected_key = record.api_key.get_secret_value().encode("utf-8")
        if hmac.compare_digest(presented_key, expected_key):
            matched_record = record

    if matched_record is None:
        resource_guard.check_rate_limit(auth_rate_subject, "auth")
        logger.warning("api_authentication_denied reason=invalid_bearer")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid bearer API key is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedPrincipal(
        subject=matched_record.subject,
        scopes=matched_record.scopes,
    )


def require_scope(required_scope: ApiScope) -> Callable[..., Iterator[AuthenticatedPrincipal]]:
    return require_access(required_scope)


def require_access(
    required_scope: ApiScope,
    operation: str | None = None,
) -> Callable[..., Iterator[AuthenticatedPrincipal]]:
    operation_name = operation or required_scope.value

    def dependency(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> Iterator[AuthenticatedPrincipal]:
        if required_scope not in principal.scopes:
            logger.warning("api_authorization_denied scope=%s", required_scope.value)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key lacks the required '{required_scope.value}' scope.",
            )

        resource_guard.check_rate_limit(principal.subject, operation_name)
        resource_guard.acquire_operation(principal.subject, operation_name)
        try:
            yield principal
        finally:
            resource_guard.release_operation(principal.subject, operation_name)

    dependency.__name__ = f"require_{operation_name.replace(':', '_')}_access"
    return dependency
