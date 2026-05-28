"""Stripe membership wiring · 3 new columns on Organization

Members-only · $100/yr · one-time annual payment · test mode first.

Flow: apply → admin approves (status='approved') → checkout (Stripe-hosted) →
webhook fires `checkout.session.completed` → status='active' + seat assigned.

Columns added:
  stripe_customer_id          Stripe customer for the org · stable across renewals
  stripe_payment_intent_id    The specific PI for the current annual cycle · used
                              as the idempotency key so a duplicate webhook
                              delivery doesn't double-activate
  membership_renewal_at       activated_at + 1 year · the date the seat lapses
                              if not re-paid manually (one-time billing doctrine)

Status taxonomy widens by one value (no DB constraint to update — the column
is a free-text String(16)):

  pending      application submitted, admin hasn't reviewed
  waitlisted   100-seat cap was hit at application time
  approved     admin reviewed and approved · waiting on $100 checkout · NEW
  active       paid and on-chain · seat_number assigned
  inactive     lapsed / cancelled

Revision ID: 0012_stripe_membership
Revises: 0011_download_notifications
Create Date: 2026-05-28 23:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_stripe_membership"
down_revision: Union[str, None] = "0011_download_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("stripe_customer_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("stripe_payment_intent_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("membership_renewal_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_organizations_stripe_customer_id",
        "organizations",
        ["stripe_customer_id"],
    )
    # Unique on payment_intent_id makes the webhook idempotent: a duplicate
    # delivery for the same PI hits the constraint and we no-op instead of
    # advancing the membership state twice.
    op.create_index(
        "ix_organizations_stripe_payment_intent_id",
        "organizations",
        ["stripe_payment_intent_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organizations_stripe_payment_intent_id",
        table_name="organizations",
    )
    op.drop_index(
        "ix_organizations_stripe_customer_id",
        table_name="organizations",
    )
    op.drop_column("organizations", "membership_renewal_at")
    op.drop_column("organizations", "stripe_payment_intent_id")
    op.drop_column("organizations", "stripe_customer_id")
