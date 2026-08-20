from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, generate_business_id


class ShareToken(CreatedAtMixin, Base):
    __tablename__ = "share_token"
    __table_args__ = (
        Index("ix_share_token_token", "token_hash"),
        Index("ix_share_token_artifact_id", "artifact_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    share_token_id: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        default=lambda: generate_business_id("share"),
        nullable=False,
    )
    artifact_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("artifact.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_human_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("human_user.id"))
    created_by_agent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agent.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_human_id: Mapped[int | None] = mapped_column(BigInteger)
    revoked_by_agent_id: Mapped[int | None] = mapped_column(BigInteger)
