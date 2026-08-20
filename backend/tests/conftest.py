"""测试基础设施：用 testcontainers 起临时 PostgreSQL / Redis，避免依赖宿主机服务。

约定：显式设置 AERO_TEST_POSTGRES_DSN / AERO_TEST_REDIS_URL 时用该值（供已自备
服务的环境），否则自动起容器，测试结束即销毁。容器用同步 start/stop 管理，
不卷入 pytest-asyncio 的 async session fixture 生命周期。
"""

import os

import pytest
import pytest_asyncio  # noqa: F401
import redis.asyncio as aioredis  # noqa: F401
from httpx import ASGITransport, AsyncClient  # noqa: F401
from sqlalchemy.ext.asyncio import (  # noqa: F401
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models import Base


@pytest.fixture(scope="session")
def postgres_container():
    """提供测试用 PostgreSQL 的 async DSN。显式环境变量优先，否则起临时容器。"""
    explicit = os.environ.get("AERO_TEST_POSTGRES_DSN")
    if explicit:
        yield explicit
        return

    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="session")
def redis_container():
    """提供测试用 Redis 的 URL。显式环境变量优先，否则起临时容器。"""
    explicit = os.environ.get("AERO_TEST_REDIS_URL")
    if explicit:
        yield explicit
        return

    from testcontainers.community.redis import RedisContainer

    with RedisContainer("redis:7-alpine") as redis:
        host = redis.get_container_host_ip()
        port = redis.get_exposed_port(6379)
        yield f"redis://{host}:{port}/2"


@pytest_asyncio.fixture
async def engine(postgres_container):
    eng = create_async_engine(postgres_container, pool_pre_ping=True, future=True)
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
async def client(engine, redis_container):
    from app.api.deps import get_redis
    from app.core.database import get_session
    from app.main import app

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_session():
        async with maker() as s:
            yield s

    test_redis = aioredis.from_url(redis_container, decode_responses=True)
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