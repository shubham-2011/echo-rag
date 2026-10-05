"""On-disk FAISS index and corpus persistence."""

from .index_store import IndexStore, compute_dataset_hash

__all__ = ["IndexStore", "compute_dataset_hash"]
