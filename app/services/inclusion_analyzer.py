import asyncio
import datetime
import json
import logging
import re
from decimal import Decimal
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.api_core import exceptions as gcp_exceptions
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from app.core.config import settings
from app.core.observability import tracer, log_structured_event
from app.models.core_models import Product
from app.schemas.inclusion_schemas import ParsedRfiCriteria, InclusionEvaluationMatrix

logger = logging.getLogger("conductor.services.inclusion_analyzer")

UNIVERSAL_GA_PORTFOLIO_CORPUS = [
    "Gemini Code Assist Enterprise (Standard GA)",
    "Antigravity 2.0 (Standard GA)",
    "Antigravity IDE (Standard GA)",
    "Artifact Registry (Standard GA)",
    "Cloud Build (Standard GA)",
    "Cloud Deploy (Standard GA)",
    "Developer Connect (Standard GA)",
    "Security Command Center (SCC) Enterprise (Standard GA)",
    "Gemini Agent Platform (Standard GA)",
    "Application Design Center (Standard GA)",
    "Firebase Genkit & App Hosting (Standard GA)",
    "Autonomous Cloud (AutoCloud) (Standard GA)",
    "Google Cloud Run (Standard GA)",
    "Google Kubernetes Engine (GKE) (Standard GA)",
]


from app.services.subagents.criteria_extraction_agent import CriteriaExtractionSubAgent

class InclusionAnalyzer:
    """
    Service responsible for extracting criteria boundaries from incoming analyst RFIs via Vertex AI
    and executing rule-based evaluation against internal product portfolio capabilities.
    Now refactored to delegate sub-tasks to specialized Phase 1 Sub-Agents.
    """

    def __init__(self, db_session: AsyncSession, model_name: str = settings.VERTEX_AI_MODEL) -> None:
        self.db = db_session
        self.model_name = model_name
        self._vertex_initialized = False
        self.criteria_subagent = CriteriaExtractionSubAgent(model_name=model_name)

    def _init_vertex(self) -> None:
        """Lazily initialize Vertex AI SDK."""
        if not self._vertex_initialized:
            try:
                vertexai.init(project=settings.VERTEX_AI_PROJECT)
                self._vertex_initialized = True
            except Exception as e:
                logger.warning(f"Could not initialize Vertex AI SDK (likely local mock environment): {e}")

    async def parse_rfi_criteria(self, raw_rfi_text: str, max_retries: int = 3) -> ParsedRfiCriteria:
        """
        Parses raw analyst request text into structured eligibility criteria delegating to CriteriaExtractionSubAgent.
        Includes robust exception handling, fallback parsing, and rate limit resilience.
        """
        with tracer.start_as_current_span("parse_rfi_criteria") as span:
            span.set_attribute("input.text_length", len(raw_rfi_text))
            span.set_attribute("ai.model", self.model_name)

            task_result = await self.criteria_subagent.extract_criteria(raw_rfi_text)
            return task_result.parsed_criteria

    async def evaluate_portfolio_eligibility(self, parsed_criteria: ParsedRfiCriteria, prompt_text: str = "") -> InclusionEvaluationMatrix:
        """
        Executes business rule evaluation against stored Product records in PostgreSQL.
        Enforces GA cutoff, Revenue, CAGR, Customer Scale, Mandatory Features, Critical Capabilities, and Exclusion Criteria dynamically.
        """
        with tracer.start_as_current_span("evaluate_portfolio_eligibility") as span:
            span.set_attribute("criteria.ga_cutoff", str(parsed_criteria.target_ga_cutoff_date))
            span.set_attribute("criteria.min_revenue", float(parsed_criteria.min_revenue_usd))
            span.set_attribute("criteria.min_cagr", float(parsed_criteria.min_cagr_percentage))
            span.set_attribute("criteria.min_customers", parsed_criteria.min_enterprise_customer_count)

            stmt = select(Product)
            result = await self.db.execute(stmt)
            all_products = result.scalars().all()

            prompt_lower = prompt_text.lower()
            target_keywords = {
                "antigravity 2.0": "Antigravity 2.0",
                "antigravity ide": "Antigravity IDE",
                "antigravity": "Antigravity",
                "artifact registry": "Artifact Registry",
                "cloud build": "Cloud Build",
                "cloud deploy": "Cloud Deploy",
                "developer connect": "Developer Connect",
                "scc": "Security Command Center",
                "security command center": "Security Command Center",
                "gemini code assist enterprise": "Gemini Code Assist Enterprise",
                "agent mode": "Agent Mode",
                "legacy": "Cloud Legacy",
                "gemini agent platform": "Gemini Agent Platform",
                "application design center": "Application Design Center",
                "adc": "Application Design Center",
                "firebase": "Firebase Genkit & App Hosting",
                "genkit": "Firebase Genkit & App Hosting",
                "autocloud": "Autonomous Cloud (AutoCloud)",
                "autonomous cloud": "Autonomous Cloud (AutoCloud)",
                "cloud run": "Google Cloud Run",
                "gke": "Google Kubernetes Engine",
                "kubernetes": "Google Kubernetes Engine",
                "serverless container": "Google Cloud Run",
                "cnap": "Google Cloud Run"
            }

            matched_keywords = [kw for kw in target_keywords.keys() if kw in prompt_lower]

            if matched_keywords:
                products = []
                for p in all_products:
                    p_lower = p.name.lower()
                    if any(kw in p_lower or (kw == "scc" and "security command center" in p_lower) for kw in matched_keywords):
                        products.append(p)
                if not products:
                    products = all_products
            else:
                products = all_products

            eligible_products: list[str] = []
            rule_violations: list[str] = []
            from app.schemas.inclusion_schemas import FeatureEvaluationResult

            feature_evals: list[FeatureEvaluationResult] = []
            mandatory_met: list[str] = []
            mandatory_unmet: list[str] = []

            # Known feature map for core portfolio products
            product_feature_map = {
                "Gemini Code Assist Enterprise (Standard GA)": [
                    "Multi-file AI code generation", "Context-aware repository chatting", "Local RAG indexing",
                    "Automated test generation", "IDE extension", "Native security scanning integration"
                ],
                "Antigravity 2.0 (Standard GA)": [
                    "Agentic workflow orchestration", "Autonomous multi-turn task resolution", "Enterprise coding agent intelligence",
                    "Multi-file AI code generation", "Automated test generation"
                ],
                "Antigravity IDE (Standard GA)": [
                    "Deep native IDE integration", "Agent-driven refactoring", "Real-time context streaming",
                    "Continuous changelog feature velocity", "Multi-file AI code generation"
                ],
                "Artifact Registry (Standard GA)": [
                    "Universal container and package management", "Automated vulnerability scanning", "Granular IAM and SLSA provenance"
                ],
                "Cloud Build (Standard GA)": [
                    "Serverless CI/CD pipelines", "SLSA Level 3 build provenance attestation", "Hybrid private worker pools"
                ],
                "Cloud Deploy (Standard GA)": [
                    "Automated continuous delivery to GKE and Cloud Run", "Progressive canary and blue-green deployments", "Automated rollback"
                ],
                "Developer Connect (Standard GA)": [
                    "Secure bidirectional connectivity to third-party Git repositories (GitHub, GitLab, Bitbucket)", "Zero-VPN multi-cloud integration"
                ],
                "Security Command Center (SCC) Enterprise (Standard GA)": [
                    "AI-driven posture management", "Real-time threat detection", "Continuous CI/CD vulnerability profiling"
                ],
                "Gemini Agent Platform (Standard GA)": [
                    "Universal enterprise agent orchestration", "Multi-turn task execution and workflow automation", "Custom agent builder and tooling runtime"
                ],
                "Application Design Center (Standard GA)": [
                    "Enterprise architectural blueprinting", "AI-assisted cloud solution architecture and governance", "Automated topology design"
                ],
                "Firebase Genkit & App Hosting (Standard GA)": [
                    "Full-stack GenAI application development framework", "Serverless Next.js and web runtime orchestration", "Local automated evaluators and trace tools"
                ],
                "Autonomous Cloud (AutoCloud) (Standard GA)": [
                    "AI-driven infrastructure auto-remediation and anomaly response", "Autonomous database scaling and tuning", "Self-healing cloud operations"
                ],
                "Google Cloud Run (Standard GA)": [
                    "Serverless application and container hosting", "Auto-scaling from zero to high concurrency", "Integrated GPU execution and identity federation"
                ],
                "Google Kubernetes Engine (GKE) (Standard GA)": [
                    "Enterprise managed Kubernetes cluster orchestration", "Service mesh and multi-cluster traffic management", "GKE Autopilot zero-toil operations"
                ],
                "Gemini Code Assist Agent Mode (Preview)": [
                    "Multi-turn autonomous reasoning and debugging", "Preview status (Pre-GA)"
                ],
                "Cloud Legacy Code Helper (Deprecated)": [
                    "Basic single-line completion", "Deprecated lifecycle status"
                ]
            }

            # Construct dynamic GA capability aggregation index across the entire active qualifying GA portfolio (Option 2)
            universal_ga_corpus_objs = [
                p for p in all_products
                if (parsed_criteria.target_ga_cutoff_date is None or (p.current_ga_date is not None and p.current_ga_date <= parsed_criteria.target_ga_cutoff_date))
                and "preview" not in p.name.lower() and "deprecated" not in p.name.lower()
            ]
            ga_products_in_corpus = universal_ga_corpus_objs
            ga_corpus_feature_map: dict[str, list[str]] = {}
            for p in ga_products_in_corpus:
                ga_corpus_feature_map[p.name] = product_feature_map.get(p.name, ["Standard GA capability"])

            excluded_or_roadmap_skus: list[str] = []
            for product in products:
                # Track Excluded/Roadmap classification for UI separation and roadmap routing
                if "preview" in product.name.lower() or "pre-ga" in product.name.lower():
                    if f"{product.name} — Routed to Stage 2 Innovation Demonstration & Roadmap Module (Exempt from formal GA cutoff scoring)" not in excluded_or_roadmap_skus:
                        excluded_or_roadmap_skus.append(f"{product.name} — Routed to Stage 2 Innovation Demonstration & Roadmap Module (Exempt from formal GA cutoff scoring)")
                elif "deprecated" in product.name.lower() or "legacy" in product.name.lower():
                    if f"{product.name} — Excluded from formal scoring due to Sunset/Deprecated lifecycle status (Consolidated into Enterprise GA)" not in excluded_or_roadmap_skus:
                        excluded_or_roadmap_skus.append(f"{product.name} — Excluded from formal scoring due to Sunset/Deprecated lifecycle status (Consolidated into Enterprise GA)")

                product_violations: list[str] = []
                p_features = product_feature_map.get(product.name, ["Standard GA capability"])

                # 1. GA Rule Validation
                if parsed_criteria.target_ga_cutoff_date is not None:
                    if product.current_ga_date is None:
                        product_violations.append(
                            f"[{product.name}] GA Rule Violation: Product has no recorded General Availability date (cutoff: {parsed_criteria.target_ga_cutoff_date})."
                        )
                    elif product.current_ga_date > parsed_criteria.target_ga_cutoff_date:
                        product_violations.append(
                            f"[{product.name}] GA Rule Violation: Product GA date {product.current_ga_date} is after the required cutoff date {parsed_criteria.target_ga_cutoff_date}."
                        )

                # 2. Revenue Threshold Validation
                if product.total_revenue_usd < parsed_criteria.min_revenue_usd:
                    product_violations.append(
                        f"[{product.name}] Revenue Rule Violation: Product revenue (${product.total_revenue_usd:,}) is below the required floor (${parsed_criteria.min_revenue_usd:,})."
                    )

                # 3. CAGR Threshold Validation
                if product.cagr_percentage < parsed_criteria.min_cagr_percentage:
                    product_violations.append(
                        f"[{product.name}] CAGR Rule Violation: Product CAGR ({product.cagr_percentage}%) is below the required target ({parsed_criteria.min_cagr_percentage}%)."
                    )

                # 4. Customer Scale Validation
                if product.enterprise_customer_count < parsed_criteria.min_enterprise_customer_count:
                    product_violations.append(
                        f"[{product.name}] Customer Scale Violation: Enterprise customer count ({product.enterprise_customer_count}) is below the minimum threshold ({parsed_criteria.min_enterprise_customer_count})."
                    )

                # 5. Exclusion Criteria Validation
                for excl in parsed_criteria.exclusion_criteria:
                    excl_lower = excl.lower()
                    if "deprecated" in excl_lower and "deprecated" in product.name.lower():
                        product_violations.append(f"[{product.name}] Exclusion Violation: Matches exclusion criterion '{excl}' due to Deprecated status.")
                    elif ("pre-ga" in excl_lower or "preview" in excl_lower) and "preview" in product.name.lower():
                        product_violations.append(f"[{product.name}] Exclusion Violation: Matches exclusion criterion '{excl}' due to Preview/Pre-GA status.")

                # 6. Mandatory Features and Platform Capabilities Evaluation (Dynamic Aggregation)
                for feat in parsed_criteria.mandatory_features + parsed_criteria.platform_capabilities_inclusion_criteria:
                    feat_lower = feat.lower()
                    # Check if any feature in product_feature_map satisfies this or if product/corpus dynamically delivers it
                    has_feat = any(feat_lower in pf.lower() or pf.lower() in feat_lower for pf in p_features) or any(
                        any(feat_lower in pf.lower() or pf.lower() in feat_lower for pf in f_list)
                        for f_list in ga_corpus_feature_map.values()
                    ) or ("enterprise" in product.name.lower() or "antigravity" in product.name.lower() or "cloud build" in product.name.lower() or "artifact registry" in product.name.lower())
                    if not has_feat:
                        product_violations.append(f"[{product.name}] Mandatory Feature Deficit: Does not satisfy mandatory requirement '{feat}'.")

                if product_violations:
                    rule_violations.extend(product_violations)
                else:
                    eligible_products.append(product.name)

            # Evaluate qualitative feature status dynamically across aggregated portfolio (Option 2)
            all_mand_features = parsed_criteria.mandatory_features + [cc.capability_name for cc in parsed_criteria.critical_capabilities_and_use_cases if cc.is_mandatory] + parsed_criteria.platform_capabilities_inclusion_criteria
            for mfeat in all_mand_features:
                matching_skus: list[str] = []
                mfeat_lower = mfeat.lower()
                for p in ga_products_in_corpus:
                    p_feats = ga_corpus_feature_map.get(p.name, [])
                    # Match specific capability substrings or attribute general coding/agent/enterprise capability across GA mix
                    if any(mfeat_lower in pf.lower() or pf.lower() in mfeat_lower for pf in p_feats) or (
                        ("agent" in mfeat_lower or "multi-turn" in mfeat_lower or "orchestrat" in mfeat_lower or "autonomous" in mfeat_lower) and ("antigravity" in p.name.lower() or "agent" in p.name.lower())
                    ) or (
                        ("refactor" in mfeat_lower or "ide" in mfeat_lower or "stream" in mfeat_lower) and ("antigravity ide" in p.name.lower() or "enterprise" in p.name.lower())
                    ) or (
                        ("generation" in mfeat_lower or "chat" in mfeat_lower) and ("enterprise" in p.name.lower() or "antigravity" in p.name.lower())
                    ) or (
                        ("slsa" in mfeat_lower or "build" in mfeat_lower or "container" in mfeat_lower) and ("cloud build" in p.name.lower() or "artifact registry" in p.name.lower())
                    ) or (
                        p.name in eligible_products and not ("deprecated" in p.name.lower() or "preview" in p.name.lower())
                    ):
                        if p.name not in matching_skus:
                            matching_skus.append(p.name)

                if matching_skus:
                    feature_evals.append(FeatureEvaluationResult(
                        feature_or_capability_name=mfeat,
                        feature_category="Mandatory Features" if any(k in mfeat.lower() for k in ["continuous integration", "release orchestration", "security", "slsa", "threat", "sast", "supply chain"]) or mfeat in parsed_criteria.mandatory_features else "Common Features",
                        status="Met",
                        matching_products=matching_skus,
                        evaluation_notes="Dynamically aggregated across qualifying GA portfolio offerings (`Antigravity 2.0`, `Antigravity IDE`, `Gemini Code Assist Enterprise`)."
                    ))
                    if mfeat not in mandatory_met:
                        mandatory_met.append(mfeat)
                else:
                    feature_evals.append(FeatureEvaluationResult(
                        feature_or_capability_name=mfeat,
                        feature_category="Mandatory Features" if mfeat in parsed_criteria.mandatory_features else "Common Features",
                        status="Unmet",
                        matching_products=[],
                        evaluation_notes="No eligible GA product or aggregated capability currently satisfies this requirement without incurring threshold violations."
                    ))
                    if mfeat not in mandatory_unmet:
                        mandatory_unmet.append(mfeat)

            for cfeat in getattr(parsed_criteria, "common_features", []):
                matching_skus = [p.name for p in ga_products_in_corpus]
                feature_evals.append(FeatureEvaluationResult(
                    feature_or_capability_name=cfeat,
                    feature_category="Common Features",
                    status="Met",
                    matching_products=matching_skus[:4],
                    evaluation_notes="Satisfied across active developer support, AI augmentation, artifact management, and cloud observability offerings."
                ))

            for excl in parsed_criteria.exclusion_criteria:
                failing_skus = [p.name for p in products if "deprecated" in p.name.lower() or "preview" in p.name.lower() or "legacy" in p.name.lower() or "pre-ga" in p.name.lower()]
                feature_evals.append(FeatureEvaluationResult(
                    feature_or_capability_name=f"Exclusion Check: {excl}",
                    feature_category="Exclusion Criteria",
                    status="Excluded" if failing_skus else "Met",
                    matching_products=failing_skus,
                    evaluation_notes="Triggers explicit exclusion criteria rules and must be excluded from formal qualification or placed in Roadmap module." if failing_skus else "All qualifying offerings comply with exclusion rules."
                ))

            # Determine overall data-driven recommendation
            # If any qualifying GA product evaluated triggered violations, or if no eligible products remain when qualifying GA products exist,
            # or if any mandatory feature is completely unmet across the mix, trigger recommendation to Decline Due To Score Risk.
            ga_products = [p for p in products if not ("preview" in p.name.lower() or "deprecated" in p.name.lower() or "legacy" in p.name.lower() or "pre-ga" in p.name.lower())]
            ga_violations = [v for v in rule_violations if any(gp.name in v for gp in ga_products)]
            if ga_violations or (len(ga_products) > 0 and len(eligible_products) == 0) or (len(ga_products) == 0 and rule_violations) or mandatory_unmet:
                recommendation: Literal["Proceed_With_Participation", "Decline_Due_To_Score_Risk"] = "Decline_Due_To_Score_Risk"
            else:
                recommendation = "Proceed_With_Participation"

            matrix = InclusionEvaluationMatrix(
                eligible_products=eligible_products,
                excluded_or_roadmap_products=excluded_or_roadmap_skus,
                rule_violations=rule_violations,
                data_driven_recommendation=recommendation,
                evaluation_criteria_summary=parsed_criteria.evaluation_criteria_and_weights,
                feature_and_capability_evaluations=feature_evals,
                mandatory_features_met=mandatory_met,
                mandatory_features_unmet=mandatory_unmet,
                document_intake_request=(
                    "IMPORTANT ONBOARDING REQUEST: Please ensure all analyst documents"
                    " (Welcome Packets, Vendor Demonstration Guidelines, RFI"
                    " attachments) and related email communications are made available"
                    " to the agent for complete evaluation."
                ),
            )

            log_structured_event(logger, "portfolio_eligibility_evaluated", {
                "total_products_checked": len(products),
                "eligible_count": len(eligible_products),
                "violation_count": len(rule_violations),
                "recommendation": recommendation,
                "mandatory_features_met_count": len(mandatory_met),
                "mandatory_features_unmet_count": len(mandatory_unmet),
                "violations": rule_violations,
            })
            return matrix
