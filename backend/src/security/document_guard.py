import hashlib

from src.security.injection_detector import InjectionDetector
from src.security.models import (
    DocumentSecurityMetadata,
    SecurityInputSource,
    SecurityStatus,
    SecurityViolation,
)


class DocumentGuard:
    def __init__(self, injection_detector: InjectionDetector | None = None):
        self.injection_detector = injection_detector or InjectionDetector()

    def inspect(
        self,
        content: str,
        document_id: str,
        source: str,
        owner: str | None = None,
        raw_content: bytes | None = None,
    ) -> DocumentSecurityMetadata:
        scan = self.injection_detector.inspect(content, SecurityInputSource.RETRIEVED_DOCUMENT)
        findings: tuple[SecurityViolation, ...] = scan.violations
        digest_input = raw_content if raw_content is not None else content.encode("utf-8")
        return DocumentSecurityMetadata(
            document_id=document_id,
            sha256=hashlib.sha256(digest_input).hexdigest(),
            source=source,
            owner=owner,
            security_status=SecurityStatus.REVIEW if findings else SecurityStatus.SCANNED,
            findings=findings,
        )
