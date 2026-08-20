from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, InvalidAnchorError, NotFoundError
from app.models.project import HumanUser
from app.repos.agent import AgentRepo
from app.repos.artifact import ArtifactRepo
from app.repos.audit import AuditRepo
from app.repos.feedback import FeedbackRepo
from app.repos.human import HumanRepo
from app.repos.project import ProjectRepo
from app.services.auth_service import WRITE_ROLES, Principal
from app.services.block_parser import compute_migration_status


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

    async def _assert_human_write_scope(
        self, human: HumanUser, project_pk: int
    ) -> None:
        # 提交反馈是写操作：仅拥有写角色（publisher/both）的 human 可写，
        # 与 artifact_service._assert_human_write_scope 的规则保持一致。
        scope = await self.project_repo.get_human_scope_by_pk(human.id, project_pk)
        if scope is None or scope.role not in WRITE_ROLES:
            raise ForbiddenError("human lacks write access to project")

    async def create_feedback(
        self,
        principal: Principal,
        artifact_id: str,
        kind: str,
        body: str | None,
        block_id: str | None = None,
        version_no: int | None = None,
        selector: str | None = None,
    ) -> dict:
        if principal.human is None:
            raise ForbiddenError("only humans can submit feedback")
        human = principal.human

        artifact = await self.artifact_repo.get_artifact_by_artifact_id(artifact_id)
        if artifact is None:
            raise NotFoundError("artifact not found", {"artifact_id": artifact_id})
        await self._assert_human_write_scope(human, artifact.project_id)

        target_version = version_no if version_no is not None else artifact.current_version
        v = await self.artifact_repo.get_version(artifact.id, target_version)
        if v is None:
            raise NotFoundError(
                "version not found",
                {"artifact_id": artifact_id, "version": target_version},
            )

        # 行内评论必须锚定到 target_version block map 中真实存在的块；
        # block_path / block_text 从 block 记录取，一并落入 inline_anchor，
        # 供 list_feedback 在线计算 migration_status 时作为旧块快照（避免逐条回查锚定版本）。
        inline_anchor: dict | None = None
        if block_id is not None:
            block = await self.artifact_repo.get_version_block(v.id, block_id)
            if block is None:
                raise InvalidAnchorError(
                    "block_id not found in version block map",
                    {"block_id": block_id, "version_no": target_version},
                )
            inline_anchor = {
                "block_id": block_id,
                "block_path": block.block_path,
                "block_text": block.block_text,
                "selector": selector,
                "version_no": target_version,
            }

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
            payload={"kind": kind, "block_id": block_id},
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

    async def list_feedback(
        self,
        principal: Principal,
        artifact_id: str,
        viewing_version: int | None = None,
    ) -> list[dict]:
        artifact = await self.artifact_repo.get_artifact_by_artifact_id(artifact_id)
        if artifact is None:
            raise NotFoundError("artifact not found", {"artifact_id": artifact_id})
        await self._assert_principal_read_scope(principal, artifact.project_id)

        # migration_status 以"当前查看版本"的 block map 为基准在线计算，不持久化。
        # viewing_version 缺省取 current_version；取不到 block map 时该版本视为无块（全部 stale）。
        effective_viewing = (
            viewing_version if viewing_version is not None else artifact.current_version
        )
        viewing_version_obj = await self.artifact_repo.get_version(
            artifact.id, effective_viewing
        )
        viewing_blocks: list = []
        if viewing_version_obj is not None:
            viewing_blocks = await self.artifact_repo.list_version_blocks(
                viewing_version_obj.id
            )

        feedbacks = await self.feedback_repo.list_feedback(artifact.id)
        human_pks = {fb.author_human_id for fb in feedbacks}
        humans = await self.human_repo.get_id_map(list(human_pks))

        results: list[dict] = []
        for fb in feedbacks:
            migration_status: str | None = None
            anchor = fb.inline_anchor
            if anchor and anchor.get("block_id"):
                migration_status = compute_migration_status(
                    anchor["block_id"],
                    anchor.get("block_path", ""),
                    anchor.get("block_text", ""),
                    viewing_blocks,
                )
            results.append(
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
                    "migration_status": migration_status,
                    "created_at": fb.created_at,
                }
            )
        return results
