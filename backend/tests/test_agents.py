from datetime import date
import json
import pytest

from app.modules.agents.llm_client import GeminiClient, MultiProviderLLMRouter
from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentExtractedLeave,
    AIRecommendation,
)


def test_gemini_client_fallback_leave_parsing():
    client = GeminiClient()
    response_json = client._fallback_response("I need 2 days off next Monday for personal reasons")
    data = json.loads(response_json)

    assert data["is_leave_request"] is True
    assert "start_date" in data
    assert "end_date" in data
    assert data["confidence"] >= 0.8


def test_gemini_client_fallback_sick_leave_detection():
    client = GeminiClient()
    response_json = client._fallback_response("I am sick with high fever and need to see a doctor for 3 days")
    data = json.loads(response_json)

    assert data["is_leave_request"] is True
    assert data["leave_type"] == "sick"


def test_gemini_client_fallback_annual_leave_detection():
    client = GeminiClient()
    response_json = client._fallback_response("Planning a family vacation next week for 5 days")
    data = json.loads(response_json)

    assert data["is_leave_request"] is True
    assert data["leave_type"] == "annual"


def test_agent_chat_request_schema():
    req = AgentChatRequest(message="What is my annual leave balance?")
    assert req.message == "What is my annual leave balance?"
    assert req.conversation_id is None


def test_ai_recommendation_schema():
    rec = AIRecommendation(
        decision="APPROVE",
        confidence_score=0.97,
        reasoning="All leave criteria satisfied.",
        policy_citations=["Rule 4.1: Entitlement standard"],
        suggested_comment="Auto-approved by policy engine.",
    )
    assert rec.decision == "APPROVE"
    assert rec.confidence_score == 0.97
    assert len(rec.policy_citations) == 1


@pytest.mark.asyncio
async def test_multi_provider_router_fallback_to_deterministic():
    router = MultiProviderLLMRouter()
    text, provider, model = await router.generate_with_metadata(
        "System directive",
        "I need 2 days off next Monday for medical checkup"
    )
    assert provider == "deterministic"
    assert model == "workforceai-rule-engine-v1"
    parsed = json.loads(text)
    assert parsed["is_leave_request"] is True
    assert parsed["leave_type"] == "sick"


@pytest.mark.asyncio
async def test_multi_provider_router_failover_on_quota_exhausted(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from app.config import get_settings
    settings = get_settings()

    monkeypatch.setattr(settings, "LLM_ROUTING_ORDER", "omniroute,openrouter,deterministic")
    monkeypatch.setattr(settings, "OMNIROUTE_API_KEY", "real-omniroute-key-123")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "real-openrouter-key-456")

    import httpx

    # Simulate OmniRoute returning 402 (payment required/credits out) and OpenRouter returning 429
    calls = []

    async def mock_post(self, url, *args, **kwargs):
        calls.append(str(url))
        resp = MagicMock()
        if "omniroute" in str(url):
            resp.status_code = 402
            resp.text = "Payment Required: insufficient credits"
        elif "openrouter" in str(url):
            resp.status_code = 429
            resp.text = "Rate Limit Exceeded"
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    router = MultiProviderLLMRouter()
    text, provider, model = await router.generate_with_metadata(
        "System directive",
        "Vacation next week for 4 days"
    )

    # Should have tried both and fallen back cleanly to deterministic
    assert len(calls) == 2
    assert provider == "deterministic"
    parsed = json.loads(text)
    assert parsed["leave_type"] == "annual"


def test_agent_chat_response_telemetry():
    resp = AgentChatResponse(
        reply="Your request has been drafted.",
        provider="omniroute",
        model="gpt-4o-mini",
    )
    assert resp.provider == "omniroute"
    assert resp.model == "gpt-4o-mini"

