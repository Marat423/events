import asyncio
import logging

from fastapi import APIRouter
from sqlalchemy import func, select

from src.db import models
from src.db.database import AsyncSessionLocal
from src.services.background_sync import sync_once

router = APIRouter(prefix="/sync", tags=["sync"])

logger = logging.getLogger(__name__)

_sync_task: asyncio.Task | None = None
_sync_lock = asyncio.Lock()


async def get_events_count() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(models.Event))
        return result.scalar() or 0


async def run_sync_safely() -> None:
    async with _sync_lock:
        try:
            await sync_once()
        except Exception:
            logger.exception("Manual background sync failed")


@router.post("/trigger")
async def trigger_sync():
    global _sync_task

    events_count = await get_events_count()

    if events_count == 0:
        count = await sync_once()

        return {
            "status": "synced",
            "count": count,
            "message": "Initial sync completed",
        }

    if _sync_task is not None and not _sync_task.done():
        return {
            "status": "already_running",
            "message": "Sync is already running",
        }

    _sync_task = asyncio.create_task(run_sync_safely())

    return {
        "status": "started",
        "message": "Sync started in background",
    }