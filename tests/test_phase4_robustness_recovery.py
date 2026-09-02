import pytest
import uuid
import json
from unittest.mock import AsyncMock, MagicMock
from app.services.rfi_architect_agent import RfiArchitectAgentService
from app.services.a2ui_generator import A2UIGenerator
from app.api.v1.a2ui_chat import handle_a2ui_chat, A2UIChatRequest
from app.models.core_models import RfiQuestion, RagDocumentChunk


@pytest.mark.asyncio
async def test_malformed_spreadsheet_input_recovery():
    """
    Asserts that passing an unrecognized or malformed URL/string to ingest_multitab_spreadsheet
    returns a clean error dictionary with clear required inputs and recovery actions instead of crashing.
    """
    mock_db = AsyncMock()
    eval_id = uuid.uuid4()
    
    malformed_input = "https://example.com/not_a_valid_file_path"
    res = await RfiArchitectAgentService.ingest_multitab_spreadsheet(workbook_source=malformed_input, evaluation_id=eval_id, db_session=mock_db)
    
    assert res["status"] == "error"
    assert res["error_type"] == "INVALID_SPREADSHEET_SOURCE"
    assert "RFI Questionnaire Source Unrecognized" in res["recovery_message"]
    assert len(res["required_inputs"]) >= 3
    assert any("valid Google Sheets" in item for item in res["required_inputs"])


@pytest.mark.asyncio
async def test_zero_technical_questions_detected_recovery():
    """
    Asserts that if all worksheets in an ingested dictionary are administrative or instructional,
    the engine gracefully intercepts the deficit and returns clear end-user guidance on required question format.
    """
    mock_db = AsyncMock()
    eval_id = uuid.uuid4()
    
    instruction_only_workbook = {
        "sheets": {
            "Tab 1: Vendor Instructions": ["Please sign non-disclosure agreements and adhere to word counts."],
            "Tab 2: Scoring Legend & NDA": ["Score 1 = Not Offered, Score 5 = Natively Offered GA."]
        }
    }
    
    res = await RfiArchitectAgentService.ingest_multitab_spreadsheet(workbook_source=instruction_only_workbook, evaluation_id=eval_id, db_session=mock_db)
    
    assert res["status"] == "warning"
    assert res["error_type"] == "ZERO_TECHNICAL_QUESTIONS_DETECTED"
    assert "No Technical Questions Decomposed" in res["recovery_message"]
    assert any("explicit technical evaluation questions" in item for item in res["required_inputs"])
    assert res["instruction_tabs_count"] == 2
    assert res["decomposed_questions_count"] == 0


def test_generate_rfi_recovery_surface_rendering():
    """
    Verifies that generate_rfi_recovery_surface formats valid A2UI JSON containing alert status,
    required input bullet points, and interactive resolution buttons.
    """
    recovery_payload = {
        "error_type": "TEST_DEFICIT_DETECTED",
        "recovery_message": "An unsupported format was submitted.",
        "required_inputs": ["Input Rule 1: Google Sheet link", "Input Rule 2: Excel upload"]
    }
    surface_xml = A2UIGenerator.generate_rfi_recovery_surface(recovery_data=recovery_payload, context_data={"analyst_report": "Gartner DevSecOps MQ"})
    
    assert "<a2ui-json>" in surface_xml and "</a2ui-json>" in surface_xml
    json_str = surface_xml.replace("<a2ui-json>", "").replace("</a2ui-json>", "").strip()
    data = json.loads(json_str)
    
    assert data["surfaceId"] == "rfi_recovery_card"
    components = data["components"]
    
    # Assert alert box presence
    card_comps = [c for c in components if "Card" in c["component"]]
    assert len(card_comps) >= 1
    assert card_comps[0]["component"]["Card"]["title"] == "Validation Status: Test Deficit Detected"
    
    # Assert recovery action buttons
    btn_comps = [c["component"]["Button"]["action"]["eventId"] for c in components if "Button" in c["component"]]
    assert "auto_populate_rfi_demo" in btn_comps
    assert "upload_rfi" in btn_comps
    assert "copy_sample_spreadsheet_link" in btn_comps


@pytest.mark.asyncio
async def test_a2ui_chat_malformed_ingestion_interception_and_recovery():
    """
    Asserts that sending a malformed RFI ingest message in conversational chat routes to defensive recovery,
    and clicking auto-populate restores 100% RAG grounding without errors.
    """
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    
    # Step 1: Submit malformed ingestion command
    payload_bad = A2UIChatRequest(message="ingest rfi broken_random_text", action_id="ingest_rfi", context_data={"evaluation_id": "test-val"})
    res_bad = await handle_a2ui_chat(payload_bad, db=mock_db)
    
    assert "Phase 4: Ingestion Input Assistance & Recovery" in res_bad.response_text
    assert len(res_bad.a2ui_payloads) == 1
    assert "rfi_recovery_card" in res_bad.a2ui_payloads[0]
    
    # Step 2: Trigger sample link guidance
    payload_sample = A2UIChatRequest(message="view sample link", action_id="copy_sample_spreadsheet_link", context_data={})
    res_sample = await handle_a2ui_chat(payload_sample, db=mock_db)
    assert "Verified Sample DevSecOps RFI Spreadsheet Link" in res_sample.response_text
    assert "10uLRcBQehAx4h14cKy3zSgFjXNazcKTIM0Il7xB1_E8" in res_sample.a2ui_payloads[0]
    
    # Step 3: Trigger auto_populate demo benchmark recovery action
    # Configure mock execute to return RfiQuestion first and RagDocumentChunk second for RfiArchitectAgentService.generate_grounded_drafts
    mock_q = RfiQuestion(id=uuid.uuid4(), evaluation_id="test-val", section_identifier="[Tab 1] Q1", worksheet_tab="Security", question_text="IAM integration capability", assigned_sme_id="security-sme@google.com", response_status="Drafted")
    mock_chunk = RagDocumentChunk(id=uuid.uuid4(), chunk_type="Historical RFI", chunk_text="Native IAM via SAML and Workload Identity.", source_rfi_title="2025 Gartner CNAP")
    
    mock_res_q = MagicMock()
    mock_res_q.scalars.return_value.all.return_value = [mock_q]
    mock_res_chunk = MagicMock()
    mock_res_chunk.scalars.return_value.all.return_value = [mock_chunk]
    mock_db.execute.side_effect = [mock_res_q, mock_res_chunk]
    
    payload_demo = A2UIChatRequest(message="run benchmark rfi", action_id="auto_populate_rfi_demo", context_data={"evaluation_id": "test-val"})
    res_demo = await handle_a2ui_chat(payload_demo, db=mock_db)
    
    assert "Phase 4: Auto-Populated Benchmark RFI Execution" in res_demo.response_text
    assert "2026 Gartner DevSecOps Benchmark Spreadsheet" in res_demo.response_text
    assert len(res_demo.a2ui_payloads) == 1
    assert "rfi_response_card" in res_demo.a2ui_payloads[0]
