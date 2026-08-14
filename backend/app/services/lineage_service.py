from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError
from app.repos.agent import AgentRepo
from app.repos.artifact import ArtifactRepo
from app.repos.project import ProjectRepo
from app.services.auth_service import Principal


class LineageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.artifact_repo = ArtifactRepo(session)
        self.agent_repo = AgentRepo(session)
        self.project_repo = ProjectRepo(session)

    async def _assert_human_read_scope(self, principal: Principal, project_pk: int) -> None:
        if principal.human is None:
            raise ForbiddenError("lineage access requires human authentication")
        scope = await self.project_repo.get_human_scope_by_pk(
            principal.human.id, project_pk
        )
        if scope is None:
            raise ForbiddenError("human lacks access to project")

    async def get_lineage(
        self, principal: Principal, artifact_id: str
    ) -> list[dict]:
        start = await self.artifact_repo.get_artifact_by_artifact_id(artifact_id)
        if start is None:
            raise NotFoundError("artifact not found", {"artifact_id": artifact_id})

        await self._assert_human_read_scope(principal, start.project_id)

        chain: list[dict] = []
        visited: set[int] = set()
        current = start
        while current is not None and current.id not in visited:
            visited.add(current.id)
            versions = await self.artifact_repo.get_versions(current.id)
            project = await self.project_repo.get_by_id(current.project_id)

            node: dict = {
                "artifact_id": current.artifact_id,
                "title": current.title,
                "current_version": current.current_version,
                "project_id": project.project_id if project else None,
                "versions": [
                    {
                        "version_no": v.version_no,
                        "title": v.title,
                        "created_at": v.created_at,
                    }
                    for v in versions
                ],
                "parent": None,
            }

            lineage = await self.artifact_repo.get_lineage(current.id)
            if lineage is not None:
                parent_artifact = await self.artifact_repo.get_artifact(
                    lineage.parent_artifact_id
                )
                if parent_artifact is not None:
                    node["parent"] = {
                        "artifact_id": parent_artifact.artifact_id,
                        "version_no": lineage.parent_version_no,
                        "fork_note": lineage.fork_note,
                    }
                    current = parent_artifact
                else:
                    current = None
            else:
                current = None

            chain.append(node)

        return chain
