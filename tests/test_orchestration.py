import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.models.core_models import RfiQuestion
from app.schemas.orchestration_schemas import ExclusionWindow, WorkbackTimeline, RoutingResult
from app.services.timeline_engine import TimelineEngine
from app.services.routing_engine import RoutingEngine


def test_timeline_engine_standard_offsets_no_exclusion() -> None:
    """
    Verify TimelineEngine computes accurate backward offsets across all 12 milestones
    and tags each with its assigned 7-Phase End-to-End Operational Process.
    """
    deadline = datetime.datetime(2026, 6, 20, 17, 0, tzinfo=datetime.timezone.utc)
    timeline: WorkbackTimeline = TimelineEngine.generate_timeline(target_deadline=deadline, exclusion_windows=[])

    assert len(timeline.milestones) == 12
    assert timeline.external_deadline == deadline

    # Convert to dict mapped by name for assertions
    milestone_map = {m.name: m for m in timeline.milestones}

    assert milestone_map["External Deadline"].target_date == deadline
    assert milestone_map["External Deadline"].operational_phase == "7. Finalize Publication Strategy & Recognize Contributors"
    assert milestone_map["Final QA, Packaging, and Form Submission"].target_date == deadline - datetime.timedelta(days=2)
    assert milestone_map["Executive Approval Panel Review"].target_date == deadline - datetime.timedelta(days=5)
    assert milestone_map["Final Video Recording & TOC Bookmark Verification"].target_date == deadline - datetime.timedelta(days=8)
    assert milestone_map["Consolidated OPM/SME Technical Review Session"].target_date == deadline - datetime.timedelta(days=9)
    assert milestone_map["Demo Script Rehearsal & Dry-Run"].target_date == deadline - datetime.timedelta(days=10)
    assert milestone_map["Demo Environment & Sandbox Deployment"].target_date == deadline - datetime.timedelta(days=12)
    assert milestone_map["Initial SME Curation Draft Deadline"].target_date == deadline - datetime.timedelta(days=15)
    assert milestone_map["Automated RAG Ingestion and Draft Pre-population"].target_date == deadline - datetime.timedelta(days=16)
    assert milestone_map["Automated RAG Ingestion and Draft Pre-population"].operational_phase == "4. Generate Initial RFI Responses"
    assert milestone_map["Stakeholder Kickoff & Response Project Alignment"].target_date == deadline - datetime.timedelta(days=18)
    assert milestone_map["Automated Workback Schedule & Task Routing"].target_date == deadline - datetime.timedelta(days=19)
    assert milestone_map["Portfolio Eligibility & Go/No-Go Evaluation"].target_date == deadline - datetime.timedelta(days=20)
    assert milestone_map["Portfolio Eligibility & Go/No-Go Evaluation"].operational_phase == "1. Evaluate Inclusion Criteria & Strategic Participation"

    # Asserts no milestones shifted
    for m in timeline.milestones:
        assert m.shifted is False
        assert m.shift_reason is None


def test_timeline_engine_with_exclusion_window_shift() -> None:
    """
    Verify TimelineEngine shifts milestones and all prior milestones back in time
    when a calculated date falls inside a corporate exclusion window (e.g. Cloud Next),
    plus a 24-hour buffer.
    """
    deadline = datetime.datetime(2026, 6, 20, 17, 0, tzinfo=datetime.timezone.utc)
    # T-5 milestone ("Executive Approval Panel Review") falls on 2026-06-15 17:00:00.
    # We define an exclusion window from 2026-06-14 00:00:00 to 2026-06-16 23:59:59 ("Google Cloud Next").
    cloud_next = ExclusionWindow(
        name="Google Cloud Next",
        start_date=datetime.datetime(2026, 6, 14, 0, 0, tzinfo=datetime.timezone.utc),
        end_date=datetime.datetime(2026, 6, 16, 23, 59, tzinfo=datetime.timezone.utc),
    )

    timeline: WorkbackTimeline = TimelineEngine.generate_timeline(
        target_deadline=deadline,
        exclusion_windows=[cloud_next]
    )

    milestone_map = {m.name: m for m in timeline.milestones}

    # Day T (June 20) and T-2 (June 18) are after Cloud Next (June 14-16), so not shifted
    assert milestone_map["External Deadline"].shifted is False
    assert milestone_map["Final QA, Packaging, and Form Submission"].shifted is False

    # Day T-5 (June 15) fell inside Cloud Next.
    # It must shift to right before start_date (June 14) plus 24-hour buffer -> June 13
    shifted_panel_date = datetime.datetime(2026, 6, 13, 0, 0, tzinfo=datetime.timezone.utc)
    assert milestone_map["Executive Approval Panel Review"].shifted is True
    assert milestone_map["Executive Approval Panel Review"].target_date == shifted_panel_date

    # All earlier milestones (T-9, T-15, T-18) must also be shifted earlier by the accumulated shift difference
    # Original T-5 was June 15 17:00, new is June 13 00:00 (difference: 2 days + 17 hours = 2 days, 17:00:00)
    accumulated_delta = datetime.datetime(2026, 6, 15, 17, 0, tzinfo=datetime.timezone.utc) - shifted_panel_date
    for name in [
        "Consolidated OPM/SME Technical Review Session",
        "Initial SME Curation Draft Deadline",
        "Automated RAG Ingestion and Draft Pre-population",
    ]:
        original = milestone_map[name].original_date
        assert milestone_map[name].shifted is True
        assert milestone_map[name].target_date == original - accumulated_delta


@pytest.mark.asyncio
async def test_routing_engine_keyword_matches_and_fallback() -> None:
    """
    Verify RoutingEngine maps RFI questions to correct SMEs using keyword/domain rules,
    and falls back to OPM coordinator when no domain match clears confidence threshold.
    """
    mock_db = AsyncMock()

    eval_id = uuid.uuid4()
    q_devops = RfiQuestion(
        id=uuid.uuid4(),
        evaluation_id=eval_id,
        section_identifier="3.1.2",
        question_text="Describe how your CI/CD pipeline and Cloud Build integrate with container registries.",
        response_status="Unassigned",
    )
    q_security = RfiQuestion(
        id=uuid.uuid4(),
        evaluation_id=eval_id,
        section_identifier="4.2.1",
        question_text="Detail your data encryption at rest and Workload Identity IAM roles.",
        response_status="Unassigned",
    )
    q_unknown = RfiQuestion(
        id=uuid.uuid4(),
        evaluation_id=eval_id,
        section_identifier="9.9.9",
        question_text="Provide executive summary of billing discounts for multi-year enterprise contracts.",
        response_status="Unassigned",
    )

    routing_engine = RoutingEngine(db_session=mock_db, fallback_sme="opm-coordinator@google.com")

    results: list[RoutingResult] = await routing_engine.route_questions(
        questions=[q_devops, q_security, q_unknown],
        confidence_threshold=0.7,
    )

    assert len(results) == 3

    # Check DevOps routing
    assert results[0].question_id == q_devops.id
    assert results[0].assigned_sme_id == "devops-sme@google.com"
    assert results[0].routing_method == "Keyword/Semantic Match"
    assert q_devops.response_status == "SME_Review"

    # Check Security routing
    assert results[1].question_id == q_security.id
    assert results[1].assigned_sme_id == "security-sme@google.com"
    assert results[1].routing_method == "Keyword/Semantic Match"
    assert q_security.response_status == "SME_Review"

    # Check Fallback coordinator routing
    assert results[2].question_id == q_unknown.id
    assert results[2].assigned_sme_id == "opm-coordinator@google.com"
    assert results[2].routing_method == "Fallback Coordinator"
    assert q_unknown.response_status == "SME_Review"

    # Assert database commit called
    mock_db.commit.assert_awaited_once()
