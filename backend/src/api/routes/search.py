import time
from fastapi import APIRouter, HTTPException
from src.api.schemas import SearchRequest, SearchResponse, SearchHit, RerankTelemetry, AdaptiveTelemetry
from src.api.dependencies import app_state

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
def search_corpus(payload: SearchRequest):
    """
    Search the indexed corpus using Sparse BM25, Dense FAISS, Hybrid RRF, or Adaptive routing.
    Optionally applies threshold-gated reranking to save compute.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    start_time = time.perf_counter()
    mode = payload.mode.lower()

    adaptive_info = None

    if mode == "adaptive":
        adaptive_retriever = app_state.get_adaptive_retriever()
        adaptive_res = adaptive_retriever.search(
            query=payload.query,
            top_k=payload.top_k,
            use_cache=True,
            apply_dynamic_filter=True
        )
        candidates = adaptive_res.hits
        adaptive_info = AdaptiveTelemetry(
            complexity=adaptive_res.complexity.value,
            cache_tier=adaptive_res.cache_tier,
            cache_similarity=adaptive_res.cache_similarity,
            retrieval_mode_chosen=adaptive_res.retrieval_mode_chosen,
            energy_saving_reason=adaptive_res.energy_saving_reason,
            pruned_chunks=adaptive_res.pruned_candidate_count
        )

        # If retrieved from L1/L2 cache, skip reranking entirely!
        if adaptive_res.cache_tier != "MISS":
            final_hits = candidates[:payload.top_k]
            rerank_info = RerankTelemetry(
                bypassed=True,
                reason=f"Cached retrieval ({adaptive_res.cache_tier}) bypassed cross-encoder."
            )
        else:
            if payload.enable_rerank and candidates:
                rerank_result = app_state.reranker.rerank(
                    query=payload.query,
                    candidates=candidates,
                    top_k=payload.top_k
                )
                final_hits = rerank_result.ranked_chunks
                rerank_info = RerankTelemetry(
                    bypassed=rerank_result.bypassed,
                    reason=rerank_result.reason
                )
            else:
                final_hits = candidates[:payload.top_k]
                rerank_info = None

    elif mode == "sparse":
        retriever = app_state.get_bm25_retriever()
        candidates = retriever.search(payload.query, top_k=payload.top_k * 2)
        rerank_info = None
        if payload.enable_rerank and candidates:
            rerank_result = app_state.reranker.rerank(
                query=payload.query,
                candidates=candidates,
                top_k=payload.top_k
            )
            final_hits = rerank_result.ranked_chunks
            rerank_info = RerankTelemetry(
                bypassed=rerank_result.bypassed,
                reason=rerank_result.reason
            )
        else:
            final_hits = candidates[:payload.top_k]

    elif mode == "dense":
        retriever = app_state.get_dense_retriever()
        candidates = retriever.search(payload.query, top_k=payload.top_k * 2)
        rerank_info = None
        if payload.enable_rerank and candidates:
            rerank_result = app_state.reranker.rerank(
                query=payload.query,
                candidates=candidates,
                top_k=payload.top_k
            )
            final_hits = rerank_result.ranked_chunks
            rerank_info = RerankTelemetry(
                bypassed=rerank_result.bypassed,
                reason=rerank_result.reason
            )
        else:
            final_hits = candidates[:payload.top_k]

    elif mode == "hybrid":
        retriever = app_state.get_hybrid_retriever()
        candidates = retriever.search(payload.query, top_k=payload.top_k * 2)
        rerank_info = None
        if payload.enable_rerank and candidates:
            rerank_result = app_state.reranker.rerank(
                query=payload.query,
                candidates=candidates,
                top_k=payload.top_k
            )
            final_hits = rerank_result.ranked_chunks
            rerank_info = RerankTelemetry(
                bypassed=rerank_result.bypassed,
                reason=rerank_result.reason
            )
        else:
            final_hits = candidates[:payload.top_k]

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported retrieval mode '{payload.mode}'.")

    latency_ms = (time.perf_counter() - start_time) * 1000.0

    hits = [
        SearchHit(
            chunk_id=c.chunk_id,
            doc_id=c.doc_id,
            text=c.text,
            score=round(score, 4),
            rank=rank
        )
        for rank, (c, score) in enumerate(final_hits, 1)
    ]

    return SearchResponse(
        query=payload.query,
        mode=payload.mode,
        hits=hits,
        rerank_telemetry=rerank_info,
        adaptive_telemetry=adaptive_info,
        latency_ms=round(latency_ms, 2)
    )

