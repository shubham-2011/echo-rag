from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class SecurityAction(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    SANITIZE = "SANITIZE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    TERMINATE = "TERMINATE"


class SecurityRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SecurityInputSource(str, Enum):
    DIRECT_USER_INPUT = "DIRECT_USER_INPUT"
    RETRIEVED_DOCUMENT = "RETRIEVED_DOCUMENT"
    SYSTEM_INSTRUCTION = "SYSTEM_INSTRUCTION"


class SecurityTrustLevel(str, Enum):
    UNTRUSTED = "UNTRUSTED"


class SecurityStatus(str, Enum):
    SCANNED = "SCANNED"
    REVIEW = "REVIEW"


class SecurityViolation(BaseModel):
    code: str
    message: str
    risk_level: SecurityRiskLevel


class SecurityDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: bool
    action: SecurityAction
    risk_level: SecurityRiskLevel
    reason: str
    rule_id: str
    violations: tuple[SecurityViolation, ...] = ()


class SecurityContext(BaseModel):
    source: SecurityInputSource
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str | None = None


class SecurityEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    context: SecurityContext
    decision: SecurityDecision


class DocumentSecurityMetadata(BaseModel):
    document_id: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: str
    owner: str | None = None
    trust_level: SecurityTrustLevel = SecurityTrustLevel.UNTRUSTED
    security_status: SecurityStatus
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    findings: tuple[SecurityViolation, ...] = ()
