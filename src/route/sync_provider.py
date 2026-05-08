from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.services.provider_client import ProviderClient
from src.services.sync_service import SyncService

router = APIRouter()


@router.get("/sync-from-provider")
async def sync_events(
    api_key: str = Query(...),
    changed_at: date = Query(date(2000, 1, 1)),
    db: AsyncSession = Depends(get_db),
):
    client = ProviderClient()
    service = SyncService(db, client)
    count = await service.sync_events_from_provider(changed_at, api_key)
    return {"status": "synced", "count": count}
