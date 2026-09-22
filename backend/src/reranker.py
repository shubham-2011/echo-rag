from typing import List, Tuple, Optional
from dataclasses import dataclass

from src.ingestion import Chunk


@dataclass
class RerankResult:
    """Encapsulates reranker output and green-computing bypass telemetry."""
    ranked_chunks: List[Tuple[Chunk, float]]
    bypassed: bool
    reason: str


class ThresholdGatedReranker:
    """
    Green-computing conditional reranker for EcoRAG.
    Evaluates retriever candidate confidence scores:
      - If Candidate #1 exceeds high confidence AND margin over #2, bypasses Cross-Encoder.
      - If scores are clustered or ambiguous, fires Cross-Encoder on Top candidate subset.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        confidence_threshold: float = 0.85,
        margin_threshold: float = 0.12,
        device: str = "cpu"
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.margin_threshold = margin_threshold
        self.device = device
        self._cross_encoder = None

        # Telemetry counters
        self.total_queries = 0
        self.bypassed_queries = 0

    @property
    def cross_encoder(self):
        """Lazy-load CrossEncoder to avoid memory allocation until actually needed."""
        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder
            self._cross_encoder = CrossEncoder(self.model_name, device=self.device)
        return self._cross_encoder

    def rerank(
        self,
        query: str,
        candidates: List[Tuple[Chunk, float]],
        top_k: int = 3,
        max_rerank_pool: int = 8
    ) -> RerankResult:
        """
        Conditionally reranks candidates based on score confidence.
        """
        self.total_queries += 1

        if not candidates:
            return RerankResult(ranked_chunks=[], bypassed=True, reason="Empty candidates")

        # If only 1 candidate, no reranking needed
        if len(candidates) == 1:
            self.bypassed_queries += 1
            return RerankResult(
                ranked_chunks=candidates[:top_k],
                bypassed=True,
                reason="Single candidate, rerank bypassed"
            )

        top1_score = candidates[0][1]
        top2_score = candidates[1][1]
        margin = top1_score - top2_score

        # Check gating condition for bypass
        if top1_score >= self.confidence_threshold and margin >= self.margin_threshold:
            self.bypassed_queries += 1
            return RerankResult(
                ranked_chunks=candidates[:top_k],
                bypassed=True,
                reason=f"High confidence ({top1_score:.3f}) and margin ({margin:.3f}) bypassed cross-encoder."
            )

        # Ambiguous confidence or small margin -> Fire Cross-Encoder on top candidates
        eval_candidates = candidates[:max_rerank_pool]
        pairs = [(query, c.text) for c, _ in eval_candidates]

        ce_scores = self.cross_encoder.predict(pairs)

        # Pair candidates with their new cross-encoder scores
        reranked = [
            (eval_candidates[i][0], float(ce_scores[i]))
            for i in range(len(eval_candidates))
        ]
        reranked.sort(key=lambda x: x[1], reverse=True)

        if top1_score < self.confidence_threshold:
            trigger_reason = f"Top-1 score ({top1_score:.3f}) below confidence threshold ({self.confidence_threshold:.2f})."
        else:
            trigger_reason = f"Margin ({margin:.3f}) below threshold ({self.margin_threshold:.2f})."

        return RerankResult(
            ranked_chunks=reranked[:top_k],
            bypassed=False,
            reason=f"{trigger_reason} Cross-Encoder reranking executed."
        )

    @property
    def bypass_rate(self) -> float:
        """Percentage of queries that successfully bypassed the cross-encoder."""
        if self.total_queries == 0:
            return 0.0
        return (self.bypassed_queries / self.total_queries) * 100.0
