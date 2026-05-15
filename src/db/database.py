from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import settings

raw_url = settings.DATABASE_URL

if raw_url.startswith("postgresql://") and "+asyncpg" not in raw_url:
    async_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgres://"):
    async_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    async_url = raw_url

engine_kwargs = {
    "echo": False,
}

if async_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {
        "timeout": 30,
    }

engine = create_async_engine(async_url, **engine_kwargs)


if async_url.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
