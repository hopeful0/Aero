import os

os.environ.setdefault(
    "AERO_POSTGRES_DSN",
    "postgresql+asyncpg://aero:aero@localhost:5432/aero_test",
)

import pytest_asyncio  # noqa: E402
import redis.asyncio as aioredis  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings  # noqa: E402
from app.models import Base  # noqa: E402


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(settings.postgres_dsn, pool_pre_ping=True, future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture
async def client(engine):
    from app.api.deps import get_redis
    from app.core.database import get_session
    from app.main import app

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_session():
        async with maker() as s:
            yield s

    test_redis = aioredis.from_url(
        "redis://localhost:6379/2", decode_responses=True
    )
    await test_redis.flushdb()

    def override_redis():
        return test_redis

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_redis] = override_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await test_redis.flushdb()
    await test_redis.aclose()
