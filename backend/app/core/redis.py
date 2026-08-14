import secrets

import redis.asyncio as aioredis

from app.core.config import settings

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


SESSION_PREFIX = "aero:session:"
SESSION_TTL = 12 * 3600


async def create_session(client: aioredis.Redis, human_id: str) -> str:
    session_id = secrets.token_urlsafe(32)
    await client.set(SESSION_PREFIX + session_id, human_id, ex=SESSION_TTL)
    return session_id


async def get_session_human(client: aioredis.Redis, session_id: str) -> str | None:
    return await client.get(SESSION_PREFIX + session_id)


async def delete_session(client: aioredis.Redis, session_id: str) -> None:
    await client.delete(SESSION_PREFIX + session_id)
