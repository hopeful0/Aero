from collections import deque

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError
from app.models.artifact import Artifact
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

    async def _is_visible_to_human(
        self, artifact: Artifact, human_pk: int
    ) -> bool:
        if artifact.visibility == "public":
            return True
        scope = await self.project_repo.get_human_scope_by_pk(
            human_pk, artifact.project_id
        )
        return scope is not None

    async def _build_node(
        self,
        artifact: Artifact,
        parent_artifact_id: str | None,
        parent_version_no: int | None,
        fork_note: str | None,
    ) -> dict:
        versions = await self.artifact_repo.get_versions(artifact.id)
        project = await self.project_repo.get_by_id(artifact.project_id)
        parent = None
        if parent_artifact_id is not None:
            parent = {
                "artifact_id": parent_artifact_id,
                "version_no": parent_version_no,
                "fork_note": fork_note,
            }
        return {
            "artifact_id": artifact.artifact_id,
            "title": artifact.title,
            "current_version": artifact.current_version,
            "project_id": project.project_id if project else None,
            "versions": [
                {
                    "version_no": v.version_no,
                    "title": v.title,
                    "created_at": v.created_at,
                }
                for v in versions
            ],
            "parent": parent,
        }

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
            lineage = await self.artifact_repo.get_lineage(current.id)
            parent_artifact_id: str | None = None
            parent_version_no: int | None = None
            fork_note: str | None = None
            next_artifact: Artifact | None = None
            if lineage is not None:
                parent_artifact = await self.artifact_repo.get_artifact(
                    lineage.parent_artifact_id
                )
                if parent_artifact is not None:
                    parent_artifact_id = parent_artifact.artifact_id
                    parent_version_no = lineage.parent_version_no
                    fork_note = lineage.fork_note
                    next_artifact = parent_artifact
            chain.append(
                await self._build_node(
                    current, parent_artifact_id, parent_version_no, fork_note
                )
            )
            current = next_artifact

        if principal.human is not None:
            await self._collect_descendants(
                start, principal.human.id, visited, chain
            )

        return chain

    async def _collect_descendants(
        self,
        start: Artifact,
        human_pk: int,
        visited: set[int],
        nodes: list[dict],
    ) -> None:
        queue: deque[Artifact] = deque([start])
        while queue:
            parent = queue.popleft()
            child_lineages = await self.artifact_repo.get_child_lineages(parent.id)
            for lineage in child_lineages:
                if lineage.child_artifact_id in visited:
                    continue
                child = await self.artifact_repo.get_artifact(
                    lineage.child_artifact_id
                )
                if child is None:
                    continue
                # 不可见的后代整棵子树剪枝：不入队、不递归，
                # 避免向当前用户泄露其无权访问的 artifact 的存在。
                if not await self._is_visible_to_human(child, human_pk):
                    continue
                visited.add(child.id)
                nodes.append(
                    await self._build_node(
                        child,
                        parent.artifact_id,
                        lineage.parent_version_no,
                        lineage.fork_note,
                    )
                )
                queue.append(child)
