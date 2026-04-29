"""add is_published to notes

Revision ID: 9593194998a9
Revises: 5517f2b1f2eb
Create Date: 2026-04-29 23:17:17.784760
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa



revision: str = '9593194998a9'
down_revision: str | None = '5517f2b1f2eb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'notes',
        sa.Column(
            'is_published',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('notes', 'is_published')
