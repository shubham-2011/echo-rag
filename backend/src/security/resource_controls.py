import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

from src.security.config import SECURITY_CONFIG, SecurityConfig

logger = logging.getLogger(__name__)


class ResourceGuard:
    def __init__(self, config: SecurityConfig = SECURITY_CONFIG):
        self.config = config
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._global_active: dict[str, int] = defaultdict(int)
        self._subject_active: dict[tuple[str, str], int] = defaultdict(int)

    def check_rate_limit(self, subject: str, operation: str) -> None:
        now = time.monotonic()
        key = (subject, operation)
        max_requests = self._request_limit(operation)
        with self._lock:
            requests = self._requests[key]
            cutoff = now - self.config.rate_limit_window_seconds
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= max_requests:
                retry_after = max(1, int(requests[0] + self.config.rate_limit_window_seconds - now))
                logger.warning("api_rate_limit_denied operation=%s", operation)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Request rate limit exceeded.",
                    headers={"Retry-After": str(retry_after)},
                )
            requests.append(now)

    def acquire_operation(self, subject: str, operation: str) -> None:
        key = (subject, operation)
        with self._lock:
            global_limit = self._concurrency_limit(operation)
            per_subject_limit = max(1, global_limit // 2)
            if (
                self._global_active[operation] >= global_limit
                or self._subject_active[key] >= per_subject_limit
            ):
                logger.warning("api_concurrency_limit_denied operation=%s", operation)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Concurrent operation limit reached; retry later.",
                    headers={"Retry-After": "1"},
                )
            self._global_active[operation] += 1
            self._subject_active[key] += 1

    def release_operation(self, subject: str, operation: str) -> None:
        key = (subject, operation)
        with self._lock:
            self._global_active[operation] = max(0, self._global_active[operation] - 1)
            self._subject_active[key] = max(0, self._subject_active[key] - 1)
            if self._subject_active[key] == 0:
                del self._subject_active[key]

    def _request_limit(self, operation: str) -> int:
        return {
            "auth": self.config.auth_requests_per_window,
            "query": self.config.query_requests_per_window,
            "search": self.config.search_requests_per_window,
            "ingestion": self.config.ingestion_requests_per_window,
        }.get(operation, self.config.search_requests_per_window)

    def _concurrency_limit(self, operation: str) -> int:
        return {
            "query": self.config.max_concurrent_queries,
            "search": self.config.max_concurrent_searches,
            "ingestion": self.config.max_concurrent_ingestions,
            "parse": self.config.max_concurrent_parses,
        }.get(operation, self.config.max_concurrent_searches)


resource_guard = ResourceGuard()
