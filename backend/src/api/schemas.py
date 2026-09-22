from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


# --- Health Schemas ---
class HealthResponse(BaseModel):
    status: str
    total_indexed_chunks: int
    active_embedding_dimension: int
    embedding_provider: str
    reranker_model: str
    reranker_bypass_rate: float


# --- Ingestion Schemas ---
class IngestTextRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=5_000_000,
        description="Document content to ingest and index (max 5MB text payload)."
    )
    doc_id: str = Field(default="doc_default", description="Identifier for source document.")
    chunk_size: int = Field(
        default=50,
        ge=10,
        le=4096,
        description="Chunk size in words (must be between 10 and 4096)."
    )
    chunk_overlap: int = Field(
        default=10,
        ge=0,
        le=2048,
        description="Chunk overlap in words (must be non-negative and less than chunk_size)."
    )
    enable_dedup: bool = Field(default=True, description="Whether to filter near-duplicate chunks.")
    strategy: str = Field(default="standard", description="Ingestion strategy: 'standard', 'sentence_window', or 'markdown'.")
    window_size: int = Field(default=2, ge=0, le=10, description="Default sentence expansion window.")

    @model_validator(mode="after")
    def validate_overlap(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be strictly less than chunk_size ({self.chunk_size})"
            )
        return self


class IngestResponse(BaseModel):
    doc_id: str
    total_chunks_produced: int
    unique_chunks_indexed: int
    deduplicated_count: int
    total_vectors_in_store: int


# --- Search Schemas ---
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string.")
    mode: str = Field(default="hybrid", description="Retrieval mode: 'adaptive', 'dense', 'sparse', or 'hybrid'.")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of candidate chunks to return (1 to 100).")
    enable_rerank: bool = Field(default=True, description="Whether to apply threshold-gated reranking.")


class SearchHit(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float
    rank: int


class RerankTelemetry(BaseModel):
    bypassed: bool
    reason: str


class AdaptiveTelemetry(BaseModel):
    complexity: str
    cache_tier: str
    cache_similarity: Optional[float] = None
    retrieval_mode_chosen: str
    energy_saving_reason: str
    pruned_chunks: int = 0


class SearchResponse(BaseModel):
    query: str
    mode: str
    hits: List[SearchHit]
    rerank_telemetry: Optional[RerankTelemetry] = None
    adaptive_telemetry: Optional[AdaptiveTelemetry] = None
    latency_ms: float


# --- Query / Generation Schemas ---
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question to be answered by EcoRAG.")
    retrieval_mode: str = Field(default="adaptive", description="'adaptive', 'dense', 'sparse', or 'hybrid'.")
    top_k: int = Field(default=3, ge=1, le=50, description="Number of context chunks to retrieve (1 to 50).")
    max_tokens: int = Field(default=200, ge=10, le=2048, description="Maximum completion tokens to generate.")
    context_strategy: str = Field(default="sentence_window", description="Context expansion strategy: 'standard', 'sentence_window', or 'parent_document'.")
    window_size: int = Field(default=2, ge=0, le=10, description="Sentence window expansion radius (+/- W sentences).")


class TelemetryMetrics(BaseModel):
    latency_ms: float
    peak_ram_mb: float
    estimated_wh: float
    rerank_bypassed: bool
    eco_score: float
    cache_tier: Optional[str] = "MISS"
    complexity: Optional[str] = None
    attention_work_ratio: Optional[float] = None
    context_tokens: Optional[int] = None
    estimated_joules: Optional[float] = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[SearchHit]
    telemetry: TelemetryMetrics

