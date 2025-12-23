"""add partner requests and partner role

Revision ID: 6b9c7f4f8bda
Revises: 0254994d22c1
Create Date: 2025-03-09 10:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b9c7f4f8bda"
down_revision: Union[str, None] = "0254994d22c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.Enum("admin", "owner", "user", name="userrole", native_enum=False),
            type_=sa.Enum("admin", "owner", "partner", "user", name="userrole", native_enum=False),
            existing_nullable=False,
        )

    op.execute("UPDATE users SET role='partner' WHERE role='owner'")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.Enum("admin", "owner", "partner", "user", name="userrole", native_enum=False),
            type_=sa.Enum("admin", "partner", "user", name="userrole", native_enum=False),
            existing_nullable=False,
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
            sa.Enum("pending", "approved", "rejected", name="partnerrequeststatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("partner_requests")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.Enum("admin", "partner", "user", name="userrole", native_enum=False),
            type_=sa.Enum("admin", "owner", "partner", "user", name="userrole", native_enum=False),
            existing_nullable=False,
        )

    op.execute("UPDATE users SET role='owner' WHERE role='partner'")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.Enum("admin", "owner", "partner", "user", name="userrole", native_enum=False),
            type_=sa.Enum("admin", "owner", "user", name="userrole", native_enum=False),
            existing_nullable=False,
        )
