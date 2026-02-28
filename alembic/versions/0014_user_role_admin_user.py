"""restrict users.role to admin and user

Revision ID: 0014_user_role_admin_user
Revises: 0013_rm_partner_role_requests
Create Date: 2026-02-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0014_user_role_admin_user"
down_revision: Union[str, None] = "0013_rm_partner_role_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'user' WHERE role = 'partner'")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS userrole")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role_allowed")
    op.create_check_constraint(
        "ck_users_role_allowed",
        "users",
        "role IN ('admin', 'user')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role_allowed", "users", type_="check")
    op.create_check_constraint(
        "userrole",
        "users",
        "role IN ('admin', 'partner', 'user')",
    )
