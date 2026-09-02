import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.models.core_models import Product
from app.schemas.inclusion_schemas import ParsedRfiCriteria, InclusionEvaluationMatrix
from app.services.inclusion_analyzer import InclusionAnalyzer


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Fixture providing a mocked SQLAlchemy AsyncSession."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_inclusion_analyzer_perfect_match(mock_db_session: AsyncMock) -> None:
    """
    Scenario 1: Perfect Match Scenario.
    Product has $25M revenue, 55% CAGR, 40 enterprise clients, and reached GA 2 months before the cutoff date.
    Expect `Proceed_With_Participation`.
    """
    cutoff_date = datetime.date(2026, 3, 1)
    ga_date = datetime.date(2026, 1, 1)  # 2 months prior to cutoff

    perfect_product = Product(
        name="Google Cloud AI Modernizer GA",
        current_ga_date=ga_date,
        total_revenue_usd=Decimal("25000000.00"),
        cagr_percentage=Decimal("55.0"),
        enterprise_customer_count=40,
    )

    # Mock DB execute returning scalars().all() -> [perfect_product]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [perfect_product]
    mock_db_session.execute.return_value = mock_result

    analyzer = InclusionAnalyzer(db_session=mock_db_session)

    criteria = ParsedRfiCriteria(
        target_ga_cutoff_date=cutoff_date,
        min_revenue_usd=Decimal("5000000.00"),
        min_cagr_percentage=Decimal("50.0"),
        min_enterprise_customer_count=25,
    )

    # Execute evaluation
    matrix: InclusionEvaluationMatrix = await analyzer.evaluate_portfolio_eligibility(criteria)

    assert matrix.data_driven_recommendation == "Proceed_With_Participation"
    assert "Google Cloud AI Modernizer GA" in matrix.eligible_products
    assert len(matrix.rule_violations) == 0


@pytest.mark.asyncio
async def test_inclusion_analyzer_post_ga_cutoff(mock_db_session: AsyncMock) -> None:
    """
    Scenario 2: Post-GA Cutoff Scenario.
    Product meets all revenue/CAGR criteria but reaches GA exactly 1 day after the specified analyst cutoff.
    Expect `Decline_Due_To_Score_Risk` with a clear GA rule violation flag.
    """
    cutoff_date = datetime.date(2026, 3, 1)
    ga_date = datetime.date(2026, 3, 2)  # exactly 1 day after cutoff

    post_ga_product = Product(
        name="Google Cloud NextGen Preview",
        current_ga_date=ga_date,
        total_revenue_usd=Decimal("30000000.00"),
        cagr_percentage=Decimal("60.0"),
        enterprise_customer_count=50,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [post_ga_product]
    mock_db_session.execute.return_value = mock_result

    analyzer = InclusionAnalyzer(db_session=mock_db_session)

    criteria = ParsedRfiCriteria(
        target_ga_cutoff_date=cutoff_date,
        min_revenue_usd=Decimal("5000000.00"),
        min_cagr_percentage=Decimal("50.0"),
        min_enterprise_customer_count=25,
    )

    matrix: InclusionEvaluationMatrix = await analyzer.evaluate_portfolio_eligibility(criteria)

    assert matrix.data_driven_recommendation == "Decline_Due_To_Score_Risk"
    assert len(matrix.eligible_products) == 0
    assert len(matrix.rule_violations) == 1
    assert "GA Rule Violation" in matrix.rule_violations[0]
    assert "after the required cutoff date" in matrix.rule_violations[0]


@pytest.mark.asyncio
async def test_inclusion_analyzer_revenue_deficit(mock_db_session: AsyncMock) -> None:
    """
    Scenario 3: Revenue Deficit Scenario.
    Product is GA, has 100 enterprise clients, but revenue is $4M with a 10% CAGR against an analyst
    floor of $5M at 50% CAGR.
    Expect `Decline_Due_To_Score_Risk`.
    """
    cutoff_date = datetime.date(2026, 3, 1)
    ga_date = datetime.date(2025, 6, 1)  # well before GA cutoff

    deficit_product = Product(
        name="Google Cloud Legacy Tool",
        current_ga_date=ga_date,
        total_revenue_usd=Decimal("4000000.00"),
        cagr_percentage=Decimal("10.0"),
        enterprise_customer_count=100,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [deficit_product]
    mock_db_session.execute.return_value = mock_result

    analyzer = InclusionAnalyzer(db_session=mock_db_session)

    criteria = ParsedRfiCriteria(
        target_ga_cutoff_date=cutoff_date,
        min_revenue_usd=Decimal("5000000.00"),
        min_cagr_percentage=Decimal("50.0"),
        min_enterprise_customer_count=25,
    )

    matrix: InclusionEvaluationMatrix = await analyzer.evaluate_portfolio_eligibility(criteria)

    assert matrix.data_driven_recommendation == "Decline_Due_To_Score_Risk"
    assert len(matrix.eligible_products) == 0
    # Both Revenue ($4M < $5M) and CAGR (10% < 50%) violated
    assert len(matrix.rule_violations) == 2
    assert any("Revenue Rule Violation" in v for v in matrix.rule_violations)
    assert any("CAGR Rule Violation" in v for v in matrix.rule_violations)


@pytest.mark.asyncio
@patch("app.services.subagents.criteria_extraction_agent.GenerativeModel")
async def test_parse_rfi_criteria_success(mock_generative_model_cls: MagicMock, mock_db_session: AsyncMock) -> None:
    """
    Test the Vertex AI Gemini parsing logic via CriteriaExtractionSubAgent.
    """
    mock_model_inst = MagicMock()
    mock_response = MagicMock()
    mock_response.text = """
    {
        "target_ga_cutoff_date": "2026-03-01",
        "min_revenue_usd": 5000000.0,
        "min_cagr_percentage": 50.0,
        "min_enterprise_customer_count": 25,
        "confidence_score": 0.95,
        "raw_explanation": "Extracted Gartner criteria successfully",
        "evaluation_criteria_and_weights": [],
        "mandatory_features": [],
        "common_features": [],
        "critical_capabilities_and_use_cases": [],
        "platform_capabilities_inclusion_criteria": [],
        "exclusion_criteria": []
    }
    """
    mock_model_inst.generate_content_async = AsyncMock(return_value=mock_response)
    mock_generative_model_cls.return_value = mock_model_inst

    analyzer = InclusionAnalyzer(db_session=mock_db_session)
    criteria: ParsedRfiCriteria = await analyzer.parse_rfi_criteria("Sample Gartner RFI Criteria text")

    assert criteria.target_ga_cutoff_date == datetime.date(2026, 3, 1)
    assert criteria.min_revenue_usd == Decimal("5000000.0")
    assert criteria.min_cagr_percentage == Decimal("50.0")
    assert criteria.min_enterprise_customer_count == 25
    assert criteria.confidence_score == 0.95


@pytest.mark.asyncio
@patch("app.services.subagents.criteria_extraction_agent.GenerativeModel")
async def test_parse_rfi_criteria_expanded_fields(mock_generative_model_cls: MagicMock, mock_db_session: AsyncMock) -> None:
    """
    Test that CriteriaExtractionSubAgent properly extracts and structures Evaluation Criteria and Weights,
    Mandatory Features, Critical Capabilities and Use Cases Definitions, and Exclusion Criteria.
    """
    mock_model_inst = MagicMock()
    mock_response = MagicMock()
    mock_response.text = """
    {
        "target_ga_cutoff_date": "2026-03-01",
        "min_revenue_usd": 10000000.0,
        "min_cagr_percentage": 40.0,
        "min_enterprise_customer_count": 50,
        "confidence_score": 0.99,
        "raw_explanation": "Extracted comprehensive report criteria for 2026",
        "evaluation_criteria_and_weights": [
            {
                "criterion_name": "Evaluation Criteria and Weights: Market Responsiveness",
                "weight_percentage": 30.0,
                "description": "Responsiveness to AI coding prompts and latency"
            }
        ],
        "mandatory_features": [
            "Multi-file AI code generation",
            "SLSA Level 3 build provenance attestation"
        ],
        "common_features": [],
        "critical_capabilities_and_use_cases": [
            {
                "capability_name": "Critical Capabilities and Use Cases Definitions: IDE Integration",
                "definition": "Deep native IDE extension for refactoring and test generation",
                "is_mandatory": true,
                "required_level": "Standard GA"
            }
        ],
        "platform_capabilities_inclusion_criteria": [
            "Platform Capabilities Inclusion Criteria: Zero-VPN multi-cloud repository integration"
        ],
        "exclusion_criteria": [
            "No deprecated or sunset lifecycle services permitted"
        ]
    }
    """
    mock_model_inst.generate_content_async = AsyncMock(return_value=mock_response)
    mock_generative_model_cls.return_value = mock_model_inst

    analyzer = InclusionAnalyzer(db_session=mock_db_session)
    criteria: ParsedRfiCriteria = await analyzer.parse_rfi_criteria("Full Gartner 2026 welcome packet with weights and definitions")

    assert len(criteria.evaluation_criteria_and_weights) == 1
    assert criteria.evaluation_criteria_and_weights[0].weight_percentage == 30.0
    assert "Multi-file AI code generation" in criteria.mandatory_features
    assert len(criteria.critical_capabilities_and_use_cases) == 1
    assert criteria.critical_capabilities_and_use_cases[0].is_mandatory is True
    assert len(criteria.platform_capabilities_inclusion_criteria) == 1
    assert "No deprecated or sunset lifecycle services permitted" in criteria.exclusion_criteria


@pytest.mark.asyncio
async def test_inclusion_analyzer_expanded_criteria_and_exclusions(mock_db_session: AsyncMock) -> None:
    """
    Test that evaluate_portfolio_eligibility enforces exclusion criteria and mandatory feature checks,
    calling out specific products and capabilities as part of the go/no-go decision.
    """
    cutoff_date = datetime.date(2026, 3, 1)
    # Create two products: one qualifying Enterprise SKU and one Deprecated SKU
    flagship_product = Product(
        name="Gemini Code Assist Enterprise (Standard GA)",
        current_ga_date=datetime.date(2024, 11, 15),
        total_revenue_usd=Decimal("35000000.00"),
        cagr_percentage=Decimal("65.0"),
        enterprise_customer_count=620,
    )
    deprecated_product = Product(
        name="Cloud Legacy Code Helper (Deprecated)",
        current_ga_date=datetime.date(2022, 6, 1),
        total_revenue_usd=Decimal("30000000.00"),
        cagr_percentage=Decimal("60.0"),
        enterprise_customer_count=100,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [flagship_product, deprecated_product]
    mock_db_session.execute.return_value = mock_result

    analyzer = InclusionAnalyzer(db_session=mock_db_session)
    from app.schemas.inclusion_schemas import EvaluationCriterionWeight

    criteria = ParsedRfiCriteria(
        target_ga_cutoff_date=cutoff_date,
        min_revenue_usd=Decimal("25000000.00"),
        min_cagr_percentage=Decimal("40.0"),
        min_enterprise_customer_count=50,
        evaluation_criteria_and_weights=[
            EvaluationCriterionWeight(criterion_name="AI Capabilities", weight_percentage=50.0, description="Core AI coding check")
        ],
        mandatory_features=["Multi-file AI code generation"],
        exclusion_criteria=["No deprecated services"]
    )

    matrix: InclusionEvaluationMatrix = await analyzer.evaluate_portfolio_eligibility(criteria)

    # Flagship passes, Deprecated fails due to exclusion rules
    assert "Gemini Code Assist Enterprise (Standard GA)" in matrix.eligible_products
    assert any("Exclusion Violation" in v for v in matrix.rule_violations)
    assert len(matrix.evaluation_criteria_summary) == 1
    assert any(fe.status == "Met" and fe.feature_or_capability_name == "Multi-file AI code generation" for fe in matrix.feature_and_capability_evaluations)
    assert "Multi-file AI code generation" in matrix.mandatory_features_met


@pytest.mark.asyncio
async def test_inclusion_analyzer_dynamic_capability_aggregation_option_2(mock_db_session: AsyncMock) -> None:
    """
    Test Option 2: Dynamic Capability Aggregation across the qualifying GA corpus.
    Verifies that when mandatory features or critical use cases like 'Autonomous multi-turn task resolution'
    or 'Agent-driven refactoring' are evaluated across the portfolio, the engine dynamically aggregates
    and matches capabilities across all qualifying GA SKUs (Antigravity 2.0 / Antigravity IDE),
    securing status='Met' and Proceed_With_Participation without reporting false feature deficits.
    """
    cutoff_date = datetime.date(2026, 3, 1)
    enterprise_product = Product(
        name="Gemini Code Assist Enterprise (Standard GA)",
        current_ga_date=datetime.date(2024, 11, 15),
        total_revenue_usd=Decimal("35000000.00"),
        cagr_percentage=Decimal("65.0"),
        enterprise_customer_count=620,
    )
    antigravity2_product = Product(
        name="Antigravity 2.0 (Standard GA)",
        current_ga_date=datetime.date(2025, 5, 20),
        total_revenue_usd=Decimal("145000000.00"),
        cagr_percentage=Decimal("110.0"),
        enterprise_customer_count=2100,
    )
    antigravity_ide_product = Product(
        name="Antigravity IDE (Standard GA)",
        current_ga_date=datetime.date(2025, 8, 14),
        total_revenue_usd=Decimal("88000000.00"),
        cagr_percentage=Decimal("95.0"),
        enterprise_customer_count=1450,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [enterprise_product, antigravity2_product, antigravity_ide_product]
    mock_db_session.execute.return_value = mock_result

    analyzer = InclusionAnalyzer(db_session=mock_db_session)
    from app.schemas.inclusion_schemas import CriticalCapabilityUseCase

    criteria = ParsedRfiCriteria(
        target_ga_cutoff_date=cutoff_date,
        min_revenue_usd=Decimal("25000000.00"),
        min_cagr_percentage=Decimal("40.0"),
        min_enterprise_customer_count=50,
        mandatory_features=["Autonomous multi-turn task resolution", "Agent-driven refactoring"],
        critical_capabilities_and_use_cases=[
            CriticalCapabilityUseCase(capability_name="Agentic workflow orchestration", is_mandatory=True, required_level="Standard GA")
        ]
    )

    matrix: InclusionEvaluationMatrix = await analyzer.evaluate_portfolio_eligibility(criteria)

    assert matrix.data_driven_recommendation == "Proceed_With_Participation"
    assert len(matrix.rule_violations) == 0
    assert len(matrix.mandatory_features_unmet) == 0
    assert "Autonomous multi-turn task resolution" in matrix.mandatory_features_met
    assert "Agent-driven refactoring" in matrix.mandatory_features_met
    assert "Agentic workflow orchestration" in matrix.mandatory_features_met
    # Verify exact qualitative aggregation attribution in feature_evals
    for fe in matrix.feature_and_capability_evaluations:
        assert fe.status == "Met"
        assert len(fe.matching_products) > 0
        assert "Dynamically aggregated" in fe.evaluation_notes


def test_universal_ga_portfolio_corpus() -> None:
    from app.services.inclusion_analyzer import UNIVERSAL_GA_PORTFOLIO_CORPUS
    assert len(UNIVERSAL_GA_PORTFOLIO_CORPUS) == 14
    assert "Gemini Agent Platform (Standard GA)" in UNIVERSAL_GA_PORTFOLIO_CORPUS
    assert "Application Design Center (Standard GA)" in UNIVERSAL_GA_PORTFOLIO_CORPUS
    assert "Firebase Genkit & App Hosting (Standard GA)" in UNIVERSAL_GA_PORTFOLIO_CORPUS
    assert "Autonomous Cloud (AutoCloud) (Standard GA)" in UNIVERSAL_GA_PORTFOLIO_CORPUS
    assert "Google Cloud Run (Standard GA)" in UNIVERSAL_GA_PORTFOLIO_CORPUS
    assert "Google Kubernetes Engine (GKE) (Standard GA)" in UNIVERSAL_GA_PORTFOLIO_CORPUS


