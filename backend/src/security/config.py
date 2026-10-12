import os
import math
from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class SecurityConfig:
    max_query_chars: int = 20_000
    max_document_chars: int = 5_000_000
    max_upload_bytes: int = 25 * 1024 * 1024
    max_request_bytes: int = 32 * 1024 * 1024
    max_filename_chars: int = 255
    max_doc_id_chars: int = 200
    min_chunk_size: int = 10
    max_chunk_size: int = 4096
    max_chunk_overlap: int = 2048
    parse_timeout_seconds: float = 15.0
    model_timeout_seconds: float = 30.0
    rate_limit_window_seconds: int = 60
    auth_requests_per_window: int = 30
    query_requests_per_window: int = 30
    search_requests_per_window: int = 60
    ingestion_requests_per_window: int = 10
    max_concurrent_queries: int = 4
    max_concurrent_searches: int = 8
    max_concurrent_ingestions: int = 2
    max_concurrent_parses: int = 2
    allowed_file_extensions: FrozenSet[str] = field(
        default_factory=lambda: frozenset({".pdf", ".doc", ".docx", ".txt", ".md", ".csv"})
    )

    def __post_init__(self) -> None:
        positive_limits = (
            self.max_query_chars,
            self.max_document_chars,
            self.max_upload_bytes,
            self.max_request_bytes,
            self.max_filename_chars,
            self.max_doc_id_chars,
            self.min_chunk_size,
            self.max_chunk_size,
            self.parse_timeout_seconds,
            self.model_timeout_seconds,
            self.rate_limit_window_seconds,
            self.auth_requests_per_window,
            self.query_requests_per_window,
            self.search_requests_per_window,
            self.ingestion_requests_per_window,
            self.max_concurrent_queries,
            self.max_concurrent_searches,
            self.max_concurrent_ingestions,
            self.max_concurrent_parses,
        )
        if any(limit <= 0 for limit in positive_limits):
            raise ValueError("Security size and chunk limits must be positive.")
        if not math.isfinite(self.parse_timeout_seconds) or not math.isfinite(self.model_timeout_seconds):
            raise ValueError("Security timeouts must be finite values.")
        if self.max_chunk_overlap < 0 or self.max_chunk_overlap >= self.max_chunk_size:
            raise ValueError("max_chunk_overlap must be non-negative and less than max_chunk_size.")
        if not self.allowed_file_extensions:
            raise ValueError("At least one supported document extension is required.")

    @classmethod
    def from_environment(cls) -> "SecurityConfig":
        return cls(
            max_query_chars=int(os.getenv("SECURITY_MAX_QUERY_CHARS", "20000")),
            max_document_chars=int(os.getenv("SECURITY_MAX_DOCUMENT_CHARS", "5000000")),
            max_upload_bytes=int(os.getenv("SECURITY_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024))),
            max_request_bytes=int(os.getenv("SECURITY_MAX_REQUEST_BYTES", str(32 * 1024 * 1024))),
            max_filename_chars=int(os.getenv("SECURITY_MAX_FILENAME_CHARS", "255")),
            max_doc_id_chars=int(os.getenv("SECURITY_MAX_DOC_ID_CHARS", "200")),
            min_chunk_size=int(os.getenv("SECURITY_MIN_CHUNK_SIZE", "10")),
            max_chunk_size=int(os.getenv("SECURITY_MAX_CHUNK_SIZE", "4096")),
            max_chunk_overlap=int(os.getenv("SECURITY_MAX_CHUNK_OVERLAP", "2048")),
            parse_timeout_seconds=float(os.getenv("SECURITY_PARSE_TIMEOUT_SECONDS", "15")),
            model_timeout_seconds=float(os.getenv("SECURITY_MODEL_TIMEOUT_SECONDS", "30")),
            rate_limit_window_seconds=int(os.getenv("SECURITY_RATE_LIMIT_WINDOW_SECONDS", "60")),
            auth_requests_per_window=int(os.getenv("SECURITY_AUTH_REQUESTS_PER_WINDOW", "30")),
            query_requests_per_window=int(os.getenv("SECURITY_QUERY_REQUESTS_PER_WINDOW", "30")),
            search_requests_per_window=int(os.getenv("SECURITY_SEARCH_REQUESTS_PER_WINDOW", "60")),
            ingestion_requests_per_window=int(os.getenv("SECURITY_INGESTION_REQUESTS_PER_WINDOW", "10")),
            max_concurrent_queries=int(os.getenv("SECURITY_MAX_CONCURRENT_QUERIES", "4")),
            max_concurrent_searches=int(os.getenv("SECURITY_MAX_CONCURRENT_SEARCHES", "8")),
            max_concurrent_ingestions=int(os.getenv("SECURITY_MAX_CONCURRENT_INGESTIONS", "2")),
            max_concurrent_parses=int(os.getenv("SECURITY_MAX_CONCURRENT_PARSES", "2")),
        )


SECURITY_CONFIG = SecurityConfig.from_environment()
