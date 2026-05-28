"""api keys · client-dashboard-v1

API keys for programmatic access — the alternative to the magic-link JWT.
Format `dc_<32 url-safe base64>` so they're easy to spot in logs and pastes.
The plaintext secret is only ever returned ONCE on creation; thereafter we
store only its SHA-256 (via `hash_token`) and the short prefix for display.

Revision ID: 0008_api_keys
Revises: 0007_incidents
Create Date: 2026-05-28 18:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_api_keys"
down_revision: Union[str, None] = "0007_incidents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "org_id",
            sa.String(length=36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key_prefix", sa.String(length=12), nullable=False, unique=True, index=True),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
