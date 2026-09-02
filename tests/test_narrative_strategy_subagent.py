import pytest
from app.services.subagents.narrative_strategy_agent import NarrativeStrategySubAgent


def test_narrative_strategy_subagent_cnap_generation():
    res = NarrativeStrategySubAgent.generate_narrative_strategy(report_name="Gartner CNAP MQ 2026")
    assert res["lead_author"] == "Mukul Saha"
    assert res["firm"] == "Gartner"
    assert "Solidify Google's position in the Leader Quadrant" in res["headline_goal"]
    assert "## 6. AR Strategic Evaluation & Leader Placement Strategy" in res["section6_markdown"]
    assert "Prior-Year Analyst Report Audit & Criticism Mitigation Strategy" in res["section6_markdown"]
    assert "2025 Caution 1: Prescriptive Workflows in Platform Blueprints" in res["section6_markdown"]
    assert "MITIGATED / RECTIFIED IN 2026" in res["section6_markdown"]
    assert "Demonstration Strategy & Video Timecode Proof" in res["section6_markdown"]
    assert "Agentic Lifecycle Management" in res["section6_markdown"]


def test_narrative_strategy_subagent_devsecops_generation():
    res = NarrativeStrategySubAgent.generate_narrative_strategy(report_name="Forrester Wave DevSecOps 2026")
    assert res["lead_author"] == "Sandy Carielli"
    assert res["firm"] == "Forrester Research"
    assert "Sandy Carielli" in res["section6_markdown"]
    assert "2025 Caution 1: Complex Policy Configuration Overhead" in res["section6_markdown"]
    assert "Software Supply Chain Security" in res["section6_markdown"]
