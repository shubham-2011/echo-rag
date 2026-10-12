from pathlib import PurePath

from src.security.config import SECURITY_CONFIG, SecurityConfig
from src.security.models import SecurityAction, SecurityDecision, SecurityRiskLevel


class InputGuard:
    def __init__(self, config: SecurityConfig = SECURITY_CONFIG):
        self.config = config

    def check_query(self, query: str) -> SecurityDecision:
        if not query.strip():
            return self._deny("Query must not be empty.", "input.query.empty")
        if len(query) > self.config.max_query_chars:
            return self._deny("Query exceeds the configured length limit.", "input.query.length")
        if self._contains_disallowed_controls(query):
            return self._deny("Query contains unsupported control characters.", "input.query.controls")
        return self._allow("Query input passed validation.", "input.query.valid")

    def check_document(self, text: str, document_id: str) -> SecurityDecision:
        if not text.strip():
            return self._deny("Document text must not be empty.", "input.document.empty")
        if len(text) > self.config.max_document_chars:
            return self._deny("Document exceeds the configured text limit.", "input.document.length")
        if self._contains_disallowed_controls(text):
            return self._deny("Document contains unsupported control characters.", "input.document.controls")
        if not document_id or len(document_id) > self.config.max_doc_id_chars:
            return self._deny("Document identifier is empty or too long.", "input.document.id")
        if (
            document_id in {".", ".."}
            or "/" in document_id
            or "\\" in document_id
            or self._contains_disallowed_controls(document_id)
        ):
            return self._deny("Document identifier contains unsafe characters.", "input.document.id")
        return self._allow("Document input passed validation.", "input.document.valid")

    def check_upload(
        self,
        filename: str,
        content_size: int,
        chunk_size: int,
        chunk_overlap: int,
        content_type: str | None = None,
    ) -> SecurityDecision:
        if not filename or len(filename) > self.config.max_filename_chars:
            return self._deny("Filename is empty or exceeds the configured limit.", "input.upload.filename")
        if (
            filename in {".", ".."}
            or PurePath(filename).name != filename
            or "/" in filename
            or "\\" in filename
            or self._contains_disallowed_controls(filename)
        ):
            return self._deny("Filename contains unsafe path or control characters.", "input.upload.filename")
        extension = PurePath(filename).suffix.lower()
        if extension not in self.config.allowed_file_extensions:
            return self._deny("Uploaded file type is not supported.", "input.upload.type")
        accepted_types = {
            ".pdf": {"application/pdf", "application/x-pdf"},
            ".doc": {"application/msword"},
            ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
            ".txt": {"text/plain"},
            ".md": {"text/markdown", "text/x-markdown", "text/plain"},
            ".csv": {"text/csv", "application/csv", "text/plain"},
        }
        if content_type and content_type.lower() not in accepted_types.get(extension, set()) | {
            "application/octet-stream"
        }:
            return self._deny("Uploaded content type does not match a supported document type.", "input.upload.content_type")
        if content_size <= 0:
            return self._deny("Uploaded file is empty.", "input.upload.empty")
        if content_size > self.config.max_upload_bytes:
            return self._deny("Uploaded file exceeds the configured size limit.", "input.upload.size")
        if chunk_size < self.config.min_chunk_size or chunk_size > self.config.max_chunk_size:
            return self._deny("Chunk size is outside the configured bounds.", "input.chunk.size")
        if chunk_overlap < 0 or chunk_overlap > self.config.max_chunk_overlap or chunk_overlap >= chunk_size:
            return self._deny("Chunk overlap is outside the configured bounds.", "input.chunk.overlap")
        return self._allow("Upload input passed validation.", "input.upload.valid")

    @staticmethod
    def _contains_disallowed_controls(value: str) -> bool:
        if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            return True
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            return True
        return False

    @staticmethod
    def _allow(reason: str, rule_id: str) -> SecurityDecision:
        return SecurityDecision(
            allowed=True,
            action=SecurityAction.ALLOW,
            risk_level=SecurityRiskLevel.LOW,
            reason=reason,
            rule_id=rule_id,
        )

    @staticmethod
    def _deny(reason: str, rule_id: str) -> SecurityDecision:
        return SecurityDecision(
            allowed=False,
            action=SecurityAction.DENY,
            risk_level=SecurityRiskLevel.HIGH,
            reason=reason,
            rule_id=rule_id,
        )
