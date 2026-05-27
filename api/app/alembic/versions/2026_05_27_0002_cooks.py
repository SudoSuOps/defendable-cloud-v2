"""cooks · datasets catalog + fine-tune jobs

Revision ID: 0002_cooks
Revises: 0001_initial
Create Date: 2026-05-27 02:00:00.000000
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002_cooks"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_DATASETS = [
    ("cre-memo-repair", "CRE Memo Repair", "cre", "agent", 980, "royal_jelly",
     "Tightens CRE memo / LOI review: standard-vs-nonstandard term flagging, cap-rate and NOI math, citation discipline.",
     "agent omits or fabricates deal terms; weak numeric checks"),
    ("support-refund-policy", "Support Refund Policy", "support", "agent", 640, "honey",
     "Teaches a support agent to stay inside the refund permission envelope and escalate instead of acting outside policy.",
     "agent takes actions outside its permission envelope"),
    ("dataset-provenance-qa", "Dataset Provenance QA", "dataset_qa", "dataset", 750, "honey",
     "Improves dataset triage: source attribution, dedup reasoning, and training-grade vs reject judgments.",
     "weak provenance / mislabels training-grade data"),
    ("compute-bench-readout", "Compute Bench Readout", "compute", "compute", 520, "honey",
     "Sharpens benchmark interpretation: GPU identity, power/thermal sanity, and sale/rental readiness calls.",
     "misreads benchmark logs or power state"),
    ("general-grounding", "General Grounding", "general", "other", 1000, "honey",
     "Broad grounding pass: cite-or-abstain, refuse fabrication, show the evidence behind a claim.",
     "hallucination / unsupported claims"),
]


def _ts():
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    datasets = op.create_table(
        "datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(48), nullable=False),
        sa.Column("lane", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("pair_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tier", sa.String(16), nullable=False, server_default="honey"),
        sa.Column("targets", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _ts(),
    )

    op.create_table(
        "cooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("base_model", sa.String(120), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("eval_before", sa.Float(), nullable=False, server_default="0"),
        sa.Column("eval_after", sa.Float(), nullable=True),
        sa.Column("lift", sa.Float(), nullable=True),
        sa.Column("pairs", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("adapter_ref", sa.Text(), nullable=True),
        sa.Column("runner", sa.String(80), nullable=True),
        sa.Column("metrics", JSONB(), nullable=False, server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        _ts(),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cooks_org_id", "cooks", ["org_id"])
    op.create_index("ix_cooks_run_id", "cooks", ["run_id"])
    op.create_index("ix_cooks_status", "cooks", ["status"])
    op.create_index("ix_cooks_created_at", "cooks", ["created_at"])

    now = datetime.now(timezone.utc)
    op.bulk_insert(
        datasets,
        [
            {
                "id": uuid.uuid4().hex, "slug": s, "name": n, "domain": d, "lane": ln,
                "pair_count": pc, "tier": t, "description": desc, "targets": tg,
                "active": True, "created_at": now,
            }
            for (s, n, d, ln, pc, t, desc, tg) in SEED_DATASETS
        ],
    )


def downgrade() -> None:
    op.drop_table("cooks")
    op.drop_table("datasets")
