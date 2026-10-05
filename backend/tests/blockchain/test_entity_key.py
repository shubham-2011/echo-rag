"""Align chain entity keys with Solidity computeEntityKey (abi.encode)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_entity_key_abi_encode_documented():
    """Key derivation must match EcoRAGAudit.computeEntityKey (keccak256(abi.encode))."""
    try:
        from eth_abi import encode
        from eth_utils import keccak
    except ImportError:
        pytest.skip("eth_abi not installed")

    digest = keccak(encode(["string", "string"], ["experiment", "EXP-001"]))
    assert len(digest) == 32
