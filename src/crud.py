from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import models
from src.db.models import Event


async def get_events(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(Event).offset(skip).limit(limit))
    return result.scalars().all()


async def count_events(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(models.Event))
    return result.scalar()


async def get_place(db: AsyncSession, place_id: str) -> models.Place | None:
    result = await db.execute(select(models.Place).where(models.Place.id == place_id))
    return result.scalar_one_or_none()


async def get_event(db: AsyncSession, event_id: str) -> models.Event | None:
    result = await db.execute(select(models.Event).where(models.Event.id == event_id))
    return result.scalar_one_or_none()


async def get_seat_by_row_number(
    db: AsyncSession, event_id: UUID, row: str, number: int
) -> models.Seat | None:
    result = await db.execute(
        select(models.Seat)
        .where(models.Seat.event_id == event_id)
        .where(models.Seat.row == row)
        .where(models.Seat.number == number)
    )
    return result.scalar_one_or_none()


async def create_ticket(db: AsyncSession, ticket_data: dict) -> models.Ticket:
    ticket = models.Ticket(**ticket_data)
    db.add(ticket)
    await db.flush()
    return ticket


async def update_seat_availability(
    db: AsyncSession, seat_id: UUID, is_available: bool
) -> None:
    seat = await db.get(models.Seat, seat_id)
    if seat:
        seat.is_available = is_available
        await db.flush()


async def get_ticket(db: AsyncSession, ticket_id: UUID) -> models.Ticket | None:
    return await db.get(models.Ticket, ticket_id)


async def delete_ticket(db: AsyncSession, ticket_id: UUID) -> bool:
    ticket = await get_ticket(db, ticket_id)
    if ticket:
        await db.delete(ticket)
        await db.flush()
        return True
    return False
