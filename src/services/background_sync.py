import asyncio
import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select

from src.config import settings
from src.db import models
from src.db.database import AsyncSessionLocal
from src.services.provider_client import ProviderClient
from src.services.sync_service import SyncService

logger = logging.getLogger(__name__)

FIRST_SYNC_DATE = date(2000, 1, 1)
SYNC_INTERVAL_SECONDS = 24 * 60 * 60


async def get_or_create_sync_state(db):
    result = await db.execute(select(models.SyncState).where(models.SyncState.id == 1))
    state = result.scalar_one_or_none()

    if state is None:
        state = models.SyncState(
            id=1,
            sync_status="pending",
        )
        db.add(state)
        await db.flush()

    return state


async def sync_once(changed_at: date | None = None) -> int:
    async with AsyncSessionLocal() as db:
        state = await get_or_create_sync_state(db)

        if changed_at is None:
            if state.last_changed_at is None:
                changed_at = FIRST_SYNC_DATE
            else:
                changed_at = state.last_changed_at.date()

        state.sync_status = "running"
        await db.commit()

        try:
            client = ProviderClient(
                base_url=settings.CLIENT_HOST.rstrip("/"),
                api_key=settings.EVENTS_API_KEY,
            )
            service = SyncService(db, client)

            count = await service.sync_events_from_provider(changed_at)

            result = await db.execute(select(func.max(models.Event.changed_at)))
            max_changed_at = result.scalar_one_or_none()

            state = await get_or_create_sync_state(db)
            state.last_sync_time = datetime.now(timezone.utc)
            state.last_changed_at = max_changed_at or state.last_changed_at
            state.sync_status = "success"

            await db.commit()

            logger.info("Events sync completed. Count: %s", count)

            return count

        except Exception:
            await db.rollback()

            state = await get_or_create_sync_state(db)
            state.last_sync_time = datetime.now(timezone.utc)
            state.sync_status = "failed"

            await db.commit()

            logger.exception("Events sync failed")
            raise


async def sync_worker():
    while True:
        try:
            await sync_once()
        except Exception:
            logger.exception("Background sync failed")

        await asyncio.sleep(60 * 60 * 24)
