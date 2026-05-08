from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
import httpx

from src.db.database import get_db
from src import crud
from src.schemas.schemas import TicketCreateRequest, TicketResponse, CancelTicketResponse
from src.config import settings

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.post("/", response_model=TicketResponse, status_code=201)
async def register_ticket(
    payload: TicketCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    # 1. Локальная валидация
    event = await crud.get_event(db, str(payload.event_id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status != "published":
        raise HTTPException(status_code=400, detail="Registration is only allowed for published events")
    now = datetime.now(event.registration_deadline.tzinfo) if event.registration_deadline.tzinfo else datetime.utcnow()
    if now > event.registration_deadline:
        raise HTTPException(status_code=400, detail="Registration deadline has passed")
    seat_str = payload.seat
    if not seat_str or not seat_str[0].isalpha() or not seat_str[1:].isdigit():
        raise HTTPException(status_code=400, detail="Invalid seat format")
    row = seat_str[0].upper()
    number = int(seat_str[1:])
    seat = await crud.get_seat_by_row_number(db, payload.event_id, row, number)
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found for this event")
    if not seat.is_available:
        raise HTTPException(status_code=409, detail="Seat already taken")

    # 2. Запрос к Events Provider API
    async with httpx.AsyncClient(timeout=30.0) as client:
        external_resp = await client.post(
            f"{settings.CLIENT_HOST}/api/events/{payload.event_id}/register/",
            json={
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "email": payload.email,
                "seat": payload.seat,
            },
            headers={"x-api-key": settings.EVENTS_API_KEY}
        )
        if external_resp.status_code != 201:
            raise HTTPException(status_code=external_resp.status_code, detail=external_resp.text)
        external_data = external_resp.json()
        ticket_id_str = external_data.get("ticket_id")
        if not ticket_id_str:
            raise HTTPException(status_code=502, detail="External API did not return ticket_id")

    # 3. Локальное сохранение билета
    ticket_data = {
        "id": UUID(ticket_id_str),
        "event_id": payload.event_id,
        "seat_id": seat.id,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "email": payload.email,
    }
    ticket = await crud.create_ticket(db, ticket_data)
    await crud.update_seat_availability(db, seat.id, is_available=False)
    await db.commit()
    return TicketResponse(ticket_id=ticket.id)

@router.delete("/{ticket_id}", response_model=CancelTicketResponse)
async def cancel_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    # 1. Локальный поиск билета
    ticket = await crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # 2. Запрос к Events Provider API
    async with httpx.AsyncClient(timeout=30.0) as client:
        external_resp = await client.request(
            "DELETE",
            f"{settings.CLIENT_HOST}/api/tickets/{ticket_id}",
            headers={"x-api-key": settings.EVENTS_API_KEY}
        )
        if external_resp.status_code not in (200, 204):
            raise HTTPException(status_code=external_resp.status_code, detail="External cancellation failed")

    # 3. Локальное удаление
    await crud.update_seat_availability(db, ticket.seat_id, is_available=True)
    await crud.delete_ticket(db, ticket_id)
    await db.commit()
    return CancelTicketResponse(success=True)