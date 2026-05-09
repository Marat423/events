from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlaceSchema(BaseModel):
    id: UUID
    name: str
    city: str
    address: str
    seats_pattern: str | None = None


class EventSchema(BaseModel):
    id: UUID
    name: str
    event_time: datetime | None = None
    registration_deadline: datetime | None = None
    status: str
    number_of_visitors: int | None = 0
    place: PlaceSchema | None = None
    place_id: UUID | None = None

    class Config:
        from_attributes = True
