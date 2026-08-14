from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import UnauthorizedError
from app.core.redis import get_redis
from app.models.agent import Agent
from app.models.project import HumanUser
from app.services.admin_service import AdminService
from app.services.artifact_service import ArtifactService
from app.services.auth_service import AuthService, Principal
from app.services.feedback_service import FeedbackService
from app.services.lineage_service import LineageService

BearerHeader = Annotated[str | None, Header(alias="Authorization")]


def get_admin_service(session: Annotated[AsyncSession, Depends(get_session)]) -> AdminService:
    return AdminService(session)


def get_artifact_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArtifactService:
    return ArtifactService(session)


def get_feedback_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FeedbackService:
    return FeedbackService(session)


def get_lineage_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LineageService:
    return LineageService(session)


async def get_current_agent(
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    authorization: BearerHeader = None,
) -> Agent:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    auth_service = AuthService(session, redis)
    return await auth_service.authenticate_agent(token)


async def get_current_human(
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    request: Request,
) -> HumanUser:
    session_id = request.cookies.get("aero_session")
    if not session_id:
        raise UnauthorizedError("missing session cookie")
    auth_service = AuthService(session, redis)
    return await auth_service.get_human_from_session(session_id)


async def get_current_principal(
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    request: Request,
    authorization: BearerHeader = None,
) -> Principal:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    session_id = request.cookies.get("aero_session")
    auth_service = AuthService(session, redis)
    return await auth_service.authenticate_principal(token, session_id)


async def get_optional_principal(
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    request: Request,
    authorization: BearerHeader = None,
) -> Principal:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    session_id = request.cookies.get("aero_session")
    auth_service = AuthService(session, redis)
    try:
        return await auth_service.authenticate_principal(token, session_id)
    except UnauthorizedError:
        return Principal(kind="anonymous")


CurrentAgent = Annotated[Agent, Depends(get_current_agent)]
CurrentHuman = Annotated[HumanUser, Depends(get_current_human)]
CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
OptionalPrincipal = Annotated[Principal, Depends(get_optional_principal)]
AdminSvc = Annotated[AdminService, Depends(get_admin_service)]
ArtifactSvc = Annotated[ArtifactService, Depends(get_artifact_service)]
FeedbackSvc = Annotated[FeedbackService, Depends(get_feedback_service)]
LineageSvc = Annotated[LineageService, Depends(get_lineage_service)]
