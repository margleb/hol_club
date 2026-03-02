"""add event commission and registration commission snapshot

Revision ID: 0015_add_event_commission_stats
Revises: 0014_user_role_admin_user
Create Date: 2026-03-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0015_add_event_commission_stats"
down_revision: Union[str, None] = "0014_user_role_admin_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "commission_percent",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_events_commission_percent_range",
        "events",
        "commission_percent >= 0 AND commission_percent <= 100",
    )

    op.add_column(
        "event_registrations",
        sa.Column(
            "admin_commission_amount",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("event_registrations", "admin_commission_amount")
    op.drop_constraint("ck_events_commission_percent_range", "events", type_="check")
    op.drop_column("events", "commission_percent")
