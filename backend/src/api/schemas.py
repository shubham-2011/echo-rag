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
    index_persisted: bool = False
    index_loaded_from_disk: bool = False
    dataset_hash: Optional[str] = None


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
    filename: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    retrieval_score: Optional[float] = None
    rerank_score: Optional[float] = None


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
    session_id: Optional[str] = Field(default=None, description="Conversation/session identifier for trace correlation.")
    turn: int = Field(default=1, ge=1, description="Conversation turn number.")
    doc_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional document scope filter; when set, retrieval is limited to these doc_ids.",
    )


class TelemetryMetrics(BaseModel):
    request_id: str = Field(..., description="Correlation ID for this query (matches logs and X-Request-ID).")
    latency_ms: float
    peak_ram_mb: float
    estimated_wh: float
    energy_source: str = Field(
        default="ESTIMATED",
        description="MEASURED | ESTIMATED | CALCULATED | UNAVAILABLE — how energy_wh was derived.",
    )
    measurement_type: str = Field(
        default="estimated",
        description="measured | estimated — whether stage/total energy was measured or estimated.",
    )
    rerank_bypassed: bool
    eco_score: float
    cache_tier: Optional[str] = "MISS"
    complexity: Optional[str] = None
    attention_work_ratio: Optional[float] = None
    context_tokens: Optional[int] = None
    estimated_joules: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    stage_timings_ms: Optional[Dict[str, float]] = None
    stage_energy_j: Optional[Dict[str, float]] = None
    grounding_passed: Optional[bool] = None
    retrieved_count: Optional[int] = None
    baseline_joules: Optional[float] = None
    saved_joules: Optional[float] = None
    reduction_percent: Optional[float] = None


class QueryResponse(BaseModel):
    request_id: str
    query: str
    answer: str
    citations: List[SearchHit]
    telemetry: TelemetryMetrics
    trace: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional pipeline trace when ECORAG_EXPOSE_TRACE=true.",
    )


# --- Audit / Provenance Schemas ---
class AuditAnchorRequest(BaseModel):
    """A complete record kept off-chain and committed by its SHA-256 hash."""
    entity_type: str = Field(default="experiment", min_length=1, max_length=100)
    entity_id: str = Field(..., min_length=1, max_length=255)
    payload: Dict[str, Any] = Field(..., description="JSON-safe experiment, document, or benchmark record.")
    schema_version: str = Field(default="1", min_length=1, max_length=32)


class AuditBatchAnchorRequest(BaseModel):
    records: List[AuditAnchorRequest] = Field(..., min_length=1, max_length=500)


class AuditVerifyRequest(BaseModel):
    """Optional current payload. Omit it to verify the stored record itself."""
    payload: Optional[Dict[str, Any]] = None
    entity_type: str = Field(default="experiment", min_length=1, max_length=100)


class AuditAnchorResponse(BaseModel):
    audit_record_id: str
    entity_type: str
    entity_id: str
    payload_hash: str
    merkle_root: str
    anchor_type: str
    block_number: int
    block_hash: str
    transaction_hash: Optional[str] = None
    status: str
    anchored_at: str


class AuditVerificationResponse(BaseModel):
    entity_type: str
    entity_id: str
    database_hash: str
    anchored_hash: str
    merkle_root: str
    calculated_merkle_root: str
    block_number: int
    anchor_type: str
    verified: bool
    status: str


class MerkleProofItem(BaseModel):
    position: str
    hash: str


class AuditProofResponse(BaseModel):
    entity_type: str
    entity_id: str
    payload_hash: str
    leaf_index: int
    proof: List[MerkleProofItem]
    merkle_root: str
    block_number: int
    anchor_type: str
    verified: bool


# --- Experiment lifecycle schemas ---
class ExperimentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    dataset: Dict[str, Any] = Field(..., description="Frozen dataset identity or benchmark snapshot.")
    configuration: Dict[str, Any] = Field(..., description="Frozen effective pipeline configuration.")


class ExperimentCompleteRequest(BaseModel):
    result: Dict[str, Any] = Field(..., description="Aggregate experiment result metrics.")
    telemetry: Dict[str, Any] = Field(default_factory=dict, description="Telemetry summary for the run.")
    environment: Dict[str, Any] = Field(default_factory=dict, description="Git, runtime, and model metadata.")


class ExperimentRunResponse(BaseModel):
    experiment_id: str
    name: str
    status: str
    dataset: Dict[str, Any]
    configuration: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    telemetry: Optional[Dict[str, Any]] = None
    manifest: Optional[Dict[str, Any]] = None
    manifest_hash: Optional[str] = None
    audit: Optional[AuditAnchorResponse] = None
    failure_reason: Optional[str] = None
    created_at: str
    updated_at: str

