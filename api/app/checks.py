"""Deterministic verification check engine.

Each lane has a small set of checks across four categories — schema, math,
evidence, policy. Checks are pure functions of the run's inputs + evidence;
no model calls, no randomness. The verdict aggregates the results.

v1 keeps templates simple and deterministic on purpose: a receipt is only as
defensible as the checks behind it, and deterministic checks are reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CheckOutcome:
    check_key: str
    label: str
    category: str  # schema | math | evidence | policy
    status: str  # pass | fail | risk | skip
    detail: str = ""
    score: float | None = None


@dataclass
class VerdictOutcome:
    outcome: str  # pass | fail | risk | repair
    summary: str
    score: float
    checks_passed: int
    checks_failed: int


def _is_number(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    try:
        float(str(v))
        return True
    except (TypeError, ValueError):
        return False


# ── common checks ────────────────────────────────────────────────────────────


def _check_evidence_present(inputs: dict, evidence: list[dict]) -> CheckOutcome:
    n = len(evidence)
    return CheckOutcome(
        "evidence_present", "Evidence attached", "evidence",
        "pass" if n > 0 else "fail",
        f"{n} evidence item(s) attached." if n else "No evidence attached to this run.",
    )


def _check_file_hashes(inputs: dict, evidence: list[dict]) -> CheckOutcome:
    files = [e for e in evidence if e.get("kind") == "file"]
    if not files:
        return CheckOutcome("file_hash_integrity", "File hash integrity", "evidence", "skip",
                            "No file evidence to hash.")
    missing = [e for e in files if not e.get("sha256")]
    if missing:
        return CheckOutcome("file_hash_integrity", "File hash integrity", "evidence", "fail",
                            f"{len(missing)} of {len(files)} files missing a SHA-256.")
    return CheckOutcome("file_hash_integrity", "File hash integrity", "evidence", "pass",
                        f"All {len(files)} file(s) carry a SHA-256.")


def _check_approval_gate(inputs: dict, evidence: list[dict]) -> CheckOutcome:
    return CheckOutcome("human_approval_gate", "Human approval gate", "policy", "pass",
                        "A human owner must approve before a receipt is issued.")


def _require_fields(key: str, label: str, fields: list[str]):
    def _check(inputs: dict, evidence: list[dict]) -> CheckOutcome:
        missing = [f for f in fields if not str(inputs.get(f, "")).strip()]
        if missing:
            return CheckOutcome(key, label, "schema", "fail",
                                f"Missing required input(s): {', '.join(missing)}.")
        return CheckOutcome(key, label, "schema", "pass",
                            f"Required input(s) present: {', '.join(fields)}.")
    return _check


def _check_agent_io(inputs: dict, evidence: list[dict]) -> CheckOutcome:
    kinds = {e.get("kind") for e in evidence}
    if kinds & {"tool_output", "model_output"}:
        return CheckOutcome("agent_io", "Agent input/output captured", "evidence", "pass",
                            "Tool or model output is on record.")
    return CheckOutcome("agent_io", "Agent input/output captured", "evidence", "risk",
                        "No tool/model output attached — the agent's work isn't fully shown.")


def _check_positive_number(key: str, label: str, field: str):
    def _check(inputs: dict, evidence: list[dict]) -> CheckOutcome:
        v = inputs.get(field)
        if not _is_number(v):
            return CheckOutcome(key, label, "math", "fail", f"'{field}' is not a number: {v!r}.")
        if float(str(v)) <= 0:
            return CheckOutcome(key, label, "math", "fail", f"'{field}' must be > 0 (got {v}).")
        return CheckOutcome(key, label, "math", "pass", f"'{field}' = {v} is a positive number.")
    return _check


# ── lane templates ───────────────────────────────────────────────────────────

LaneCheck = Callable[[dict, list[dict]], CheckOutcome]

LANE_TEMPLATES: dict[str, list[LaneCheck]] = {
    "agent": [
        _require_fields("agent_inputs", "Task definition present", ["task"]),
        _check_agent_io,
    ],
    "dataset": [
        _require_fields("dataset_inputs", "Source + size declared", ["source", "row_count"]),
        _check_positive_number("dataset_rows", "Row count is positive", "row_count"),
    ],
    "compute": [
        _require_fields("compute_inputs", "Machine + benchmark declared", ["machine", "benchmark_score"]),
        _check_positive_number("compute_score", "Benchmark score is numeric", "benchmark_score"),
    ],
    "other": [],
}

COMMON_CHECKS: list[LaneCheck] = [
    _check_evidence_present,
    _check_file_hashes,
    _check_approval_gate,
]


def run_checks(lane: str, inputs: dict, evidence: list[dict]) -> tuple[list[CheckOutcome], VerdictOutcome]:
    template = LANE_TEMPLATES.get(lane, [])
    results: list[CheckOutcome] = [c(inputs, evidence) for c in (template + COMMON_CHECKS)]
    return results, _verdict(results)


def _verdict(results: list[CheckOutcome]) -> VerdictOutcome:
    graded = [r for r in results if r.status != "skip"]
    passed = sum(1 for r in graded if r.status == "pass")
    failed = sum(1 for r in graded if r.status == "fail")
    risky = sum(1 for r in graded if r.status == "risk")
    total = max(len(graded), 1)
    score = round(passed / total, 4)

    if failed:
        outcome = "fail"
        summary = f"{failed} check(s) failed. Not defendable until repaired."
    elif risky:
        outcome = "risk"
        summary = f"{passed} passed, {risky} flagged for review. Approve with judgment."
    else:
        outcome = "pass"
        summary = f"All {passed} graded checks passed. Ready for approval."

    return VerdictOutcome(outcome, summary, score, passed, failed)
