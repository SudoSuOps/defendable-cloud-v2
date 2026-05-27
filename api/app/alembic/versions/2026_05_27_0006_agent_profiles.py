"""agent_profiles · books-and-records for the agent STACK (harness/model/runtime)

Revision ID: 0006_agent_profiles
Revises: 0005_eval_spec
Create Date: 2026-05-27 18:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0006_agent_profiles"
down_revision: Union[str, None] = "0005_eval_spec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("harness", sa.String(length=80), nullable=True),
        sa.Column("harness_version", sa.String(length=40), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("model_provider", sa.String(length=80), nullable=True),
        sa.Column("served_by", sa.String(length=40), nullable=True),
        sa.Column("runtime_host", sa.String(length=120), nullable=True),
        sa.Column("runtime_os", sa.String(length=80), nullable=True),
        sa.Column("runtime_hardware", sa.String(length=160), nullable=True),
        sa.Column("tools", JSONB(), nullable=False, server_default="[]"),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("capability_tier", sa.String(length=16), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column("runs", sa.Column("agent_profile_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "runs_agent_profile_id_fkey", "runs", "agent_profiles",
        ["agent_profile_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("runs_agent_profile_id_fkey", "runs", type_="foreignkey")
    op.drop_column("runs", "agent_profile_id")
    op.drop_table("agent_profiles")
