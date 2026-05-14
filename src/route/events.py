from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.database import get_db
from src.schemas.schemas import (
    EventDetailSchema,
    EventStatus,
    SeatsResponse,
)
from src.services.event_service import EventService
from src.services.provider_client import ProviderClient

router = APIRouter(prefix="/events", tags=["events"])

_seats_cache = {}
_seats_cache_time = {}


def get_event_service(db: AsyncSession) -> EventService:
    provider_client = ProviderClient(
        base_url=settings.CLIENT_HOST,
        api_key=settings.EVENTS_API_KEY,
    )
    return EventService(db=db, provider_client=provider_client)


@router.get("")
@router.get("/", include_in_schema=False)
async def get_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: Optional[int] = Query(None, ge=1, le=100),
    date_from: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if limit is not None:
        page_size = limit

    service = get_event_service(db)
    payload = await service.get_events(
        page=page,
        page_size=page_size,
        date_from=date_from,
        status=status,
    )

    return JSONResponse(content=jsonable_encoder(payload))


@router.get("/{event_id}", response_model=EventDetailSchema)
async def get_event_detail(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = get_event_service(db)
    event = await service.get_event(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventDetailSchema.model_validate(event, from_attributes=True)


@router.get("/{event_id}/seats", response_model=SeatsResponse)
async def get_available_seats(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = get_event_service(db)
    event = await service.get_event(event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != EventStatus.PUBLISHED.value:
        raise HTTPException(status_code=400, detail="Event is not published")

    available = await service.get_available_seats(event)

    return SeatsResponse(
        event_id=event_id,
        available_seats=available,
    )
