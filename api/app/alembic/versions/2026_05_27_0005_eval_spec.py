"""eval_spec · executable check spec on flight sheets (Phase 6 executor)

Revision ID: 0005_eval_spec
Revises: 0004_rulebook
Create Date: 2026-05-27 05:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005_eval_spec"
down_revision: Union[str, None] = "0004_rulebook"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("flight_sheets", sa.Column("eval_spec", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("flight_sheets", "eval_spec")
