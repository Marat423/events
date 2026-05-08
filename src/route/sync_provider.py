from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.database import get_db
from src.services.provider_client import ProviderClient
from src.services.sync_service import SyncService

router = APIRouter()


@router.post("/sync/trigger")
async def sync_events(
    changed_at: date = Query(date(2000, 1, 1)),
    db: AsyncSession = Depends(get_db),
):
    client = ProviderClient(
        base_url=settings.CLIENT_HOST.rstrip("/"),
        api_key=settings.EVENTS_API_KEY,
    )

    service = SyncService(db, client)
    count = await service.sync_events_from_provider(changed_at)

    return {
        "status": "synced",
        "count": count,
    }