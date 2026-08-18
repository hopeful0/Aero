from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError, VersionConflictError
from app.models.agent import Agent
from app.models.artifact import Artifact
from app.models.project import HumanUser
from app.repos.agent import AgentRepo
from app.repos.artifact import ArtifactRepo
from app.repos.audit import AuditRepo
from app.repos.feedback import FeedbackRepo
from app.repos.project import ProjectRepo
from app.schemas.artifact import SearchParams
from app.services.auth_service import READ_ROLES, WRITE_ROLES, Principal


class ArtifactService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.artifact_repo = ArtifactRepo(session)
        self.agent_repo = AgentRepo(session)
        self.project_repo = ProjectRepo(session)
        self.audit_repo = AuditRepo(session)
        self.feedback_repo = FeedbackRepo(session)

    async def _assert_agent_write_scope(self, agent: Agent, project_pk: int) -> None:
        scope = await self.agent_repo.get_project_scope_by_pk(agent.id, project_pk)
        if scope is None or scope.role not in WRITE_ROLES:
            raise ForbiddenError("agent lacks write access to project")

    async def _assert_agent_read_scope(self, agent: Agent, project_pk: int) -> None:
        scope = await self.agent_repo.get_project_scope_by_pk(agent.id, project_pk)
        if scope is None or scope.role not in READ_ROLES:
            raise ForbiddenError("agent lacks read access to project")

    async def _assert_principal_read_scope(
        self, principal: Principal, project_pk: int
    ) -> None:
        if principal.kind == "agent" and principal.agent is not None:
            await self._assert_agent_read_scope(principal.agent, project_pk)
            return
        if principal.kind == "human" and principal.human is not None:
            scope = await self.project_repo.get_human_scope_by_pk(
                principal.human.id, project_pk
            )
            if scope is None or scope.role not in READ_ROLES:
                raise ForbiddenError("human lacks read access to project")
            return
        raise ForbiddenError("principal lacks read access to project")

    async def _assert_human_write_scope(
        self, human: HumanUser, project_pk: int
    ) -> None:
        scope = await self.project_repo.get_human_scope_by_pk(
            human.id, project_pk
        )
        if scope is None or scope.role not in WRITE_ROLES:
            raise ForbiddenError("human lacks write access to project")

    async def _resolve_artifact(self, artifact_id: str) -> Artifact:
        artifact = await self.artifact_repo.get_artifact_by_artifact_id(artifact_id)
        if artifact is None:
            raise NotFoundError("artifact not found", {"artifact_id": artifact_id})
        if artifact.archived_at is not None:
            raise NotFoundError("artifact archived", {"artifact_id": artifact_id})
        return artifact

    async def publish(
        self,
        agent: Agent,
        project_id: str,
        title: str,
        summary: str | None,
        artifact_type: str,
        content: str,
        tags: list[str],
        context: dict | None,
        visibility: str = "private",
    ) -> dict:
        project = await self.project_repo.get_by_project_id(project_id)
        if project is None:
            raise NotFoundError("project not found", {"project_id": project_id})
        await self._assert_agent_write_scope(agent, project.id)

        context_pk = None
        if context is not None:
            snap = await self.artifact_repo.create_context_snapshot(
                prompt_snapshot=context.get("prompt_snapshot"),
                external_refs=context.get("external_refs"),
                execution_trace_id=context.get("execution_trace_id"),
            )
            context_pk = snap.id

        artifact = await self.artifact_repo.create_artifact(
            project_pk=project.id,
            title=title,
            summary=summary,
            artifact_type=artifact_type,
            tags=tags or None,
            creator_agent_pk=agent.id,
            owner_human_pk=agent.owner_human_id,
            visibility=visibility,
        )
        await self.artifact_repo.insert_version(
            artifact_pk=artifact.id,
            version_no=1,
            title=title,
            summary=summary,
            content=content,
            content_format=artifact_type,
            changelog=None,
            created_by_agent_pk=agent.id,
            context_snapshot_pk=context_pk,
        )
        await self.audit_repo.write_audit_log(
            event="publish",
            actor_agent_id=agent.id,
            on_behalf_of_human_id=agent.owner_human_id,
            target_artifact_id=artifact.id,
            target_version_no=1,
            payload={"title": title, "artifact_type": artifact_type, "visibility": visibility},
        )
        await self.session.commit()
        return {
            "artifact_id": artifact.artifact_id,
            "version": 1,
            "visibility": artifact.visibility,
            "web_url": f"/artifacts/{artifact.artifact_id}",
        }

    async def get_artifact(
        self,
        principal: Principal,
        artifact_id: str,
        version: int | None = None,
        include_context: bool = False,
        include_feedback: bool = False,
    ) -> dict:
        artifact = await self._resolve_artifact(artifact_id)
        is_anon = principal.kind == "anonymous"
        if artifact.visibility == "public":
            pass
        else:
            if is_anon:
                raise NotFoundError("artifact not found", {"artifact_id": artifact_id})
            await self._assert_principal_read_scope(principal, artifact.project_id)

        version_no = version if version is not None else artifact.current_version
        v = await self.artifact_repo.get_version(artifact.id, version_no)
        if v is None:
            raise NotFoundError(
                "version not found",
                {"artifact_id": artifact_id, "version": version_no},
            )

        project = await self.project_repo.get_by_id(artifact.project_id)
        creator_agent_id = None
        if artifact.creator_agent_id is not None:
            creator = await self.agent_repo.get_by_id(artifact.creator_agent_id)
            if creator is not None:
                creator_agent_id = creator.agent_id

        data: dict = {
            "artifact_id": artifact.artifact_id,
            "version": v.version_no,
            "title": v.title or artifact.title,
            "summary": v.summary or artifact.summary,
            "artifact_type": artifact.artifact_type,
            "tags": artifact.tags or [],
            "creator_agent_id": creator_agent_id,
            "project_id": project.project_id if project else None,
            "content": v.content,
            "content_format": v.content_format,
            "changelog": v.changelog,
            "created_at": v.created_at,
            "updated_at": artifact.updated_at,
            "visibility": artifact.visibility,
        }

        if include_context:
            data["context"] = None
            if v.context_snapshot_id is not None:
                snap = await self.artifact_repo.get_context_snapshot(
                    v.context_snapshot_id
                )
                if snap is not None:
                    data["context"] = {
                        "prompt_snapshot": snap.prompt_snapshot,
                        "external_refs": snap.external_refs,
                        "execution_trace_id": snap.execution_trace_id,
                    }

        if include_feedback and not is_anon:
            feedbacks = await self.feedback_repo.list_feedback(artifact.id)
            data["feedback"] = [
                {
                    "id": fb.id,
                    "version_no": fb.version_no,
                    "kind": fb.kind,
                    "body": fb.body,
                    "inline_anchor": fb.inline_anchor,
                    "created_at": fb.created_at,
                }
                for fb in feedbacks
            ]

        if principal.kind == "agent" and principal.agent is not None:
            await self.audit_repo.write_audit_log(
                event="fetch",
                actor_agent_id=principal.agent.id,
                on_behalf_of_human_id=principal.agent.owner_human_id,
                target_artifact_id=artifact.id,
                target_version_no=version_no,
                payload={"version": version_no, "include_feedback": include_feedback},
            )
            await self.session.commit()
        elif principal.kind == "human" and principal.human is not None:
            await self.audit_repo.write_audit_log(
                event="view",
                actor_human_id=principal.human.id,
                target_artifact_id=artifact.id,
                target_version_no=version_no,
                payload={"version": version_no, "include_feedback": include_feedback},
            )
            await self.session.commit()
        return data

    async def list_versions(self, principal: Principal, artifact_id: str) -> list[dict]:
        artifact = await self._resolve_artifact(artifact_id)
        is_anon = principal.kind == "anonymous"
        if artifact.visibility == "public":
            pass
        else:
            if is_anon:
                raise NotFoundError("artifact not found", {"artifact_id": artifact_id})
            await self._assert_principal_read_scope(principal, artifact.project_id)
        versions = await self.artifact_repo.get_versions(artifact.id)
        return [
            {
                "version_no": v.version_no,
                "title": v.title,
                "summary": v.summary,
                "content_format": v.content_format,
                "changelog": v.changelog,
                "created_at": v.created_at,
            }
            for v in versions
        ]

    async def add_version(
        self,
        agent: Agent,
        artifact_id: str,
        base_version: int,
        title: str | None,
        summary: str | None,
        content: str,
        changelog: str | None,
        context: dict | None,
    ) -> dict:
        artifact = await self._resolve_artifact(artifact_id)
        await self._assert_agent_write_scope(agent, artifact.project_id)

        new_no = base_version + 1
        context_pk = None
        if context is not None:
            snap = await self.artifact_repo.create_context_snapshot(
                prompt_snapshot=context.get("prompt_snapshot"),
                external_refs=context.get("external_refs"),
                execution_trace_id=context.get("execution_trace_id"),
            )
            context_pk = snap.id

        await self.artifact_repo.insert_version(
            artifact_pk=artifact.id,
            version_no=new_no,
            title=title,
            summary=summary,
            content=content,
            content_format=artifact.artifact_type,
            changelog=changelog,
            created_by_agent_pk=agent.id,
            context_snapshot_pk=context_pk,
        )
        affected = await self.artifact_repo.update_current_version(artifact.id, new_no)
        if affected == 0:
            fresh = await self.artifact_repo.get_artifact(artifact.id)
            current = fresh.current_version if fresh is not None else base_version
            raise VersionConflictError(
                {"current_version": current, "expected_base": base_version}
            )
        await self.audit_repo.write_audit_log(
            event="version",
            actor_agent_id=agent.id,
            on_behalf_of_human_id=agent.owner_human_id,
            target_artifact_id=artifact.id,
            target_version_no=new_no,
            payload={"base_version": base_version, "changelog": changelog},
        )
        await self.session.commit()
        return {
            "artifact_id": artifact.artifact_id,
            "version": new_no,
        }

    async def fork(
        self,
        agent: Agent,
        artifact_id: str,
        from_version: int | None,
        new_title: str | None,
        content: str | None,
        context: dict | None,
    ) -> dict:
        parent = await self._resolve_artifact(artifact_id)
        await self._assert_agent_write_scope(agent, parent.project_id)

        parent_version_no = from_version if from_version is not None else parent.current_version
        parent_v = await self.artifact_repo.get_version(parent.id, parent_version_no)
        if parent_v is None:
            raise NotFoundError(
                "parent version not found",
                {"artifact_id": artifact_id, "version": parent_version_no},
            )

        context_pk = None
        if context is not None:
            snap = await self.artifact_repo.create_context_snapshot(
                prompt_snapshot=context.get("prompt_snapshot"),
                external_refs=context.get("external_refs"),
                execution_trace_id=context.get("execution_trace_id"),
            )
            context_pk = snap.id

        fork_title = new_title or parent_v.title or parent.title
        fork_content = content if content is not None else parent_v.content

        child = await self.artifact_repo.create_artifact(
            project_pk=parent.project_id,
            title=fork_title,
            summary=parent.summary,
            artifact_type=parent.artifact_type,
            tags=parent.tags,
            creator_agent_pk=agent.id,
            owner_human_pk=agent.owner_human_id,
            visibility="private",
        )
        await self.artifact_repo.insert_version(
            artifact_pk=child.id,
            version_no=1,
            title=fork_title,
            summary=parent.summary,
            content=fork_content,
            content_format=parent.artifact_type,
            changelog=None,
            created_by_agent_pk=agent.id,
            context_snapshot_pk=context_pk,
        )
        await self.artifact_repo.insert_fork_lineage(
            child_artifact_pk=child.id,
            parent_artifact_pk=parent.id,
            parent_version_no=parent_version_no,
            forked_by_agent_pk=agent.id,
        )
        await self.audit_repo.write_audit_log(
            event="fork",
            actor_agent_id=agent.id,
            on_behalf_of_human_id=agent.owner_human_id,
            target_artifact_id=child.id,
            target_version_no=1,
            payload={
                "parent_artifact_id": artifact_id,
                "parent_version_no": parent_version_no,
            },
        )
        await self.session.commit()
        return {
            "artifact_id": child.artifact_id,
            "version": 1,
            "web_url": f"/artifacts/{child.artifact_id}",
            "parent_artifact_id": parent.artifact_id,
            "parent_version_no": parent_version_no,
        }

    async def search(self, principal: Principal, params: SearchParams) -> list[dict]:
        is_anon = principal.kind == "anonymous"
        if params.project_id is not None:
            project = await self.project_repo.get_by_project_id(params.project_id)
            if project is None:
                raise NotFoundError(
                    "project not found", {"project_id": params.project_id}
                )
            if not is_anon:
                await self._assert_principal_read_scope(principal, project.id)
            results = await self.artifact_repo.list_artifacts(params, public_only=is_anon)
        else:
            if is_anon:
                results = await self.artifact_repo.list_artifacts(params, public_only=True)
            else:
                if principal.kind == "agent" and principal.agent is not None:
                    scoped_pks = await self.agent_repo.list_agent_project_pks(
                        principal.agent.id
                    )
                elif principal.kind == "human" and principal.human is not None:
                    scoped_pks = await self.project_repo.list_human_project_pks(
                        principal.human.id
                    )
                else:
                    scoped_pks = []
                if not scoped_pks:
                    results = await self.artifact_repo.list_artifacts(params, public_only=True)
                else:
                    results = await self.artifact_repo.list_artifacts(
                        params, project_pks=scoped_pks, include_public=True
                    )
        return [
            {
                "artifact_id": a.artifact_id,
                "title": a.title,
                "summary": a.summary,
                "current_version": a.current_version,
                "artifact_type": a.artifact_type,
                "tags": a.tags or [],
                "updated_at": a.updated_at,
                "visibility": a.visibility,
            }
            for a in results
        ]

    async def change_visibility(
        self,
        human: HumanUser,
        artifact_id: str,
        visibility: str,
    ) -> dict:
        artifact = await self._resolve_artifact(artifact_id)
        await self._assert_human_write_scope(human, artifact.project_id)
        await self.artifact_repo.update_visibility(artifact.id, visibility)
        await self.audit_repo.write_audit_log(
            event="visibility_change",
            actor_human_id=human.id,
            target_artifact_id=artifact.id,
            payload={"visibility": visibility},
        )
        await self.session.commit()
        return {
            "artifact_id": artifact.artifact_id,
            "visibility": visibility,
        }
