from datetime import date, datetime, timezone
from uuid import UUID  # добавьте этот импорт

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import models
from src.services.provider_client import ProviderClient

router = APIRouter()


class SyncService:
    def __init__(self, db: AsyncSession, provider_client: ProviderClient):
        self.db = db
        self.provider = provider_client

    def _to_datetime(self, value):
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except:
                return None
        return value

    async def sync_place(self, place_data: dict) -> models.Place:
        place_id = place_data["id"]
        result = await self.db.execute(
            select(models.Place).where(models.Place.id == place_id)
        )
        place = result.scalar_one_or_none()
        if not place:
            clean_place = {
                "id": place_data["id"],
                "name": place_data["name"],
                "city": place_data["city"],
                "address": place_data["address"],
                "seats_pattern": place_data.get("seats_pattern"),
                "changed_at": self._to_datetime(place_data.get("changed_at")),
                "created_at": self._to_datetime(place_data.get("created_at")),
            }
            place = models.Place(**clean_place)
            self.db.add(place)
        else:
            place.name = place_data["name"]
            place.city = place_data["city"]
            place.address = place_data["address"]
            place.seats_pattern = place_data.get("seats_pattern")
            place.changed_at = self._to_datetime(place_data.get("changed_at"))
            place.created_at = self._to_datetime(place_data.get("created_at"))
        return place

    def _generate_seats(self, event_id: UUID, seats_pattern: str) -> list[models.Seat]:
        seats = []
        if not seats_pattern:
            return seats
        parts = seats_pattern.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            row = part[0]
            if "-" not in part:
                continue

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
            for num in range(start, end + 1):
                seats.append(
                    models.Seat(
                        event_id=event_id, row=row, number=num, is_available=True
                    )
                )
        return seats

    async def sync_event(
        self, event_data: dict, place_id: str, seats_pattern: str = ""
    ) -> models.Event:
        event_id = event_data["id"]
        result = await self.db.execute(
            select(models.Event).where(models.Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        clean_event = {
            "id": event_id,
            "name": event_data.get("name"),
            "event_time": self._to_datetime(event_data.get("event_time")),
            "registration_deadline": self._to_datetime(
                event_data.get("registration_deadline")
            ),
            "status": event_data.get("status"),
            "number_of_visitors": event_data.get("number_of_visitors", 0),
            "changed_at": self._to_datetime(event_data.get("changed_at")),
            "created_at": self._to_datetime(event_data.get("created_at")),
            "status_changed_at": self._to_datetime(event_data.get("status_changed_at")),
            "place_id": place_id,
        }
        if not event:
            event = models.Event(**clean_event)
            self.db.add(event)
            await self.db.flush()

            if seats_pattern:
                seats = self._generate_seats(event.id, seats_pattern)
                for seat in seats:
                    self.db.add(seat)
        else:
            for key, value in clean_event.items():
                setattr(event, key, value)

        return event

    async def sync_events_from_provider(self, changed_at: date, api_key: str) -> int:
        count = 0
        async for item in self.provider.fetch_all_events(changed_at, api_key):
            place = await self.sync_place(item["place"])
            seats_pattern = item["place"].get("seats_pattern", "")
            await self.sync_event(item, place.id, seats_pattern)
            count += 1
        await self.db.commit()
        return count
