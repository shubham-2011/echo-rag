from fastapi.testclient import TestClient

from src.api.app import app
from src.security.auth import ApiScope, AuthenticatedPrincipal
from src.security.tool_policy import ToolPolicy
from conftest import TEST_API_KEY, TEST_AUTH_HEADERS


def test_api_key_authentication_is_required_for_read_and_write_routes():
    client = TestClient(app)

    missing = client.post("/api/search", json={"query": "energy"})
    invalid = client.post(
        "/api/search",
        headers={"Authorization": "Bearer wrong-api-key"},
        json={"query": "energy"},
    )
    valid = client.post("/api/search", headers=TEST_AUTH_HEADERS, json={"query": "energy"})

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert invalid.status_code == 401
    assert valid.status_code == 200


def test_api_returns_service_unavailable_when_key_is_not_configured(monkeypatch):
    monkeypatch.delenv("ECORAG_API_KEY")
    client = TestClient(app)

    response = client.post(
        "/api/search",
        headers=TEST_AUTH_HEADERS,
        json={"query": "energy"},
    )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_scopes_restrict_write_routes_but_leave_configured_read_access(monkeypatch):
    monkeypatch.setenv("ECORAG_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("ECORAG_API_SCOPES", "read")
    client = TestClient(app, headers=TEST_AUTH_HEADERS)

    read_response = client.post("/api/search", json={"query": "energy"})
    write_response = client.post(
        "/api/ingest/text",
        json={"text": "A small document for testing authorization."},
    )

    assert read_response.status_code == 200
    assert write_response.status_code == 403


def test_invalid_scope_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv("ECORAG_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("ECORAG_API_SCOPES", "read,admin")
    client = TestClient(app, headers=TEST_AUTH_HEADERS)

    response = client.post("/api/search", json={"query": "energy"})

    assert response.status_code == 503


def test_invalid_legacy_subject_fails_closed(monkeypatch):
    monkeypatch.setenv("ECORAG_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("ECORAG_API_SCOPES", "read")
    monkeypatch.setenv("ECORAG_API_USER_ID", "../invalid")
    client = TestClient(app, headers=TEST_AUTH_HEADERS)

    response = client.post("/api/search", json={"query": "energy"})

    assert response.status_code == 503


def test_tool_policy_denies_by_default_and_requires_explicit_allowlist_and_scope():
    reader = AuthenticatedPrincipal(subject="reader", scopes=frozenset({ApiScope.READ}))
    tool_operator = AuthenticatedPrincipal(subject="operator", scopes=frozenset({ApiScope.TOOLS_INVOKE}))
    deny_by_default = ToolPolicy()
    explicit_policy = ToolPolicy(allowed_tools=frozenset({"approved.lookup"}))

    assert not deny_by_default.authorize("approved.lookup", tool_operator).allowed
    assert not explicit_policy.authorize("approved.lookup", reader).allowed
    assert explicit_policy.authorize("approved.lookup", tool_operator).allowed
    assert not explicit_policy.authorize("../shell", tool_operator).allowed


def test_model_provider_timeout_is_reported_not_replaced_by_success_shaped_fallback(monkeypatch):
    from fastapi import HTTPException

    from src.api.dependencies import app_state
    from src.api.routes import query as query_route

    class TimeoutModels:
        def generate_content(self, **_kwargs):
            raise TimeoutError("provider timed out")

    client = type("Client", (), {"models": TimeoutModels()})()
    monkeypatch.setattr(app_state, "get_gemini_client", lambda: client)

    try:
        query_route._generate_answer("a valid question", [], 32)
    except HTTPException as error:
        assert error.status_code == 504
    else:
        raise AssertionError("Model timeout must not produce a success-shaped answer.")
