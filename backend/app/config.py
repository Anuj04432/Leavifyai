from functools import lru_cache
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "WorkforceAI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "development-secret-key-change-in-production-min-32-chars"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        import json
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/workforceai"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/workforceai"
    DATABASE_URL_UNPOOLED: Optional[str] = None

    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Authentication
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Multi-Provider AI & LLM Routing Configuration
    LLM_ROUTING_ORDER: str = "omniroute,openrouter,gemini,grok,local,deterministic"

    # OmniRoute (Free Credits / Aggregator)
    OMNIROUTE_API_KEY: str = ""
    OMNIROUTE_BASE_URL: str = "http://localhost:20128/v1"
    OMNIROUTE_MODEL: str = "auto"

    # OpenRouter (Aggregator / Free tiers)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openrouter/free"

    # Decoupled OpenRouter Decision Engine (Free Tier / Dedicated URL)
    OPENROUTER_DECISION_API_KEY: str = ""
    OPENROUTER_DECISION_BASE_URL: str = "https://openrouter.ai/api/alpha/decisions"
    OPENROUTER_DECISION_MODEL: str = "parallel/decisions-fast:free"

    # Decoupled OpenRouter Chat Engine (Dedicated URL)
    OPENROUTER_CHAT_API_KEY: str = ""
    OPENROUTER_CHAT_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_CHAT_MODEL: str = "openrouter/free"

    # Google Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    EMBEDDING_MODEL: str = "text-embedding-004"

    # Grok (xAI) / GroqCloud
    GROK_API_KEY: str = ""
    GROK_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROK_MODEL: str = "openai/gpt-oss-120b"

    # Local / Near AI Models (Ollama, vLLM, Near)
    LOCAL_LLM_URL: str = "http://localhost:11434/v1"
    LOCAL_LLM_MODEL: str = "qwen2.5:3b-instruct"

    # PayPal Developer Sandbox
    PAYPAL_MODE: str = "sandbox"
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_WEBHOOK_ID: str = ""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
