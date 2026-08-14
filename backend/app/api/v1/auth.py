from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.redis import get_redis
from app.core.response import ok
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService

router = APIRouter(tags=["auth"])

SESSION_TTL = 12 * 3600


@router.post("/auth/login")
async def login(
    body: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    auth_service = AuthService(session, redis)
    human, session_id = await auth_service.login_human(body.email, body.password)
    response.set_cookie(
        "aero_session",
        session_id,
        httponly=True,
        samesite="strict",
        path="/",
        max_age=SESSION_TTL,
        secure=settings.env == "prod",
    )
    return ok({"human_id": human.human_id, "name": human.name})
