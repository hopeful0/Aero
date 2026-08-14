from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_business_id


class Agent(TimestampMixin, Base):
    __tablename__ = "agent"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    agent_id: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        default=lambda: generate_business_id("agent"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(Text)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    owner_human_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("human_user.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )


class AgentProjectScope(Base):
    __tablename__ = "agent_project_scope"

    agent_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent.id"), primary_key=True
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("project.id"), primary_key=True
    )
    role: Mapped[str | None] = mapped_column(Text)
