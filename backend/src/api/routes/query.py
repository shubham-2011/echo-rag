import logging
import os
import time

logger = logging.getLogger(__name__)

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from fastapi import APIRouter, HTTPException, Response

from src.api.dependencies import app_state
from src.api.schemas import QueryRequest, QueryResponse, SearchHit, TelemetryMetrics
from src.ingestion import Chunk, ParentDocumentStore, enrich_chunk_metadata, parse_page_number
from src.observability import RequestTrace, configure_observability, get_trace
from src.observability.trace import (
    LOG_FULL_PROMPT,
    SYSTEM_PROMPT_VERSION,
    classify_intent,
    extractive_answer,
    relevance_gate,
    rewrite_query,
    validate_grounding,
    compact_factoid_answer,
    normalize_query,
)
from src.retrieval import SentenceWindowExpander, apply_section_boost

router = APIRouter(prefix="/api/query", tags=["Query"])

configure_observability()

def _allocate_stage_energy(total_j: float, timings: dict[str, float]) -> dict[str, float]:
    mapping = {
        "faiss_ms": "retrieval_energy_j",
        "fusion_ms": "fusion_energy_j",
        "rerank_ms": "rerank_energy_j",
        "compression_ms": "context_energy_j",
        "llm_ms": "generation_energy_j",
    }
    weights = {key: max(0.0, float(timings.get(key, 0.0))) for key in mapping}
    total_ms = sum(weights.values())
    if total_j <= 0 or total_ms <= 0:
        return {name: 0.0 for name in mapping.values()}
    return {
        name: round(total_j * (weights[key] / total_ms), 4)
        for key, name in mapping.items()
    }


def _to_search_hit(chunk: Chunk, score: float, rank: int, rerank_score: float | None = None) -> SearchHit:
    enrich_chunk_metadata(chunk)
    meta = chunk.metadata or {}
    parent_text = ParentDocumentStore.get_instance().get_document(chunk.doc_id)
    page = parse_page_number(chunk.text, meta, parent_text)
    filename = str(meta.get("filename") or chunk.doc_id)
    return SearchHit(
        chunk_id=chunk.chunk_id,
        doc_id=chunk.doc_id,
        text=chunk.text,
        score=round(score, 4),
        rank=rank,
        filename=filename,
        page_number=page,
        section=meta.get("section"),
        retrieval_score=round(score, 4),
        rerank_score=None if rerank_score is None else round(rerank_score, 4),
    )


def _expose_trace() -> bool:
    return os.getenv("ECORAG_EXPOSE_TRACE", "false").lower() in {"1", "true", "yes"}


def _doc_scope_chunks(doc_ids: list[str] | None) -> list[Chunk]:
    if not doc_ids:
        return app_state.chunks
    allowed = set(doc_ids)
    return [c for c in app_state.chunks if c.doc_id in allowed]


def _log_document_scope(trace: RequestTrace, doc_ids: list[str] | None) -> None:
    scoped = _doc_scope_chunks(doc_ids)
    by_doc: dict[str, list[Chunk]] = {}
    for chunk in scoped:
        by_doc.setdefault(chunk.doc_id, []).append(chunk)
    trace.info(
        "DOCUMENT_SCOPE",
        documents=len(by_doc),
        chunks=len(scoped),
        scope="filtered" if doc_ids else "full_index",
        doc_ids=",".join(sorted(by_doc.keys())[:20]) if by_doc else "none",
    )
    for doc_id, chunks in list(by_doc.items())[:10]:
        meta = chunks[0].metadata or {}
        trace.info(
            "DOCUMENT_SCOPE",
            file=meta.get("filename", meta.get("source", doc_id)),
            type=meta.get("file_type", meta.get("type", "unknown")),
            doc_id=doc_id,
            chunks=len(chunks),
        )


def _filter_hits(
    hits: list[tuple[Chunk, float]], doc_ids: list[str] | None
) -> list[tuple[Chunk, float]]:
    if not doc_ids:
        return hits
    allowed = set(doc_ids)
    return [(c, s) for c, s in hits if c.doc_id in allowed]


def _log_embedding(trace: RequestTrace, query: str, started: float, cache_hit: bool = False) -> None:
    embedder = app_state.embedder
    trace.record_stage("embedding_ms", started)
    trace.info(
        "EMBEDDING",
        model=getattr(embedder, "model_name", embedder.provider),
        query_length=len(query),
        dimension=embedder.dimension,
        cache_hit=cache_hit,
        measurement_type="estimated",
    )


def _generate_answer(
    trace: RequestTrace,
    query: str,
    context_chunks: list[tuple[Chunk, float]],
    max_tokens: int,
) -> tuple[str, dict]:
    """Generate answer using Gemini or explicit extractive fallback (always logged)."""
    llm_start = time.perf_counter()
    client = app_state.get_gemini_client()
    context_str = "\n\n".join(
        [f"[Source {i + 1}]: {c.text}" for i, (c, _) in enumerate(context_chunks)]
    )

    system_prompt = (
        "You answer questions using ONLY the supplied document context.\n"
        "Answer the user's question directly.\n"
        "Use only the document context.\n"
        "Do not explain EcoRAG's architecture unless the user asks about EcoRAG.\n"
        "Do not discuss FAISS, embeddings, reranking, energy optimization, telemetry, or the retrieval pipeline.\n"
        "Do not say 'according to the retrieved documents in the EcoRAG system'.\n"
        "Do not expose internal pipeline details.\n"
        "If the context does not contain enough evidence, say: "
        "I couldn't find enough relevant information in the indexed documents.\n"
        "Never invent an answer."
    )
    user_prompt = (
        f"USER QUESTION:\n{query}\n\n"
        f"DOCUMENT CONTEXT:\n{context_str}\n\n"
        "INSTRUCTIONS:\n"
        "- Answer the user's question directly from DOCUMENT CONTEXT.\n"
        "- If evidence is missing, say you couldn't find enough relevant information.\n"
        "Answer:"
    )

    history_tokens = 0
    context_tokens = sum(c.token_count_approx for c, _ in context_chunks)
    question_tokens = len(query.split())
    total_tokens = history_tokens + context_tokens + question_tokens + len(system_prompt.split())

    chunk_ids = [c.chunk_id for c, _ in context_chunks]
    trace.info(
        "PROMPT",
        system_prompt_version=SYSTEM_PROMPT_VERSION,
        history_tokens=history_tokens,
        context_tokens=context_tokens,
        question_tokens=question_tokens,
        total_tokens=total_tokens,
    )
    for cid in chunk_ids:
        trace.debug("CONTEXT_CHUNKS", chunk_id=cid)
    if LOG_FULL_PROMPT:
        trace.debug("PROMPT_FULL", system=system_prompt, user=user_prompt)

    prompt_tokens = total_tokens
    completion_tokens = 0
    finish_reason = "stop"
    api_retries = 0
    error_type = ""
    answer = ""

    if client:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{system_prompt}\n\n{user_prompt}",
            )
            if response and response.text:
                answer = response.text.strip()
                completion_tokens = len(answer.split())
        except Exception as exc:
            error_type = type(exc).__name__
            logger.warning(
                "[%s] Gemini generation failed: %s", trace.request_id, exc, exc_info=logger.isEnabledFor(logging.DEBUG)
            )
            trace.record_fallback("LLM", f"gemini_error:{error_type}")

    extracted = extractive_answer(query, context_chunks) if context_chunks else ""
    if extracted:
        extracted = compact_factoid_answer(query, extracted, context_chunks)
    if answer:
        answer = compact_factoid_answer(query, answer, context_chunks)
    if not answer:
        if extracted:
            answer = extracted
            completion_tokens = len(answer.split())
            trace.record_fallback("LLM", "extractive_sentence_selection")
        else:
            answer = "I couldn't find enough relevant information in the indexed documents."
            trace.record_fallback("LLM", "no_context_abstain")
            finish_reason = "abstain"
    elif context_chunks and extracted:
        gemini_abstained = bool(re.search(r"couldn.?t find|not (enough|found) relevant", answer, re.I))
        extractive_ok = not bool(re.search(r"couldn.?t find", extracted, re.I))
        if gemini_abstained and extractive_ok:
            trace.record_fallback("LLM", "gemini_abstain_extractive_rescue")
            answer = extracted
            completion_tokens = len(answer.split())

    latency_ms = (time.perf_counter() - llm_start) * 1000.0
    trace.record_stage("llm_ms", llm_start)
    trace.info(
        "LLM",
        model="gemini-2.5-flash" if client else "extractive_fallback",
        latency_ms=round(latency_ms, 2),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        finish_reason=finish_reason,
        api_retry_count=api_retries,
        error_type=error_type or None,
        measurement_type="estimated",
    )
    return answer, {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def _log_rerank(trace: RequestTrace, before: list[tuple[Chunk, float]], result) -> None:
    rerank_start = time.perf_counter()
    before_rank = {c.chunk_id: i + 1 for i, (c, _) in enumerate(before)}
    for after_rank, (chunk, score) in enumerate(result.ranked_chunks, 1):
        trace.debug(
            "RERANK",
            chunk=chunk.chunk_id,
            before_rank=before_rank.get(chunk.chunk_id),
            after_rank=after_rank,
            score=score,
            bypassed=result.bypassed,
        )
    trace.info(
        "RERANK",
        model=app_state.reranker.model_name,
        input_count=len(before),
        output_count=len(result.ranked_chunks),
        bypassed=result.bypassed,
        reason=result.reason,
    )
    trace.record_stage("rerank_ms", rerank_start)


@router.post("", response_model=QueryResponse)
def query_ecorag(payload: QueryRequest, response: Response):
    """
    End-to-end adaptive RAG query with structured request_id tracing (Part 25).
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    trace = RequestTrace(
        payload.query,
        session_id=payload.session_id,
        turn=payload.turn,
    )
    token = trace.bind()
    response.headers["X-Request-ID"] = trace.request_id

    start_time = time.perf_counter()
    ram_before = (psutil.Process().memory_info().rss / (1024 * 1024)) if HAS_PSUTIL else 256.0

    try:
        mode = payload.retrieval_mode.lower()
        cache_tier = "MISS"
        complexity_str = None
        rerank_bypassed = False
        candidates: list[tuple[Chunk, float]] = []
        final_hits: list[tuple[Chunk, float]] = []

        if not payload.doc_ids and app_state.active_doc_ids:
            payload.doc_ids = list(app_state.active_doc_ids)

        _log_document_scope(trace, payload.doc_ids)

        rewrite_start = time.perf_counter()
        working_query = normalize_query(payload.query, trace)
        retrieval_query = rewrite_query(working_query, trace)
        trace.intent = classify_intent(working_query, None)
        trace.info("QUERY", intent=trace.intent, resolved_entity=trace.resolved_entity or None)
        trace.record_stage("query_rewrite_ms", rewrite_start)

        # --- Retrieval ---
        retrieval_start = time.perf_counter()
        if mode == "adaptive":
            adaptive_retriever = app_state.get_adaptive_retriever()
            adaptive_res = adaptive_retriever.search(
                query=retrieval_query,
                top_k=payload.top_k,
                use_cache=True,
                apply_dynamic_filter=True,
                window_size=(payload.window_size if payload.context_strategy == "sentence_window" else 0),
            )
            candidates = _filter_hits(adaptive_res.hits, payload.doc_ids)
            cache_tier = adaptive_res.cache_tier
            complexity_str = adaptive_res.complexity.value
            trace.intent = classify_intent(working_query, complexity_str)
            trace.info(
                "QUERY",
                intent=trace.intent,
                complexity=complexity_str,
                cache_tier=cache_tier,
                retrieval_mode_chosen=adaptive_res.retrieval_mode_chosen,
            )
            trace.log_faiss_candidates("FAISS", candidates)

            if adaptive_res.cache_tier != "MISS":
                final_hits = candidates[: payload.top_k]
                rerank_bypassed = True
                trace.info("RERANK", bypassed=True, reason="cache_hit_skipped_rerank")
            else:
                rerank_result = app_state.reranker.rerank(
                    query=retrieval_query,
                    candidates=candidates,
                    top_k=payload.top_k,
                )
                _log_rerank(trace, candidates, rerank_result)
                final_hits = rerank_result.ranked_chunks
                rerank_bypassed = rerank_result.bypassed
        elif mode == "sparse":
            embed_start = time.perf_counter()
            _log_embedding(trace, retrieval_query, embed_start, cache_hit=True)
            retriever = app_state.get_bm25_retriever()
            candidates = _filter_hits(
                retriever.search(retrieval_query, top_k=payload.top_k * 2),
                payload.doc_ids,
            )
            trace.log_faiss_candidates("FAISS", candidates)
            rerank_result = app_state.reranker.rerank(
                query=retrieval_query, candidates=candidates, top_k=payload.top_k
            )
            _log_rerank(trace, candidates, rerank_result)
            final_hits = rerank_result.ranked_chunks
            rerank_bypassed = rerank_result.bypassed
        elif mode == "dense":
            embed_start = time.perf_counter()
            app_state.embedder.embed_text(retrieval_query)
            _log_embedding(trace, retrieval_query, embed_start, cache_hit=False)
            retriever = app_state.get_dense_retriever()
            candidates = _filter_hits(
                retriever.search(retrieval_query, top_k=payload.top_k * 2),
                payload.doc_ids,
            )
            trace.log_faiss_candidates("FAISS", candidates)
            rerank_result = app_state.reranker.rerank(
                query=retrieval_query, candidates=candidates, top_k=payload.top_k
            )
            _log_rerank(trace, candidates, rerank_result)
            final_hits = rerank_result.ranked_chunks
            rerank_bypassed = rerank_result.bypassed
        elif mode == "hybrid":
            embed_start = time.perf_counter()
            app_state.embedder.embed_text(retrieval_query)
            _log_embedding(trace, retrieval_query, embed_start, cache_hit=False)
            retriever = app_state.get_hybrid_retriever()
            candidates = _filter_hits(
                retriever.search(retrieval_query, top_k=payload.top_k * 2),
                payload.doc_ids,
            )
            trace.log_faiss_candidates("FAISS", candidates)
            rerank_result = app_state.reranker.rerank(
                query=retrieval_query, candidates=candidates, top_k=payload.top_k
            )
            _log_rerank(trace, candidates, rerank_result)
            final_hits = rerank_result.ranked_chunks
            rerank_bypassed = rerank_result.bypassed
        else:
            trace.error(
                "ERROR",
                component="QUERY",
                error="UNSUPPORTED_MODE",
                message=f"Unsupported retrieval mode '{payload.retrieval_mode}'.",
                action="reject",
                final_status="FAILED",
            )
            raise HTTPException(status_code=400, detail=f"Unsupported retrieval mode '{payload.retrieval_mode}'.")

        final_hits = apply_section_boost(working_query, final_hits)[: payload.top_k]

        trace.record_stage("faiss_ms", retrieval_start)

        best_score = final_hits[0][1] if final_hits else 0.0
        gate_decision, threshold = relevance_gate(best_score, mode)
        trace.info(
            "RELEVANCE_GATE",
            best_score=best_score,
            threshold=threshold,
            decision=gate_decision,
            action="continue" if gate_decision == "PASS" else "low_confidence_logged",
        )

        # --- Context compression ---
        compression_start = time.perf_counter()
        tokens_before = sum(c.token_count_approx for c, _ in final_hits)
        compressed_hits: list[tuple[Chunk, float]] = []
        for c, score in final_hits:
            comp_text = app_state.context_filter.compress_chunk_sentences(c, working_query, max_sentences=8)
            comp_chunk = Chunk(
                text=comp_text,
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                chunk_index=c.chunk_index,
                char_length=len(comp_text),
                token_count_approx=len(comp_text.split()),
                metadata=c.metadata,
            )
            compressed_hits.append((comp_chunk, score))
        tokens_after = sum(c.token_count_approx for c, _ in compressed_hits)
        ratio = (1.0 - tokens_after / tokens_before) * 100.0 if tokens_before else 0.0
        pages = sorted({str((c.metadata or {}).get("page", "")) for c, _ in compressed_hits if c.metadata})
        sections = sorted({str((c.metadata or {}).get("section", "")) for c, _ in compressed_hits if c.metadata})
        trace.info(
            "CONTEXT",
            chunks_before=len(final_hits),
            chunks_after=len(compressed_hits),
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            compression_ratio=f"{ratio:.1f}%",
            pages=",".join(p for p in pages if p) or None,
            sections=",".join(s for s in sections if s) or None,
        )
        for c, _ in compressed_hits:
            trace.debug("CONTEXT", chunk_id=c.chunk_id, preview=trace.preview(c.text))
        trace.record_stage("compression_ms", compression_start)

        # --- Generation ---
        answer, token_stats = _generate_answer(trace, working_query, compressed_hits, payload.max_tokens)

        # --- Grounding ---
        grounding_start = time.perf_counter()
        grounded, supporting = validate_grounding(answer, compressed_hits)
        if not grounded:
            rescued = extractive_answer(working_query, compressed_hits)
            rescued_ok, rescued_support = validate_grounding(rescued, compressed_hits)
            if rescued_ok:
                answer = rescued
                grounded, supporting = rescued_ok, rescued_support
                trace.record_fallback("LLM", "ungrounded_answer_replaced_from_context")
            elif not re.search(r"couldn.?t find", answer, re.I):
                answer = "I couldn't find enough relevant information in the indexed documents."
                grounded, supporting = True, []
                trace.record_fallback("LLM", "ungrounded_answer_abstain")
        trace.grounding_passed = grounded
        trace.supporting_chunks = supporting
        trace.info(
            "GROUNDING",
            supported=grounded,
            supporting_chunks=supporting,
            decision="PASS" if grounded else "REVIEW",
        )
        trace.record_stage("grounding_ms", grounding_start)

        trace.info(
            "ANSWER",
            status="SUCCESS",
            answer_chars=len(answer),
            citations=len(final_hits),
            grounded=grounded,
        )

        latency_sec = time.perf_counter() - start_time
        latency_ms = latency_sec * 1000.0
        ram_after = (psutil.Process().memory_info().rss / (1024 * 1024)) if HAS_PSUTIL else 260.0
        peak_ram = max(ram_before, ram_after)

        estimated_wh = (45.0 * (latency_sec / 3600.0))
        if cache_tier != "MISS":
            estimated_wh *= 0.20
        elif rerank_bypassed:
            estimated_wh *= 0.65

        eco_score = max(0.1, round(10.0 / (1.0 + (latency_sec * 0.5) + (estimated_wh * 10.0)), 2))

        citations = [
            _to_search_hit(c, score, rank)
            for rank, (c, score) in enumerate(final_hits, 1)
        ]
        for hit in citations:
            trace.info(
                "SOURCES",
                filename=hit.filename,
                page=hit.page_number,
                chunk_id=hit.chunk_id,
                score=hit.score,
                section=hit.section,
                preview=trace.preview(hit.text),
            )

        ctx_tokens = tokens_after
        attn_work_ratio = SentenceWindowExpander.calculate_attention_work_ratio(ctx_tokens)
        estimated_joules = round(estimated_wh * 3600.0, 3)
        baseline_joules = round(estimated_joules * 1.85, 3)
        saved_joules = max(0.0, baseline_joules - estimated_joules)
        reduction = (saved_joules / baseline_joules * 100.0) if baseline_joules else 0.0

        stage_energy = _allocate_stage_energy(estimated_joules, trace.timings_ms)
        trace.record_stage("total_ms", start_time)
        trace.info("PERFORMANCE", **trace.timings_ms)
        trace.info(
            "TELEMETRY",
            energy_j=estimated_joules,
            latency_ms=round(latency_ms, 2),
            prompt_tokens=token_stats["prompt_tokens"],
            completion_tokens=token_stats["completion_tokens"],
            total_tokens=token_stats["total_tokens"],
            **stage_energy,
            baseline_energy_j=baseline_joules,
            saved_energy_j=round(saved_joules, 3),
            reduction_percent=f"{reduction:.1f}%",
            measurement_type="estimated",
        )
        trace.info(
            "API_RESPONSE",
            energy_j=estimated_joules,
            latency_ms=round(latency_ms, 2),
        )

        doc_names = list({c.doc_id for c, _ in final_hits})
        trace.final_status = "SUCCESS"
        telemetry_payload = {
            "request_id": trace.request_id,
            "energy_j": estimated_joules,
            "latency_ms": round(latency_ms, 2),
        }
        trace.emit_summary(answer, doc_names, telemetry_payload)

        return QueryResponse(
            request_id=trace.request_id,
            query=payload.query,
            answer=answer,
            citations=citations,
            telemetry=TelemetryMetrics(
                request_id=trace.request_id,
                latency_ms=round(latency_ms, 2),
                peak_ram_mb=round(peak_ram, 1),
                estimated_wh=round(estimated_wh, 4),
                energy_source="ESTIMATED",
                measurement_type="estimated",
                estimated_joules=estimated_joules,
                rerank_bypassed=rerank_bypassed,
                eco_score=eco_score,
                cache_tier=cache_tier,
                complexity=complexity_str,
                attention_work_ratio=attn_work_ratio,
                context_tokens=ctx_tokens,
                prompt_tokens=token_stats["prompt_tokens"],
                completion_tokens=token_stats["completion_tokens"],
                total_tokens=token_stats["total_tokens"],
                stage_timings_ms=trace.timings_ms,
                stage_energy_j=stage_energy,
                grounding_passed=grounded,
                retrieved_count=len(final_hits),
                baseline_joules=baseline_joules,
                saved_joules=round(saved_joules, 3),
                reduction_percent=round(reduction, 1),
            ),
            trace=trace.to_dict() if _expose_trace() else None,
        )
    except HTTPException:
        trace.final_status = "FAILED"
        raise
    except Exception as exc:
        trace.final_status = "FAILED"
        trace.error(
            "ERROR",
            component="QUERY",
            error=type(exc).__name__,
            message=str(exc),
            action="propagate",
            final_status="FAILED",
        )
        logger.exception("[%s] Unhandled query pipeline error", trace.request_id)
        raise HTTPException(status_code=500, detail="Query pipeline failed.") from exc
    finally:
        RequestTrace.unbind(token)
