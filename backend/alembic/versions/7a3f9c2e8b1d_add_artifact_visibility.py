"""add artifact visibility

Revision ID: 7a3f9c2e8b1d
Revises: dcb84fe74273
Create Date: 2026-08-14 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7a3f9c2e8b1d'
down_revision: str | Sequence[str] | None = 'dcb84fe74273'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'artifact',
        sa.Column('visibility', sa.Text(), server_default='private', nullable=False),
    )
    op.create_index(
        'ix_artifact_visibility_public',
        'artifact',
        ['updated_at'],
        unique=False,
        postgresql_where=sa.text("visibility = 'public' AND archived_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_artifact_visibility_public', table_name='artifact')
    op.drop_column('artifact', 'visibility')
