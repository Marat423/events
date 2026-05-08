from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.db.database import Base, engine
from src.route import events, sync_provider, tickets


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # удалить все таблицы
        await conn.run_sync(Base.metadata.create_all)  # создать заново
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


# app = FastAPI()
@app.get("/api/health")
async def health():
    return {"status": "ok"}


app.include_router(sync_provider.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
