from sqlalchemy import func, select, update

from app.models.share_token import ShareToken
from app.repos.base import BaseRepo


class ShareTokenRepo(BaseRepo):
    async def create(
        self,
        artifact_pk: int,
        token_hash: str,
        created_by_human_id: int | None = None,
        created_by_agent_id: int | None = None,
    ) -> ShareToken:
        share_token = ShareToken(
            artifact_id=artifact_pk,
            token_hash=token_hash,
            created_by_human_id=created_by_human_id,
            created_by_agent_id=created_by_agent_id,
        )
        self.session.add(share_token)
        await self.session.flush()
        return share_token

    async def find_by_token_hash(self, token_hash: str) -> ShareToken | None:
        result = await self.session.execute(
            select(ShareToken).where(ShareToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def find_by_share_token_id(self, share_token_id: str) -> ShareToken | None:
        result = await self.session.execute(
            select(ShareToken).where(ShareToken.share_token_id == share_token_id)
        )
        return result.scalar_one_or_none()

    async def list_for_artifact(self, artifact_pk: int) -> list[ShareToken]:
        result = await self.session.execute(
            select(ShareToken)
            .where(ShareToken.artifact_id == artifact_pk)
            .order_by(ShareToken.created_at)
        )
        return list(result.scalars().all())

    async def revoke(
        self,
        share_token_pk: int,
        revoked_by_human_id: int | None = None,
        revoked_by_agent_id: int | None = None,
    ) -> ShareToken | None:
        result = await self.session.execute(
            update(ShareToken)
            .where(
                ShareToken.id == share_token_pk,
                ShareToken.revoked_at.is_(None),
            )
            .values(
                revoked_at=func.now(),
                revoked_by_human_id=revoked_by_human_id,
                revoked_by_agent_id=revoked_by_agent_id,
            )
            .returning(ShareToken)
        )
        return result.scalar_one_or_none()
