import logging

from src.security.config import SECURITY_CONFIG, SecurityConfig
from src.security.auth import AuthenticatedPrincipal
from src.security.document_guard import DocumentGuard
from src.security.injection_detector import InjectionDetector
from src.security.input_guard import InputGuard
from src.security.models import (
    DocumentSecurityMetadata,
    SecurityContext,
    SecurityDecision,
    SecurityEvent,
    SecurityInputSource,
)
from src.security.tool_policy import ToolPolicy

logger = logging.getLogger(__name__)


class SecurityGateway:
    def __init__(self, config: SecurityConfig = SECURITY_CONFIG):
        self.input_guard = InputGuard(config)
        self.injection_detector = InjectionDetector()
        self.document_guard = DocumentGuard(self.injection_detector)
        self.tool_policy = ToolPolicy()

    def inspect_query(self, query: str) -> SecurityDecision:
        context = SecurityContext(source=SecurityInputSource.DIRECT_USER_INPUT)
        decision = self.input_guard.check_query(query)
        if decision.allowed:
            decision = self.injection_detector.inspect(query, context.source)
        self._record_event(SecurityEvent(context=context, decision=decision))
        return decision

    def inspect_document(
        self,
        content: str,
        document_id: str,
        source: str,
        owner: str | None = None,
        raw_content: bytes | None = None,
    ) -> tuple[SecurityDecision, DocumentSecurityMetadata | None]:
        context = SecurityContext(
            source=SecurityInputSource.RETRIEVED_DOCUMENT,
            document_id=document_id,
        )
        decision = self.input_guard.check_document(content, document_id)
        metadata = None
        if decision.allowed:
            metadata = self.document_guard.inspect(
                content,
                document_id=document_id,
                source=source,
                owner=owner,
                raw_content=raw_content,
            )
            decision = SecurityDecision(
                allowed=True,
                action=decision.action,
                risk_level=(
                    metadata.findings[0].risk_level
                    if metadata.findings
                    else decision.risk_level
                ),
                reason=(
                    "Document retained and marked for review; retrieved content remains untrusted."
                    if metadata.findings
                    else decision.reason
                ),
                rule_id=(
                    "document.injection.review"
                    if metadata.findings
                    else decision.rule_id
                ),
                violations=metadata.findings,
            )
        self._record_event(SecurityEvent(context=context, decision=decision))
        return decision, metadata

    def inspect_upload(
        self,
        filename: str,
        content: bytes,
        chunk_size: int,
        chunk_overlap: int,
        content_type: str | None = None,
    ) -> SecurityDecision:
        context = SecurityContext(
            source=SecurityInputSource.RETRIEVED_DOCUMENT,
            document_id=filename,
        )
        decision = self.input_guard.check_upload(
            filename=filename,
            content_size=len(content),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            content_type=content_type,
        )
        self._record_event(SecurityEvent(context=context, decision=decision))
        return decision

    def authorize_tool(
        self,
        tool_name: str,
        principal: AuthenticatedPrincipal,
    ) -> SecurityDecision:
        decision = self.tool_policy.authorize(tool_name, principal)
        self._record_event(
            SecurityEvent(
                context=SecurityContext(
                    source=SecurityInputSource.DIRECT_USER_INPUT,
                    request_id=principal.subject,
                ),
                decision=decision,
            )
        )
        return decision

    @staticmethod
    def _record_event(event: SecurityEvent) -> None:
        logger.info(
            "security_event id=%s source=%s action=%s risk=%s rule_id=%s",
            event.event_id,
            event.context.source.value,
            event.decision.action.value,
            event.decision.risk_level.value,
            event.decision.rule_id,
        )
