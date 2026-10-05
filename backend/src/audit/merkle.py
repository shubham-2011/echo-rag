"""Small, dependency-free Merkle tree helpers for audit batches."""

from __future__ import annotations

from typing import Iterable

from .canonicalizer import sha256_hex


def merkle_root(leaf_hashes: Iterable[str]) -> str:
    """Calculate a deterministic SHA-256 Merkle root from hexadecimal leaves.

    The final leaf is duplicated on odd-sized levels, a common convention
    which keeps verification deterministic without storing filler records.
    """
    level = list(leaf_hashes)
    if not level:
        raise ValueError("Cannot create a Merkle root without audit records.")

    for leaf in level:
        if len(leaf) != 64:
            raise ValueError("Merkle leaves must be SHA-256 hexadecimal hashes.")

    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [sha256_hex(left + right) for left, right in zip(level[::2], level[1::2])]
    return level[0]


def merkle_proof(leaf_hashes: Iterable[str], leaf_index: int) -> list[dict[str, str]]:
    """Return the deterministic sibling path for one leaf in a Merkle tree."""
    level = list(leaf_hashes)
    if not level:
        raise ValueError("Cannot create a Merkle proof without audit records.")
    if leaf_index < 0 or leaf_index >= len(level):
        raise ValueError("Merkle leaf index is out of range.")
    if any(len(leaf) != 64 for leaf in level):
        raise ValueError("Merkle leaves must be SHA-256 hexadecimal hashes.")

    index = leaf_index
    proof: list[dict[str, str]] = []
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sibling_index = index - 1 if index % 2 else index + 1
        proof.append({
            "position": "left" if sibling_index < index else "right",
            "hash": level[sibling_index],
        })
        level = [sha256_hex(left + right) for left, right in zip(level[::2], level[1::2])]
        index //= 2
    return proof


def verify_merkle_proof(leaf_hash: str, proof: Iterable[dict[str, str]], root: str) -> bool:
    """Verify a proof produced by :func:`merkle_proof` without database access."""
    if len(leaf_hash) != 64 or len(root) != 64:
        return False
    current = leaf_hash
    for item in proof:
        sibling = item.get("hash", "")
        position = item.get("position")
        if len(sibling) != 64 or position not in {"left", "right"}:
            return False
        current = sha256_hex(sibling + current if position == "left" else current + sibling)
    return current == root
