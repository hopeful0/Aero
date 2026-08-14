from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_business_id


class Project(TimestampMixin, Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        default=lambda: generate_business_id("proj"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class HumanUser(TimestampMixin, Base):
    __tablename__ = "human_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    human_id: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        default=lambda: generate_business_id("user"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )


class HumanProjectScope(Base):
    __tablename__ = "human_project_scope"

    human_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("human_user.id"), primary_key=True
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("project.id"), primary_key=True
    )
    role: Mapped[str | None] = mapped_column(Text)
