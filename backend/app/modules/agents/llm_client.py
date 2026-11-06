import json
import logging
import re
from datetime import date, timedelta
from typing import Any, Dict, Optional, Tuple
import httpx

from app.config import get_settings

logger = logging.getLogger("workforceai.agents.router")
settings = get_settings()


class MultiProviderLLMRouter:
    """
    Intelligent Multi-Provider LLM Router with sequential fallback.
    Supported providers: OmniRoute, OpenRouter, Gemini, Grok (xAI), Local LLM (Ollama/vLLM), Deterministic.
    Automatically handles quota exhaustion (402), rate limits (429), auth failures (401), and timeouts.
    """

    def __init__(self):
        self.last_provider: Optional[str] = None
        self.last_model: Optional[str] = None

    def _is_valid_key(self, key: Optional[str]) -> bool:
        if not key:
            return False
        clean = key.strip().lower()
        return bool(clean) and not clean.startswith("your-") and not clean.startswith("sk-placeholder")

    async def generate_text(self, system_instruction: str, prompt: str) -> str:
        """Standard generation method returning text while tracking last provider."""
        text, provider, model = await self.generate_with_metadata(system_instruction, prompt)
        return text

    async def generate_with_metadata(self, system_instruction: str, prompt: str) -> Tuple[str, str, str]:
        """
        Executes prompt through the configured priority fallback chain.
        Returns: (generated_text, provider_name, model_name)
        """
        raw_order = settings.LLM_ROUTING_ORDER or "omniroute,openrouter,gemini,grok,local,deterministic"
        providers = [p.strip().lower() for p in raw_order.split(",") if p.strip()]

        async with httpx.AsyncClient(timeout=12.0) as client:
            for provider in providers:
                try:
                    if provider == "omniroute":
                        if not self._is_valid_key(settings.OMNIROUTE_API_KEY):
                            continue
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.OMNIROUTE_BASE_URL or "https://api.omniroute.ai/v1",
                            api_key=settings.OMNIROUTE_API_KEY,
                            model=settings.OMNIROUTE_MODEL or "gpt-4o-mini",
                            system_instruction=system_instruction,
                            prompt=prompt,
                        )
                        if text:
                            self.last_provider = "omniroute"
                            self.last_model = settings.OMNIROUTE_MODEL or "gpt-4o-mini"
                            return text, self.last_provider, self.last_model

                    elif provider == "openrouter":
                        if not self._is_valid_key(settings.OPENROUTER_API_KEY):
                            continue
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1",
                            api_key=settings.OPENROUTER_API_KEY,
                            model=settings.OPENROUTER_MODEL or "meta-llama/llama-3.3-70b-instruct:free",
                            system_instruction=system_instruction,
                            prompt=prompt,
                        )
                        if text:
                            self.last_provider = "openrouter"
                            self.last_model = settings.OPENROUTER_MODEL or "meta-llama/llama-3.3-70b-instruct:free"
                            return text, self.last_provider, self.last_model

                    elif provider == "gemini":
                        if not self._is_valid_key(settings.GEMINI_API_KEY):
                            continue
                        text = await self._call_gemini(
                            client=client,
                            api_key=settings.GEMINI_API_KEY,
                            model=settings.GEMINI_MODEL or "gemini-2.5-flash",
                            system_instruction=system_instruction,
                            prompt=prompt,
                        )
                        if text:
                            self.last_provider = "gemini"
                            self.last_model = settings.GEMINI_MODEL or "gemini-2.5-flash"
                            return text, self.last_provider, self.last_model

                    elif provider == "grok":
                        if not self._is_valid_key(settings.GROK_API_KEY):
                            continue
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.GROK_BASE_URL or "https://api.x.ai/v1",
                            api_key=settings.GROK_API_KEY,
                            model=settings.GROK_MODEL or "grok-2-latest",
                            system_instruction=system_instruction,
                            prompt=prompt,
                        )
                        if text:
                            self.last_provider = "grok"
                            self.last_model = settings.GROK_MODEL or "grok-2-latest"
                            return text, self.last_provider, self.last_model

                    elif provider == "local":
                        # Local endpoints (Ollama/vLLM) often run locally without an API key
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.LOCAL_LLM_URL or "http://localhost:11434/v1",
                            api_key="ollama-local",
                            model=settings.LOCAL_LLM_MODEL or "llama3",
                            system_instruction=system_instruction,
                            prompt=prompt,
                        )
                        if text:
                            self.last_provider = "local"
                            self.last_model = settings.LOCAL_LLM_MODEL or "llama3"
                            return text, self.last_provider, self.last_model

                    elif provider == "deterministic":
                        break

                except Exception as e:
                    logger.warning(f"LLM provider '{provider}' encountered error: {e}. Routing to fallback...")
                    continue

        # Zero-cost in-house deterministic fallback guarantee
        self.last_provider = "deterministic"
        self.last_model = "workforceai-rule-engine-v1"
        logger.info("Utilizing deterministic fallback rule engine for leave supervisor.")
        return self._fallback_response(prompt), self.last_provider, self.last_model

    async def _call_openai_compatible(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        model: str,
        system_instruction: str,
        prompt: str,
    ) -> Optional[str]:
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 1000,
        }
        res = await client.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            data = res.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        logger.warning(f"OpenAI-compatible endpoint {url} returned status {res.status_code}: {res.text[:200]}")
        return None

    async def _call_gemini(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        model: str,
        system_instruction: str,
        prompt: str,
    ) -> Optional[str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
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
        res = await client.post(url, json=payload)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        logger.warning(f"Gemini API returned status {res.status_code}: {res.text[:200]}")
        return None

    def _fallback_response(self, prompt: str) -> str:
        """Deterministic NLP extractor when remote LLM APIs are exhausted, offline, or unconfigured."""
        lower = prompt.lower()
        today = date.today()

        days = 1
        num_match = re.search(r"(\d+)\s*(?:day|days)", lower)
        if num_match:
            days = int(num_match.group(1))

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


# Backward compatibility alias
GeminiClient = MultiProviderLLMRouter
