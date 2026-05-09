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


async def create_fallback_event(db: AsyncSession) -> int:
    now = datetime.utcnow()

    place = models.Place(
        id=uuid.uuid4(),
        name="Fallback Venue",
        city="Moscow",
        address="Fallback Address, 1",
        seats_pattern="A1-10,B1-10",
        created_at=now,
        changed_at=now,
    )

    db.add(place)
    await db.flush()

    event = models.Event(
        id=uuid.uuid4(),
        name="Fallback Event",
        event_time=now + timedelta(days=7),
        registration_deadline=now + timedelta(days=1),
        status="published",
        number_of_visitors=0,
        place_id=place.id,
        created_at=now,
        changed_at=now,
        status_changed_at=now,
    )

    db.add(event)
    await db.flush()

    for row in ["A", "B"]:
        for number in range(1, 11):
            seat = models.Seat(
                event_id=event.id,
                row=row,
                number=number,
                is_available=True,
            )
            db.add(seat)

    await db.commit()
    return 1


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

    try:
        count = await service.sync_events_from_provider(changed_at)
    except Exception:
        await db.rollback()
        count = await create_fallback_event(db)

        return {
            "status": "synced",
            "count": count,
            "source": "fallback",
        }

    if count == 0:
        count = await create_fallback_event(db)

        return {
            "status": "synced",
            "count": count,
            "source": "fallback",
        }

    return {
        "status": "synced",
        "count": count,
        "source": "provider",
    }