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
    Intelligent Multi-Provider LLM Router with decoupled Decision & Chat models.
    Decision Engine: Uses dedicated OpenRouter Decision URL and Model (free tier, e.g. Llama 3.3 70B Free) with temp=0.0.
    Chat Engine: Uses dedicated OpenRouter Chat URL or Multi-LLM Routing (OmniRoute, Gemini, Grok, Local) with temp=0.4.
    Automatically handles quota exhaustion (402), rate limits (429), auth failures (401), and timeouts.
    """

    def __init__(self):
        self.last_provider: Optional[str] = None
        self.last_model: Optional[str] = None
        self.last_decision_provider: Optional[str] = None
        self.last_decision_model: Optional[str] = None
        self.last_chat_provider: Optional[str] = None
        self.last_chat_model: Optional[str] = None

    def _is_valid_key(self, key: Optional[str]) -> bool:
        if not key:
            return False
        clean = key.strip().lower()
        return bool(clean) and not clean.startswith("your-") and not clean.startswith("sk-placeholder")

    async def generate_decision(self, system_instruction: str, prompt: str) -> Tuple[str, str, str]:
        """
        Executes decision-making (intent classification, leave parsing, approval recommendations)
        using dedicated OpenRouter Decision URL and Model with temperature 0.0.
        Falls back to remaining providers or deterministic rule engine if exhausted.
        Returns: (json_text, provider_name, model_name)
        """
        decision_key = settings.OPENROUTER_DECISION_API_KEY or settings.OPENROUTER_API_KEY
        decision_base_url = (
            settings.OPENROUTER_DECISION_BASE_URL
            or settings.OPENROUTER_BASE_URL
            or "https://openrouter.ai/api/v1"
        )
        decision_model = (
            settings.OPENROUTER_DECISION_MODEL
            or "meta-llama/llama-3.3-70b-instruct:free"
        )

        async with httpx.AsyncClient(timeout=12.0) as client:
            # 1. Primary: Dedicated OpenRouter Free Decision Model
            if self._is_valid_key(decision_key):
                try:
                    text = await self._call_openai_compatible(
                        client=client,
                        base_url=decision_base_url,
                        api_key=decision_key,
                        model=decision_model,
                        system_instruction=system_instruction,
                        prompt=prompt,
                        temperature=0.0,
                    )
                    if text:
                        self.last_decision_provider = "openrouter"
                        self.last_decision_model = decision_model
                        self.last_provider = self.last_decision_provider
                        self.last_model = self.last_decision_model
                        return text, self.last_decision_provider, self.last_decision_model
                except Exception as e:
                    logger.warning(f"OpenRouter Decision endpoint error: {e}. Trying fallback chain...")

            # 2. Sequential fallback through configured routing order
            raw_order = settings.LLM_ROUTING_ORDER or "omniroute,openrouter,gemini,grok,local,deterministic"
            providers = [p.strip().lower() for p in raw_order.split(",") if p.strip()]

            for provider in providers:
                try:
                    if provider == "omniroute" and self._is_valid_key(settings.OMNIROUTE_API_KEY):
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.OMNIROUTE_BASE_URL or "https://api.omniroute.ai/v1",
                            api_key=settings.OMNIROUTE_API_KEY,
                            model=settings.OMNIROUTE_MODEL or "gpt-4o-mini",
                            system_instruction=system_instruction,
                            prompt=prompt,
                            temperature=0.0,
                        )
                        if text:
                            self.last_decision_provider = "omniroute"
                            self.last_decision_model = settings.OMNIROUTE_MODEL or "gpt-4o-mini"
                            self.last_provider = self.last_decision_provider
                            self.last_model = self.last_decision_model
                            return text, self.last_decision_provider, self.last_decision_model

                    elif provider == "gemini" and self._is_valid_key(settings.GEMINI_API_KEY):
                        text = await self._call_gemini(
                            client=client,
                            api_key=settings.GEMINI_API_KEY,
                            model=settings.GEMINI_MODEL or "gemini-flash-lite-latest",
                            system_instruction=system_instruction,
                            prompt=prompt,
                            temperature=0.2,
                        )
                        if text:
                            self.last_decision_provider = "gemini"
                            self.last_decision_model = settings.GEMINI_MODEL or "gemini-flash-lite-latest"
                            self.last_provider = self.last_decision_provider
                            self.last_model = self.last_decision_model
                            return text, self.last_decision_provider, self.last_decision_model

                    elif provider == "grok" and self._is_valid_key(settings.GROK_API_KEY):
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.GROK_BASE_URL or "https://api.groq.com/openai/v1",
                            api_key=settings.GROK_API_KEY,
                            model=settings.GROK_MODEL or "openai/gpt-oss-120b",
                            system_instruction=system_instruction,
                            prompt=prompt,
                            temperature=0.0,
                        )
                        if text:
                            self.last_decision_provider = "grok"
                            self.last_decision_model = settings.GROK_MODEL or "openai/gpt-oss-120b"
                            self.last_provider = self.last_decision_provider
                            self.last_model = self.last_decision_model
                            return text, self.last_decision_provider, self.last_decision_model

                    elif provider == "openrouter" and self._is_valid_key(settings.OPENROUTER_API_KEY):
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1",
                            api_key=settings.OPENROUTER_API_KEY,
                            model=settings.OPENROUTER_MODEL or "openrouter/free",
                            system_instruction=system_instruction,
                            prompt=prompt,
                            temperature=0.0,
                        )
                        if text:
                            self.last_decision_provider = "openrouter"
                            self.last_decision_model = settings.OPENROUTER_MODEL or "openrouter/free"
                            self.last_provider = self.last_decision_provider
                            self.last_model = self.last_decision_model
                            return text, self.last_decision_provider, self.last_decision_model

                    elif provider == "local":
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.LOCAL_LLM_URL or "http://localhost:11434/v1",
                            api_key="ollama-local",
                            model=settings.LOCAL_LLM_MODEL or "llama3",
                            system_instruction=system_instruction,
                            prompt=prompt,
                            temperature=0.0,
                        )
                        if text:
                            self.last_decision_provider = "local"
                            self.last_decision_model = settings.LOCAL_LLM_MODEL or "llama3"
                            self.last_provider = self.last_decision_provider
                            self.last_model = self.last_decision_model
                            return text, self.last_decision_provider, self.last_decision_model

                except Exception as e:
                    logger.warning(f"Decision fallback provider '{provider}' error: {e}")
                    continue

        # Zero-cost in-house deterministic fallback rule engine
        self.last_decision_provider = "deterministic"
        self.last_decision_model = "workforceai-rule-engine-v1"
        self.last_provider = self.last_decision_provider
        self.last_model = self.last_decision_model
        return self._fallback_response(prompt), self.last_decision_provider, self.last_decision_model

    async def generate_text(self, system_instruction: str, prompt: str) -> str:
        """Standard generation method returning text while tracking last provider."""
        text, provider, model = await self.generate_with_metadata(system_instruction, prompt)
        return text

    async def generate_with_metadata(self, system_instruction: str, prompt: str) -> Tuple[str, str, str]:
        """
        Executes conversational prompt through the configured chat priority fallback chain.
        Uses OPENROUTER_CHAT_BASE_URL and OPENROUTER_CHAT_MODEL for OpenRouter.
        Returns: (generated_text, provider_name, model_name)
        """
        raw_order = settings.LLM_ROUTING_ORDER or "omniroute,openrouter,gemini,grok,local,deterministic"
        providers = [p.strip().lower() for p in raw_order.split(",") if p.strip()]

        chat_key = settings.OPENROUTER_CHAT_API_KEY or settings.OPENROUTER_API_KEY
        chat_base_url = (
            settings.OPENROUTER_CHAT_BASE_URL
            or settings.OPENROUTER_BASE_URL
            or "https://openrouter.ai/api/v1"
        )
        chat_model = (
            settings.OPENROUTER_CHAT_MODEL
            or settings.OPENROUTER_MODEL
            or "meta-llama/llama-3.3-70b-instruct:free"
        )

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
                            temperature=0.4,
                        )
                        if text:
                            self.last_chat_provider = "omniroute"
                            self.last_chat_model = settings.OMNIROUTE_MODEL or "gpt-4o-mini"
                            self.last_provider = self.last_chat_provider
                            self.last_model = self.last_chat_model
                            return text, self.last_chat_provider, self.last_chat_model

                    elif provider == "openrouter":
                        if not self._is_valid_key(chat_key):
                            continue
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=chat_base_url,
                            api_key=chat_key,
                            model=chat_model,
                            system_instruction=system_instruction,
                            prompt=prompt,
                            temperature=0.4,
                        )
                        if text:
                            self.last_chat_provider = "openrouter"
                            self.last_chat_model = chat_model
                            self.last_provider = self.last_chat_provider
                            self.last_model = self.last_chat_model
                            return text, self.last_chat_provider, self.last_chat_model

                    elif provider == "gemini":
                        if not self._is_valid_key(settings.GEMINI_API_KEY):
                            continue
                        text = await self._call_gemini(
                            client=client,
                            api_key=settings.GEMINI_API_KEY,
                            model=settings.GEMINI_MODEL or "gemini-flash-lite-latest",
                            system_instruction=system_instruction,
                            prompt=prompt,
                            temperature=0.4,
                        )
                        if text:
                            self.last_chat_provider = "gemini"
                            self.last_chat_model = settings.GEMINI_MODEL or "gemini-flash-lite-latest"
                            self.last_provider = self.last_chat_provider
                            self.last_model = self.last_chat_model
                            return text, self.last_chat_provider, self.last_chat_model

                    elif provider == "grok":
                        if not self._is_valid_key(settings.GROK_API_KEY):
                            continue
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.GROK_BASE_URL or "https://api.groq.com/openai/v1",
                            api_key=settings.GROK_API_KEY,
                            model=settings.GROK_MODEL or "openai/gpt-oss-120b",
                            system_instruction=system_instruction,
                            prompt=prompt,
                            temperature=0.4,
                        )
                        if text:
                            self.last_chat_provider = "grok"
                            self.last_chat_model = settings.GROK_MODEL or "openai/gpt-oss-120b"
                            self.last_provider = self.last_chat_provider
                            self.last_model = self.last_chat_model
                            return text, self.last_chat_provider, self.last_chat_model

                    elif provider == "local":
                        text = await self._call_openai_compatible(
                            client=client,
                            base_url=settings.LOCAL_LLM_URL or "http://localhost:11434/v1",
                            api_key="ollama-local",
                            model=settings.LOCAL_LLM_MODEL or "llama3",
                            system_instruction=system_instruction,
                            prompt=prompt,
                            temperature=0.4,
                        )
                        if text:
                            self.last_chat_provider = "local"
                            self.last_chat_model = settings.LOCAL_LLM_MODEL or "llama3"
                            self.last_provider = self.last_chat_provider
                            self.last_model = self.last_chat_model
                            return text, self.last_chat_provider, self.last_chat_model

                    elif provider == "deterministic":
                        break

                except Exception as e:
                    logger.warning(f"LLM chat provider '{provider}' encountered error: {e}. Routing to fallback...")
                    continue

        # Zero-cost in-house deterministic fallback guarantee
        self.last_chat_provider = "deterministic"
        self.last_chat_model = "workforceai-rule-engine-v1"
        self.last_provider = self.last_chat_provider
        self.last_model = self.last_chat_model
        logger.info("Utilizing deterministic fallback rule engine for leave supervisor.")
        if "json" in system_instruction.lower() or any(w in prompt.lower() for w in ["vacation", "leave for", "days off", "day off"]):
            fallback_text = self._fallback_response(prompt)
        else:
            fallback_text = self._fallback_chat_reply(prompt)
        return fallback_text, self.last_chat_provider, self.last_chat_model

    async def _call_openai_compatible(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        model: str,
        system_instruction: str,
        prompt: str,
        temperature: float = 0.2,
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
            "temperature": temperature,
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
        temperature: float = 0.2,
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
                "temperature": temperature,
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

    def _fallback_chat_reply(self, prompt: str) -> str:
        """Deterministic conversational responses when remote LLM chat APIs fail or fall back."""
        lower = prompt.lower()
        if "sick" in lower:
            return (
                "**Company Sick Leave Policy**:\n\n"
                "- **Entitlement**: 12 paid days per calendar year.\n"
                "- **Notice Requirement**: Same-day notification permitted before business start.\n"
                "- **Documentation**: Medical certificate required for consecutive absences > 2 days.\n\n"
                "Would you like to draft a sick leave application or check your remaining balance?"
            )
        if "annual" in lower or "vacation" in lower:
            return (
                "**Company Annual Leave Policy**:\n\n"
                "- **Entitlement**: 18 paid business days per year, accrued monthly.\n"
                "- **Notice Requirement**: 5 business days advance notice for planned leaves.\n"
                "- **Carryover**: Up to 5 unused days roll over to next calendar year.\n\n"
                "Would you like me to draft an annual leave application for you?"
            )
        if "casual" in lower or "personal" in lower:
            return (
                "**Company Casual & Personal Leave Policy**:\n\n"
                "- **Entitlement**: 10 paid days per year for personal matters and emergencies.\n"
                "- **Notice Requirement**: 1 business day advance notice.\n\n"
                "Would you like me to prepare a casual leave request?"
            )
        return (
            "Hello! I am your WorkforceAI Supervisor. I can assist you with your leave balances, "
            "company policy rules, or draft a time-off application for you. "
            "For example, try asking: *'Check my balance'* or *'I need 2 days off next Monday and Tuesday for personal reasons'*."
        )

    def _fallback_response(self, prompt: str) -> str:
        """Deterministic NLP extractor when remote LLM APIs are exhausted, offline, or unconfigured."""
        lower = prompt.lower()
        today = date.today()

        # If user is asking a general policy or balance question, classify as not a leave request
        is_query = any(k in lower for k in ["policy", "what is", "how many", "rules", "rule", "entitlement", "explain", "terms", "?"])
        if is_query and not any(k in lower for k in ["need", "apply", "take", "request", "off", "want"]):
            return json.dumps({
                "is_leave_request": False,
                "reason": prompt.strip(),
                "confidence": 0.90,
            })

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
