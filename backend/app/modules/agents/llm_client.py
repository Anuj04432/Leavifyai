import json
import logging
import re
from datetime import date, timedelta
from typing import Any, Dict, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger("workforceai.agents.gemini")
settings = get_settings()


class GeminiClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate_text(self, system_instruction: str, prompt: str) -> str:
        """Call Gemini 2.5 Flash via REST endpoint or return fallback if offline/unconfigured."""
        if not self.api_key or self.api_key == "your-gemini-api-key-here":
            logger.info("Gemini API key not configured. Using deterministic fallback parser.")
            return self._fallback_response(prompt)

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"System Directive:\n{system_instruction}\n\nUser Input:\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1000,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                logger.warning(f"Gemini API returned status {res.status_code}: {res.text}")
        except Exception as e:
            logger.warning(f"Gemini API connection error: {e}")

        return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        """Deterministic NLP extractor when Gemini API is unconfigured or offline."""
        lower = prompt.lower()
        today = date.today()

        # Extract number of days requested
        days = 1
        num_match = re.search(r"(\d+)\s*(?:day|days)", lower)
        if num_match:
            days = int(num_match.group(1))

        # Infer start date
        start = today + timedelta(days=1)
        if "next monday" in lower:
            days_ahead = (7 - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            start = today + timedelta(days=days_ahead)
        elif "tomorrow" in lower:
            start = today + timedelta(days=1)
        elif "next week" in lower:
            start = today + timedelta(days=7)

        end = start + timedelta(days=days - 1)

        # Infer leave type
        ltype = "casual"
        if "sick" in lower or "doctor" in lower or "fever" in lower or "medical" in lower:
            ltype = "sick"
        elif "vacation" in lower or "annual" in lower or "holiday" in lower:
            ltype = "annual"
        elif "unpaid" in lower:
            ltype = "unpaid"

        return json.dumps({
            "is_leave_request": True,
            "leave_type": ltype,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "reason": prompt.strip(),
            "confidence": 0.95,
        })
