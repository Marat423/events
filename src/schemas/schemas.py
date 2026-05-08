from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict  # убедитесь, что ConfigDict импортирован


class PlaceSchema(BaseModel):
    id: UUID
    name: str
    city: str
    address: str
    seats_pattern: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class EventSchema(BaseModel):
    id: UUID
    name: str
    place: PlaceSchema
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int
    model_config = ConfigDict(from_attributes=True)


class EventListResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[EventSchema]


class SeatSchema(BaseModel):
    id: UUID
    event_id: UUID
    row: str
    number: int
    is_available: bool

    class Config:
        from_attributes = True


class TicketCreateRequest(BaseModel):
    first_name: str
    last_name: str
    seat: str
    email: str


class TicketResponse(BaseModel):
    ticket_id: UUID


class TicketSchema(BaseModel):
    id: UUID
    event_id: UUID
    seat_id: UUID
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class CancelRegistrationRequest(BaseModel):
    ticket_id: UUID


class SourceCreate(BaseModel):
    name: str
    base_url: str
    api_key: str


class SourceResponse(SourceCreate):
    id: str
    is_active: bool
