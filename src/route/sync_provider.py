import logging

from fastapi import APIRouter, HTTPException

from src.services.background_sync import sync_once

router = APIRouter(prefix="/sync", tags=["sync"])

logger = logging.getLogger(__name__)


@router.post("/trigger")
async def trigger_sync():
    try:
        count = await sync_once()
    except Exception as exc:
        logger.exception("Manual sync failed")

        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {type(exc).__name__}: {exc}",
        ) from exc

    return {
        "status": "synced",
        "count": count,
        "source": "provider",
    }