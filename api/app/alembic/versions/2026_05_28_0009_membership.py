"""membership · members-only community · capped seats · trust-based monthly billing

Adds membership columns to organizations. Each org starts as `pending` and
becomes `active` only after manual admin approval (handled out-of-band until
an admin endpoint lands later). When active_count would exceed the cap, new
applications go to `waitlisted` instead.

  pending     → never applied OR application not yet decided
  active      → member · holds a seat in the cap
  waitlisted  → applied but cap was full at application time
  inactive    → member who lapsed (legacy/future)

Revision ID: 0009_membership
Revises: 0008_api_keys
Create Date: 2026-05-28 19:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0009_membership"
down_revision: Union[str, None] = "0008_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "membership_status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("membership_applied_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("membership_activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("membership_seat_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("membership_application", JSONB(), nullable=True),
    )
    op.create_index(
        "ix_organizations_membership_status",
        "organizations",
        ["membership_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_organizations_membership_status", table_name="organizations")
    op.drop_column("organizations", "membership_application")
    op.drop_column("organizations", "membership_seat_number")
    op.drop_column("organizations", "membership_activated_at")
    op.drop_column("organizations", "membership_applied_at")
    op.drop_column("organizations", "membership_status")
