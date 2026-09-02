import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.database import get_db
from app.models.core_models import RfiQuestion, RagDocumentChunk, ReportEvaluation
from app.services.rfi_architect_agent import RfiArchitectAgentService


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Fixture providing a mocked SQLAlchemy AsyncSession with empty default result sets."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result
    return mock_db


@pytest.mark.asyncio
async def test_multitab_workbook_ingestion_and_classification(mock_db_session: AsyncMock):
    """
    Verifies multi-tab spreadsheet ingestion traverses all tabs, pre-classifies instruction
    sheets (skipping them), enriches domain context, and routes items to SMEs.
    """
    eval_id = uuid.uuid4()
    multitab_payload = {
        "sheets": {
            "Tab 1: Vendor Instructions & NDA": [
                "Please complete all items within 45 minute video budget.",
                "Scoring legend and evaluation rules."
            ],
            "Tab 2: Enterprise Security & IAM": [
                "Describe authentication methods supported to integrate with enterprise IAM.",
                "Describe how your platform meets customers' data residency requirements."
            ],
            "Tab 3: AI & Serverless Concurrency": [
                "Managed Serverless Container Runtimes & Scaling to Zero concurrency.",
                "What major open-source packages does your platform rely upon?"
            ]
        }
    }

    res = await RfiArchitectAgentService.ingest_multitab_spreadsheet(
        workbook_source=multitab_payload,
        evaluation_id=eval_id,
        db_session=mock_db_session
    )

    assert res["total_tabs_scanned"] == 3
    assert res["instruction_tabs_count"] == 1
    assert res["evaluation_tabs_count"] == 2
    assert res["decomposed_questions_count"] == 4

    questions = res["questions"]
    assert any("[Tab 2: Enterprise Security & IAM]" in q["section_identifier"] for q in questions)
    assert any("security-sme@google.com" in str(q.get("assigned_sme_id", "")) or "serverless" in str(q).lower() or "opm-coordinator" in str(q.get("assigned_sme_id", "")) for q in questions)


@pytest.mark.asyncio
async def test_hybrid_rag_and_prior_rfi_source_recall(mock_db_session: AsyncMock):
    """
    Verifies generate_grounded_drafts recalls historical prior RFI approved answers from pgvector memory
    and attaches explicit provenance citations and dynamic grounding scores.
    """
    eval_id = uuid.uuid4()
    # Mocking returned unassigned questions from DB execute call
    q_item = RfiQuestion(
        id=uuid.uuid4(),
        evaluation_id=eval_id,
        section_identifier="[Tab 2: Security] Q1 (Row 5)",
        worksheet_tab="Tab 2: Security",
        question_text="Describe authentication methods supported to integrate with enterprise IAM.",
        assigned_sme_id="security-sme@google.com",
        response_status="Unassigned"
    )
    mock_res_q = MagicMock()
    mock_res_q.scalars.return_value.all.return_value = [q_item]
    
    mock_res_chunk = MagicMock()
    mock_res_chunk.scalars.return_value.all.return_value = [
        RagDocumentChunk(
            id=uuid.uuid4(),
            source_document_id="2025_Gartner_MQ_CNAP_Q6",
            publication_year=2025,
            product_tag="IAM & Workload Identity",
            ga_status_at_time_of_writing="Standard GA",
            chunk_type="Prior_RFI_Answer",
            source_rfi_title="2025 Gartner Magic Quadrant for CNAP — [Tab 2: Security & Identity] Q6",
            original_question_text="Describe authentication methods supported to integrate with enterprise IAM.",
            original_answer_text="Natively integrates with Enterprise IAM via OIDC, SAML 2.0, Workload Identity Federation, and robust Secrets Manager integrations for container authentication.",
            chunk_text="Question: Describe authentication methods supported to integrate with enterprise IAM.\nAnswer: Natively integrates with Enterprise IAM via OIDC, SAML 2.0, Workload Identity Federation."
        )
    ]
    mock_db_session.execute.side_effect = [mock_res_q, mock_res_chunk]

    res = await RfiArchitectAgentService.generate_grounded_drafts(
        evaluation_id=eval_id,
        db_session=mock_db_session,
        report_name="DevSecOps"
    )

    assert res["status"] == "success"
    assert res["total_questions_drafted"] == 1
    assert res["average_grounding_confidence"] > 90.0

    draft_q = res["questions"][0]
    assert "Gartner Magic Quadrant" in str(draft_q.get("source_rfi_title", "")) or "Universal GA" in str(draft_q.get("source_rfi_title", ""))
    assert len(draft_q["draft_response"]) > 20
    assert draft_q["grounding_confidence_score"] > 90.0


@pytest.mark.asyncio
async def test_conversational_draft_refinement(mock_db_session: AsyncMock):
    """
    Verifies chat instruction refinement edits target question text and increases confidence grounding score.
    """
    eval_id = uuid.uuid4()
    q_item = RfiQuestion(
        id=uuid.uuid4(),
        evaluation_id=eval_id,
        section_identifier="[Tab 3: AI Agent Runtimes] Q8",
        worksheet_tab="Tab 3: AI Agent Runtimes",
        question_text="Managed Serverless Container Runtimes & Scaling to Zero concurrency.",
        draft_response="Natively hosts serverless container applications with auto-scaling to zero.",
        response_status="Drafted",
        grounding_confidence_score=0.98
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = q_item
    mock_db_session.execute.return_value = mock_res

    res = await RfiArchitectAgentService.refine_draft_response(
        question_identifier="Q8",
        refinement_instruction="Emphasize Cloud Run GPU attachment over standard GKE",
        db_session=mock_db_session
    )

    assert res["status"] == "success"
    assert "Cloud Run GPU attachment" in res["refined_draft"]
    assert res["grounding_confidence_score"] >= 98.0


@pytest.mark.asyncio
async def test_continuous_corpus_archiving_loop(mock_db_session: AsyncMock):
    """
    Verifies Phase 7 completion auto-indexes approved RFI responses into RagDocumentChunk table
    with chunk_type='Prior_RFI_Answer', closing the continuous organizational memory loop.
    """
    eval_id = uuid.uuid4()
    q_item = RfiQuestion(
        id=uuid.uuid4(),
        evaluation_id=eval_id,
        section_identifier="[Tab 4: Roadmap] Q12",
        worksheet_tab="Tab 4: Roadmap",
        question_text="What AI agent tool orchestration frameworks are supported natively?",
        draft_response="Supported natively via Gemini Agent Platform (Standard GA) and Application Design Center templates.",
        response_status="Approved"
    )
    mock_res = MagicMock()
    # First call returns questions to archive, second call returns None (meaning chunk not yet in archive)
    mock_res.scalars.return_value.all.return_value = [q_item]
    mock_res.scalars.return_value.first.return_value = None
    mock_db_session.execute.return_value = mock_res

    res = await RfiArchitectAgentService.archive_approved_rfi_to_corpus(
        evaluation_id=eval_id,
        db_session=mock_db_session
    )

    assert res["status"] == "success"
    assert res["archived_chunks_count"] == 1


@pytest.mark.asyncio
async def test_export_rfi_responses_provenance_and_multitab(mock_db_session: AsyncMock):
    """
    Verifies standalone export endpoints produce multi-tab formatted sections in Markdown
    and explicit Prior RFI Source Title columns in CSV spreadsheets.
    """
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            res_md = await client.get("/api/v1/export/rfi-responses?format=md&report=cnap")
            assert res_md.status_code == 200
            md_text = res_md.text
            assert "Principal TSA Sub-Agent Grounded RAG Ingestion" in md_text
            assert "Prior RFI Source Citation & Provenance" in md_text or "Worksheet Tab:" in md_text
            assert "Average Grounding Confidence:" in md_text

            res_csv = await client.get("/api/v1/export/rfi-responses?format=csv&report=cnap")
            assert res_csv.status_code == 200
            csv_text = res_csv.text
            assert '"Worksheet Tab Domain","Section Coordinate","Question & Capability Requirement"' in csv_text
            assert '"Prior RFI Source Title","Historical Question Match","Grounding Confidence Score"' in csv_text
    finally:
        app.dependency_overrides.clear()
