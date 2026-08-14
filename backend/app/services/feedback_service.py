from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError
from app.repos.agent import AgentRepo
from app.repos.artifact import ArtifactRepo
from app.repos.audit import AuditRepo
from app.repos.feedback import FeedbackRepo
from app.repos.human import HumanRepo
from app.repos.project import ProjectRepo
from app.services.auth_service import Principal


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.artifact_repo = ArtifactRepo(session)
        self.feedback_repo = FeedbackRepo(session)
        self.agent_repo = AgentRepo(session)
        self.human_repo = HumanRepo(session)
        self.project_repo = ProjectRepo(session)
        self.audit_repo = AuditRepo(session)

    async def _assert_principal_read_scope(
        self, principal: Principal, project_pk: int
    ) -> None:
        if principal.kind == "agent" and principal.agent is not None:
            scope = await self.agent_repo.get_project_scope_by_pk(
                principal.agent.id, project_pk
            )
            if scope is None:
                raise ForbiddenError("agent lacks access to project")
        elif principal.kind == "human" and principal.human is not None:
            scope = await self.project_repo.get_human_scope_by_pk(
                principal.human.id, project_pk
            )
            if scope is None:
                raise ForbiddenError("human lacks access to project")
        else:
            raise ForbiddenError("no principal")

    async def create_feedback(
        self,
        principal: Principal,
        artifact_id: str,
        kind: str,
        body: str | None,
        inline_anchor: dict | None,
        version_no: int | None = None,
    ) -> dict:
        if principal.human is None:
            raise ForbiddenError("only humans can submit feedback")
        human = principal.human

        artifact = await self.artifact_repo.get_artifact_by_artifact_id(artifact_id)
        if artifact is None:
            raise NotFoundError("artifact not found", {"artifact_id": artifact_id})
        await self._assert_principal_read_scope(principal, artifact.project_id)

        target_version = version_no if version_no is not None else artifact.current_version
        v = await self.artifact_repo.get_version(artifact.id, target_version)
        if v is None:
            raise NotFoundError(
                "version not found",
                {"artifact_id": artifact_id, "version": target_version},
            )

        feedback = await self.feedback_repo.create_feedback(
            artifact_pk=artifact.id,
            version_no=target_version,
            author_human_pk=human.id,
            kind=kind,
            body=body,
            inline_anchor=inline_anchor,
        )
        await self.audit_repo.write_audit_log(
            event="feedback",
            actor_human_id=human.id,
            target_artifact_id=artifact.id,
            target_version_no=target_version,
            payload={"kind": kind},
        )
        await self.session.commit()
        return {
            "id": feedback.id,
            "artifact_id": artifact.artifact_id,
            "version_no": feedback.version_no,
            "kind": feedback.kind,
            "body": feedback.body,
            "inline_anchor": feedback.inline_anchor,
            "created_at": feedback.created_at,
        }

    async def list_feedback(self, principal: Principal, artifact_id: str) -> list[dict]:
        artifact = await self.artifact_repo.get_artifact_by_artifact_id(artifact_id)
        if artifact is None:
            raise NotFoundError("artifact not found", {"artifact_id": artifact_id})
        await self._assert_principal_read_scope(principal, artifact.project_id)
        feedbacks = await self.feedback_repo.list_feedback(artifact.id)
        human_pks = {fb.author_human_id for fb in feedbacks}
        humans = await self.human_repo.get_id_map(list(human_pks))
        return [
            {
                "id": fb.id,
                "artifact_id": artifact.artifact_id,
                "version_no": fb.version_no,
                "author_human_id": humans[fb.author_human_id].human_id
                if fb.author_human_id in humans
                else None,
                "kind": fb.kind,
                "body": fb.body,
                "inline_anchor": fb.inline_anchor,
                "created_at": fb.created_at,
            }
            for fb in feedbacks
        ]
