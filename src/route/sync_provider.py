import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from src.services.background_sync import sync_once

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sync/trigger")
async def sync_events(
    changed_at: date = Query(date(2000, 1, 1)),
):
    try:
        count = await sync_once(changed_at=changed_at)

        return {
            "status": "synced",
            "count": count,
            "source": "provider",
        }

    except Exception as exc:
        logger.exception("Provider sync failed")

        raise HTTPException(
            status_code=502,
            detail=f"Provider sync failed: {type(exc).__name__}: {str(exc)}",
        )
