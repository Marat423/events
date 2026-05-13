from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlaceSchema(BaseModel):
    id: UUID
    name: str
    city: str
    address: str
    model_config = ConfigDict(from_attributes=True)


class PlaceDetailSchema(PlaceSchema):
    seats_pattern: Optional[str] = None


class EventSchema(BaseModel):
    id: UUID
    name: str
    place: PlaceSchema
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int
    model_config = ConfigDict(from_attributes=True)


class EventDetailSchema(EventSchema):
    place: PlaceDetailSchema


class EventListResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[EventSchema]


class SeatsResponse(BaseModel):
    event_id: UUID
    available_seats: List[str]


class TicketCreateRequest(BaseModel):
    event_id: str
    first_name: str
    last_name: str
    email: str
    seat: str


class TicketResponse(BaseModel):
    ticket_id: UUID


class CancelTicketResponse(BaseModel):
    success: bool


class SourceCreate(BaseModel):
    name: str
    base_url: str
    api_key: str


class SourceResponse(SourceCreate):
    id: str
    is_active: bool
