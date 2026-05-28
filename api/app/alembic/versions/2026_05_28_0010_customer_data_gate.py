"""customer data gate · the doctrine lock

Adds `customer_provided` BOOLEAN (default TRUE) to evidence_items and
agent_submissions. Default TRUE is fail-safe — any row we forgot to tag
explicitly is treated as customer data and refused by the curation pipeline.

The discipline:
  customer evidence + submissions NEVER enter the SwarmJelly training pool.

This migration only opens the column. Enforcement is two-layer:
  1. Route layer · explicit `customer_provided=True` on all customer-org
     create paths (runs.add_evidence, runs.upload_evidence, eval.add_submission).
  2. Curation layer · SwarmJelly extraction reads only WHERE customer_provided
     IS FALSE (operator-original / synthetic / licensed inputs).

Revision ID: 0010_customer_data_gate
Revises: 0009_membership
Create Date: 2026-05-28 20:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_customer_data_gate"
down_revision: Union[str, None] = "0009_membership"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fail-safe: every existing row + every future row is `True` unless an
    # operator-side pipeline explicitly marks it `False`. We never silently
    # forget to mark a row as customer-data.
    op.add_column(
        "evidence_items",
        sa.Column(
            "customer_provided",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "agent_submissions",
        sa.Column(
            "customer_provided",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_index(
        "ix_evidence_items_customer_provided",
        "evidence_items",
        ["customer_provided"],
    )
    op.create_index(
        "ix_agent_submissions_customer_provided",
        "agent_submissions",
        ["customer_provided"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_submissions_customer_provided", table_name="agent_submissions")
    op.drop_index("ix_evidence_items_customer_provided", table_name="evidence_items")
    op.drop_column("agent_submissions", "customer_provided")
    op.drop_column("evidence_items", "customer_provided")
