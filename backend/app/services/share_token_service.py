import hashlib
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.repos.artifact import ArtifactRepo
from app.repos.audit import AuditRepo
from app.repos.share_token import ShareTokenRepo
from app.services.artifact_service import ArtifactService
from app.services.auth_service import Principal


class ShareTokenService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.share_token_repo = ShareTokenRepo(session)
        self.artifact_repo = ArtifactRepo(session)
        self.artifact_service = ArtifactService(session)
        self.audit_repo = AuditRepo(session)

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def _assert_write_scope(self, principal: Principal, project_pk: int) -> None:
        if principal.kind == "agent" and principal.agent is not None:
            await self.artifact_service._assert_agent_write_scope(principal.agent, project_pk)
            return
        if principal.kind == "human" and principal.human is not None:
            await self.artifact_service._assert_human_write_scope(principal.human, project_pk)
            return
        raise UnauthorizedError("authentication required")

    async def _resolve_artifact(self, artifact_id: str):
        artifact = await self.artifact_repo.get_artifact_by_artifact_id(artifact_id)
        if artifact is None:
            raise NotFoundError("artifact not found", {"artifact_id": artifact_id})
        if artifact.archived_at is not None:
            raise NotFoundError("artifact archived", {"artifact_id": artifact_id})
        return artifact

    async def create_share_token(self, principal: Principal, artifact_id: str) -> dict:
        artifact = await self._resolve_artifact(artifact_id)
        await self._assert_write_scope(principal, artifact.project_id)

        for _ in range(5):
            token = secrets.token_urlsafe(32)
            token_hash = self._hash(token)
            existing = await self.share_token_repo.find_by_token_hash(token_hash)
            if existing is None:
                break
        else:
            raise ForbiddenError("unable to allocate a unique token")

        share_token = await self.share_token_repo.create(
            artifact_pk=artifact.id,
            token_hash=token_hash,
            created_by_human_id=principal.human_pk,
            created_by_agent_id=(principal.agent.id if principal.agent is not None else None),
        )
        await self.audit_repo.write_audit_log(
            event="share_token_created",
            actor_human_id=(principal.human.id if principal.human is not None else None),
            actor_agent_id=(principal.agent.id if principal.agent is not None else None),
            on_behalf_of_human_id=principal.human_pk,
            target_artifact_id=artifact.id,
            payload={"share_token_id": share_token.share_token_id},
        )
        await self.session.commit()
        return {
            "share_token_id": share_token.share_token_id,
            "token": token,
            "artifact_id": artifact.artifact_id,
            "url": f"/artifacts/{artifact.artifact_id}/share/{token}",
            "created_at": share_token.created_at,
        }

    async def revoke_share_token(
        self, principal: Principal, artifact_id: str, share_token_id: str
    ) -> dict:
        artifact = await self._resolve_artifact(artifact_id)
        await self._assert_write_scope(principal, artifact.project_id)

        share_token = await self.share_token_repo.find_by_share_token_id(share_token_id)
        if share_token is None or share_token.artifact_id != artifact.id:
            raise NotFoundError("share token not found", {"share_token_id": share_token_id})
        if share_token.revoked_at is not None:
            return {
                "share_token_id": share_token.share_token_id,
                "revoked_at": share_token.revoked_at,
            }

        updated = await self.share_token_repo.revoke(
            share_token.id,
            revoked_by_human_id=(principal.human.id if principal.human is not None else None),
            revoked_by_agent_id=(principal.agent.id if principal.agent is not None else None),
        )
        if updated is None:
            share_token = await self.share_token_repo.find_by_share_token_id(share_token_id)

        await self.audit_repo.write_audit_log(
            event="share_token_revoked",
            actor_human_id=(principal.human.id if principal.human is not None else None),
            actor_agent_id=(principal.agent.id if principal.agent is not None else None),
            on_behalf_of_human_id=principal.human_pk,
            target_artifact_id=artifact.id,
            payload={"share_token_id": share_token_id},
        )
        await self.session.commit()
        revoked_at = updated.revoked_at if updated is not None else share_token.revoked_at
        return {"share_token_id": share_token_id, "revoked_at": revoked_at}

    async def read_share_token(self, token: str, artifact_id: str) -> dict:
        token_hash = self._hash(token)
        share_token = await self.share_token_repo.find_by_token_hash(token_hash)
        artifact = await self.artifact_repo.get_artifact_by_artifact_id(artifact_id)
        if artifact is None or artifact.archived_at is not None:
            raise NotFoundError("artifact not found", {"artifact_id": artifact_id})
        if share_token is None or share_token.artifact_id != artifact.id:
            raise NotFoundError("share token not found")
        if share_token.revoked_at is not None:
            raise ForbiddenError(
                "share token has been revoked",
                {"token_state": "revoked"},
            )

        data = await self.artifact_service.get_artifact_no_auth(
            artifact_id=artifact.artifact_id, include_context=True
        )
        await self.audit_repo.write_audit_log(
            event="share_token_access",
            target_artifact_id=artifact.id,
            payload={"share_token_id": share_token.share_token_id},
        )
        await self.session.commit()
        return data
