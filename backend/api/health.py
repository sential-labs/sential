from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from backend.config import settings
from backend.database import get_session

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    status = {"api": "ok", "database": "ok", "redis": "ok"}

    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        status["database"] = "error"

    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        await redis.aclose()
    except Exception:
        status["redis"] = "error"

    healthy = all(v == "ok" for v in status.values())
    return {"healthy": healthy, **status}