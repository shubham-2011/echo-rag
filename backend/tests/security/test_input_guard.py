from src.security.config import SecurityConfig
from src.security.input_guard import InputGuard


def test_query_limits_and_control_characters():
    guard = InputGuard(SecurityConfig(max_query_chars=12))

    assert guard.check_query("normal query").allowed
    assert not guard.check_query("query is too long").allowed
    assert not guard.check_query("bad\x00query").allowed
    assert not guard.check_query("   ").allowed


def test_document_identifier_and_size_validation():
    guard = InputGuard(SecurityConfig(max_document_chars=10))

    assert guard.check_document("short text", "doc-1").allowed
    assert not guard.check_document("this text is too long", "doc-1").allowed
    assert not guard.check_document("short text", "..\\secrets.txt").allowed


def test_upload_validation_rejects_unsafe_and_unsupported_inputs():
    guard = InputGuard(SecurityConfig(max_upload_bytes=4))

    assert guard.check_upload("report.txt", 4, 10, 0, "text/plain").allowed
    assert not guard.check_upload("../report.txt", 1, 10, 0, "text/plain").allowed
    assert not guard.check_upload("script.exe", 1, 10, 0, "application/octet-stream").allowed
    assert not guard.check_upload("report.pdf", 5, 10, 0, "application/pdf").allowed
    assert not guard.check_upload("report.txt", 1, 10, 10, "text/plain").allowed
    assert not guard.check_upload("report.pdf", 1, 10, 0, "text/plain").allowed
