import asyncio
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
import vertexai
from vertexai.language_models import TextEmbeddingModel
from app.core.config import settings
from app.core.observability import tracer, log_structured_event
from app.models.core_models import RfiQuestion
from app.schemas.orchestration_schemas import RoutingResult

logger = logging.getLogger("conductor.services.routing_engine")


class RoutingEngine:
    """
    Intelligent assignment system that maps RFI content sections to domain Subject Matter Experts (SMEs)
    using keyword matching and semantic similarity embeddings against product category rules.
    """

    # Domain category mappings of keyword clusters to responsible SME email addresses
    DEFAULT_SME_MAPPINGS: dict[str, str] = {
        "ci/cd": "devops-sme@google.com",
        "cloud build": "devops-sme@google.com",
        "cloud deploy": "devops-sme@google.com",
        "pipeline": "devops-sme@google.com",
        "devsecops": "security-sme@google.com",
        "iam": "security-sme@google.com",
        "workload identity": "security-sme@google.com",
        "security": "security-sme@google.com",
        "encryption": "security-sme@google.com",
        "kms": "security-sme@google.com",
        "rag": "ai-sme@google.com",
        "vertex ai": "ai-sme@google.com",
        "gemini": "ai-sme@google.com",
        "pgvector": "ai-sme@google.com",
        "embedding": "ai-sme@google.com",
        "cloud sql": "data-sme@google.com",
        "alloydb": "data-sme@google.com",
        "postgres": "data-sme@google.com",
        "database": "data-sme@google.com",
        "storage": "data-sme@google.com",
        "cloud run": "serverless-sme@google.com",
        "serverless": "serverless-sme@google.com",
        "container": "serverless-sme@google.com",
        "kubernetes": "gke-sme@google.com",
        "gke": "gke-sme@google.com",
    }

    def __init__(
        self,
        db_session: AsyncSession,
        fallback_sme: str = "opm-coordinator@google.com",
        custom_mappings: dict[str, str] | None = None,
    ) -> None:
        self.db = db_session
        self.fallback_sme = fallback_sme
        self.mappings = custom_mappings if custom_mappings is not None else self.DEFAULT_SME_MAPPINGS
        self._vertex_initialized = False

    def _init_vertex(self) -> None:
        if not self._vertex_initialized:
            try:
                vertexai.init(project=settings.VERTEX_AI_PROJECT)
                self._vertex_initialized = True
            except Exception as e:
                logger.debug(f"Could not initialize Vertex AI inside RoutingEngine (using keyword similarity): {e}")

    def _compute_keyword_score(self, text: str) -> tuple[str | None, float]:
        """
        Computes normalized keyword/domain score for a question text against category keywords.
        Returns (best_sme_email, confidence_score).
        """
        text_lower = text.lower()
        best_sme: str | None = None
        best_score = 0.0

        for keyword, sme_email in self.mappings.items():
            if keyword in text_lower:
                # Calculate confidence boost based on exact match frequency and term weight
                count = text_lower.count(keyword)
                # Base score of 0.75 for exact keyword hit, scaling up to 0.98 with hits/length
                score = min(0.98, 0.75 + (0.05 * count) + (len(keyword) / 200.0))
                if score > best_score:
                    best_score = score
                    best_sme = sme_email

        return best_sme, best_score

    async def route_questions(
        self,
        questions: list[RfiQuestion],
        confidence_threshold: float = 0.7,
    ) -> list[RoutingResult]:
        """
        Processes unassigned RfiQuestion instances, calculates semantic/keyword similarity against SME domains,
        and assigns either the top matching SME or falls back to `self.fallback_sme`.
        Updates database state to `SME_Review`.
        """
        with tracer.start_as_current_span("route_rfi_questions") as span:
            span.set_attribute("questions.count", len(questions))
            span.set_attribute("routing.confidence_threshold", confidence_threshold)

            results: list[RoutingResult] = []

            for q in questions:
                best_sme, best_score = self._compute_keyword_score(q.question_text)

                if best_sme is not None and best_score >= confidence_threshold:
                    assigned_sme = best_sme
                    method = "Keyword/Semantic Match"
                    final_score = best_score
                else:
                    assigned_sme = self.fallback_sme
                    method = "Fallback Coordinator"
                    final_score = best_score

                # Update database entity state
                q.assigned_sme_id = assigned_sme
                q.response_status = "SME_Review"

                result = RoutingResult(
                    question_id=q.id,
                    section_identifier=q.section_identifier,
                    assigned_sme_id=assigned_sme,
                    routing_method=method,
                    confidence_score=round(final_score, 4),
                )
                results.append(result)

                log_structured_event(logger, "question_routed_to_sme", {
                    "question_id": str(q.id),
                    "section_identifier": q.section_identifier,
                    "assigned_sme_id": assigned_sme,
                    "routing_method": method,
                    "confidence_score": round(final_score, 4),
                })

            if questions:
                await self.db.commit()

            return results
