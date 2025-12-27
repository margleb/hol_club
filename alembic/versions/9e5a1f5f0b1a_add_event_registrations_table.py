"""add event registrations table

Revision ID: 9e5a1f5f0b1a
Revises: 4a6f1c2b7f9a
Create Date: 2025-03-10 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e5a1f5f0b1a"
down_revision: Union[str, None] = "4a6f1c2b7f9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_registrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_registrations"),
    )
    op.create_index(
        "ix_event_registrations_event_id",
        "event_registrations",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_registrations_event_id",
        table_name="event_registrations",
    )
    op.drop_table("event_registrations")
