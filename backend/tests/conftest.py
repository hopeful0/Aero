import os

os.environ.setdefault(
    "AERO_POSTGRES_DSN",
    "postgresql+asyncpg://aero:aero@localhost:5432/aero_test",
)

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Base


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
