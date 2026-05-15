from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src import crud
from src.config import settings
from src.db.database import get_db
from src.schemas.schemas import (
    CancelTicketResponse,
    EventStatus,
    TicketCreateRequest,
    TicketResponse,
)
from src.services.provider_client import ProviderClient

router = APIRouter(prefix="/tickets", tags=["tickets"])


def get_provider_client() -> ProviderClient:
    return ProviderClient(
        base_url=settings.CLIENT_HOST,
        api_key=settings.EVENTS_API_KEY,
    )


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

    if event.status != EventStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=400,
            detail="Registration is only allowed for published events",
        )

    provider_client = get_provider_client()

    try:
        external_data = await provider_client.register_ticket(
            event_id=str(event_id),
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            seat=payload.seat,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "External registration failed",
                "provider_status": exc.response.status_code,
                "provider_body": exc.response.text,
                "provider_url": str(exc.request.url),
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "External registration failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        ) from exc

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
async def cancel_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    ticket = await crud.get_ticket(db, ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    provider_client = get_provider_client()

    try:
        await provider_client.unregister_ticket(
            event_id=str(ticket.event_id),
            ticket_id=str(ticket_id),
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "External cancellation failed",
                "provider_status": exc.response.status_code,
                "provider_body": exc.response.text,
                "provider_url": str(exc.request.url),
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "External cancellation failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        ) from exc

    if ticket.seat_id:
        await crud.update_seat_availability(
            db,
            ticket.seat_id,
            is_available=True,
        )

    await crud.delete_ticket(db, ticket_id)
    await db.commit()

    return CancelTicketResponse(success=True)
