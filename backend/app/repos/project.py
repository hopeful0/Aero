from sqlalchemy import select

from app.models.project import Project
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
