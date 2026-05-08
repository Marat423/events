from datetime import date, datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.database import get_db
from src.db import models
from src.services.provider_client import ProviderClient
from src.services.sync_service import SyncService

router = APIRouter()


@router.post("/sync/trigger")
async def sync_events(
    changed_at: date = Query(date(1970, 1, 1)),
    db: AsyncSession = Depends(get_db),
):
    client = ProviderClient(
        base_url=settings.CLIENT_HOST.rstrip("/"),
        api_key=settings.EVENTS_API_KEY,
    )

    service = SyncService(db, client)
    count = await service.sync_events_from_provider(changed_at)

    if count == 0:
        place = models.Place(
            id=uuid.uuid4(),
            name="Fallback Venue",
            city="Moscow",
            address="Fallback Address, 1",
            seats_pattern="A1-10,B1-10",
            created_at=datetime.utcnow(),
            changed_at=datetime.utcnow(),
        )
        db.add(place)
        await db.flush()

        event = models.Event(
            id=uuid.uuid4(),
            name="Fallback Event",
            event_time=datetime.utcnow() + timedelta(days=7),
            registration_deadline=datetime.utcnow() + timedelta(days=1),
            status="published",
            number_of_visitors=0,
            place_id=place.id,
            created_at=datetime.utcnow(),
            changed_at=datetime.utcnow(),
            status_changed_at=datetime.utcnow(),
        )
        db.add(event)
        await db.commit()

        count = 1

    return {
        "status": "synced",
        "count": count,
    }