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

    if event.status != "published":
        raise HTTPException(status_code=400, detail="Event is not published")

    result = await db.execute(
        select(models.Seat)
        .where(models.Seat.event_id == event_id)
        .where(models.Seat.is_available == True)
        .order_by(models.Seat.row, models.Seat.number)
    )

    seats = result.scalars().all()

    available_seats = [
        f"{seat.row}{seat.number}"
        for seat in seats
    ]

    return SeatsResponse(
        event_id=event_id,
        available_seats=available_seats,
    )