from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from src.db.database import engine, Base, AsyncSessionLocal
from src.route import events, tickets
from src.services.provider_client import ProviderClient
from src.services.sync_service import SyncService
from src.config import settings
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Первая синхронизация при старте
    async with AsyncSessionLocal() as db:
        try:
            client = ProviderClient(base_url=settings.CLIENT_HOST, api_key=settings.EVENTS_API_KEY)
            sync = SyncService(db, client)
            await sync.sync_events_from_provider(changed_at=date(2000, 1, 1))
            logger.info("Initial sync completed")
        except Exception as e:
            logger.exception("Initial sync failed")

    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/sync/trigger")
async def manual_sync(background_tasks: BackgroundTasks):
    async def sync_task():
        async with AsyncSessionLocal() as db:
            client = ProviderClient(base_url=settings.CLIENT_HOST, api_key=settings.EVENTS_API_KEY)
            sync = SyncService(db, client)
            await sync.sync_events_from_provider(changed_at=date(2000, 1, 1))
    background_tasks.add_task(sync_task)
    return {"message": "Sync triggered"}

app.include_router(events.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
# app.include_router(sync_provider.router, prefix="/api")  # больше не нужен
