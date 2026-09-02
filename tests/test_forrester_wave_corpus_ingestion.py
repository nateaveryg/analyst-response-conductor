import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.services.rfi_architect_agent import RfiArchitectAgentService
from app.models.core_models import RfiQuestion


@pytest.mark.asyncio
async def test_forrester_wave_q3_2026_questionnaire_ingestion_and_rag():
    url = "https://docs.google.com/spreadsheets/d/1rM5FlzejyVY_xWCJxdxnzusNxtpH07w7/edit?gid=45519069#gid=45519069"
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    eval_id = uuid.uuid4()

    # Step 1: Execute Automated Multi-Tab Ingestion against Forrester Wave URL
    ingest_res = await RfiArchitectAgentService.ingest_multitab_spreadsheet(
        workbook_source=url,
        evaluation_id=eval_id,
        db_session=mock_db
    )
    
    assert ingest_res["status"] == "success"
    assert ingest_res["evaluation_tabs_count"] >= 25
    assert ingest_res["decomposed_questions_count"] >= 25

    # Prepare mock entities for grounding step
    created_questions = []
    for q_data in ingest_res["questions"]:
        q = RfiQuestion(
            id=uuid.uuid4(),
            evaluation_id=eval_id,
            section_identifier=q_data["section_identifier"],
            worksheet_tab=q_data["worksheet_tab"],
            question_text=q_data["question_text"],
            assigned_sme_id=q_data["assigned_sme_id"],
            response_status="Unassigned"
        )
        created_questions.append(q)

    mock_res_q = MagicMock()
    mock_res_q.scalars.return_value.all.return_value = created_questions
    mock_res_chunk = MagicMock()
    mock_res_chunk.scalars.return_value.all.return_value = []
    mock_db.execute.side_effect = [mock_res_q, mock_res_chunk]

    # Step 2: Execute Hybrid RAG Grounding Engine against Forrester Wave Q3 2026 Corpus
    rag_res = await RfiArchitectAgentService.generate_grounded_drafts(
        evaluation_id=eval_id,
        db_session=mock_db,
        report_name="Forrester Wave Public Cloud Platforms Q3 2026"
    )

    assert rag_res["status"] == "success"
    assert rag_res["average_grounding_confidence"] >= 95.0
    assert rag_res["total_questions_drafted"] >= 25

    # Step 3: Verify provenance citation and pre-populated answers
    first_q = rag_res["questions"][0]
    assert "2026 Forrester Wave Public Cloud Platforms" in first_q["source_rfi_title"]
    assert len(first_q["draft_response"]) > 20
    assert first_q["grounding_confidence_score"] >= 95.0
