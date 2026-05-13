from datetime import datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src import crud
from src.config import settings
from src.db.database import get_db
from src.schemas.schemas import (
    CancelTicketResponse,
    TicketCreateRequest,
    TicketResponse,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
@router.post(
    "/",
    response_model=TicketResponse,
    status_code=201,
    include_in_schema=False,
)
async def register_ticket(
    payload: TicketCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        event_id = UUID(payload.event_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid event_id") from exc

    event = await crud.get_event(db, event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != "published":
        raise HTTPException(
            status_code=400,
            detail="Registration is only allowed for published events",
        )

    now = (
        datetime.now(event.registration_deadline.tzinfo)
        if event.registration_deadline.tzinfo
        else datetime.utcnow()
    )

    if now > event.registration_deadline:
        raise HTTPException(status_code=400, detail="Registration deadline has passed")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        external_resp = await client.post(
            f"{settings.CLIENT_HOST.rstrip('/')}/api/events/{event_id}/register/",
            json={
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "email": payload.email,
                "seat": payload.seat,
            },
            headers={"x-api-key": settings.EVENTS_API_KEY},
        )

    if external_resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=external_resp.status_code,
            detail=external_resp.text,
        )

    external_data = external_resp.json()
    ticket_id_str = external_data.get("ticket_id")

    if not ticket_id_str:
        raise HTTPException(
            status_code=502,
            detail="External API did not return ticket_id",
        )

    ticket_data = {
        "id": UUID(ticket_id_str),
        "event_id": event_id,
        "seat_id": None,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "email": payload.email,
    }

    ticket = await crud.create_ticket(db, ticket_data)
    await db.commit()

    return TicketResponse(ticket_id=ticket.id)


@router.delete("/{ticket_id}", response_model=CancelTicketResponse)
async def cancel_ticket(ticket_id: UUID, db: AsyncSession = Depends(get_db)):
    ticket = await crud.get_ticket(db, ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    async with httpx.AsyncClient(timeout=30.0) as client:
        external_resp = await client.request(
            "DELETE",
            f"{settings.CLIENT_HOST.rstrip('/')}/api/events/{ticket.event_id}/unregister/",
            json={"ticket_id": str(ticket_id)},
            headers={"x-api-key": settings.EVENTS_API_KEY},
        )

    if external_resp.status_code not in (200, 204):
        raise HTTPException(
            status_code=external_resp.status_code,
            detail="External cancellation failed",
        )

    if ticket.seat_id:
        await crud.update_seat_availability(db, ticket.seat_id, is_available=True)

    await crud.delete_ticket(db, ticket_id)
    await db.commit()

    return CancelTicketResponse(success=True)
