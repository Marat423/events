import asyncio
import logging

from fastapi import APIRouter

from src.services.background_sync import sync_once

router = APIRouter(prefix="/sync", tags=["sync"])

logger = logging.getLogger(__name__)

_sync_task: asyncio.Task | None = None


async def run_manual_sync() -> None:
    try:
        await sync_once()
    except Exception:
        logger.exception("Manual sync failed")


@router.post("/trigger")
async def trigger_sync():
    global _sync_task

    if _sync_task is not None and not _sync_task.done():
        return {
            "status": "already_running",
            "message": "Sync is already running",
        }

    _sync_task = asyncio.create_task(run_manual_sync())

    return {
        "status": "started",
        "message": "Sync started in background",
    }