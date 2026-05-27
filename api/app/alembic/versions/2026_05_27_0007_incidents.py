"""incidents · agent ops governance + hash-chained incident receipts

Revision ID: 0007_incidents
Revises: 0006_agent_profiles
Create Date: 2026-05-27 20:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0007_incidents"
down_revision: Union[str, None] = "0006_agent_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_profiles", sa.Column("governance", JSONB(), nullable=True))
    # Incident receipts ride the same per-org hash chain but have no run → relax run_id.
    op.alter_column("receipts", "run_id", existing_type=sa.String(length=36), nullable=True)
    op.alter_column("artifacts", "run_id", existing_type=sa.String(length=36), nullable=True)
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_profile_id", sa.String(length=36), sa.ForeignKey("agent_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(length=24), nullable=False),       # rogue | dark | policy_violation | recurring_flag
        sa.Column("tier", sa.String(length=16), nullable=False, server_default="high"),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("lane", sa.String(length=200), nullable=True),
        sa.Column("response", JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("receipt_id", sa.String(length=36), sa.ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("incidents")
    op.alter_column("artifacts", "run_id", existing_type=sa.String(length=36), nullable=False)
    op.alter_column("receipts", "run_id", existing_type=sa.String(length=36), nullable=False)
    op.drop_column("agent_profiles", "governance")
