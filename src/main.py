from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Depends
from datetime import datetime, timedelta, date
import uuid
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import engine, Base, AsyncSessionLocal, get_db
from src.route import events, tickets, sync_provider
from src.config import settings
from src.db import models
from src.services.provider_client import ProviderClient
from src.services.sync_service import SyncService




logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(models.Event))).scalar()
        if count == 0:
            logger.info("No events found, creating seed event...")
            # Создаём площадку
            place = models.Place(
                id=uuid.uuid4(),
                name="Seed Venue",
                city="Moscow",
                address="Seed Address, 1",
                seats_pattern="A1-10,B1-10"
            )
            db.add(place)
            await db.flush()
            # Создаём событие
            event = models.Event(
                id=uuid.uuid4(),
                name="Seed Event",
                event_time=datetime.now() + timedelta(days=7),
                registration_deadline=datetime.now() + timedelta(hours=24),
                status="published",
                number_of_visitors=0,
                place_id=place.id
            )
            db.add(event)
            await db.commit()
            logger.info("Seed event created successfully")
        else:
            logger.info(f"Found {count} events, no seeding needed")



    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/sync/trigger")
async def manual_sync(db: AsyncSession = Depends(get_db)):
    client = ProviderClient(
        base_url=settings.CLIENT_HOST.rstrip("/"),
        api_key=settings.EVENTS_API_KEY,
    )

    service = SyncService(db, client)

    count = await service.sync_events_from_provider(
        changed_at=date(1970, 1, 1)
    )

    return {
        "status": "synced",
        "count": count,
    }

app.include_router(events.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(sync_provider.router, prefix="/api")