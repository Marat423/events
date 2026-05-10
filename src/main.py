import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import settings
from src.db.database import engine
from src.route import events, sync_provider, tickets
from src.services.background_sync import sync_worker

logger = logging.getLogger(__name__)

print(">>> MAIN.PY LOADED")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> LIFESPAN STARTED")

    task = asyncio.create_task(sync_worker())

    try:
        yield
    finally:
        task.cancel()

        with suppress(asyncio.CancelledError):
            await task

        await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def debug_exceptions(request: Request, call_next):
    print(">>> REQUEST:", request.method, request.url.path)

    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled error")

        return JSONResponse(
            status_code=500,
            content={
                "error_type": type(exc).__name__,
                "error": str(exc),
                "path": str(request.url.path),
            },
        )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/debug/settings")
async def debug_settings():
    return {
        "client_host": settings.CLIENT_HOST,
        "has_api_key": bool(settings.EVENTS_API_KEY),
    }


app.include_router(events.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(sync_provider.router, prefix="/api")
