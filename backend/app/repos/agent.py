from sqlalchemy import select

from app.models.agent import Agent
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
