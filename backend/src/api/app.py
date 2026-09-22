from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.schemas import HealthResponse
from src.api.dependencies import app_state
from src.api.routes import ingest, search, query

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


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def get_health():
    """System health check, active embedding dimensionality, and reranker bypass statistics."""
    return HealthResponse(
        status="healthy",
        total_indexed_chunks=app_state.vector_store.total_vectors,
        active_embedding_dimension=app_state.embedder.dimension,
        embedding_provider=app_state.embedder.provider,
        reranker_model=app_state.reranker.model_name,
        reranker_bypass_rate=round(app_state.reranker.bypass_rate, 1)
    )


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to the EcoRAG API",
        "docs_url": "/docs",
        "health_url": "/api/health"
    }
