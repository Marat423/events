import os
import sys
from pathlib import Path

# 1. Добавляем фейковые переменные окружения ДО импорта src, чтобы Pydantic не падал
os.environ["CLIENT_HOST"] = "http://localhost:3000"
os.environ["EVENTS_API_KEY"] = "test_secret_api_key_123"
# Если используются другие важные переменные (например, URL базы данных для тестов), укажите их тут:
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# 2. Настройка путей (ваш исходный код)
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Также добавляем корень проекта в sys.path, чтобы импорты 'src.main' работали корректно
project_root = root_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 3. Теперь импорты пройдут успешно без ValidationError
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.db.database import Base, get_db  # Путь изменен на ваш src.db.database

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        async with session.begin():
            yield session


@pytest.fixture(scope="function")
async def client(db_session):
    def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
