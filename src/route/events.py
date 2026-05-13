import time
from datetime import date, datetime
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import crud
from src.config import settings
from src.db import models
from src.db.database import get_db
from src.dependencies.pagination import PaginationParams, get_pagination_params
from src.schemas.schemas import (
    EventDetailSchema,
    EventListResponse,
    EventSchema,
    SeatsResponse,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListResponse)
@router.get("/", response_model=EventListResponse, include_in_schema=False)
async def get_events(
    pagination: PaginationParams = Depends(get_pagination_params),
    date_from: Optional[date] = Query(
        None,
        description="Filter events after given date (YYYY-MM-DD)",
    ),
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

    query = (
        select(models.Event)
        .options(selectinload(models.Event.place))
        .order_by(models.Event.event_time)
    )

    if filters:
        query = query.where(*filters)

    query = query.offset(skip).limit(pagination.page_size)
    result = await db.execute(query)
    events = result.scalars().all()

    results = [EventSchema.model_validate(e, from_attributes=True) for e in events]

    base_url = str(request.url).split("?")[0]
    next_url = None
    prev_url = None
    if pagination.page * pagination.page_size < total:
        next_url = (
            f"{base_url}?page={pagination.page + 1}&page_size={pagination.page_size}"
        )
    if pagination.page > 1:
        prev_url = (
            f"{base_url}?page={pagination.page - 1}&page_size={pagination.page_size}"
        )

    if date_from:
        date_param = f"date_from={date_from.isoformat()}"

        if next_url:
            next_url += f"&{date_param}"

        if prev_url:
            prev_url += f"&{date_param}"

    return {
        "count": total,
        "next": next_url,
        "previous": prev_url,
        "results": [
            event.model_dump(mode="json")
            for event in results
        ],
    }


@router.get("/{event_id}", response_model=EventDetailSchema)
async def get_event_detail(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    event = await crud.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventDetailSchema.model_validate(event, from_attributes=True)


_seats_cache = {}
_seats_cache_time = {}


def generate_seats_from_pattern(seats_pattern: str | None) -> list[str]:
    seats = []

    if not seats_pattern:
        return seats

    parts = seats_pattern.split(",")

    for part in parts:
        part = part.strip()

        if not part or "-" not in part:
            continue

        row = part[0]

        i = 1
        while i < len(part) and part[i].isdigit():
            i += 1

        if i == len(part) or part[i] != "-":
            continue

        start_str = part[1:i]
        end_str = part[i + 1 :]

        try:
            start = int(start_str)
            end = int(end_str)
        except ValueError:
            continue

        for number in range(start, end + 1):
            seats.append(f"{row}{number}")

    return seats


@router.get("/{event_id}/seats", response_model=SeatsResponse)
async def get_available_seats(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    event = await crud.get_event(db, event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != "published":
        raise HTTPException(status_code=400, detail="Event is not published")

    now = time.time()

    if event_id in _seats_cache and (now - _seats_cache_time.get(event_id, 0)) < 30:
        return SeatsResponse(
            event_id=event_id,
            available_seats=_seats_cache[event_id],
        )

    available = []

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                f"{settings.CLIENT_HOST.rstrip('/')}/api/events/{event_id}/seats/",
                headers={"x-api-key": settings.EVENTS_API_KEY},
            )

        if resp.status_code == 200:
            data = resp.json()
            available = data.get("available_seats") or data.get("seats") or []
        else:
            pattern = event.place.seats_pattern if event.place else None
            available = generate_seats_from_pattern(pattern)

    except Exception:
        pattern = event.place.seats_pattern if event.place else None
        available = generate_seats_from_pattern(pattern)

    _seats_cache[event_id] = available
    _seats_cache_time[event_id] = now

    return SeatsResponse(
        event_id=event_id,
        available_seats=available,
    )
