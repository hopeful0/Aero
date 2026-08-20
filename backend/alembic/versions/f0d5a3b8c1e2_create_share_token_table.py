"""create share_token table

Revision ID: f0d5a3b8c1e2
Revises: e8a1c4f7b9d2
Create Date: 2026-08-20 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0d5a3b8c1e2"
down_revision: str | Sequence[str] | None = "e8a1c4f7b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "share_token",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("share_token_id", sa.String(length=40), nullable=False),
        sa.Column("artifact_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by_human_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_agent_id", sa.BigInteger(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_human_id", sa.BigInteger(), nullable=True),
        sa.Column("revoked_by_agent_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifact.id"]),
        sa.ForeignKeyConstraint(["created_by_agent_id"], ["agent.id"]),
        sa.ForeignKeyConstraint(["created_by_human_id"], ["human_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token_id"),
    )
    op.create_index("ix_share_token_token", "share_token", ["token_hash"], unique=False)
    op.create_index(
        "ix_share_token_artifact_id", "share_token", ["artifact_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_share_token_artifact_id", table_name="share_token"
    )
    op.drop_index("ix_share_token_token", table_name="share_token")
    op.drop_table("share_token")