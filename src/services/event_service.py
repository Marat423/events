from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import crud
from src.db import models
from src.schemas.pagination import PaginatedResponse, PaginationParams
from src.schemas.schemas import EventSchema


class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_events(self, pagination: PaginationParams, base_url: str):
        skip = (pagination.page - 1) * pagination.limit
        stmt = (
            select(models.Event)
            .options(selectinload(models.Event.place))
            .offset(skip)
            .limit(pagination.limit)
        )
        result = await self.db.execute(stmt)
        events = result.scalars().all()

        total = await crud.count_events(self.db)

        results = [EventSchema.model_validate(e) for e in events]

        next_url = None
        prev_url = None
        if pagination.page * pagination.limit < total:
            next_url = f"{base_url}?page={pagination.page + 1}&limit={pagination.limit}"
        if pagination.page > 1:
            prev_url = f"{base_url}?page={pagination.page - 1}&limit={pagination.limit}"

        return PaginatedResponse[EventSchema](
            items=results,
            total=total,
            page=pagination.page,
            limit=pagination.limit,
            next=next_url,
            previous=prev_url,
        )

    async def get_event_by_id(self, event_id: str) -> models.Event | None:
        stmt = (
            select(models.Event)
            .where(models.Event.id == event_id)
            .options(selectinload(models.Event.place))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
