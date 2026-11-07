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
        decision_provider="openrouter",
        decision_model="meta-llama/llama-3.3-70b-instruct:free",
        chat_provider="omniroute",
        chat_model="gpt-4o-mini",
    )
    assert resp.provider == "omniroute"
    assert resp.model == "gpt-4o-mini"
    assert resp.decision_provider == "openrouter"
    assert resp.decision_model == "meta-llama/llama-3.3-70b-instruct:free"
    assert resp.chat_provider == "omniroute"


@pytest.mark.asyncio
async def test_decoupled_decision_model_uses_separate_openrouter_url(monkeypatch):
    from unittest.mock import MagicMock
    from app.config import get_settings
    settings = get_settings()

    monkeypatch.setattr(settings, "OPENROUTER_DECISION_BASE_URL", "https://decision.openrouter.ai/v1")
    monkeypatch.setattr(settings, "OPENROUTER_DECISION_API_KEY", "dec-key-test-999")
    monkeypatch.setattr(settings, "OPENROUTER_DECISION_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

    import httpx

    captured_url = None
    captured_json = None

    async def mock_post(self, url, *args, **kwargs):
        nonlocal captured_url, captured_json
        captured_url = str(url)
        captured_json = kwargs.get("json")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"is_leave_request": True, "leave_type": "annual"})}}]
        }
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    router = MultiProviderLLMRouter()
    text, provider, model = await router.generate_decision("System", "Vacation next week")

    assert "https://decision.openrouter.ai/v1/chat/completions" in captured_url
    assert captured_json["temperature"] == 0.0
    assert captured_json["model"] == "meta-llama/llama-3.3-70b-instruct:free"
    assert provider == "openrouter"


@pytest.mark.asyncio
async def test_decision_failover_from_openrouter_to_gemini(monkeypatch):
    from unittest.mock import MagicMock
    from app.config import get_settings
    settings = get_settings()

    monkeypatch.setattr(settings, "LLM_ROUTING_ORDER", "openrouter,gemini,grok,deterministic")
    monkeypatch.setattr(settings, "OPENROUTER_DECISION_API_KEY", "openrouter-dead-key")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "valid-gemini-live-key")

    import httpx

    captured_calls = []

    async def mock_post(self, url, *args, **kwargs):
        captured_calls.append(str(url))
        resp = MagicMock()
        if "openrouter" in str(url):
            resp.status_code = 402  # credits exhausted on OpenRouter
            resp.text = "Payment required"
        elif "generativelanguage.googleapis.com" in str(url):
            resp.status_code = 200
            resp.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{"text": json.dumps({"is_leave_request": True, "leave_type": "sick"})}]
                    }
                }]
            }
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    router = MultiProviderLLMRouter()
    text, provider, model = await router.generate_decision("System", "Sick for 2 days")

    assert len(captured_calls) >= 2
    assert provider == "gemini"
    assert model == (settings.GEMINI_MODEL or "gemini-2.5-flash")
    parsed = json.loads(text)
    assert parsed["leave_type"] == "sick"



@pytest.mark.asyncio
async def test_decoupled_chat_model_uses_separate_chat_url(monkeypatch):
    from unittest.mock import MagicMock
    from app.config import get_settings
    settings = get_settings()

    monkeypatch.setattr(settings, "LLM_ROUTING_ORDER", "openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_CHAT_BASE_URL", "https://chat.openrouter.ai/v1")
    monkeypatch.setattr(settings, "OPENROUTER_CHAT_API_KEY", "chat-key-test-888")
    monkeypatch.setattr(settings, "OPENROUTER_CHAT_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

    import httpx

    captured_url = None
    captured_json = None

    async def mock_post(self, url, *args, **kwargs):
        nonlocal captured_url, captured_json
        captured_url = str(url)
        captured_json = kwargs.get("json")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {"content": "Hello, how can I help you today?"}}]
        }
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    router = MultiProviderLLMRouter()
    text, provider, model = await router.generate_with_metadata("System", "Hello")

    assert "https://chat.openrouter.ai/v1/chat/completions" in captured_url
    assert captured_json["temperature"] == 0.4
    assert captured_json["model"] == "meta-llama/llama-3.3-70b-instruct:free"
    assert provider == "openrouter"




