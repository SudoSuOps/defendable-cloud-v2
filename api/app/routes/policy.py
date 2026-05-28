"""/policy — public-facing policy surfaces.

The first policy we publish is the training-data policy — the explicit
doctrine lock that customer-uploaded evidence + submissions NEVER enter the
SwarmJelly training pool. The body is FROZEN in code with a stable SHA-256
so anyone can verify the policy hasn't drifted.

This endpoint is intentionally unauthenticated — the brand promise needs to
be readable by anyone, anywhere, without sign-in.
"""
from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter

from app.schemas import TrainingDataPolicy

router = APIRouter(prefix="/policy", tags=["policy"])


# ── Frozen policy bodies ──────────────────────────────────────────────────────
#
# Updates require a deploy that bumps the version + last_updated. The SHA-256
# is computed deterministically; any field change shifts the hash. The hash
# IS the receipt for the policy at a point in time.

TRAINING_DATA_POLICY_V1 = {
    "version": "v1",
    "statement": (
        "We learn from how agents fail. We never learn from what your "
        "business is doing. Every day's new pairs come with a receipt."
    ),
    "we_learn_from": [
        "Aggregated failure patterns derived from the rulebook engine — e.g. "
        "'9B-tier agents systematically fail DSCR re-derivation in this shape' — "
        "at the pattern level, never the deal level.",
        "Public datasets we license + curated synthetic data we cook in-house.",
        "Mr. Defendable founder source material, deeded as books-and-records "
        "(DDEED-FOUNDER-ORIGIN, DDEED-VOCAB, etc.).",
        "Operator-grade content captured with explicit consent (StreetChat pipeline).",
    ],
    "we_dont_learn_from": [
        "Customer evidence — documents, files, notes attached to any Run.",
        "Customer agent submissions — the structured JSON output the agent produced.",
        "Customer-identifiable content — org names, project names, deal terms, "
        "addresses, financial specifics.",
        "Anything carrying customer-identifiable signal of any kind.",
    ],
    "enforcement": [
        "Every evidence_items row carries customer_provided=TRUE at upload "
        "(database default + explicit on every customer-facing route).",
        "Every agent_submissions row carries customer_provided=TRUE at upload "
        "(database default + explicit on every customer-facing route).",
        "The curation pipeline (SwarmJelly extraction) refuses any row with "
        "customer_provided=TRUE — only operator-original / synthetic / licensed "
        "inputs reach training.",
        "Daily-cook receipts publish the provenance hash trail proving no "
        "customer data was used (when the daily-cook pipeline ships).",
        "This policy is versioned in code with a frozen SHA-256; updates "
        "require a deploy that visibly bumps the version.",
    ],
    "effective_at": "2026-05-28T00:00:00Z",
    "last_updated": "2026-05-28T00:00:00Z",
}


def _canonical_hash(policy: dict) -> str:
    """Stable SHA-256 over the policy body (excluding the sha256 field itself).
    Sorted keys + no whitespace = stable across Python versions.
    """
    body = {k: v for k, v in policy.items() if k != "sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def training_data_policy() -> dict:
    """Return the current training-data policy with its computed SHA-256."""
    return {**TRAINING_DATA_POLICY_V1, "sha256": _canonical_hash(TRAINING_DATA_POLICY_V1)}


@router.get("/training-data", response_model=TrainingDataPolicy)
async def get_training_data_policy():
    """The frozen doctrine — what enters and never enters the training corpus.

    No auth required. The brand promise is readable by anyone.
    """
    return training_data_policy()
