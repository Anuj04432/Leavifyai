from datetime import date
import json
import pytest

from app.modules.agents.llm_client import GeminiClient
from app.schemas.agent import (
    AgentChatRequest,
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
