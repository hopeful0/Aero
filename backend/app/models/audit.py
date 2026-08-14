from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin


class AuditLog(CreatedAtMixin, Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_actor_agent_id", "actor_agent_id"),
        Index("ix_audit_log_on_behalf_of_human_id", "on_behalf_of_human_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event: Mapped[str] = mapped_column(Text, nullable=False)
    actor_agent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent.id")
    )
    on_behalf_of_human_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("human_user.id")
    )
    actor_human_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("human_user.id")
    )
    target_artifact_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("artifact.id")
    )
    target_version_no: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict | None] = mapped_column(JSONB)
