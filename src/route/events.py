from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import date, datetime
from uuid import UUID
from typing import Optional
import httpx
import time

from src.db.database import get_db
from src.dependencies.pagination import get_pagination_params, PaginationParams
from src.schemas.schemas import (
    EventSchema, EventDetailSchema, EventListResponse, SeatsResponse
)
from src import crud
from src.db import models
from src.config import settings

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=EventListResponse)
async def get_events(
    pagination: PaginationParams = Depends(get_pagination_params),
    date_from: Optional[date] = Query(None, description="Filter events after given date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):

    filters = []
    if date_from:
        dt_from = datetime.combine(date_from, datetime.min.time())
        filters.append(models.Event.event_time >= dt_from)


    total_query = select(func.count()).select_from(models.Event)
    if filters:
        total_query = total_query.where(*filters)
    total = (await db.execute(total_query)).scalar()


    skip = (pagination.page - 1) * pagination.page_size
    query = select(models.Event).options(selectinload(models.Event.place))
    if filters:
        query = query.where(*filters)
    query = query.offset(skip).limit(pagination.page_size)
    result = await db.execute(query)
    events = result.scalars().all()


    results = [EventSchema.model_validate(e, from_attributes=True) for e in events]


    base_url = str(request.url).split('?')[0]
    next_url = None
    prev_url = None
    if pagination.page * pagination.page_size < total:
        next_url = f"{base_url}?page={pagination.page + 1}&page_size={pagination.page_size}"
    if pagination.page > 1:
        prev_url = f"{base_url}?page={pagination.page - 1}&page_size={pagination.page_size}"
    # Если есть date_from, добавить его в ссылки
    if date_from:
        next_url += f"&date_from={date_from.isoformat()}" if next_url else f"?date_from={date_from.isoformat()}"
        prev_url += f"&date_from={date_from.isoformat()}" if prev_url else f"?date_from={date_from.isoformat()}"

    return EventListResponse(
        count=total,
        next=next_url,
        previous=prev_url,
        results=results
    )


@router.get("/{event_id}", response_model=EventDetailSchema)
async def get_event_detail(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    event = await crud.get_event(db, str(event_id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventDetailSchema.model_validate(event, from_attributes=True)


_seats_cache = {}
_seats_cache_time = {}

@router.get("/{event_id}/seats", response_model=SeatsResponse)
async def get_available_seats(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):

    event = await crud.get_event(db, str(event_id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    now = time.time()
    if event_id in _seats_cache and (now - _seats_cache_time.get(event_id, 0)) < 30:
        return SeatsResponse(event_id=event_id, available_seats=_seats_cache[event_id])


    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.CLIENT_HOST}/api/events/{event_id}/seats",
                headers={"x-api-key": settings.EVENTS_API_KEY}
            )
            resp.raise_for_status()
            data = resp.json()
            available = data.get("available_seats", [])
            _seats_cache[event_id] = available
            _seats_cache_time[event_id] = now
            return SeatsResponse(event_id=event_id, available_seats=available)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch seats: {str(e)}")