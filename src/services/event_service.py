from datetime import date, datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db import models
from src.schemas.schemas import EventSchema
from src.services.provider_client import ProviderClient


class EventService:
    def __init__(
        self,
        db: AsyncSession,
        provider_client: ProviderClient,
    ) -> None:
        self.db = db
        self.provider_client = provider_client

    async def get_events(
        self,
        page: int,
        page_size: int,
        date_from: date | None = None,
        status: str | None = None,
    ) -> dict:
        filters = []

        if date_from:
            dt_from = datetime.combine(date_from, datetime.min.time())
            filters.append(models.Event.event_time >= dt_from)

        if status:
            filters.append(models.Event.status == status)

        total_query = select(func.count()).select_from(models.Event)

        if filters:
            total_query = total_query.where(*filters)

        total = (await self.db.execute(total_query)).scalar() or 0
        skip = (page - 1) * page_size

        status_order = case(
            (models.Event.status == "published", 0),
            else_=1,
        )

        query = (
            select(models.Event)
            .options(selectinload(models.Event.place))
            .order_by(status_order, models.Event.event_time)
            .offset(skip)
            .limit(page_size)
        )

        if filters:
            query = query.where(*filters)

        result = await self.db.execute(query)
        events = result.scalars().all()

        results = [
            EventSchema.model_validate(event, from_attributes=True).model_dump(
                mode="json"
            )
            for event in events
        ]

        query_params = [f"page_size={page_size}"]

        if date_from:
            query_params.append(f"date_from={date_from.isoformat()}")

        if status:
            query_params.append(f"status={status}")

        next_url = None
        previous_url = None

        if page * page_size < total:
            next_url = f"/api/events?page={page + 1}&" + "&".join(query_params)

        if page > 1:
            previous_url = f"/api/events?page={page - 1}&" + "&".join(query_params)

        return {
            "count": int(total),
            "next": next_url,
            "previous": previous_url,
            "results": results,
        }

    async def get_event(self, event_id: UUID) -> models.Event | None:
        result = await self.db.execute(
            select(models.Event)
            .options(selectinload(models.Event.place))
            .where(models.Event.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_available_seats(self, event: models.Event) -> list[str]:
        try:
            return await self.provider_client.fetch_event_seats(str(event.id))
        except Exception:
            pattern = event.place.seats_pattern if event.place else None
            return self.generate_seats_from_pattern(pattern)

    @staticmethod
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