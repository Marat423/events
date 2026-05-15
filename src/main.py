import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.db import models as _models  # noqa: F401
from src.db.database import Base, engine
from src.route import events, sync_provider, tickets

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

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
