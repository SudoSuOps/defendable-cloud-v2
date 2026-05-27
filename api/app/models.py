from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Tenancy ────────────────────────────────────────────────────────────────


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(16), default="owner", nullable=False)  # owner | member
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class MagicToken(Base):
    """One-time login token. We store only the sha256 of the token."""

    __tablename__ = "magic_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


# ─── Work ───────────────────────────────────────────────────────────────────


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_projects_org_slug"),)


class FlightSheet(Base):
    """A reusable, versioned eval template — the game plan a client picks."""

    __tablename__ = "flight_sheets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(16), default="1.0", nullable=False)
    lane: Mapped[str] = mapped_column(String(16), nullable=False)  # eval type
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    assignment_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    required_inputs: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    expected_outputs: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    audit_checks: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # [{key,label,category,kind}]
    pass_threshold: Mapped[int] = mapped_column(BigInteger, default=80, nullable=False)
    fail_threshold: Mapped[int] = mapped_column(BigInteger, default=60, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    flight_sheet_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("flight_sheets.id", ondelete="SET NULL"), nullable=True)
    lane: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # agent | dataset | compute | other
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    # draft | assignment_issued | submitted | audited | findings_ready | approved | rejected | receipted
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    inputs: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    assignment_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    evidence: Mapped[list["EvidenceItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    checks: Mapped[list["CheckResult"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class EvidenceItem(Base):
    """Inputs attached to a run: files (in Tigris), notes, URLs, outputs, logs."""

    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)  # file | note | url | observation | tool_output | model_output | log
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # for note/url/text
    tigris_key: Mapped[str | None] = mapped_column(Text, nullable=True)  # for files
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    byte_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class AgentSubmission(Base):
    """What the agent returned — first-class, hashed, with model identity."""

    __tablename__ = "agent_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    tool_logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    check_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)  # structure | evidence | math | policy | readiness
    # pass | fail | risk | skip | review  (review = awaiting operator judgment)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(12), nullable=True)  # honey | jelly | propolis
    source: Mapped[str] = mapped_column(String(10), default="auto", nullable=False)  # auto | operator
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class Verdict(Base):
    __tablename__ = "verdicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(8), nullable=False)  # pass | fail | risk | repair
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0..1
    score_100: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(12), nullable=True)  # honey | jelly | propolis
    client_ready: Mapped[str | None] = mapped_column(String(40), nullable=True)  # yes | after edits | no
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    checks_passed: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    checks_failed: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(12), nullable=False)  # approved | rejected | escalated
    approver_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approver_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class Receipt(Base):
    """The hash-chained proof object. One chain per organization."""

    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    org_seq: Mapped[int] = mapped_column(BigInteger, nullable=False)  # monotonic per org
    parent_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    share_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    json_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False, index=True)

    __table_args__ = (UniqueConstraint("org_id", "org_seq", name="uq_receipts_org_seq"),)


class Dataset(Base):
    """A pre-baked, eval-aligned dataset available in the vault to fine-tune with."""

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(48), nullable=False)  # cre | support | dataset_qa | compute | general
    lane: Mapped[str] = mapped_column(String(16), nullable=False)  # which run lane it targets
    description: Mapped[str] = mapped_column(Text, nullable=False)
    pair_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    tier: Mapped[str] = mapped_column(String(16), default="honey", nullable=False)  # royal_jelly | honey | jelly
    targets: Mapped[str | None] = mapped_column(Text, nullable=True)  # what failure mode it addresses
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


class Cook(Base):
    """A fine-tune job: tune one of our base models on a dataset, then re-eval to prove lift."""

    __tablename__ = "cooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    base_model: Mapped[str] = mapped_column(String(120), nullable=False)
    # queued | claimed | running | succeeded | failed
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False, index=True)
    eval_before: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    eval_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    lift: Mapped[float | None] = mapped_column(Float, nullable=True)
    pairs: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    adapter_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    runner: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("receipts.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)


class Artifact(Base):
    """A generated, exportable file (JSON receipt, PDF, evidence bundle) in Tigris."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("receipts.id", ondelete="CASCADE"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)  # receipt_json | receipt_pdf | evidence_bundle
    tigris_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
