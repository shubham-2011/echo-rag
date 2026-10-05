"""Tamper-evident provenance services for EcoRAG records.

This package deliberately keeps detailed RAG data off-chain.  It canonicalizes
records locally, persists their hashes, and can later hand only a Merkle root
to a blockchain adapter.
"""

from .service import AuditService

__all__ = ["AuditService"]
