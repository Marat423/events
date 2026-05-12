import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.db.database import engine
from src.route import events, sync_provider, tickets
#from src.services.background_sync import sync_worker

logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await engine.dispose()

app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def debug_exceptions(request: Request, call_next):
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


app.include_router(events.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(sync_provider.router, prefix="/api")
