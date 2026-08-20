"""add artifact_version_block

Revision ID: e8a1c4f7b9d2
Revises: 7a3f9c2e8b1d
Create Date: 2026-08-19 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e8a1c4f7b9d2'
down_revision: str | Sequence[str] | None = '7a3f9c2e8b1d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'artifact_version_block',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('artifact_version_id', sa.BigInteger(), nullable=False),
        sa.Column('block_id', sa.String(length=16), nullable=False),
        sa.Column('block_path', sa.Text(), nullable=False),
        sa.Column('block_index', sa.Integer(), nullable=False),
        sa.Column('block_text', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['artifact_version_id'], ['artifact_version.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    # block_id 是纯内容哈希（sha256[:16]），同一版本内重复段落/多个 hr 会共享
    # block_id；唯一性由 (artifact_version_id, block_index) 承担（block_index
    # 由 parse_blocks 按索引递增，天然唯一）。跨版本迁移仍以 block_id 做 exact 匹配。
    op.create_index(
        'ix_artifact_version_block_version_id_block_index',
        'artifact_version_block',
        ['artifact_version_id', 'block_index'],
        unique=True,
    )
    op.create_index(
        'ix_artifact_version_block_version_id',
        'artifact_version_block',
        ['artifact_version_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_artifact_version_block_version_id',
        table_name='artifact_version_block',
    )
    op.drop_index(
        'ix_artifact_version_block_version_id_block_index',
        table_name='artifact_version_block',
    )
    op.drop_table('artifact_version_block')
