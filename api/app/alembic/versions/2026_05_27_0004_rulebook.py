"""rulebook · referee rules carry kind (auto|checklist) + severity (critical|noncritical)

Revision ID: 0004_rulebook
Revises: 0003_flight_sheets
Create Date: 2026-05-27 04:00:00.000000
"""
from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_rulebook"
down_revision: Union[str, None] = "0003_flight_sheets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def r(key, label, category, kind, severity):
    return {"key": key, "label": label, "category": category, "kind": kind, "severity": severity}


RULES = {
    "agent-general-v1": [
        r("sections_present", "Required sections present", "structure", "auto", "critical"),
        r("output_nonempty", "Output is substantive", "structure", "auto", "noncritical"),
        r("followed_assignment", "Followed the assignment", "policy", "checklist", "critical"),
        r("evidence_used", "Used the provided evidence", "evidence", "checklist", "critical"),
        r("assumptions_labeled", "Assumptions clearly labeled", "policy", "checklist", "noncritical"),
        r("unsupported_claim", "No unsupported claims", "evidence", "checklist", "critical"),
        r("client_ready", "Client-readiness checklist", "readiness", "checklist", "noncritical"),
    ],
    "cre-memo-v1": [
        r("sections_present", "Required sections present", "structure", "auto", "critical"),
        r("numbers_present", "Key metrics quantified", "math", "auto", "noncritical"),
        r("citations_present", "Evidence is cited", "evidence", "auto", "noncritical"),
        r("cre_math", "NOI / cap rate / DSCR reconcile", "math", "checklist", "critical"),
        r("evidence_alignment", "Claims match the provided evidence", "evidence", "checklist", "critical"),
        r("unsupported_claim", "No unsupported / fabricated numbers", "evidence", "checklist", "critical"),
        r("underwriting_discipline", "Underwriting discipline", "policy", "checklist", "noncritical"),
        r("client_ready", "IC-ready checklist", "readiness", "checklist", "noncritical"),
    ],
    "dataset-quality-v1": [
        r("sections_present", "Required sections present", "structure", "auto", "critical"),
        r("output_nonempty", "Output is substantive", "structure", "auto", "noncritical"),
        r("dedup_reasoning", "Dedup / count reasoning shown", "math", "checklist", "noncritical"),
        r("provenance_check", "Provenance established", "evidence", "checklist", "critical"),
        r("label_quality", "Label quality assessed", "readiness", "checklist", "noncritical"),
        r("risk_flags", "Risk / safety flags raised", "policy", "checklist", "noncritical"),
        r("training_usefulness", "Training-grade verdict supported", "readiness", "checklist", "noncritical"),
    ],
    "compute-benchmark-v1": [
        r("sections_present", "Required sections present", "structure", "auto", "critical"),
        r("specs_present", "Specs quantified", "structure", "auto", "noncritical"),
        r("bench_math", "Benchmark numbers reconcile", "math", "checklist", "critical"),
        r("power_sanity", "Power / thermal state sane", "policy", "checklist", "noncritical"),
        r("readiness_verdict", "Readiness verdict supported", "readiness", "checklist", "noncritical"),
    ],
    "document-draft-v1": [
        r("sections_present", "Required sections present", "structure", "auto", "critical"),
        r("output_nonempty", "Output is substantive", "structure", "auto", "noncritical"),
        r("evidence_use", "Evidence used correctly", "evidence", "checklist", "critical"),
        r("policy_compliance", "Within policy boundaries", "policy", "checklist", "critical"),
        r("missing_facts", "Missing facts flagged, not invented", "evidence", "checklist", "noncritical"),
        r("send_ready", "Send-ready checklist", "readiness", "checklist", "noncritical"),
    ],
}


def upgrade() -> None:
    bind = op.get_bind()
    for slug, rules in RULES.items():
        bind.execute(
            sa.text("UPDATE flight_sheets SET audit_checks = CAST(:checks AS jsonb) WHERE slug = :slug"),
            {"checks": json.dumps(rules), "slug": slug},
        )


def downgrade() -> None:
    pass  # forward-only content update
