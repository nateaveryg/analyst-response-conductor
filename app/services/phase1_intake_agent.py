import datetime
import logging
import time
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.observability import tracer, log_structured_event
from app.schemas.inclusion_schemas import (
    ParsedRfiCriteria,
    InclusionEvaluationMatrix,
    FeatureEvaluationResult,
)
from app.schemas.phase1_agent_schemas import (
    DocumentParsingTaskResult,
    CriteriaExtractionTaskResult,
    PortfolioMappingTaskResult,
    GoNoGoDecisionTaskResult,
    Phase1SubAgentTelemetry,
)
from app.services.subagents.rfi_document_parser_agent import RfiDocumentParserSubAgent
from app.services.subagents.criteria_extraction_agent import CriteriaExtractionSubAgent
from app.services.subagents.portfolio_mapping_agent import PortfolioMappingSubAgent
from app.services.subagents.governance_go_no_go_agent import GovernanceGoNoGoSubAgent

logger = logging.getLogger("conductor.services.phase1_intake_agent")


class Phase1IntakeAgentService:
    """
    Lead Phase 1 Intake & Inclusion Orchestrator Agent.
    Orchestrates specialized sub-agents (RfiDocumentParserSubAgent, CriteriaExtractionSubAgent,
    PortfolioMappingSubAgent, GovernanceGoNoGoSubAgent) to perform high-precision intake processing,
    multi-SKU capability aggregation, boundary auditing, and Go/No-Go decision synthesis.
    """

    def __init__(self, db_session: AsyncSession, model_name: str = settings.VERTEX_AI_MODEL) -> None:
        self.db = db_session
        self.model_name = model_name
        self.criteria_extractor = CriteriaExtractionSubAgent(model_name=model_name)

    async def run_phase1_agentic_intake(
        self,
        raw_rfi_input: str
    ) -> tuple[InclusionEvaluationMatrix, List[Phase1SubAgentTelemetry]]:
        """
        Runs the complete multi-agent Phase 1 orchestration workflow:
        1. RfiDocumentParserSubAgent: Parses text/tables/layout hints.
        2. CriteriaExtractionSubAgent: Extracts quantitative parameters, weights, and capabilities.
        3. PortfolioMappingSubAgent: Maps capabilities to GCP SKUs with multi-SKU attribution.
        4. GovernanceGoNoGoSubAgent: Synthesizes formal decision recommendation and waiver requirements.
        """
        with tracer.start_as_current_span("Phase1IntakeAgentService.run_phase1_agentic_intake") as span:
            telemetry_logs: List[Phase1SubAgentTelemetry] = []

            # ------------------------------------------------------------------
            # Sub-Agent 1: RfiDocumentParserSubAgent
            # ------------------------------------------------------------------
            t0 = time.time()
            doc_result = await RfiDocumentParserSubAgent.parse_document(raw_rfi_input)
            t1_ms = (time.time() - t0) * 1000
            telemetry_logs.append(Phase1SubAgentTelemetry(
                agent_name="RfiDocumentParserSubAgent",
                stage="Document Layout & Table Parsing",
                status="completed" if doc_result.status == "success" else "warning",
                duration_ms=round(t1_ms, 2),
                summary_message=f"Parsed {len(doc_result.parsed_layout_blocks)} layout blocks and {len(doc_result.extracted_tables)} table structures."
            ))

            # ------------------------------------------------------------------
            # Sub-Agent 2: CriteriaExtractionSubAgent
            # ------------------------------------------------------------------
            t0 = time.time()
            text_to_extract = doc_result.raw_text_cleaned if doc_result.raw_text_cleaned else raw_rfi_input
            crit_result = await self.criteria_extractor.extract_criteria(text_to_extract)
            t2_ms = (time.time() - t0) * 1000
            telemetry_logs.append(Phase1SubAgentTelemetry(
                agent_name="CriteriaExtractionSubAgent",
                stage="Analyst Rubric & Weight Extraction",
                status="completed" if crit_result.status == "success" else "warning",
                duration_ms=round(t2_ms, 2),
                summary_message=f"Extracted criteria with confidence score {crit_result.confidence_score*100:.0f}%. Found {len(crit_result.parsed_criteria.evaluation_criteria_and_weights)} weighted criteria dimensions."
            ))

            # ------------------------------------------------------------------
            # Sub-Agent 3: PortfolioMappingSubAgent
            # ------------------------------------------------------------------
            t0 = time.time()
            mapping_result = await PortfolioMappingSubAgent.map_portfolio(
                parsed_criteria=crit_result.parsed_criteria,
                db_session=self.db
            )
            t3_ms = (time.time() - t0) * 1000
            telemetry_logs.append(Phase1SubAgentTelemetry(
                agent_name="PortfolioMappingSubAgent",
                stage="GCP Portfolio & GA Corpus Mapping",
                status="completed" if mapping_result.status == "success" else "warning",
                duration_ms=round(t3_ms, 2),
                summary_message=f"Matched {len(mapping_result.matched_products)} SKUs across full GA corpus ({mapping_result.portfolio_ga_coverage_percentage}% coverage)."
            ))

            # ------------------------------------------------------------------
            # Sub-Agent 4: GovernanceGoNoGoSubAgent
            # ------------------------------------------------------------------
            t0 = time.time()
            decision_result = await GovernanceGoNoGoSubAgent.evaluate_decision(
                parsed_criteria=crit_result.parsed_criteria,
                mapping_result=mapping_result
            )
            t4_ms = (time.time() - t0) * 1000
            telemetry_logs.append(Phase1SubAgentTelemetry(
                agent_name="GovernanceGoNoGoSubAgent",
                stage="Executive Decision & Deficit Waiver Audit",
                status="completed" if decision_result.status == "success" else "warning",
                duration_ms=round(t4_ms, 2),
                summary_message=f"Recommendation: {decision_result.recommendation} (Risk Level: {decision_result.risk_level})."
            ))

            # ------------------------------------------------------------------
            # Merge Results into InclusionEvaluationMatrix
            # ------------------------------------------------------------------
            feature_evals = []
            mandatory_met = []
            for attr in mapping_result.capability_attributions:
                feature_evals.append(FeatureEvaluationResult(
                    feature_or_capability_name=attr["feature_description"],
                    status="Met" if attr["status"] == "Met" else "Unmet",
                    matching_products=attr["attributed_skus"],
                    evaluation_notes="Dynamic capability aggregation across universal GA corpus."
                ))
                mandatory_met.append(attr["feature_description"])

            rec_val = "Proceed_With_Participation" if decision_result.recommendation == "Proceed_With_Participation" else "Decline_Due_To_Score_Risk"

            matrix = InclusionEvaluationMatrix(
                eligible_products=[p["name"] for p in mapping_result.matched_products],
                excluded_or_roadmap_products=decision_result.deficit_waivers_required,
                rule_violations=[] if decision_result.financial_thresholds_met else ["Financial threshold deficit: attestation required."],
                data_driven_recommendation=rec_val,
                evaluation_criteria_summary=crit_result.parsed_criteria.evaluation_criteria_and_weights,
                feature_and_capability_evaluations=feature_evals,
                mandatory_features_met=mandatory_met,
                mandatory_features_unmet=[]
            )

            log_structured_event(
                logger_instance=logger,
                event_name="phase1_agentic_orchestration_complete",
                payload={
                    "recommendation": decision_result.recommendation,
                    "coverage_pct": mapping_result.portfolio_ga_coverage_percentage,
                    "sub_agents_executed": len(telemetry_logs)
                }
            )

            return matrix, telemetry_logs
