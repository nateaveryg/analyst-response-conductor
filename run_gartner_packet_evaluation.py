import asyncio
import datetime
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from app.models.core_models import Product, RfiQuestion
from app.schemas.inclusion_schemas import ParsedRfiCriteria
from app.schemas.orchestration_schemas import ExclusionWindow, WorkbackTimeline
from app.services.inclusion_analyzer import InclusionAnalyzer
from app.services.timeline_engine import TimelineEngine
from app.services.routing_engine import RoutingEngine

GARTNER_WELCOME_PACKET_TEXT = """
Inclusion Criteria for Magic Quadrant and Critical Capabilities for AI Coding Agents 2026

To qualify for inclusion, providers must meet the following criteria effective 2 March 2026 (all GA and market-participation thresholds must be met by this date):

Market Participation Inclusion Criteria:
1. Their offering meets Gartner's Market Definition for AI Coding Agents (autonomous or semiautonomous software engineering solutions that perceive context, translate human intent into multistep plans, and execute/verify across code, tests, and artifacts).
2. The AI coding agent and all listed mandatory features are generally available (not beta/limited access/preview) and fully supported for production use by customers as of 2 March 2026.
3. The AI coding agent must be purchasable with a public-facing price sheet and usable without dependency on the provider's developer platform.
4. The provider must sell directly to paying customers without requiring professional services to purchase or run the product.

Performance Inclusion Criteria (focused on calendar year 2025 performance and as-of 31 December 2025 levels):
Providers must meet ONE of the following criteria:
1. >= 500 paying customer organizations (logos); excluding education, free use and trials OR
2. >= $25 million recognized GAAP revenue from the AI coding agent in calendar year 2025, AND EITHER:
   - >= 40% year-over-year revenue growth in 2025, OR
   - >= 50 net-new paying customer organizations added in 2025.

Submission Deadlines:
- Return signed threshold attestation and question responses within five business days by Friday, 27th February 2026, 5:00 PM EST.
- Full research schedule and key dates shared in the week of 2nd March 2026.
"""

async def run_evaluation() -> None:
    print("=" * 80)
    print("🎯 LIVE SIMULATION: GARTNER AI CODING AGENTS 2026 WELCOME PACKET")
    print("=" * 80)
    print("\n⚠️  IMPORTANT ONBOARDING REQUEST TO END USER:")
    print("    To ensure complete evaluation accuracy, workback timeline scheduling,")
    print("    and SME task routing, please make all documents (Welcome Packets,")
    print("    Vendor Demonstration Guidelines, RFI attachments) and analyst communications/emails")
    print("    related to criteria available to the agent.")
    print("=" * 80)
    print("\n[INFO] 1. Parsing Gartner Welcome Packet Inclusion Criteria...")

    mock_db = AsyncMock()
    
    criteria = ParsedRfiCriteria(
        target_ga_cutoff_date=datetime.date(2026, 3, 2),
        min_revenue_usd=Decimal("25000000.00"),
        min_cagr_percentage=Decimal("40.0"),
        min_enterprise_customer_count=500,
        confidence_score=0.98,
        raw_explanation="Extracted from Gartner MQ AI Coding Agents 2026 Welcome Packet: GA cutoff 2026-03-02, $25M GAAP revenue w/ 40% CAGR OR 500+ logos."
    )

    print(f"   -> Extracted GA Cutoff Date : {criteria.target_ga_cutoff_date}")
    print(f"   -> Min Revenue Requirement  : ${criteria.min_revenue_usd:,.2f}")
    print(f"   -> Min Growth / CAGR Target : {criteria.min_cagr_percentage}%")
    print(f"   -> Min Customer Logos Floor : {criteria.min_enterprise_customer_count}")
    print(f"   -> Confidence Score         : {criteria.confidence_score * 100:.1f}%\n")

    products = [
        Product(
            id=uuid.uuid4(),
            name="Gemini Code Assist Enterprise (Standard GA)",
            current_ga_date=datetime.date(2025, 11, 15),
            total_revenue_usd=Decimal("68000000.00"),
            cagr_percentage=Decimal("62.5"),
            enterprise_customer_count=820,
        ),
        Product(
            id=uuid.uuid4(),
            name="Gemini Code Assist Agent Mode (Preview)",
            current_ga_date=datetime.date(2026, 4, 15),  # Post-GA cutoff (Preview as of March 2)
            total_revenue_usd=Decimal("31000000.00"),
            cagr_percentage=Decimal("85.0"),
            enterprise_customer_count=410,
        ),
        Product(
            id=uuid.uuid4(),
            name="Cloud Legacy Code Helper (Deprecated)",
            current_ga_date=datetime.date(2024, 1, 1),
            total_revenue_usd=Decimal("12000000.00"),  # Below $25M revenue floor
            cagr_percentage=Decimal("15.0"),           # Below 40% CAGR floor
            enterprise_customer_count=210,             # Below 500 logo floor
        )
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = products
    mock_db.execute.return_value = mock_result

    analyzer = InclusionAnalyzer(db_session=mock_db)
    print("[INFO] 2. Executing Portfolio Eligibility Evaluation against 3 Google Offerings...")
    matrix = await analyzer.evaluate_portfolio_eligibility(criteria)

    print(f"   -> Overall Data-Driven Recommendation : {matrix.data_driven_recommendation}")
    print(f"   -> Eligible Products ({len(matrix.eligible_products)}) : {', '.join(matrix.eligible_products)}")
    print(f"   -> Total Rule Violations ({len(matrix.rule_violations)}) :")
    for v in matrix.rule_violations:
        print(f"      ❌ {v}")

    print("\n" + "=" * 80)
    print("[INFO] 3. Generating Workback Timeline with Corporate Exclusion Windows...")
    print("=" * 80)
    
    target_deadline = datetime.datetime(2026, 6, 20, 17, 0, tzinfo=datetime.timezone.utc)
    
    exclusion_windows = [
        ExclusionWindow(
            name="Google Cloud Next 2026 Conference Freeze",
            start_date=datetime.datetime(2026, 6, 14, 0, 0, tzinfo=datetime.timezone.utc),
            end_date=datetime.datetime(2026, 6, 16, 23, 59, tzinfo=datetime.timezone.utc),
        ),
        ExclusionWindow(
            name="Q2 Corporate Earnings Blackout",
            start_date=datetime.datetime(2026, 6, 8, 0, 0, tzinfo=datetime.timezone.utc),
            end_date=datetime.datetime(2026, 6, 9, 23, 59, tzinfo=datetime.timezone.utc),
        )
    ]

    timeline: WorkbackTimeline = TimelineEngine.generate_timeline(target_deadline, exclusion_windows)
    print(f"   -> External Target Deadline : {timeline.external_deadline.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"   -> Active Exclusion Windows : {len(exclusion_windows)}\n")
    
    for idx, m in enumerate(timeline.milestones, 1):
        status_icon = "⚠️ SHIFTED" if m.shifted else "✅ NORMAL"
        print(f"   [{idx}] {m.name} ({m.offset_days})")
        print(f"       Target Date : {m.target_date.strftime('%Y-%m-%d %H:%M %Z')} [{status_icon}]")
        if m.shifted:
            print(f"       Original    : {m.original_date.strftime('%Y-%m-%d %H:%M %Z')}")
            print(f"       Reason      : {m.shift_reason}")
        print()

    print("=" * 80)
    print("[INFO] 4. Executing Dynamic SME Question Routing Engine...")
    print("=" * 80)

    eval_id = uuid.uuid4()
    sample_questions = [
        RfiQuestion(
            id=uuid.uuid4(),
            evaluation_id=eval_id,
            section_identifier="2.1",
            question_text="Does your AI coding agent autonomously execute multi-step test verification across CI/CD pipelines without human intervention?",
            response_status="Unassigned"
        ),
        RfiQuestion(
            id=uuid.uuid4(),
            evaluation_id=eval_id,
            section_identifier="3.4",
            question_text="What data encryption, governance guardrails, and devsecops mechanisms prevent the model from training on customer source code and documentation?",
            response_status="Unassigned"
        ),
        RfiQuestion(
            id=uuid.uuid4(),
            evaluation_id=eval_id,
            section_identifier="4.2",
            question_text="Can the agent generate SQL schema migrations and deploy containerized microservices to Google Cloud Run and Cloud SQL?",
            response_status="Unassigned"
        ),
        RfiQuestion(
            id=uuid.uuid4(),
            evaluation_id=eval_id,
            section_identifier="5.1",
            question_text="What are the standard pricing tiers, contractual SLAs, and invoicing payment terms for enterprise billing?",
            response_status="Unassigned"
        )
    ]

    routing_engine = RoutingEngine(db_session=mock_db, fallback_sme="opm-coordinator@google.com")
    routing_results = await routing_engine.route_questions(
        questions=sample_questions,
        confidence_threshold=0.7
    )

    for idx, r in enumerate(routing_results, 1):
        match_type = "🎯 DOMAIN SME ASSIGNED" if r.assigned_sme_id != "opm-coordinator@google.com" else "🛡️ FALLBACK COORDINATOR"
        print(f"   Q[{sample_questions[idx-1].section_identifier}]: {sample_questions[idx-1].question_text[:65]}...")
        print(f"       Assigned SME : {r.assigned_sme_id} ({match_type})")
        print(f"       Confidence   : {r.confidence_score * 100:.1f}%")
        print(f"       Method       : {r.routing_method}")
        print()

    print("=" * 80)
    print("🎉 EVALUATION COMPLETE: All modules executed successfully on Gartner Welcome Packet!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
