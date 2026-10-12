import json
import logging

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.security.config import SECURITY_CONFIG, SecurityConfig

logger = logging.getLogger(__name__)


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, config: SecurityConfig = SECURITY_CONFIG):
        self.app = app
        self.max_request_bytes = config.max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = next(
            (value for name, value in scope.get("headers", []) if name.lower() == b"content-length"),
            None,
        )
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError:
                await self._reject(send, "Invalid Content-Length.")
                return
            if declared_length < 0:
                await self._reject(send, "Invalid Content-Length.")
                return
            if declared_length > self.max_request_bytes:
                logger.warning("request_body_rejected reason=content_length_limit")
                await self._reject(send, "Request body exceeds the configured size limit.")
                return

        received_bytes = 0
        oversized = False

        async def receive_limited() -> Message:
            nonlocal received_bytes, oversized
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_request_bytes:
                    oversized = True
                    return {"type": "http.disconnect"}
            return message

        async def send_limited(message: Message) -> None:
            if not oversized:
                await send(message)

        try:
            await self.app(scope, receive_limited, send_limited)
        except Exception:
            if not oversized:
                raise
        if oversized:
            logger.warning("request_body_rejected reason=stream_size_limit")
            await self._reject(send, "Request body exceeds the configured size limit.")

    @staticmethod
    async def _reject(send: Send, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})
