"""baseline: pgcrypto extension and worker_heartbeat table

Revision ID: 16b5a4f492ee
Revises: 
Create Date: 2026-09-24 17:35:22.430936

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16b5a4f492ee'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
    op.create_table(
        'worker_heartbeat',
        sa.Column('id', sa.SmallInteger(), primary_key=True),
        sa.Column('last_tick', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint('id = 1', name='worker_heartbeat_singleton'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('worker_heartbeat')
    op.execute('DROP EXTENSION IF EXISTS pgcrypto')
