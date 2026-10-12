import asyncio
import threading
import time

import pytest
from fastapi import HTTPException

from src.security.config import SecurityConfig
from src.security.parser import extract_text_with_limits
from src.security.request_limits import RequestBodyLimitMiddleware
from src.security.resource_controls import ResourceGuard


def test_rate_limit_returns_429_and_retry_after():
    guard = ResourceGuard(
        SecurityConfig(
            query_requests_per_window=1,
            rate_limit_window_seconds=60,
        )
    )

    guard.check_rate_limit("user-a", "query")
    with pytest.raises(HTTPException) as error:
        guard.check_rate_limit("user-a", "query")

    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"]
    guard.check_rate_limit("user-b", "query")


def test_api_search_route_enforces_rate_limit(monkeypatch):
    from fastapi.testclient import TestClient

    import src.security.auth as auth_module
    from src.api.app import app
    from conftest import TEST_AUTH_HEADERS

    monkeypatch.setattr(
        auth_module,
        "resource_guard",
        ResourceGuard(SecurityConfig(search_requests_per_window=1)),
    )
    client = TestClient(app, headers=TEST_AUTH_HEADERS)

    first = client.post("/api/search", json={"query": "energy", "mode": "sparse"})
    second = client.post("/api/search", json={"query": "energy", "mode": "sparse"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"]


def test_failed_authentication_attempts_are_rate_limited(monkeypatch):
    from fastapi.testclient import TestClient

    import src.security.auth as auth_module
    from src.api.app import app

    monkeypatch.setattr(
        auth_module,
        "resource_guard",
        ResourceGuard(SecurityConfig(auth_requests_per_window=1)),
    )
    client = TestClient(app)

    first = client.post("/api/search", json={"query": "energy"})
    second = client.post("/api/search", json={"query": "energy"})

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.headers["retry-after"]


def test_concurrency_is_limited_globally_and_per_subject():
    guard = ResourceGuard(SecurityConfig(max_concurrent_queries=2))

    guard.acquire_operation("user-a", "query")
    with pytest.raises(HTTPException) as same_user_error:
        guard.acquire_operation("user-a", "query")
    guard.acquire_operation("user-b", "query")
    with pytest.raises(HTTPException) as global_error:
        guard.acquire_operation("user-c", "query")

    assert same_user_error.value.status_code == 429
    assert global_error.value.status_code == 429
    guard.release_operation("user-a", "query")
    guard.release_operation("user-b", "query")


def test_request_body_middleware_rejects_declared_oversize():
    config = SecurityConfig(max_request_bytes=4)
    app_called = False

    async def inner_app(scope, receive, send):
        nonlocal app_called
        app_called = True

    async def receive():
        return {"type": "http.request", "body": b""}

    messages = []

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "headers": [(b"content-length", b"5")],
    }
    asyncio.run(RequestBodyLimitMiddleware(inner_app, config)(scope, receive, send))

    assert not app_called
    assert messages[0]["status"] == 413


def test_request_body_middleware_counts_chunked_stream_bytes():
    config = SecurityConfig(max_request_bytes=4)

    async def inner_app(scope, receive, send):
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        return {"type": "http.request", "body": b"12345", "more_body": False}

    messages = []

    async def send(message):
        messages.append(message)

    asyncio.run(RequestBodyLimitMiddleware(inner_app, config)({"type": "http", "headers": []}, receive, send))

    assert messages[0]["status"] == 413


def test_parser_rejects_oversize_and_times_out_without_releasing_busy_slot_early(monkeypatch):
    import src.security.parser as parser_module

    monkeypatch.setattr(parser_module, "_parse_slots", threading.BoundedSemaphore(1))

    async def check():
        with pytest.raises(HTTPException) as oversize_error:
            await extract_text_with_limits(
                b"123",
                "small.txt",
                parser=lambda _data, _name: "not run",
                config=SecurityConfig(max_upload_bytes=2),
            )
        assert oversize_error.value.status_code == 413

        def slow_parser(_data, _name):
            time.sleep(0.1)
            return "finished"

        with pytest.raises(HTTPException) as timeout_error:
            await extract_text_with_limits(
                b"x",
                "slow.txt",
                parser=slow_parser,
                config=SecurityConfig(parse_timeout_seconds=0.01),
            )
        assert timeout_error.value.status_code == 504

        with pytest.raises(HTTPException) as capacity_error:
            await extract_text_with_limits(b"x", "queued.txt", parser=lambda *_: "ok")
        assert capacity_error.value.status_code == 429

        await asyncio.sleep(0.12)
        assert await extract_text_with_limits(b"x", "done.txt", parser=lambda *_: "ok") == "ok"

    asyncio.run(check())
