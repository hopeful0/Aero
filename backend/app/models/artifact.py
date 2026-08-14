from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    generate_business_id,
)


class ContextSnapshot(CreatedAtMixin, Base):
    __tablename__ = "context_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        default=lambda: generate_business_id("snap"),
        nullable=False,
    )
    prompt_snapshot: Mapped[str | None] = mapped_column(Text)
    external_refs: Mapped[dict | None] = mapped_column(JSONB)
    execution_trace_id: Mapped[str | None] = mapped_column(Text)


class Artifact(TimestampMixin, Base):
    __tablename__ = "artifact"
    __table_args__ = (
        Index("ix_artifact_project_id", "project_id"),
        Index("ix_artifact_type", "artifact_type"),
        Index("ix_artifact_creator_agent_id", "creator_agent_id"),
        Index("ix_artifact_created_at", "created_at"),
        Index("ix_artifact_tags", "tags", postgresql_using="gin"),
        Index(
            "ix_artifact_visibility_public",
            "updated_at",
            postgresql_where=text("visibility = 'public' AND archived_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        default=lambda: generate_business_id("art"),
        nullable=False,
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("project.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    artifact_type: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    creator_agent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent.id")
    )
    owner_human_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("human_user.id"), nullable=False
    )
    current_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    content_storage: Mapped[str] = mapped_column(
        Text, nullable=False, default="inline", server_default="inline"
    )
    visibility: Mapped[str] = mapped_column(
        Text, nullable=False, default="private", server_default="private"
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ArtifactVersion(CreatedAtMixin, Base):
    __tablename__ = "artifact_version"
    __table_args__ = (
        Index(
            "ix_artifact_version_artifact_version",
            "artifact_id",
            "version_no",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    artifact_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("artifact.id"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str | None] = mapped_column(Text)
    changelog: Mapped[str | None] = mapped_column(Text)
    created_by_agent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent.id")
    )
    context_snapshot_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("context_snapshot.id")
    )


class ArtifactLineage(CreatedAtMixin, Base):
    __tablename__ = "artifact_lineage"
    __table_args__ = (
        Index("ix_artifact_lineage_child", "child_artifact_id", unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    child_artifact_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("artifact.id"), nullable=False
    )
    parent_artifact_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("artifact.id"), nullable=False
    )
    parent_version_no: Mapped[int | None] = mapped_column(Integer)
    forked_by_agent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent.id")
    )
    fork_note: Mapped[str | None] = mapped_column(Text)
