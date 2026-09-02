import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_query_corpus_of_data():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": "show me the corpus of data from which you match products"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Active Product Evaluation Corpus" in data["response_text"]
        assert "from which I match and evaluate SKUs" in data["response_text"]

@pytest.mark.asyncio
async def test_query_rerun_evaluation_mix():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        msg = "rerun the evaluation using a mix of products including but not limited to artifact registry, cloud build, cloud deploy, developer connect, and Gemini Code Assist Enterprise"
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": msg}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Portfolio Eligibility Scorecard" in data["response_text"]
        # Ensure our requested product mix is represented in the dynamic summary or payload
        assert "Artifact Registry" in data["response_text"] or "Artifact Registry" in str(data["a2ui_payloads"])
        assert "Cloud Build" in data["response_text"] or "Cloud Build" in str(data["a2ui_payloads"])
        assert "Developer Connect" in data["response_text"] or "Developer Connect" in str(data["a2ui_payloads"])

@pytest.mark.asyncio
async def test_query_scorecard_with_scc():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        msg = "Run the Scorecard with SCC as an addition to the reply that uses Gemini Code Assist Enterprise as the Qualifying Flagship Offering"
        response = await client.post(
            "/api/v1/a2ui/chat",
            json={"message": msg}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Portfolio Eligibility Scorecard" in data["response_text"]
        assert "Security Command Center" in data["response_text"] or "Security Command Center" in str(data["a2ui_payloads"])
