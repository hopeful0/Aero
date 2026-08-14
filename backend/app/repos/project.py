from sqlalchemy import select

from app.models.project import HumanProjectScope, Project
from app.repos.base import BaseRepo


class ProjectRepo(BaseRepo):
    async def create_project(self, name: str) -> Project:
        project = Project(name=name)
        self.session.add(project)
        await self.session.flush()
        return project

    async def get_by_id(self, project_pk: int) -> Project | None:
        result = await self.session.execute(
            select(Project).where(Project.id == project_pk)
        )
        return result.scalar_one_or_none()

    async def get_by_project_id(self, project_id: str) -> Project | None:
        result = await self.session.execute(
            select(Project).where(Project.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_projects_for_human(self, human_pk: int) -> list[Project]:
        stmt = (
            select(Project)
            .join(HumanProjectScope, HumanProjectScope.project_id == Project.id)
            .where(HumanProjectScope.human_id == human_pk)
            .order_by(Project.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_human_scope_by_pk(
        self, human_pk: int, project_pk: int
    ) -> HumanProjectScope | None:
        result = await self.session.execute(
            select(HumanProjectScope).where(
                HumanProjectScope.human_id == human_pk,
                HumanProjectScope.project_id == project_pk,
            )
        )
        return result.scalar_one_or_none()

    async def get_human_scope_by_business_id(
        self, human_pk: int, project_id: str
    ) -> HumanProjectScope | None:
        stmt = (
            select(HumanProjectScope)
            .join(Project, HumanProjectScope.project_id == Project.id)
            .where(
                HumanProjectScope.human_id == human_pk,
                Project.project_id == project_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def grant_human_scope(
        self, human_pk: int, project_pk: int, role: str
    ) -> HumanProjectScope:
        scope = HumanProjectScope(human_id=human_pk, project_id=project_pk, role=role)
        self.session.add(scope)
        await self.session.flush()
        return scope

    async def list_human_project_pks(self, human_pk: int) -> list[int]:
        result = await self.session.execute(
            select(HumanProjectScope.project_id).where(
                HumanProjectScope.human_id == human_pk
            )
        )
        return list(result.scalars().all())
