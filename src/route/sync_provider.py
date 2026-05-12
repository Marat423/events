import asyncio
import logging

from fastapi import APIRouter, HTTPException

from src.services.background_sync import sync_once

router = APIRouter(prefix="/sync", tags=["sync"])

logger = logging.getLogger(__name__)

_sync_task: asyncio.Task | None = None


async def run_sync_safely() -> int:
    try:
        return await sync_once()
    except Exception:
        logger.exception("Manual sync failed")
        raise


@router.post("/trigger")
async def trigger_sync():
    global _sync_task

    if _sync_task is not None and not _sync_task.done():
        return {
            "status": "already_running",
            "message": "Sync is already running",
        }

    _sync_task = asyncio.create_task(run_sync_safely())

    try:
        count = await asyncio.wait_for(
            asyncio.shield(_sync_task),
            timeout=15,
        )
    except asyncio.TimeoutError:
        return {
            "status": "started",
            "message": "Sync is still running in background",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Sync failed",
        ) from exc

    return {
        "status": "synced",
        "count": count,
        "source": "provider",
    }