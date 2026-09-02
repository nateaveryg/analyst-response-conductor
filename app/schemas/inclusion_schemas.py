import datetime
from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, Field


class EvaluationCriterionWeight(BaseModel):
    """
    Represents an evaluation criterion and its relative scoring weight or importance for a specific report/year.
    """
    criterion_name: str = Field(..., description="Name of the evaluation criterion (e.g., Market Responsiveness, AI Capabilities)")
    weight_percentage: float = Field(default=0.0, description="Weight or percentage allocated to this criterion (e.g., 25.0)")
    description: str = Field(default="", description="Detailed explanation of what the analyst evaluates under this criterion")


class CriticalCapabilityUseCase(BaseModel):
    """
    Represents a critical capability definition and specific use case required or scored in the evaluation report.
    """
    capability_name: str = Field(..., description="Name of the critical capability or use case (e.g., Multi-file Code Generation, Native IDE Integration)")
    definition: str = Field(default="", description="Formal definition of what the critical capability entails")
    is_mandatory: bool = Field(default=False, description="Whether this capability is mandatory for inclusion or optional/weighted")
    required_level: str = Field(default="Standard", description="Required capability level (e.g., Standard, Advanced, Enterprise-ready)")


class FeatureEvaluationResult(BaseModel):
    """
    Captures the evaluation status of specific products and features against mandatory features, critical capabilities, and exclusion criteria.
    """
    feature_or_capability_name: str = Field(..., description="Name of the evaluated feature, capability, or criteria condition")
    feature_category: str = Field(default="Mandatory Features", description="Category of the feature, such as Mandatory Features or Common Features (e.g., AI Augmentation, IDEs, SEI metrics)")
    status: Literal["Met", "Unmet", "Excluded", "Partial"] = Field(..., description="Whether the condition is Met by qualifying products, Unmet, Excluded, or Partial")
    matching_products: list[str] = Field(default_factory=list, description="List of specific product names or SKUs that meet or fail this feature condition")
    evaluation_notes: str = Field(default="", description="Rationale calling out specific product capabilities or deficits")


class ParsedRfiCriteria(BaseModel):
    """
    Structured boundaries, qualification thresholds, and report-specific criteria parsed from raw analyst RFI text via Gemini.
    """
    target_ga_cutoff_date: datetime.date | None = Field(
        default=None,
        description="Target General Availability cutoff date required by the analyst (e.g., 2026-03-01)"
    )
    min_revenue_usd: Decimal = Field(
        default=Decimal("0.0"),
        description="Minimum annualized product revenue floor in USD required for inclusion"
    )
    min_cagr_percentage: Decimal = Field(
        default=Decimal("0.0"),
        description="Minimum Compound Annual Growth Rate (CAGR) percentage required for inclusion"
    )
    min_enterprise_customer_count: int = Field(
        default=0,
        description="Minimum count of paying enterprise customers required for inclusion"
    )
    confidence_score: float = Field(
        default=1.0,
        description="Model confidence score between 0.0 and 1.0 for the extraction"
    )
    raw_explanation: str = Field(
        default="",
        description="Summary explanation or notes extracted alongside parameters"
    )
    evaluation_criteria_and_weights: list[EvaluationCriterionWeight] = Field(
        default_factory=list,
        description="Evaluation Criteria and Weights specific to this report and year"
    )
    mandatory_features: list[str] = Field(
        default_factory=list,
        description="Mandatory Features required for platform or product inclusion (e.g., CI/CD release orchestration, security function orchestration)"
    )
    common_features: list[str] = Field(
        default_factory=list,
        description="Common Features identified in uploaded documents (e.g., AI augmentation, IDEs, SEI metrics, artifact management, observability, environment provisioning)"
    )
    critical_capabilities_and_use_cases: list[CriticalCapabilityUseCase] = Field(
        default_factory=list,
        description="Critical Capabilities and Use Cases Definitions identified in the report documents"
    )
    platform_capabilities_inclusion_criteria: list[str] = Field(
        default_factory=list,
        description="Platform Capabilities Inclusion Criteria and mandatory architectural requirements"
    )
    exclusion_criteria: list[str] = Field(
        default_factory=list,
        description="Explicit Exclusion Criteria or disqualifying conditions that rule out a product or vendor"
    )
    document_intake_notice: str = Field(
        default=(
            "To ensure comprehensive evaluation, workback timeline accuracy, and"
            " SME task routing, please make all documents (Welcome Packets, Demo"
            " Guidelines, RFI attachments) and analyst emails related to criteria"
            " available to the agent."
        ),
        description="Notice requesting that the end user provide all relevant criteria documents and emails"
    )


class InclusionEvaluationMatrix(BaseModel):
    """
    Evaluation matrix output summarizing which products qualify, listing rule violations, and calling out specific features.
    """
    execution_timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="UTC timestamp of when the portfolio eligibility evaluation executed"
    )
    eligible_products: list[str] = Field(
        default_factory=list,
        description="List of product names that meet or exceed all inclusion criteria"
    )
    excluded_or_roadmap_products: list[str] = Field(
        default_factory=list,
        description="List of product names explicitly excluded from formal quantitative GA scoring or assigned to Roadmap/Preview demonstration modules"
    )
    rule_violations: list[str] = Field(
        default_factory=list,
        description="Detailed violation strings explaining exact deficits per ineligible product"
    )
    data_driven_recommendation: Literal["Proceed_With_Participation", "Decline_Due_To_Score_Risk"] = Field(
        ...,
        description="Data-driven recommendation on whether to proceed with this evaluation"
    )
    evaluation_criteria_summary: list[EvaluationCriterionWeight] = Field(
        default_factory=list,
        description="Summary of evaluation criteria weights specific to this report and year"
    )
    feature_and_capability_evaluations: list[FeatureEvaluationResult] = Field(
        default_factory=list,
        description="Detailed breakdown calling out specific products and product features that meet or violate mandatory features, critical capabilities, and platform inclusion criteria"
    )
    mandatory_features_met: list[str] = Field(
        default_factory=list,
        description="Mandatory features or critical capabilities satisfied by current portfolio offerings"
    )
    mandatory_features_unmet: list[str] = Field(
        default_factory=list,
        description="Mandatory features missing or violating exclusion criteria"
    )
    document_intake_request: str = Field(
        default=(
            "IMPORTANT ONBOARDING REQUEST: Please ensure all analyst documents"
            " (Welcome Packets, Vendor Demonstration Guidelines, RFI"
            " attachments) and related email communications are made available"
            " to the agent for complete evaluation."
        ),
        description="Actionable request reminding end user to provide all criteria documents and email threads"
    )


PRODUCT_DATABASE: list[dict[str, Any]] = [
    {"name": "Gemini Code Assist Enterprise (Standard GA)", "ga_date": "2024-11-15", "revenue_usd": 35000000.00, "cagr": 65.0, "logos": 620},
    {"name": "Antigravity 2.0 (Standard GA)", "ga_date": "2025-05-20", "revenue_usd": 145000000.00, "cagr": 110.0, "logos": 2100},
    {"name": "Antigravity IDE (Standard GA)", "ga_date": "2025-08-14", "revenue_usd": 88000000.00, "cagr": 95.0, "logos": 1450},
    {"name": "Artifact Registry (Standard GA)", "ga_date": "2020-05-15", "revenue_usd": 110000000.00, "cagr": 55.0, "logos": 3200},
    {"name": "Cloud Build (Standard GA)", "ga_date": "2018-07-24", "revenue_usd": 95000000.00, "cagr": 48.0, "logos": 2800},
    {"name": "Cloud Deploy (Standard GA)", "ga_date": "2021-08-30", "revenue_usd": 42000000.00, "cagr": 60.0, "logos": 850},
    {"name": "Developer Connect (Standard GA)", "ga_date": "2024-04-09", "revenue_usd": 28000000.00, "cagr": 75.0, "logos": 540},
    {"name": "Security Command Center (SCC) Enterprise (Standard GA)", "ga_date": "2023-10-10", "revenue_usd": 180000000.00, "cagr": 52.0, "logos": 1900},
    {"name": "Gemini Agent Platform (Standard GA)", "ga_date": "2025-02-10", "revenue_usd": 75000000.00, "cagr": 72.0, "logos": 1100},
    {"name": "Application Design Center (Standard GA)", "ga_date": "2024-08-15", "revenue_usd": 42000000.00, "cagr": 55.0, "logos": 650},
    {"name": "Firebase Genkit & App Hosting (Standard GA)", "ga_date": "2024-05-10", "revenue_usd": 85000000.00, "cagr": 60.0, "logos": 1300},
    {"name": "Autonomous Cloud (AutoCloud) (Standard GA)", "ga_date": "2025-01-20", "revenue_usd": 110000000.00, "cagr": 68.0, "logos": 1600},
    {"name": "Google Cloud Run (Standard GA)", "ga_date": "2019-11-14", "revenue_usd": 180000000.00, "cagr": 85.0, "logos": 2400},
    {"name": "Google Kubernetes Engine (GKE) (Standard GA)", "ga_date": "2015-08-26", "revenue_usd": 450000000.00, "cagr": 65.0, "logos": 3800},
]

