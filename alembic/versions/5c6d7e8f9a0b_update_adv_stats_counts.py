"""update adv stats counts

Revision ID: 5c6d7e8f9a0b
Revises: 4b0c1d2e3f4a
Create Date: 2025-03-20 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5c6d7e8f9a0b"
down_revision: Union[str, None] = "4b0c1d2e3f4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE adv_stats RENAME COLUMN registrations_count TO interesting_count"
    )
    op.add_column(
        "adv_stats",
        sa.Column(
            "register_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("adv_stats", "register_count")
    op.execute(
        "ALTER TABLE adv_stats RENAME COLUMN interesting_count TO registrations_count"
    )
