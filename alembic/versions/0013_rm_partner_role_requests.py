"""remove partner role related schema

Revision ID: 0013_rm_partner_role_requests
Revises: 0012_remove_events_ticket_url
Create Date: 2026-02-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_rm_partner_role_requests"
down_revision: Union[str, None] = "0012_remove_events_ticket_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE users SET role = 'user' WHERE role = 'partner'")
    )
    op.drop_table("partner_requests")
    op.drop_column("users", "commission_percent")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "commission_percent",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_table(
        "partner_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                name="partnerrequeststatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
