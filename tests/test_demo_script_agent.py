import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.demo_script_agent import DemoScriptAgentService


def test_demo_script_agent_cnap_synthesis() -> None:
    data = DemoScriptAgentService.generate_demo_playbook(report_name="Gartner CNAP 2026")
    assert "report_scope" in data
    assert "CNAP" in data["report_scope"]
    assert "executive_summary" in data
    exec_sum = data["executive_summary"]
    assert "current_ga_capabilities" in exec_sum
    assert "future_capabilities_plan" in exec_sum
    assert "terraform_infrastructure_instructions" in exec_sum

    expectations = data["analyst_expectations"]
    assert "on_the_page" in expectations
    assert "not_on_the_page" in expectations
    assert len(data.get("scripted_modules", [])) >= 5

    mod = data["scripted_modules"][0]
    assert "scripted_actions" in mod
    assert len(mod["scripted_actions"]) >= 2
    assert "spoken_dialogue" in mod


def test_format_playbook_markdown_output() -> None:
    data = DemoScriptAgentService.generate_demo_playbook("devsecops")
    md = DemoScriptAgentService.format_playbook_markdown(data)
    assert "# 🎬 Phase 5: On-Demand Demo Environments & Storyboard Playbook" in md
    assert "## 🏆 Executive Summary: Current GA vs. Future Roadmap Strategy" in md
    assert "### What's Not on the Page (Implicit Analyst Psychology & Vision)" in md
    assert "#### 🛠️ Scripted Visual UI Actions & Console Flow" in md
    assert "#### 🎙️ Spoken Voice-Over Narration Dialogue" in md


@pytest.mark.asyncio
async def test_export_demo_playbook_rich_markdown() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/export/demo-playbook?report=cnap")
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        content = response.text
        assert "Gartner Magic Quadrant" in content
        assert "Current GA Bedrock Capabilities" in content
        assert "Spoken Voice-Over Narration Dialogue" in content


@pytest.mark.asyncio
async def test_a2ui_chat_invoke_demo_architect() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        payload = {
            "action_id": "generate_demo_script_agent",
            "message": "Invoke Sr. OPM Demo Architect",
            "context_data": {"report_name": "Magic Quadrant and Critical Capabilities for DevSecOps Platforms, 2026"}
        }
        response = await client.post("/api/v1/a2ui/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "Sr. OPM / PM Demo Script Architect" in data["response_text"]
        payloads = data.get("a2ui_payloads", [])
        assert len(payloads) == 1
        assert "demo_architect_preview_card" in payloads[0]
