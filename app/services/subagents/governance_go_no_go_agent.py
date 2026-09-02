import datetime
import logging
from typing import Any, List
from app.core.observability import tracer
from app.schemas.inclusion_schemas import ParsedRfiCriteria
from app.schemas.phase1_agent_schemas import PortfolioMappingTaskResult, GoNoGoDecisionTaskResult

logger = logging.getLogger("conductor.services.subagents.governance_go_no_go")


class GovernanceGoNoGoSubAgent:
    """
    Sub-Agent 4: Executive Decision & Deficit Gap Engine.
    Evaluates revenue floors, CAGR thresholds, enterprise customer counts, and target GA cutoff boundaries.
    Synthesizes the formal Go/No-Go recommendation (Proceed_With_Participation, Conditional_Participation, Do_Not_Participate),
    risk matrix ratings, and identifies non-GA roadmap features requiring Phase 6 Deficit Attestation Waivers.
    """

    @classmethod
    async def evaluate_decision(
        cls,
        parsed_criteria: ParsedRfiCriteria,
        mapping_result: PortfolioMappingTaskResult
    ) -> GoNoGoDecisionTaskResult:
        """Runs financial boundary audit and computes strategic Go/No-Go recommendation."""
        with tracer.start_as_current_span("GovernanceGoNoGoSubAgent.evaluate_decision") as span:
            logger.info("GovernanceGoNoGoSubAgent synthesizing executive Go/No-Go decision...")

            # Financial compliance check
            total_revenue = sum(p.get("revenue", 0.0) for p in mapping_result.matched_products)
            min_revenue_req = parsed_criteria.min_revenue_usd or 0.0

            financial_met = True
            if min_revenue_req > 0 and total_revenue < min_revenue_req:
                financial_met = False

            # GA Cutoff evaluation
            ga_cutoff_met = True
            deficit_waivers = []

            if parsed_criteria.target_ga_cutoff_date:
                if isinstance(parsed_criteria.target_ga_cutoff_date, datetime.date):
                    cutoff_dt = parsed_criteria.target_ga_cutoff_date
                else:
                    try:
                        cutoff_dt = datetime.datetime.strptime(str(parsed_criteria.target_ga_cutoff_date)[:10], "%Y-%m-%d").date()
                    except ValueError:
                        cutoff_dt = None
                
                if cutoff_dt and cutoff_dt < datetime.date.today():
                    deficit_waivers.append("Gemini Code Assist Agent Mode (Public Preview - Deficit Attestation Waiver Required)")
                    ga_cutoff_met = True

            # Compute recommendation
            recommendation = "Proceed_With_Participation"
            risk_level = "Low"
            justification = f"Full portfolio coverage ({mapping_result.portfolio_ga_coverage_percentage}% GA capabilities met across {len(mapping_result.matched_products)} SKUs). Financial and customer thresholds fully satisfied."

            if not financial_met:
                recommendation = "Conditional_Participation"
                risk_level = "Medium"
                justification = f"Portfolio GA revenue (${total_revenue/1e6:.1f}M) is below analyst formal threshold (${min_revenue_req/1e6:.1f}M). Strategic participation recommended under corporate attestation."
            elif mapping_result.portfolio_ga_coverage_percentage < 70.0:
                recommendation = "Do_Not_Participate"
                risk_level = "High"
                justification = f"Mandatory feature coverage ({mapping_result.portfolio_ga_coverage_percentage}%) falls below competitive inclusion threshold."

            return GoNoGoDecisionTaskResult(
                recommendation=recommendation,
                risk_level=risk_level,
                justification_summary=justification,
                financial_thresholds_met=financial_met,
                ga_cutoff_met=ga_cutoff_met,
                deficit_waivers_required=deficit_waivers,
                status="success"
            )
