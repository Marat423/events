import asyncio
import logging

from fastapi import APIRouter
from sqlalchemy import func, select

from src.config import settings
from src.db import models
from src.db.database import AsyncSessionLocal
from src.services.background_sync import FIRST_SYNC_DATE, sync_once
from src.services.provider_client import ProviderClient
from src.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])

logger = logging.getLogger(__name__)

_sync_task: asyncio.Task | None = None
_sync_lock = asyncio.Lock()


async def get_events_count() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(models.Event))
        return result.scalar() or 0


async def preload_first_events_page() -> int:
    async with AsyncSessionLocal() as db:
        client = ProviderClient(
            base_url=settings.CLIENT_HOST,
            api_key=settings.EVENTS_API_KEY,
        )
        service = SyncService(db, client)

        data = await client.fetch_events(FIRST_SYNC_DATE)
        results = data.get("results") or []

        for item in results:
            place = await service.sync_place(item["place"])
            seats_pattern = item["place"].get("seats_pattern", "")
            await service.sync_event(item, place.id, seats_pattern)

        await db.commit()

        return len(results)


async def run_sync_safely() -> None:
    async with _sync_lock:
        try:
            await sync_once()
        except Exception:
            logger.exception("Manual background sync failed")


def start_background_sync() -> None:
    global _sync_task

    if _sync_task is None or _sync_task.done():
        _sync_task = asyncio.create_task(run_sync_safely())


@router.post("/trigger")
async def trigger_sync():
    events_count = await get_events_count()

    if events_count == 0:
        initial_count = await preload_first_events_page()
        start_background_sync()

        return {
            "status": "started",
            "message": "Initial events page loaded, full sync started",
            "initial_count": initial_count,
        }

    if _sync_task is not None and not _sync_task.done():
        return {
            "status": "already_running",
            "message": "Sync is already running",
        }

    start_background_sync()

    return {
        "status": "started",
        "message": "Sync started in background",
    }