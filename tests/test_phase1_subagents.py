import pytest
from app.schemas.inclusion_schemas import ParsedRfiCriteria
from app.schemas.phase1_agent_schemas import PortfolioMappingTaskResult
from app.services.subagents.rfi_document_parser_agent import RfiDocumentParserSubAgent
from app.services.subagents.criteria_extraction_agent import CriteriaExtractionSubAgent
from app.services.subagents.portfolio_mapping_agent import PortfolioMappingSubAgent
from app.services.subagents.governance_go_no_go_agent import GovernanceGoNoGoSubAgent


@pytest.mark.asyncio
async def test_rfi_document_parser_happy_path():
    text = """
    Gartner Magic Quadrant for DevSecOps Platforms 2026
    | Criteria | Weight |
    | AI Code Gen | 30% |
    Welcome packet and demo guidelines tab context.
    """
    res = await RfiDocumentParserSubAgent.parse_document(text)
    assert res.status == "success"
    assert res.detected_report_title is not None
    assert len(res.extracted_tables) == 1
    assert res.is_multi_tab_spreadsheet is True or len(res.parsed_layout_blocks) > 0


@pytest.mark.asyncio
async def test_rfi_document_parser_unhappy_path_gibberish():
    # Simulate an end-user entering random gibberish or non-standard text
    text = "asdfghjkl 12345 !@#$%"
    res = await RfiDocumentParserSubAgent.parse_document(text)
    assert res.status == "warning"
    assert res.error_message is not None
    assert "Unrecognized document format" in res.error_message


@pytest.mark.asyncio
async def test_criteria_extraction_happy_and_fallback_path():
    text = "Target GA cutoff: 2026-03-02. Recognized GAAP revenue >= $50M with 25% CAGR and 500 enterprise customers."
    extractor = CriteriaExtractionSubAgent()
    res = await extractor.extract_criteria(text)
    assert res.status == "success"
    assert res.parsed_criteria.min_revenue_usd >= 25000000.0
    assert res.parsed_criteria.target_ga_cutoff_date is not None or len(res.parsed_criteria.evaluation_criteria_and_weights) > 0


@pytest.mark.asyncio
async def test_criteria_extraction_unhappy_path_empty():
    extractor = CriteriaExtractionSubAgent()
    res = await extractor.extract_criteria("")
    assert res.status == "warning"
    assert res.parsed_criteria.confidence_score <= 0.5


from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_res
    return session

@pytest.mark.asyncio
async def test_portfolio_mapping_subagent(mock_db_session: AsyncMock):
    parsed = ParsedRfiCriteria(
        mandatory_features=[
            "Continuous integration via native build automation",
            "Orchestration of security functions like threat modeling, SAST/DAST/SCA",
            "AI augmentation and agentic workflows"
        ]
    )
    res = await PortfolioMappingSubAgent.map_portfolio(parsed, mock_db_session)
    assert res.status == "success"
    assert res.portfolio_ga_coverage_percentage > 70.0
    assert len(res.matched_products) >= 1
    assert len(res.capability_attributions) == 3


@pytest.mark.asyncio
async def test_governance_go_no_go_subagent_happy_and_deficit_paths():
    parsed = ParsedRfiCriteria(
        target_ga_cutoff_date="2025-01-01",  # Past date requires attestation waiver for preview features
        min_revenue_usd=50000000.0
    )
    mapping = PortfolioMappingTaskResult(
        matched_products=[{"name": "Gemini Code Assist Enterprise", "revenue": 100000000.0}],
        portfolio_ga_coverage_percentage=92.3,
        mandatory_features_met_count=3,
        mandatory_features_total_count=3
    )
    res = await GovernanceGoNoGoSubAgent.evaluate_decision(parsed, mapping)
    assert res.status == "success"
    assert res.recommendation == "Proceed_With_Participation"
    assert res.financial_thresholds_met is True
    assert len(res.deficit_waivers_required) > 0
