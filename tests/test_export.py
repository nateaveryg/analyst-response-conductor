import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_export_deep_dive_report():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/export/deep-dive-report")
        assert response.status_code == 200
        assert "universal_analyst_evaluation_deep_dive_report.md" in response.headers.get("content-disposition", "")
        assert "Universal Analyst Evaluation & RFI Orchestration Report" in response.text
        assert "Considered vs. Rejected Offerings" in response.text
        assert "Table 2.1: Feature Alignment Matrix (Mandatory vs. Common Features)" in response.text
        assert "Table 2.2: Critical Capabilities & Use Cases Alignment Matrix" in response.text
        assert "Table 2.3: Strategic Analyst Evaluation Dimensions" in response.text
        assert "Verbatim Requirement Text (Supplied Analyst Document) | Scorable Capabilities & Features | Feature Category | Welcome Packet Requirement Classification | Satisfying Product Offering Name" in response.text
        assert "Verbatim Critical Capability / Use Case Definition (Supplied Doc)" in response.text
        assert "Completeness of Vision" in response.text
        assert "Ability to Execute" in response.text
        assert "Mandatory Features" in response.text
        assert "Common Features" in response.text
        assert "Gemini Code Assist Enterprise" in response.text
        assert "Gemini Agent Platform" in response.text
        assert "Autonomous Cloud (AutoCloud)" in response.text
        assert "Gemini Code Assist Agent Mode" in response.text
        assert "7-Phase Operational Process | Milestone / Activity | Target Date" in response.text
        assert "1. Evaluate Inclusion Criteria & Strategic Participation" in response.text
        assert "2. Auto-Generate Schedules & Assign Tasks" in response.text
        assert "3. Kick Off Response Project & Align Teams" in response.text
        assert "4. Generate Initial RFI Responses" in response.text
        assert "5. Deploy On-Demand Demo Environments" in response.text
        assert "6. Manage Executive Reviews & Address Inaccuracies" in response.text
        assert "7. Finalize Publication Strategy & Recognize Contributors" in response.text


@pytest.mark.asyncio
async def test_export_workback_schedule_both_formats():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_md = await client.get("/api/v1/export/workback-schedule?format=md")
        assert res_md.status_code == 200
        assert "universal_workback_schedule.md" in res_md.headers.get("content-disposition", "")
        assert "Exclusive Workback Schedule" in res_md.text
        assert "7-Phase Operational Process | Milestone / Activity | Offset | Target Date" in res_md.text
        assert "5. Deploy On-Demand Demo Environments" in res_md.text

        res_csv = await client.get("/api/v1/export/workback-schedule?format=csv")
        assert res_csv.status_code == 200
        assert "universal_workback_schedule.csv" in res_csv.headers.get("content-disposition", "")
        assert "7-Phase Operational Process,Milestone Name,Offset (Days)" in res_csv.text
        assert "5. Deploy On-Demand Demo Environments" in res_csv.text
        assert "Demo Script Rehearsal & Dry-Run" in res_csv.text


@pytest.mark.asyncio
async def test_a2ui_chat_deep_dive_action():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "deep dive analysis", "action_id": "deep_dive_analysis"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Comprehensive Portfolio Deep Dive & Rejection Deficit Analysis" in data["response_text"]
        assert "Qualifying Flagship SKU: Gemini Code Assist Enterprise" in data["response_text"]
        assert "Antigravity 2.0" in data["response_text"]
        assert "Antigravity IDE" in data["response_text"]
        assert "Considered & Rejected SKU: Gemini Code Assist Agent Mode" in data["response_text"]
        assert "Deep Dive Portfolio Analysis & Threshold Deficit Breakdown" in data["a2ui_payloads"][0]


@pytest.mark.asyncio
async def test_export_rfi_responses_markdown_and_csv():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_md = await client.get("/api/v1/export/rfi-responses?format=md")
        assert res_md.status_code == 200
        assert "gartner_rfi_completed_responses.md" in res_md.headers.get("content-disposition", "")
        assert "Completed RFI Technical Responses" in res_md.text
        assert "David Jacobs" in res_md.text
        assert "Google Cloud Support & OSS Assurance" in res_md.text

        res_csv = await client.get("/api/v1/export/rfi-responses?format=csv")
        assert res_csv.status_code == 200
        assert "gartner_rfi_completed_responses.csv" in res_csv.headers.get("content-disposition", "")
        assert "Question & Capability Requirement" in res_csv.text
        assert "David Jacobs" in res_csv.text
        assert "Nate Avery" in res_csv.text


@pytest.mark.asyncio
async def test_export_deep_dive_report_cnap_strategy():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_md = await client.get("/api/v1/export/deep-dive-report?report=cnap")
        assert res_md.status_code == 200
        assert "gartner_cnap_mq_strategic_evaluation_deep_dive_report.md" in res_md.headers.get("content-disposition", "")
        assert "AR Strategic Evaluation & Leader Placement Strategy" in res_md.text
        assert "Mukul Saha" in res_md.text
        assert "Vs. Microsoft Azure" in res_md.text


@pytest.mark.asyncio
async def test_export_kickoff_deck_endpoint_cnap():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_md = await client.get("/api/v1/export/kickoff-deck?format=md&report=cnap")
        assert res_md.status_code == 200
        assert "2026_cnap_mq_kickoff_presentation_deck.md" in res_md.headers.get("content-disposition", "")
        assert "Executive Stakeholder Kickoff Presentation Deck" in res_md.text
        assert "April 1st, 2026" in res_md.text
        assert "@gosiagnyp" in res_md.text


@pytest.mark.asyncio
async def test_export_rfi_responses_cnap():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_md = await client.get("/api/v1/export/rfi-responses?format=md&report=cnap")
        assert res_md.status_code == 200
        assert "gartner_cnap_rfi_completed_responses.md" in res_md.headers.get("content-disposition", "")
        assert "Google Cloud Run Serverless Concurrency & GPUs" in res_md.text
        assert "Google Kubernetes Engine (GKE) & Application Design Center" in res_md.text


@pytest.mark.asyncio
async def test_export_demo_playbook_both_scopes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_devsecops = await client.get("/api/v1/export/demo-playbook?report=devsecops")
        assert res_devsecops.status_code == 200
        assert "gartner_demo_script_playbook.md" in res_devsecops.headers.get("content-disposition", "")
        assert "60 Minutes Overall Cap" in res_devsecops.text
        assert "David Jacobs" in res_devsecops.text

        res_cnap = await client.get("/api/v1/export/demo-playbook?report=cnap")
        assert res_cnap.status_code == 200
        assert "gartner_cnap_demo_script_playbook.md" in res_cnap.headers.get("content-disposition", "")
        assert "45 Minutes Overall Cap" in res_cnap.text
        assert "Serverless Domain Lead" in res_cnap.text


@pytest.mark.asyncio
async def test_export_executive_review_memo():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/export/executive-review-memo?report=cnap")
        assert res.status_code == 200
        assert "gartner_cnap_executive_review_memo.md" in res.headers.get("content-disposition", "")
        assert "APPROVED BY EXECUTIVE REVIEW PANEL" in res.text
        assert "Mukul Saha MQ Engagement Leadership Team" in res.text


@pytest.mark.asyncio
async def test_export_final_publication_bundle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/export/final-publication-bundle?report=cnap")
        assert res.status_code == 200
        assert "gartner_cnap_final_publication_and_recognition.md" in res.headers.get("content-disposition", "")
        assert "100% COMPLETE & APPROVED FOR UPLOAD" in res.text
        assert "Cloud-Native Application Platforms (CNAP) Evaluation Champions" in res.text
