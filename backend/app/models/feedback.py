from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin


class Feedback(CreatedAtMixin, Base):
    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_feedback_artifact_version", "artifact_id", "version_no"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    artifact_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("artifact.id"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    author_human_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("human_user.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    inline_anchor: Mapped[dict | None] = mapped_column(JSONB)
