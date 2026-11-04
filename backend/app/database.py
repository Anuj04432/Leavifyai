import asyncio
from typing import AsyncGenerator
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import get_settings

settings = get_settings()

def _get_async_database_url() -> str:
    raw = settings.DATABASE_URL
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw.startswith("postgresql://") and not raw.startswith("postgresql+asyncpg://"):
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "?" in raw:
        raw = raw.split("?")[0]
    return raw


connect_args = {}
if "neon.tech" in settings.DATABASE_URL or "sslmode" in settings.DATABASE_URL:
    connect_args["ssl"] = "require"

# Asynchronous PostgreSQL Engine
engine = create_async_engine(
    _get_async_database_url(),
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args=connect_args,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base model class for all SQLAlchemy declarative entities."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Verifies active connectivity to PostgreSQL database with a fast fail timeout."""
    try:
        async def _ping():
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        return await asyncio.wait_for(_ping(), timeout=1.5)
    except Exception:
        return False


async def check_redis_health() -> bool:
    """Verifies active connectivity to Redis cache with a fast fail timeout."""
    try:
        async def _ping():
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            is_alive = await client.ping()
            await client.aclose()
            return is_alive is True
        return await asyncio.wait_for(_ping(), timeout=1.5)
    except Exception:
        return False
