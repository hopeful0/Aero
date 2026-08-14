from sqlalchemy import func, or_, select, update

from app.models.agent import Agent
from app.models.artifact import (
    Artifact,
    ArtifactLineage,
    ArtifactVersion,
    ContextSnapshot,
)
from app.models.project import Project
from app.repos.base import BaseRepo
from app.schemas.artifact import SearchParams


class ArtifactRepo(BaseRepo):
    async def create_artifact(
        self,
        project_pk: int,
        title: str,
        summary: str | None,
        artifact_type: str | None,
        tags: list[str] | None,
        creator_agent_pk: int,
        owner_human_pk: int,
        content_storage: str = "inline",
        visibility: str = "private",
    ) -> Artifact:
        artifact = Artifact(
            project_id=project_pk,
            title=title,
            summary=summary,
            artifact_type=artifact_type,
            tags=tags,
            creator_agent_id=creator_agent_pk,
            owner_human_id=owner_human_pk,
            current_version=1,
            content_storage=content_storage,
            visibility=visibility,
        )
        self.session.add(artifact)
        await self.session.flush()
        return artifact

    async def get_artifact(self, artifact_pk: int) -> Artifact | None:
        result = await self.session.execute(
            select(Artifact).where(Artifact.id == artifact_pk)
        )
        return result.scalar_one_or_none()

    async def get_artifact_by_artifact_id(self, artifact_id: str) -> Artifact | None:
        result = await self.session.execute(
            select(Artifact).where(Artifact.artifact_id == artifact_id)
        )
        return result.scalar_one_or_none()

    async def list_artifacts(
        self,
        filters: SearchParams,
        project_pks: list[int] | None = None,
        *,
        public_only: bool = False,
        include_public: bool = False,
    ) -> list[Artifact]:
        stmt = select(Artifact).where(Artifact.archived_at.is_(None))
        if public_only:
            stmt = stmt.where(Artifact.visibility == "public")
        if filters.project_id is not None:
            stmt = stmt.join(Project, Artifact.project_id == Project.id).where(
                Project.project_id == filters.project_id
            )
        elif project_pks is not None:
            if include_public:
                stmt = stmt.where(
                    or_(
                        Artifact.project_id.in_(project_pks),
                        Artifact.visibility == "public",
                    )
                )
            else:
                stmt = stmt.where(Artifact.project_id.in_(project_pks))
        if filters.tags:
            stmt = stmt.where(Artifact.tags.op("&&")(filters.tags))
        if filters.type is not None:
            stmt = stmt.where(Artifact.artifact_type == filters.type)
        if filters.creator_agent_id is not None:
            stmt = stmt.join(Agent, Artifact.creator_agent_id == Agent.id).where(
                Agent.agent_id == filters.creator_agent_id
            )
        if filters.created_after is not None:
            stmt = stmt.where(Artifact.created_at >= filters.created_after)
        if filters.created_before is not None:
            stmt = stmt.where(Artifact.created_at <= filters.created_before)
        stmt = stmt.order_by(Artifact.updated_at.desc()).limit(
            filters.limit
        ).offset(filters.offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_version(
        self, artifact_pk: int, version_no: int
    ) -> ArtifactVersion | None:
        result = await self.session.execute(
            select(ArtifactVersion).where(
                ArtifactVersion.artifact_id == artifact_pk,
                ArtifactVersion.version_no == version_no,
            )
        )
        return result.scalar_one_or_none()

    async def get_versions(self, artifact_pk: int) -> list[ArtifactVersion]:
        result = await self.session.execute(
            select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact_pk)
            .order_by(ArtifactVersion.version_no)
        )
        return list(result.scalars().all())

    async def insert_version(
        self,
        artifact_pk: int,
        version_no: int,
        title: str | None,
        summary: str | None,
        content: str,
        content_format: str | None,
        changelog: str | None,
        created_by_agent_pk: int | None,
        context_snapshot_pk: int | None = None,
    ) -> ArtifactVersion:
        version = ArtifactVersion(
            artifact_id=artifact_pk,
            version_no=version_no,
            title=title,
            summary=summary,
            content=content,
            content_format=content_format,
            changelog=changelog,
            created_by_agent_id=created_by_agent_pk,
            context_snapshot_id=context_snapshot_pk,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def update_current_version(
        self, artifact_pk: int, new_version: int
    ) -> int:
        stmt = (
            update(Artifact)
            .where(
                Artifact.id == artifact_pk,
                Artifact.current_version == new_version - 1,
            )
            .values(current_version=new_version, updated_at=func.now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def insert_fork_lineage(
        self,
        child_artifact_pk: int,
        parent_artifact_pk: int,
        parent_version_no: int | None,
        forked_by_agent_pk: int | None,
        fork_note: str | None = None,
    ) -> ArtifactLineage:
        lineage = ArtifactLineage(
            child_artifact_id=child_artifact_pk,
            parent_artifact_id=parent_artifact_pk,
            parent_version_no=parent_version_no,
            forked_by_agent_id=forked_by_agent_pk,
            fork_note=fork_note,
        )
        self.session.add(lineage)
        await self.session.flush()
        return lineage

    async def get_lineage(self, artifact_pk: int) -> ArtifactLineage | None:
        result = await self.session.execute(
            select(ArtifactLineage).where(
                ArtifactLineage.child_artifact_id == artifact_pk
            )
        )
        return result.scalar_one_or_none()

    async def get_context_snapshot(self, snapshot_pk: int) -> ContextSnapshot | None:
        result = await self.session.execute(
            select(ContextSnapshot).where(ContextSnapshot.id == snapshot_pk)
        )
        return result.scalar_one_or_none()

    async def create_context_snapshot(
        self,
        prompt_snapshot: str | None = None,
        external_refs: dict | None = None,
        execution_trace_id: str | None = None,
    ) -> ContextSnapshot:
        snapshot = ContextSnapshot(
            prompt_snapshot=prompt_snapshot,
            external_refs=external_refs,
            execution_trace_id=execution_trace_id,
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot
