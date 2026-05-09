import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from src.db.database import engine
from src.route import events, sync_provider, tickets
from src.services.background_sync import sync_once, sync_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await sync_once()
    except Exception:
        logger.exception("Initial sync failed")

    task = asyncio.create_task(sync_worker())

    try:
        yield
    finally:
        task.cancel()

        with suppress(asyncio.CancelledError):
            await task

        await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


app.include_router(events.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(sync_provider.router, prefix="/api")