from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.schemas import HealthResponse
from src.api.dependencies import app_state
from src.api.routes import audit, experiments, ingest, search, query

app = FastAPI(
    title="EcoRAG API",
    description="Energy-Efficient Retrieval-Augmented Generation Backend Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

import os

cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [
    origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
] if cors_origins_env else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
]

# Enable CORS for frontend / dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest.router)
app.include_router(search.router)
app.include_router(query.router)
app.include_router(audit.router)
app.include_router(experiments.router)


@app.get("/api/documents", tags=["Ingestion"])
@app.get("/api/v1/documents", tags=["Ingestion"])
def list_documents():
    grouped: dict[str, dict] = {}
    for chunk in app_state.chunks:
        meta = chunk.metadata or {}
        doc_id = chunk.doc_id
        entry = grouped.setdefault(
            doc_id,
            {
                "id": doc_id,
                "fileName": meta.get("filename") or doc_id,
                "fileSizeFormatted": "",
                "chunkCount": 0,
                "embeddingModel": getattr(app_state.embedder, "model_name", app_state.embedder.provider),
                "status": "Indexed",
                "indexingProgress": 100.0,
                "indexedAt": None,
                "indexingEnergyJoules": 0.0,
            },
        )
        entry["chunkCount"] += 1
    return list(grouped.values())


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def get_health():
    """System health check, active embedding dimensionality, and reranker bypass statistics."""
    manifest = app_state.index_manifest or {}
    return HealthResponse(
        status="healthy",
        total_indexed_chunks=app_state.vector_store.total_vectors,
        active_embedding_dimension=app_state.embedder.dimension,
        embedding_provider=app_state.embedder.provider,
        reranker_model=app_state.reranker.model_name,
        reranker_bypass_rate=round(app_state.reranker.bypass_rate, 1),
        index_persisted=app_state.index_store.enabled and app_state.vector_store.total_vectors > 0,
        index_loaded_from_disk=app_state.index_loaded_from_disk,
        dataset_hash=manifest.get("dataset_hash"),
    )


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to the EcoRAG API",
        "docs_url": "/docs",
        "health_url": "/api/health"
    }
