from contextlib import suppress
from datetime import date
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.database import get_db
from src.services.provider_client import ProviderClient
from src.services.sync_service import SyncService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sync/trigger")
async def sync_events(
    changed_at: date = Query(date(1970, 1, 1)),
    db: AsyncSession = Depends(get_db),
):


    try:

        client = ProviderClient(
            base_url=settings.CLIENT_HOST.rstrip("/"),
            api_key=settings.EVENTS_API_KEY,
        )

        service = SyncService(db, client)

        count = await service.sync_events_from_provider(changed_at)

        return {
            "status": "synced",
            "count": count,
            "source": "provider",
        }

    except Exception as exc:
        logger.exception("Provider sync failed")

        with suppress(Exception):
            await db.rollback()

        raise HTTPException(
            status_code=502,
            detail=f"Provider sync failed: {type(exc).__name__}: {str(exc)}",
        )