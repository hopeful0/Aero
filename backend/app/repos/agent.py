from sqlalchemy import select

from app.models.agent import Agent, AgentProjectScope
from app.models.project import Project
from app.repos.base import BaseRepo


class AgentRepo(BaseRepo):
    async def create_agent(
        self, name: str, token_hash: str, owner_human_id: int
    ) -> Agent:
        agent = Agent(
            name=name,
            token_hash=token_hash,
            owner_human_id=owner_human_id,
        )
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def get_by_id(self, agent_pk: int) -> Agent | None:
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_pk)
        )
        return result.scalar_one_or_none()

    async def get_by_agent_id(self, agent_id: str) -> Agent | None:
        result = await self.session.execute(
            select(Agent).where(Agent.agent_id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token_hash(self, token_hash: str) -> Agent | None:
        result = await self.session.execute(
            select(Agent).where(Agent.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_project_scope_by_pk(
        self, agent_pk: int, project_pk: int
    ) -> AgentProjectScope | None:
        result = await self.session.execute(
            select(AgentProjectScope).where(
                AgentProjectScope.agent_id == agent_pk,
                AgentProjectScope.project_id == project_pk,
            )
        )
        return result.scalar_one_or_none()

    async def get_project_scope_by_business_id(
        self, agent_pk: int, project_id: str
    ) -> AgentProjectScope | None:
        stmt = (
            select(AgentProjectScope)
            .join(Project, AgentProjectScope.project_id == Project.id)
            .where(
                AgentProjectScope.agent_id == agent_pk,
                Project.project_id == project_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def grant_agent_scope(
        self, agent_pk: int, project_pk: int, role: str
    ) -> AgentProjectScope:
        scope = AgentProjectScope(agent_id=agent_pk, project_id=project_pk, role=role)
        self.session.add(scope)
        await self.session.flush()
        return scope

    async def list_agent_project_pks(self, agent_pk: int) -> list[int]:
        result = await self.session.execute(
            select(AgentProjectScope.project_id).where(
                AgentProjectScope.agent_id == agent_pk
            )
        )
        return list(result.scalars().all())
