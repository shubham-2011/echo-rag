"""Canonical JSON and deterministic hashing utilities."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    """Return the stable JSON representation used for all audit hashes.

    Keys are sorted and insignificant whitespace is removed, so equivalent
    JSON objects always produce the same bytes and SHA-256 digest.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def hash_payload(payload: Any) -> tuple[str, str]:
    """Return ``(canonical_json, sha256_hex)`` for a JSON-compatible value."""
    encoded = canonical_json(payload)
    return encoded, sha256_hex(encoded)
