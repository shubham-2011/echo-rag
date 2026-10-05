"""Persist and reload FAISS vectors, chunk metadata, and BM25 corpus."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.audit.canonicalizer import hash_payload
from src.ingestion import Chunk
from src.vector_store import FAISSVectorStore

if TYPE_CHECKING:
    from src.api.dependencies import AppState

logger = logging.getLogger(__name__)

MANIFEST_FILE = "index_manifest.json"
INDEX_NAME = "faiss_index"


def compute_dataset_hash(chunks: list[Chunk]) -> str:
    """Stable hash over sorted full-text SHA-256 digests of indexed chunks."""
    digests = sorted(
        hash_payload(chunk.text.strip())[1]
        for chunk in chunks
        if chunk.text.strip()
    )
    _, digest = hash_payload({"chunks_sha256": digests, "count": len(digests)})
    return digest


class IndexStore:
    def __init__(self, directory: str | Path | None = None):
        default = Path(__file__).resolve().parents[2] / "data" / "index"
        configured = os.getenv("ECORAG_INDEX_DIR")
        self.directory = Path(directory or configured or default)
        self.enabled = os.getenv("ECORAG_INDEX_PERSIST", "true").lower() not in {"0", "false", "no"}

    def manifest_path(self) -> Path:
        return self.directory / MANIFEST_FILE

    def save(self, state: AppState) -> dict[str, Any] | None:
        if not self.enabled or state.vector_store.total_vectors == 0:
            return None
        self.directory.mkdir(parents=True, exist_ok=True)
        state.vector_store.save(str(self.directory), INDEX_NAME)
        manifest = {
            "schema_version": "1",
            "embedding_provider": state.embedder.provider,
            "embedding_dimension": state.embedder.dimension,
            "embedding_model": getattr(state.embedder, "model_name", None),
            "chunk_count": len(state.chunks),
            "dataset_hash": compute_dataset_hash(state.chunks),
        }
        self.manifest_path().write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        logger.info("Persisted %s chunks to %s", manifest["chunk_count"], self.directory)
        return manifest

    def load(self, state: AppState) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        index_bin = self.directory / f"{INDEX_NAME}.bin"
        meta_json = self.directory / f"{INDEX_NAME}_meta.json"
        if not index_bin.is_file() or not meta_json.is_file() or not self.manifest_path().is_file():
            return None
        with self.manifest_path().open(encoding="utf-8") as handle:
            manifest = json.load(handle)
        if manifest.get("embedding_dimension") != state.embedder.dimension:
            logger.warning(
                "Skipping index load: saved dimension %s != active %s",
                manifest.get("embedding_dimension"),
                state.embedder.dimension,
            )
            return None
        if manifest.get("embedding_provider") != state.embedder.provider:
            logger.warning(
                "Skipping index load: saved provider %s != active %s",
                manifest.get("embedding_provider"),
                state.embedder.provider,
            )
            return None
        loaded = FAISSVectorStore.load(str(self.directory), INDEX_NAME)
        state.vector_store = loaded
        state.chunks = list(loaded.chunks)
        from src.retrieval import BM25Retriever

        state.bm25_retriever = BM25Retriever(state.chunks) if state.chunks else None
        logger.info("Loaded %s chunks from %s", len(state.chunks), self.directory)
        return manifest

    def clear(self) -> None:
        if not self.directory.exists():
            return
        for name in (MANIFEST_FILE, f"{INDEX_NAME}.bin", f"{INDEX_NAME}_meta.json"):
            path = self.directory / name
            if path.is_file():
                path.unlink()
        logger.info("Cleared persisted index at %s", self.directory)
