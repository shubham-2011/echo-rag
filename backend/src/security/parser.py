import asyncio
import logging
import threading
from collections.abc import Callable

from fastapi import HTTPException, status

from src.ingestion import extract_text_from_bytes
from src.security.config import SECURITY_CONFIG, SecurityConfig

_parse_slots = threading.BoundedSemaphore(SECURITY_CONFIG.max_concurrent_parses)
logger = logging.getLogger(__name__)


def _release_parse_slot(future: asyncio.Future[str]) -> None:
    try:
        error = future.exception()
        if error is not None:
            logger.warning(
                "document_parser_failed_after_timeout error_type=%s",
                type(error).__name__,
            )
    except asyncio.CancelledError:
        pass
    finally:
        _parse_slots.release()


async def extract_text_with_limits(
    file_bytes: bytes,
    filename: str,
    *,
    parser: Callable[[bytes, str], str] = extract_text_from_bytes,
    config: SecurityConfig = SECURITY_CONFIG,
) -> str:
    if len(file_bytes) > config.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Uploaded file exceeds the configured size limit.",
        )
    if not _parse_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Document parser is at capacity; retry later.",
            headers={"Retry-After": "1"},
        )

    loop = asyncio.get_running_loop()
    parse_future = loop.run_in_executor(None, parser, file_bytes, filename)
    release_slot = True
    try:
        return await asyncio.wait_for(
            asyncio.shield(parse_future),
            timeout=config.parse_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        release_slot = False
        parse_future.add_done_callback(_release_parse_slot)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Document parsing exceeded the configured time limit.",
        ) from exc
    finally:
        if release_slot:
            _parse_slots.release()
