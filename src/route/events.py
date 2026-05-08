from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.dependencies.pagination import get_pagination_params
from src.schemas.pagination import PaginatedResponse, PaginationParams
from src.schemas.schemas import EventSchema
from src.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=PaginatedResponse[EventSchema])
async def get_events(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    service = EventService(db)
    base_url = str(request.url).split("?")[0]
    return await service.get_events(pagination, base_url=base_url)


@router.get("/{event_id}", response_model=EventSchema)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = EventService(db)
    event = await service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
