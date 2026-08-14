from dataclasses import dataclass

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.redis import create_session, get_session_human
from app.core.security import (
    parse_agent_token,
    verify_password,
    verify_token,
)
from app.models.agent import Agent
from app.models.project import HumanUser
from app.repos.agent import AgentRepo
from app.repos.audit import AuditRepo
from app.repos.human import HumanRepo


@dataclass
class Principal:
    kind: str
    agent: Agent | None = None
    human: HumanUser | None = None

    @property
    def human_pk(self) -> int | None:
        if self.human is not None:
            return self.human.id
        if self.agent is not None:
            return self.agent.owner_human_id
        return None


READ_ROLES = {"publisher", "consumer", "both"}
WRITE_ROLES = {"publisher", "both"}


class AuthService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis) -> None:
        self.session = session
        self.redis = redis
        self.human_repo = HumanRepo(session)
        self.agent_repo = AgentRepo(session)
        self.audit_repo = AuditRepo(session)

    async def login_human(self, email: str, password: str) -> tuple[HumanUser, str]:
        human = await self.human_repo.get_by_email(email)
        if human is None or not human.is_active:
            raise UnauthorizedError("invalid credentials")
        if not verify_password(human.password_hash, password):
            raise UnauthorizedError("invalid credentials")
        session_id = await create_session(self.redis, human.human_id)
        await self.audit_repo.write_audit_log(
            event="auth",
            actor_human_id=human.id,
            payload={"action": "login"},
        )
        await self.session.commit()
        return human, session_id

    async def get_human_from_session(self, session_id: str) -> HumanUser:
        human_id = await get_session_human(self.redis, session_id)
        if human_id is None:
            raise UnauthorizedError("invalid or expired session")
        human = await self.human_repo.get_by_human_id(human_id)
        if human is None or not human.is_active:
            raise UnauthorizedError("invalid session")
        return human

    async def authenticate_agent(self, token: str) -> Agent:
        try:
            agent_id, secret = parse_agent_token(token)
        except ValueError:
            raise UnauthorizedError("invalid token") from None
        agent = await self.agent_repo.get_by_agent_id(agent_id)
        if agent is None or not agent.is_active:
            raise UnauthorizedError("invalid token")
        if not verify_token(agent.token_hash, secret):
            raise UnauthorizedError("invalid token")
        return agent

    async def authenticate_principal(
        self, token: str | None, session_id: str | None
    ) -> Principal:
        if token:
            try:
                agent = await self.authenticate_agent(token)
                return Principal(kind="agent", agent=agent)
            except UnauthorizedError:
                pass
        if session_id:
            try:
                human = await self.get_human_from_session(session_id)
                return Principal(kind="human", human=human)
            except UnauthorizedError:
                pass
        raise UnauthorizedError("authentication required")
