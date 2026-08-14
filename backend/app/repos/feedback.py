from sqlalchemy import select

from app.models.feedback import Feedback
from app.repos.base import BaseRepo


class FeedbackRepo(BaseRepo):
    async def create_feedback(
        self,
        artifact_pk: int,
        version_no: int,
        author_human_pk: int,
        kind: str,
        body: str | None = None,
        inline_anchor: dict | None = None,
    ) -> Feedback:
        feedback = Feedback(
            artifact_id=artifact_pk,
            version_no=version_no,
            author_human_id=author_human_pk,
            kind=kind,
            body=body,
            inline_anchor=inline_anchor,
        )
        self.session.add(feedback)
        await self.session.flush()
        return feedback

    async def list_feedback(
        self, artifact_pk: int, version_no: int | None = None
    ) -> list[Feedback]:
        stmt = select(Feedback).where(Feedback.artifact_id == artifact_pk)
        if version_no is not None:
            stmt = stmt.where(Feedback.version_no == version_no)
        stmt = stmt.order_by(Feedback.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
