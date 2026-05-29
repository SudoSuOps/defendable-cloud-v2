"""org invites · owner-managed RBAC onboarding

Revision ID: 0013_org_invites
Revises: 0012_stripe_membership
Create Date: 2026-05-29 00:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_org_invites"
down_revision: Union[str, None] = "0012_stripe_membership"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_invites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_org_invites_email", "org_invites", ["email"])
    op.create_index("ix_org_invites_org_id", "org_invites", ["org_id"])
    op.create_index("ix_org_invites_token_hash", "org_invites", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_org_invites_token_hash", table_name="org_invites")
    op.drop_index("ix_org_invites_org_id", table_name="org_invites")
    op.drop_index("ix_org_invites_email", table_name="org_invites")
    op.drop_table("org_invites")
