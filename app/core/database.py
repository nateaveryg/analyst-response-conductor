import logging
from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger("conductor.database")


class Base(DeclarativeBase):
    """Declarative base for SQLAlchemy 2.0 ORM models."""
    pass


# Configure async engine with explicit connection pooling limits tailored for Cloud Run dynamic scaling
# to prevent database max_connections exhaustion during scale-out events.
engine: AsyncEngine = create_async_engine(
    settings.get_async_database_url,
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,
    echo=(settings.ENVIRONMENT == "development"),
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """
    Initialization hook that automatically executes `CREATE EXTENSION IF NOT EXISTS vector;`
    on startup to enable pgvector support inside Cloud SQL for PostgreSQL, ensures
    tables are instantiated, and seeds default catalog offerings if empty.
    """
    logger.info("Initializing database and verifying pgvector extension...")
    async with engine.begin() as conn:
        # Enable pgvector extension explicitly before any tables requiring Vector data type are created
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # Create all tables declared with Base (if they don't already exist)
        await conn.run_sync(Base.metadata.create_all)
        # Defensive column migration for existing workspaces table
        try:
            await conn.execute(text("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS current_phase INTEGER DEFAULT 1;"))
            await conn.execute(text("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS last_completed_step VARCHAR(255) DEFAULT 'Phase 1: Document Intake';"))
            await conn.execute(text("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS last_action_id VARCHAR(100) DEFAULT 'open_intake';"))
            await conn.execute(text("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS context_data_json TEXT DEFAULT '{}';"))
        except Exception:
            pass
    
    # Auto-seed database with Google portfolio items if missing from Product table
    try:
        import datetime
        from decimal import Decimal
        from sqlalchemy import select
        from app.models.core_models import Product
        
        async with async_session_factory() as session:
            result = await session.execute(select(Product))
            existing_names = {p.name for p in result.scalars().all()}
            
            default_catalog = [
                Product(
                    name="Gemini Code Assist Enterprise (Standard GA)",
                    current_ga_date=datetime.date(2024, 11, 15),
                    total_revenue_usd=Decimal("35000000.00"),
                    cagr_percentage=Decimal("65.0"),
                    enterprise_customer_count=620,
                ),
                Product(
                    name="Antigravity 2.0 (Standard GA)",
                    current_ga_date=datetime.date(2025, 5, 20),
                    total_revenue_usd=Decimal("145000000.00"),
                    cagr_percentage=Decimal("110.0"),
                    enterprise_customer_count=2100,
                ),
                Product(
                    name="Antigravity IDE (Standard GA)",
                    current_ga_date=datetime.date(2025, 8, 14),
                    total_revenue_usd=Decimal("88000000.00"),
                    cagr_percentage=Decimal("95.0"),
                    enterprise_customer_count=1450,
                ),
                Product(
                    name="Gemini Code Assist Agent Mode (Preview)",
                    current_ga_date=datetime.date(2026, 4, 15),
                    total_revenue_usd=Decimal("8500000.00"),
                    cagr_percentage=Decimal("120.0"),
                    enterprise_customer_count=410,
                ),
                Product(
                    name="Cloud Legacy Code Helper (Deprecated)",
                    current_ga_date=datetime.date(2022, 6, 1),
                    total_revenue_usd=Decimal("12000000.00"),
                    cagr_percentage=Decimal("15.0"),
                    enterprise_customer_count=210,
                ),
                Product(
                    name="Artifact Registry (Standard GA)",
                    current_ga_date=datetime.date(2020, 5, 15),
                    total_revenue_usd=Decimal("110000000.00"),
                    cagr_percentage=Decimal("55.0"),
                    enterprise_customer_count=3200,
                ),
                Product(
                    name="Cloud Build (Standard GA)",
                    current_ga_date=datetime.date(2018, 7, 24),
                    total_revenue_usd=Decimal("95000000.00"),
                    cagr_percentage=Decimal("48.0"),
                    enterprise_customer_count=2800,
                ),
                Product(
                    name="Cloud Deploy (Standard GA)",
                    current_ga_date=datetime.date(2021, 8, 30),
                    total_revenue_usd=Decimal("42000000.00"),
                    cagr_percentage=Decimal("60.0"),
                    enterprise_customer_count=850,
                ),
                Product(
                    name="Developer Connect (Standard GA)",
                    current_ga_date=datetime.date(2024, 4, 9),
                    total_revenue_usd=Decimal("28000000.00"),
                    cagr_percentage=Decimal("75.0"),
                    enterprise_customer_count=540,
                ),
                Product(
                    name="Security Command Center (SCC) Enterprise (Standard GA)",
                    current_ga_date=datetime.date(2023, 10, 10),
                    total_revenue_usd=Decimal("180000000.00"),
                    cagr_percentage=Decimal("52.0"),
                    enterprise_customer_count=1900,
                ),
                Product(
                    name="Gemini Agent Platform (Standard GA)",
                    current_ga_date=datetime.date(2025, 2, 10),
                    total_revenue_usd=Decimal("75000000.00"),
                    cagr_percentage=Decimal("72.0"),
                    enterprise_customer_count=1100,
                ),
                Product(
                    name="Application Design Center (Standard GA)",
                    current_ga_date=datetime.date(2024, 8, 15),
                    total_revenue_usd=Decimal("42000000.00"),
                    cagr_percentage=Decimal("55.0"),
                    enterprise_customer_count=650,
                ),
                Product(
                    name="Firebase Genkit & App Hosting (Standard GA)",
                    current_ga_date=datetime.date(2024, 5, 10),
                    total_revenue_usd=Decimal("85000000.00"),
                    cagr_percentage=Decimal("60.0"),
                    enterprise_customer_count=1300,
                ),
                Product(
                    name="Autonomous Cloud (AutoCloud) (Standard GA)",
                    current_ga_date=datetime.date(2025, 1, 20),
                    total_revenue_usd=Decimal("110000000.00"),
                    cagr_percentage=Decimal("68.0"),
                    enterprise_customer_count=1600,
                ),
                Product(
                    name="Google Cloud Run (Standard GA)",
                    current_ga_date=datetime.date(2019, 11, 14),
                    total_revenue_usd=Decimal("180000000.00"),
                    cagr_percentage=Decimal("85.0"),
                    enterprise_customer_count=2400,
                ),
                Product(
                    name="Google Kubernetes Engine (GKE) (Standard GA)",
                    current_ga_date=datetime.date(2015, 8, 26),
                    total_revenue_usd=Decimal("450000000.00"),
                    cagr_percentage=Decimal("65.0"),
                    enterprise_customer_count=3800,
                ),
            ]
            
            missing_products = [p for p in default_catalog if p.name not in existing_names]
            if missing_products:
                logger.info(f"Seeding {len(missing_products)} missing product(s) into catalog...")
                session.add_all(missing_products)
                await session.commit()
                logger.info("Catalog seeding completed successfully.")

            # Auto-seed default workspaces if Workspace table is empty
            from app.models.core_models import Workspace, SavedArtifact
            import json
            import uuid
            from datetime import datetime, timezone

            workspace_result = await session.execute(select(Workspace))
            workspaces = list(workspace_result.scalars().all())

            if not workspaces:
                logger.info("Seeding default enterprise analyst workspaces into database...")
                ws_cnap = Workspace(
                    id=uuid.uuid4(),
                    name="Gartner MQ 2026 - CNAP",
                    report_type="Gartner Magic Quadrant",
                    description="Primary enterprise evaluation workspace for Cloud-Native Application Platforms (CNAP) 2026.",
                    owner_email="analyst-relations-core@google.com",
                    co_editors_json=json.dumps(["enterprise-analyst@google.com", "cloud-ar-leads@google.com", "opm-leadership@google.com"]),
                    is_default=True,
                    current_phase=4,
                    last_completed_step="Phase 4B: Automated RAG Ingestion & Initial Technical Drafts",
                    last_action_id="generate_rfi_responses",
                    context_data_json=json.dumps({
                        "report_name": "Magic Quadrant and Critical Capabilities for Cloud-Native Application Platforms, 2026",
                        "welcome_packet_url": "https://docs.google.com/document/d/1iR1LEtCI5mlV_CNAP_2026",
                        "evaluation_id": "c89b6c87-1a36-4509-9337-451bf2cc52ba"
                    }),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                ws_devsecops = Workspace(
                    id=uuid.uuid4(),
                    name="Forrester Wave - DevSecOps 2026",
                    report_type="Forrester Wave",
                    description="Multi-tenant collaboration workspace for Forrester Wave DevSecOps evaluation.",
                    owner_email="sec-ops-leadership@google.com",
                    co_editors_json=json.dumps(["enterprise-analyst@google.com", "cloud-sec-team@google.com"]),
                    is_default=False,
                    current_phase=3,
                    last_completed_step="Phase 3: Stakeholder Kickoff & OPM Alignment Charter",
                    last_action_id="kickoff_project",
                    context_data_json=json.dumps({
                        "report_name": "Magic Quadrant and Critical Capabilities for DevSecOps Platforms, 2026",
                        "welcome_packet_url": "https://docs.google.com/spreadsheets/d/10uLRcBQehAx4h14cKy3zSgFjXNazcKTIM0Il7xB1_E8/edit"
                    }),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                ws_idc = Workspace(
                    id=uuid.uuid4(),
                    name="IDC MarketScape - Universal Platforms 2026",
                    report_type="IDC MarketScape",
                    description="Restricted analyst response workspace for IDC MarketScape evaluation.",
                    owner_email="cloud-pm-execs@google.com",
                    co_editors_json=json.dumps(["restricted-idc-leads@google.com"]),
                    is_default=False,
                    current_phase=1,
                    last_completed_step="Phase 1A: Criteria Document Intake",
                    last_action_id="open_intake",
                    context_data_json=json.dumps({
                        "report_name": "IDC MarketScape: Enterprise AI Pair Programming & Autonomous Agents 2026"
                    }),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add_all([ws_cnap, ws_devsecops, ws_idc])
                await session.commit()
                logger.info("Enterprise workspace seeding completed successfully.")
            else:
                # Ensure existing workspaces have current_phase and last_action_id populated
                updated_any = False
                for ws in workspaces:
                    if ws.name == "Gartner MQ 2026 - CNAP" and (ws.current_phase is None or ws.current_phase == 1):
                        ws.current_phase = 4
                        ws.last_completed_step = "Phase 4B: Automated RAG Ingestion & Initial Technical Drafts"
                        ws.last_action_id = "generate_rfi_responses"
                        ws.context_data_json = json.dumps({
                            "report_name": "Magic Quadrant and Critical Capabilities for Cloud-Native Application Platforms, 2026",
                            "welcome_packet_url": "https://docs.google.com/document/d/1iR1LEtCI5mlV_CNAP_2026",
                            "evaluation_id": "c89b6c87-1a36-4509-9337-451bf2cc52ba"
                        })
                        updated_any = True
                    elif ws.name == "Forrester Wave - DevSecOps 2026" and (ws.current_phase is None or ws.current_phase == 1):
                        ws.current_phase = 3
                        ws.last_completed_step = "Phase 3: Stakeholder Kickoff & OPM Alignment Charter"
                        ws.last_action_id = "kickoff_project"
                        ws.context_data_json = json.dumps({
                            "report_name": "Magic Quadrant and Critical Capabilities for DevSecOps Platforms, 2026",
                            "welcome_packet_url": "https://docs.google.com/spreadsheets/d/10uLRcBQehAx4h14cKy3zSgFjXNazcKTIM0Il7xB1_E8/edit"
                        })
                        updated_any = True
                if updated_any:
                    await session.commit()
                    logger.info("Updated existing enterprise workspaces with journey progress metadata.")

            # Clear all saved artifacts from storage on initialization (Production clean state)
            from sqlalchemy import delete
            await session.execute(delete(SavedArtifact))
            await session.commit()
            logger.info("Cleared all saved artifacts from storage.")

            # Auto-seed foundational RagDocumentChunk historical memory if table is empty
            from app.models.core_models import RagDocumentChunk
            rag_result = await session.execute(select(RagDocumentChunk))
            if not rag_result.scalars().first():
                logger.info("Seeding initial historical RAG prior RFI memory and technical documentation...")
                session.add_all([
                    RagDocumentChunk(
                        source_document_id="2025_Gartner_MQ_CNAP_Q6",
                        publication_year=2025,
                        product_tag="IAM & Workload Identity",
                        ga_status_at_time_of_writing="Standard GA",
                        chunk_type="Prior_RFI_Answer",
                        source_rfi_title="2025 Gartner Magic Quadrant for CNAP — [Tab 2: Security & Identity] Q6",
                        original_question_text="Describe authentication methods supported to integrate with enterprise IAM.",
                        original_answer_text="Natively integrates with Enterprise IAM via OIDC, SAML 2.0, Workload Identity Federation, and robust Secrets Manager integrations for container authentication.",
                        chunk_text="Question: Describe authentication methods supported to integrate with enterprise IAM.\nAnswer: Natively integrates with Enterprise IAM via OIDC, SAML 2.0, Workload Identity Federation, and robust Secrets Manager integrations for container authentication."
                    ),
                    RagDocumentChunk(
                        source_document_id="2025_Forrester_Wave_DevSecOps_Q9",
                        publication_year=2025,
                        product_tag="Gemini Code Assist & AI SDLC",
                        ga_status_at_time_of_writing="Standard GA",
                        chunk_type="Prior_RFI_Answer",
                        source_rfi_title="2025 Forrester Wave for DevSecOps — [Tab 3: AI Augmentation] Q9",
                        original_question_text="What AI SDLC assistance is natively provided for bug remediation and local repository indexing?",
                        original_answer_text="Integrates advanced Gemini Code Assist agentic AI directly into inner/outer developer loops for autonomous multi-turn bug resolution and local RAG code indexing.",
                        chunk_text="Question: What AI SDLC assistance is natively provided for bug remediation and local repository indexing?\nAnswer: Integrates advanced Gemini Code Assist agentic AI directly into inner/outer developer loops for autonomous multi-turn bug resolution and local RAG code indexing."
                    ),
                    RagDocumentChunk(
                        source_document_id="GCP_Data_Residency_Specs_2026",
                        publication_year=2026,
                        product_tag="Assured Workloads & Data Residency",
                        ga_status_at_time_of_writing="Standard GA",
                        chunk_type="Official_Doc",
                        source_rfi_title="Google Cloud Assured Workloads & Data Residency Sovereign Specs (2026)",
                        original_question_text="Describe how your platform meets customers' data residency requirements.",
                        original_answer_text="Offers Sovereign Cloud regions, regional geopatriation controls, customer-managed encryption keys (CMEK/EKM), and enforced Data Residency boundary parameters.",
                        chunk_text="Offers Sovereign Cloud regions, regional geopatriation controls, customer-managed encryption keys (CMEK/EKM), and enforced Data Residency boundary parameters."
                    ),
                    RagDocumentChunk(
                        source_document_id="GCP_Cloud_Run_Concurrency_Specs_2026",
                        publication_year=2026,
                        product_tag="Google Cloud Run Serverless",
                        ga_status_at_time_of_writing="Standard GA",
                        chunk_type="Official_Doc",
                        source_rfi_title="Google Cloud Run Concurrency & Serverless GPUs Specs (2026)",
                        original_question_text="Managed Serverless Container Runtimes & Scaling to Zero concurrency.",
                        original_answer_text="Natively hosts serverless container applications with auto-scaling to zero, high multi-thread concurrency per instance, and integrated serverless GPU attachment.",
                        chunk_text="Natively hosts serverless container applications with auto-scaling to zero, high multi-thread concurrency per instance, and integrated serverless GPU attachment."
                    )
                ])
                await session.commit()
                logger.info("Historical RAG corpus seeding completed successfully.")

            # Check and seed Forrester Wave Public Cloud Platforms Q3 2026 corpus
            forrester_chk = await session.execute(select(RagDocumentChunk).where(RagDocumentChunk.source_document_id.like("2026_Forrester_Wave_Cloud_Platforms_%")))
            if not forrester_chk.scalars().first():
                import json
                from pathlib import Path
                json_path = Path(__file__).parent.parent.parent / "forrester_wave_q3_2026_corpus.json"
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        forrester_data = json.load(f)
                    new_chunks = []
                    for idx, item in enumerate(forrester_data, 1):
                        new_chunks.append(RagDocumentChunk(
                            source_document_id=f"2026_Forrester_Wave_Cloud_Platforms_Q{idx:02d}",
                            publication_year=2026,
                            product_tag=f"Public Cloud Platforms — {item['domain']}",
                            ga_status_at_time_of_writing="Standard GA",
                            chunk_type="Prior_RFI_Answer",
                            source_rfi_title=f"2026 Forrester Wave Public Cloud Platforms — [{item['domain']}]",
                            original_question_text=item["question_text"],
                            original_answer_text=item["submitted_response"],
                            chunk_text=f"Question: {item['question_text']}\nAnswer: {item['submitted_response']}"
                        ))
                    session.add_all(new_chunks)
                    await session.commit()
                    logger.info(f"Seeded {len(new_chunks)} Forrester Wave Public Cloud Platforms Q3 2026 answers into RAG memory.")
    except Exception as e:
        logger.warning(f"Non-fatal error during auto-seeding catalog or artifacts: {e}")

    logger.info("Database and pgvector initialization completed successfully.")


async def get_db() -> AsyncGenerator[AsyncSession | None, None]:
    """
    FastAPI dependency that yields an asynchronous database session.
    Automatically closes session and handles rollback on unhandled exceptions.
    In offline developer environments or unit test execution without Postgres, handles socket errors gracefully.
    """
    has_yielded = False
    try:
        async with async_session_factory() as session:
            try:
                has_yielded = True
                yield session
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
                raise
    except Exception as conn_err:
        if not has_yielded:
            logger.warning(f"Offline test mode: could not initiate Postgres session ({conn_err}), yielding None.")
            yield None
        else:
            raise
