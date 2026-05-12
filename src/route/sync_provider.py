import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from src.config import settings
from src.db import models
from src.db.database import AsyncSessionLocal
from src.services.background_sync import sync_once

router = APIRouter(prefix="/sync", tags=["sync"])

logger = logging.getLogger(__name__)


async def get_events_count() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(models.Event))
        return result.scalar() or 0


@router.post("/trigger")
async def trigger_sync():
    events_before = await get_events_count()

    try:
        count = await sync_once()
    except Exception as exc:
        logger.exception("Manual sync failed")

        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {type(exc).__name__}: {exc}",
        ) from exc

    events_after = await get_events_count()

    return {
        "status": "synced",
        "count": count,
        "events_before": events_before,
        "events_after": events_after,
        "source": "provider",
        "client_host": settings.CLIENT_HOST,
        "api_key_present": bool(settings.EVENTS_API_KEY),
    }