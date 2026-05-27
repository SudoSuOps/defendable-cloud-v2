"""initial · DefendableCloud Run schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-27 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts(nullable: bool = False, default: bool = True):
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=sa.func.now() if default else None,
    )


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        _ts(),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("role", sa.String(16), nullable=False, server_default="owner"),
        _ts(),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "magic_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        _ts(),
    )
    op.create_index("ix_magic_tokens_email", "magic_tokens", ["email"])
    op.create_index("ix_magic_tokens_token_hash", "magic_tokens", ["token_hash"])

    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        _ts(),
        sa.UniqueConstraint("org_id", "slug", name="uq_projects_org_slug"),
    )
    op.create_index("ix_projects_org_id", "projects", ["org_id"])

    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lane", sa.String(16), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("inputs", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        _ts(),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_runs_org_id", "runs", ["org_id"])
    op.create_index("ix_runs_project_id", "runs", ["project_id"])
    op.create_index("ix_runs_lane", "runs", ["lane"])
    op.create_index("ix_runs_status", "runs", ["status"])
    op.create_index("ix_runs_created_at", "runs", ["created_at"])

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("tigris_key", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(128), nullable=True),
        _ts(),
    )
    op.create_index("ix_evidence_items_run_id", "evidence_items", ["run_id"])

    op.create_table(
        "check_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("check_key", sa.String(64), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        _ts(),
    )
    op.create_index("ix_check_results_run_id", "check_results", ["run_id"])

    op.create_table(
        "verdicts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outcome", sa.String(8), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("checks_passed", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("checks_failed", sa.BigInteger(), nullable=False, server_default="0"),
        _ts(),
    )
    op.create_index("ix_verdicts_run_id", "verdicts", ["run_id"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(12), nullable=False),
        sa.Column("approver_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approver_email", sa.String(320), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        _ts(),
    )
    op.create_index("ix_approvals_run_id", "approvals", ["run_id"])

    op.create_table(
        "receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receipt_id", sa.String(128), nullable=False, unique=True),
        sa.Column("org_seq", sa.BigInteger(), nullable=False),
        sa.Column("parent_hash", sa.String(64), nullable=False),
        sa.Column("receipt_sha256", sa.String(64), nullable=False),
        sa.Column("share_token", sa.String(64), nullable=False, unique=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("json_key", sa.Text(), nullable=True),
        sa.Column("pdf_key", sa.Text(), nullable=True),
        _ts(),
        sa.UniqueConstraint("org_id", "org_seq", name="uq_receipts_org_seq"),
    )
    op.create_index("ix_receipts_org_id", "receipts", ["org_id"])
    op.create_index("ix_receipts_run_id", "receipts", ["run_id"])
    op.create_index("ix_receipts_receipt_id", "receipts", ["receipt_id"])
    op.create_index("ix_receipts_share_token", "receipts", ["share_token"])
    op.create_index("ix_receipts_created_at", "receipts", ["created_at"])

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("receipts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("tigris_key", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("content_type", sa.String(128), nullable=False),
        _ts(),
    )
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"])
    op.create_index("ix_artifacts_receipt_id", "artifacts", ["receipt_id"])


def downgrade() -> None:
    for t in [
        "artifacts",
        "receipts",
        "approvals",
        "verdicts",
        "check_results",
        "evidence_items",
        "runs",
        "projects",
        "magic_tokens",
        "users",
        "organizations",
    ]:
        op.drop_table(t)
