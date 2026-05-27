"""flight sheets · agent submissions · richer findings

Revision ID: 0003_flight_sheets
Revises: 0002_cooks
Create Date: 2026-05-27 03:00:00.000000
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003_flight_sheets"
down_revision: Union[str, None] = "0002_cooks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ck(key, label, category, kind):
    return {"key": key, "label": label, "category": category, "kind": kind}


SEED = [
    {
        "slug": "agent-general-v1", "name": "AI Agent General Work Eval", "version": "1.0", "lane": "agent",
        "summary": "Any business output — did the agent follow the assignment, use the evidence, and stay honest?",
        "purpose": "Evaluate whether an AI agent completed a structured assignment using provided evidence, with labeled assumptions and client-ready reasoning.",
        "assignment_instructions": "Complete the assigned task using ONLY the provided evidence unless explicitly allowed to assume. Label every assumption. If a required input is missing, say so. Do not fabricate facts or cite evidence that was not provided. Deliver: summary, evidence used, assumptions, risks, and the result.",
        "required_inputs": ["task_brief", "evidence"],
        "expected_outputs": ["summary", "evidence used", "assumptions", "risks", "result"],
        "audit_checks": [
            _ck("sections_present", "Required sections present", "structure", "auto"),
            _ck("output_nonempty", "Output is substantive", "structure", "auto"),
            _ck("followed_assignment", "Followed the assignment", "policy", "judgment"),
            _ck("evidence_used", "Used the provided evidence", "evidence", "judgment"),
            _ck("assumptions_labeled", "Assumptions clearly labeled", "policy", "judgment"),
            _ck("no_fabrication", "No fabricated facts", "evidence", "judgment"),
            _ck("client_ready", "Client-ready", "readiness", "judgment"),
        ],
        "pass_threshold": 80, "fail_threshold": 60,
    },
    {
        "slug": "cre-memo-v1", "name": "CRE Investment Memo Eval", "version": "1.0", "lane": "agent",
        "summary": "Can the agent analyze a CRE deal and produce a defendable investment-committee memo?",
        "purpose": "Evaluate CRE analysis: math discipline (NOI/cap/DSCR), evidence-backed risks, and a client-ready IC memo.",
        "assignment_instructions": "Review the provided rent roll, T12, loan terms, and market notes. Produce a concise investment-committee memo. Do not fabricate numbers. Cite only provided evidence. Label assumptions. State any missing inputs. Deliver: executive summary, key metrics, evidence citations, risk flags, math assumptions, final recommendation.",
        "required_inputs": ["deal_package", "rent_roll", "t12", "loan_terms", "market_notes"],
        "expected_outputs": ["executive summary", "key metrics", "evidence citations", "risk flags", "math assumptions", "final recommendation"],
        "audit_checks": [
            _ck("sections_present", "Required sections present", "structure", "auto"),
            _ck("numbers_present", "Key metrics quantified", "math", "auto"),
            _ck("citations_present", "Evidence is cited", "evidence", "auto"),
            _ck("cre_math", "NOI / cap rate / DSCR hold up", "math", "judgment"),
            _ck("evidence_alignment", "Claims match the provided evidence", "evidence", "judgment"),
            _ck("no_fabrication", "No fabricated numbers", "evidence", "judgment"),
            _ck("underwriting_discipline", "Underwriting discipline", "policy", "judgment"),
            _ck("client_ready", "IC-ready memo", "readiness", "judgment"),
        ],
        "pass_threshold": 80, "fail_threshold": 60,
    },
    {
        "slug": "dataset-quality-v1", "name": "Dataset Quality Eval", "version": "1.0", "lane": "dataset",
        "summary": "Can the agent inspect a dataset for structure, provenance, quality, and risk?",
        "purpose": "Evaluate dataset triage: schema validity, dedup reasoning, provenance, label quality, and training usefulness.",
        "assignment_instructions": "Inspect the provided dataset sample. Assess schema validity, duplicate rate, provenance, label quality, and risk. Do not assume rows you cannot see. Deliver: schema assessment, dedup rate, provenance, label quality, risk flags, training verdict.",
        "required_inputs": ["dataset_sample", "source_notes"],
        "expected_outputs": ["schema assessment", "dedup rate", "provenance", "label quality", "risk flags", "training verdict"],
        "audit_checks": [
            _ck("sections_present", "Required sections present", "structure", "auto"),
            _ck("output_nonempty", "Output is substantive", "structure", "auto"),
            _ck("dedup_reasoning", "Dedup / count reasoning sound", "math", "judgment"),
            _ck("provenance_check", "Provenance is established", "evidence", "judgment"),
            _ck("label_quality", "Label quality assessed", "readiness", "judgment"),
            _ck("risk_flags", "Risk / safety flags raised", "policy", "judgment"),
            _ck("training_usefulness", "Training-grade verdict justified", "readiness", "judgment"),
        ],
        "pass_threshold": 80, "fail_threshold": 60,
    },
    {
        "slug": "compute-benchmark-v1", "name": "Compute Benchmark Eval", "version": "1.0", "lane": "compute",
        "summary": "Can the agent interpret benchmark logs and issue a compute-readiness finding?",
        "purpose": "Evaluate benchmark interpretation: hardware identity, specs, power/thermal sanity, and a sale/rental readiness call.",
        "assignment_instructions": "Review the provided benchmark logs and hardware info. Confirm hardware identity, summarize specs, sanity-check power/thermal state, interpret the benchmark, and issue a readiness verdict. Do not invent specs. Deliver: hardware identity, specs, power state, benchmark results, thermal notes, readiness verdict.",
        "required_inputs": ["benchmark_log", "hardware_info"],
        "expected_outputs": ["hardware identity", "specs", "power state", "benchmark results", "thermal notes", "readiness verdict"],
        "audit_checks": [
            _ck("sections_present", "Required sections present", "structure", "auto"),
            _ck("specs_present", "Specs quantified", "structure", "auto"),
            _ck("bench_math", "Benchmark numbers interpreted correctly", "math", "judgment"),
            _ck("power_sanity", "Power / thermal state sane", "policy", "judgment"),
            _ck("readiness_verdict", "Readiness verdict justified", "readiness", "judgment"),
        ],
        "pass_threshold": 80, "fail_threshold": 60,
    },
    {
        "slug": "document-draft-v1", "name": "Document Draft Eval", "version": "1.0", "lane": "other",
        "summary": "Can the agent draft a structured letter/memo within evidence and policy boundaries?",
        "purpose": "Evaluate a client deliverable draft: structure, tone, evidence use, policy compliance, missing facts, send-readiness.",
        "assignment_instructions": "Draft the requested document using only provided facts. Keep within policy boundaries. Flag any missing facts rather than inventing them. Deliver: structure, tone, evidence, policy compliance, missing facts, send-ready status.",
        "required_inputs": ["brief", "evidence"],
        "expected_outputs": ["structure", "tone", "evidence", "policy compliance", "missing facts", "send ready"],
        "audit_checks": [
            _ck("sections_present", "Required sections present", "structure", "auto"),
            _ck("output_nonempty", "Output is substantive", "structure", "auto"),
            _ck("evidence_use", "Evidence used correctly", "evidence", "judgment"),
            _ck("policy_compliance", "Within policy boundaries", "policy", "judgment"),
            _ck("missing_facts", "Missing facts flagged, not invented", "evidence", "judgment"),
            _ck("send_ready", "Send-ready", "readiness", "judgment"),
        ],
        "pass_threshold": 80, "fail_threshold": 60,
    },
]


def upgrade() -> None:
    flight_sheets = op.create_table(
        "flight_sheets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.String(16), nullable=False, server_default="1.0"),
        sa.Column("lane", sa.String(16), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("assignment_instructions", sa.Text(), nullable=False),
        sa.Column("required_inputs", JSONB(), nullable=False, server_default="[]"),
        sa.Column("expected_outputs", JSONB(), nullable=False, server_default="[]"),
        sa.Column("audit_checks", JSONB(), nullable=False, server_default="[]"),
        sa.Column("pass_threshold", sa.BigInteger(), nullable=False, server_default="80"),
        sa.Column("fail_threshold", sa.BigInteger(), nullable=False, server_default="60"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "agent_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_name", sa.String(120), nullable=True),
        sa.Column("model_name", sa.String(120), nullable=True),
        sa.Column("provider", sa.String(120), nullable=True),
        sa.Column("output_text", sa.Text(), nullable=False),
        sa.Column("tool_logs", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_submissions_run_id", "agent_submissions", ["run_id"])

    # runs: flight sheet + assignment + agent identity, widen status
    op.add_column("runs", sa.Column("flight_sheet_id", sa.String(36), sa.ForeignKey("flight_sheets.id", ondelete="SET NULL"), nullable=True))
    op.add_column("runs", sa.Column("assignment_text", sa.Text(), nullable=True))
    op.add_column("runs", sa.Column("agent_name", sa.String(120), nullable=True))
    op.add_column("runs", sa.Column("model_name", sa.String(120), nullable=True))
    op.add_column("runs", sa.Column("provider", sa.String(120), nullable=True))
    op.alter_column("runs", "status", type_=sa.String(20))

    # verdicts: richer referee findings
    op.add_column("verdicts", sa.Column("score_100", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("verdicts", sa.Column("severity", sa.String(12), nullable=True))
    op.add_column("verdicts", sa.Column("client_ready", sa.String(40), nullable=True))
    op.add_column("verdicts", sa.Column("recommended_action", sa.Text(), nullable=True))

    # check_results: severity + source
    op.add_column("check_results", sa.Column("severity", sa.String(12), nullable=True))
    op.add_column("check_results", sa.Column("source", sa.String(10), nullable=False, server_default="auto"))
    op.alter_column("check_results", "status", type_=sa.String(8))

    now = datetime.now(timezone.utc)
    op.bulk_insert(flight_sheets, [{**s, "id": uuid.uuid4().hex, "active": True, "created_at": now} for s in SEED])


def downgrade() -> None:
    op.drop_column("check_results", "source")
    op.drop_column("check_results", "severity")
    op.drop_column("verdicts", "recommended_action")
    op.drop_column("verdicts", "client_ready")
    op.drop_column("verdicts", "severity")
    op.drop_column("verdicts", "score_100")
    for col in ("provider", "model_name", "agent_name", "assignment_text", "flight_sheet_id"):
        op.drop_column("runs", col)
    op.drop_table("agent_submissions")
    op.drop_table("flight_sheets")
