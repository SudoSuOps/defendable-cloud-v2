"""download_notifications · idempotency table for the staging-ready notifier

When a member POSTs /datasets/catalog/{slug}/download before the file is staged
in Tigris, the receipt is minted with `ready_at_grant=false`. The rails-side
stager then runs every 2 min: `aws s3 cp` from private dataset storage → Tigris bucket, then
calls /internal/stage-complete on the API.

On stage-complete, the API sweeps every receipt with that `tigris_key` whose
`ready_at_grant` was false, and sends a Resend "your download is ready" email
to the member who minted the receipt. Idempotency lives HERE — one row per
receipt that was notified — so we never email the same member twice for the
same grant if the cron retries.

We deliberately don't mutate the receipt to track this. Receipts are
books-and-records · immutable by doctrine. Notification state is operational ·
lives in its own table.

Revision ID: 0011_download_notifications
Revises: 0010_customer_data_gate
Create Date: 2026-05-28 22:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_download_notifications"
down_revision: Union[str, None] = "0010_customer_data_gate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "download_notifications",
        sa.Column("receipt_id", sa.String(length=36), primary_key=True),
        sa.Column(
            "notified_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("notified_email", sa.String(length=320), nullable=False),
        sa.Column("tigris_key", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_download_notifications_tigris_key",
        "download_notifications",
        ["tigris_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_download_notifications_tigris_key",
        table_name="download_notifications",
    )
    op.drop_table("download_notifications")
