from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src import crud
from src.db.database import get_db
from src.schemas.schemas import (
    CancelRegistrationRequest,
    TicketCreateRequest,
    TicketResponse,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("/register/", response_model=TicketResponse, status_code=201)
async def register_for_event(
    event_id: UUID,
    registration: TicketCreateRequest = Body(...),
    db: AsyncSession = Depends(get_db),
):
    event = await crud.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != "published":
        raise HTTPException(
            status_code=400, detail="Registration is only allowed for published events"
        )

    now = (
        datetime.now(event.registration_deadline.tzinfo)
        if event.registration_deadline.tzinfo
        else datetime.utcnow()
    )
    if now > event.registration_deadline:
        raise HTTPException(status_code=400, detail="Registration deadline has passed")

    seat_str = registration.seat
    if not seat_str or not seat_str[0].isalpha() or not seat_str[1:].isdigit():
        raise HTTPException(
            status_code=400, detail="Invalid seat format. Examples: A15, B1"
        )
    row = seat_str[0].upper()
    number = int(seat_str[1:])

    seat = await crud.get_seat_by_row_number(db, event_id, row, number)
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found for this event")
    if not seat.is_available:
        raise HTTPException(status_code=409, detail="Seat already taken")

    ticket_data = {
        "event_id": event_id,
        "seat_id": seat.id,
        "first_name": registration.first_name,
        "last_name": registration.last_name,
        "email": registration.email,
    }
    ticket = await crud.create_ticket(db, ticket_data)
    await crud.update_seat_availability(db, seat.id, is_available=False)
    await db.commit()
    return TicketResponse(ticket_id=ticket.id)


@router.delete("/unregister/", status_code=204)
async def cancel_registration(
    event_id: UUID,
    body: CancelRegistrationRequest = Body(...),
    db: AsyncSession = Depends(get_db),
):
    ticket = await crud.get_ticket(db, body.ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.event_id != event_id:
        raise HTTPException(
            status_code=400, detail="Ticket does not belong to this event"
        )

    await crud.update_seat_availability(db, ticket.seat_id, is_available=True)
    if not await crud.delete_ticket(db, body.ticket_id):
        raise HTTPException(status_code=500, detail="Failed to delete ticket")

    await db.commit()
    return None
