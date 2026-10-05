"""BC-MERKLE-* Merkle tree tests."""

import pytest

from src.audit.canonicalizer import sha256_hex
from src.audit.merkle import merkle_proof, merkle_root, verify_merkle_proof

pytestmark = pytest.mark.unit


def _leaf(label: str) -> str:
    return sha256_hex(label)


def test_bc_merkle_001_single_record():
    root = merkle_root([_leaf("only")])
    assert len(root) == 64


def test_bc_merkle_002_two_records_deterministic():
    leaves = [_leaf("a"), _leaf("b")]
    assert merkle_root(leaves) == merkle_root(leaves)


def test_bc_merkle_004_modify_one_leaf_changes_root():
    leaves = [_leaf("a"), _leaf("b"), _leaf("c")]
    root = merkle_root(leaves)
    tampered = [_leaf("a"), _leaf("b-changed"), _leaf("c")]
    assert merkle_root(tampered) != root


def test_bc_merkle_007_proof_verifies():
    leaves = [_leaf("q1"), _leaf("q2"), _leaf("q3")]
    root = merkle_root(leaves)
    proof = merkle_proof(leaves, 1)
    assert verify_merkle_proof(leaves[1], proof, root)


def test_bc_merkle_008_invalid_proof_fails():
    leaves = [_leaf("q1"), _leaf("q2")]
    root = merkle_root(leaves)
    bad_proof = [{"position": "left", "hash": _leaf("wrong")}]
    assert verify_merkle_proof(leaves[0], bad_proof, root) is False


def test_bc_merkle_empty_raises():
    with pytest.raises(ValueError):
        merkle_root([])
