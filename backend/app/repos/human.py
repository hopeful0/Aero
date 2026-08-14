from sqlalchemy import select

from app.models.project import HumanUser
from app.repos.base import BaseRepo


class HumanRepo(BaseRepo):
    async def create_human(self, name: str, email: str, password_hash: str) -> HumanUser:
        human = HumanUser(name=name, email=email, password_hash=password_hash)
        self.session.add(human)
        await self.session.flush()
        return human

    async def get_by_id(self, human_pk: int) -> HumanUser | None:
        result = await self.session.execute(
            select(HumanUser).where(HumanUser.id == human_pk)
        )
        return result.scalar_one_or_none()

    async def get_by_human_id(self, human_id: str) -> HumanUser | None:
        result = await self.session.execute(
            select(HumanUser).where(HumanUser.human_id == human_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> HumanUser | None:
        result = await self.session.execute(
            select(HumanUser).where(HumanUser.email == email)
        )
        return result.scalar_one_or_none()

    async def get_id_map(self, pks: list[int]) -> dict[int, HumanUser]:
        if not pks:
            return {}
        result = await self.session.execute(
            select(HumanUser).where(HumanUser.id.in_(pks))
        )
        return {h.id: h for h in result.scalars().all()}
