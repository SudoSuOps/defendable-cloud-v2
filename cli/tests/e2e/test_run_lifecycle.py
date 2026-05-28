"""End-to-end Run lifecycle against the live API.

What this test proves:
  - The `defendable` binary is installed and on PATH
  - Magic-link JWT auth is respected
  - The full Run primitive round-trips:
      Inputs → Evidence → Execution → Checks → Verdict → Approval → Receipt
  - The minted receipt's SHA-256 verifies via the public `/share/<token>` endpoint
  - The per-org hash chain includes the new receipt and validates end-to-end

The test does NOT assert a specific verdict value. The point is the lifecycle,
not the rule outcome. We assert structural correctness: severity ∈
{honey, jelly, propolis}, outcome ∈ {pass, risk, fail}, verified == True.

The test creates real artifacts in the org's data — a project named
"e2e test", a Run titled "e2e-<timestamp>", a single text evidence note, a
submission, a verdict, an approval, and a receipt. Artifacts accumulate
across runs; this is acceptable for v1 (the API is append-only by design).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from .conftest import cli


def _pick_flight_sheet(env) -> dict:
    """Prefer a known-stable schema-shaped sheet; fall back to the first agent-lane sheet."""
    sheets = cli(env, "flight-sheets", "ls", "--lane", "agent") or []
    preferred = ("genai_schema_compliance_v1", "agent_general_v1", "doc_recipient_sender_subject_v1")
    for slug in preferred:
        match = next((s for s in sheets if s.get("slug") == slug), None)
        if match:
            return match
    if sheets:
        return sheets[0]
    pytest.skip("no agent-lane flight sheets active on this API")


def _minimal_submission(flight_sheet_slug: str) -> str:
    """A minimal structured agent submission that any agent-lane flight sheet can grade.

    Matches the canonical submission shape the Kimi Library V1 evaluates. The
    referee may flag specific fields depending on the sheet's rules — that's
    fine. The point is exercising the executor, not crafting a clean pass.
    """
    return json.dumps(
        {
            "assignment_id": flight_sheet_slug,
            "agent_summary": "End-to-end CLI smoke. Structured output for the rulebook executor.",
            "inputs_used": ["e2e_evidence_note"],
            "missing_inputs": [],
            "claims": [
                {
                    "claim": "This is an end-to-end test submission.",
                    "evidence_reference": "e2e_evidence_note",
                    "confidence": "provided",
                }
            ],
            "calculations": [],
            "risks": [],
            "assumptions": ["This is a CLI e2e test, not a real assignment."],
            "open_questions": [],
            "final_output": "PASS",
            "self_check": {
                "all_required_sections_completed": True,
                "all_numbers_have_sources": True,
                "assumptions_labeled": True,
                "missing_inputs_disclosed": True,
            },
        },
        indent=2,
    )


def test_full_run_lifecycle(e2e_env, tmp_path):
    env = e2e_env

    # ── 1. auth · confirm the token is alive ────────────────────────────────────
    me = cli(env, "auth", "status")
    assert me.get("email"), f"auth status returned no email: {me}"
    org_id = me.get("org_id")
    assert org_id, "auth status returned no org_id"

    # ── 2. project · find-or-create ────────────────────────────────────────────
    projects = cli(env, "projects", "ls") or []
    project = next((p for p in projects if p.get("name") == "e2e test"), None)
    if project is None:
        project = cli(env, "projects", "create", "--name", "e2e test")
    project_id = project["id"]
    assert project_id, f"no project id: {project}"

    # ── 3. flight sheet · pick a known-stable one ──────────────────────────────
    sheet = _pick_flight_sheet(env)
    sheet_slug = sheet["slug"]

    # ── 4. runs new ────────────────────────────────────────────────────────────
    title = f"e2e-{int(time.time())}"
    run = cli(
        env, "runs", "new",
        "--project", project_id,
        "--flight-sheet", sheet_slug,
        "--title", title,
    )
    run_id = run["id"]
    assert run.get("status") in ("draft", "assignment_issued"), f"unexpected initial status: {run.get('status')}"

    # ── 5. evidence add (text note) ────────────────────────────────────────────
    cli(
        env, "evidence", "add", run_id,
        "--kind", "note",
        "--label", "e2e_evidence_note",
        "--content", "This is an end-to-end test note attached by the CLI smoke run.",
    )

    # ── 6. submission add (structured JSON) ─────────────────────────────────────
    submission_file = tmp_path / "submission.json"
    submission_file.write_text(_minimal_submission(sheet_slug))
    cli(
        env, "submission", "add", run_id,
        "--output-file", str(submission_file),
        "--agent", "e2e-cli-runner",
        "--model", "n/a",
        "--provider", "test",
    )

    # ── 7. audit run · apply the rulebook ──────────────────────────────────────
    audit = cli(env, "audit", "run", run_id)
    assert "checks" in audit, f"audit returned no checks key: {audit}"
    # `audit run` may produce the verdict directly (deterministic path) OR leave
    # checks as `open` for the operator to grade (heuristic path). Handle both.

    # ── 8. grade any `open` checks · proves the grade endpoint works ───────────
    checks = cli(env, "runs", "checks", run_id) or []
    for ch in checks:
        if ch.get("status") == "open":
            cli(env, "audit", "grade", run_id, ch["id"], "pass", "--detail", "e2e default-grade: pass")

    # ── 9. finalize · if no verdict yet, mint it ───────────────────────────────
    if audit.get("verdict") is None:
        cli(env, "audit", "finalize", run_id)

    # ── 10. assert verdict shape ───────────────────────────────────────────────
    verdict = cli(env, "runs", "verdict", run_id)
    assert verdict.get("outcome") in {"pass", "risk", "fail"}, f"bad outcome: {verdict.get('outcome')}"
    assert verdict.get("severity") in {"honey", "jelly", "propolis"}, f"bad severity: {verdict.get('severity')}"
    score = verdict.get("score_100")
    assert isinstance(score, int) and 0 <= score <= 100, f"bad score_100: {score}"
    assert isinstance(verdict.get("checks_passed"), int)
    assert isinstance(verdict.get("checks_failed"), int)

    # ── 11. approve · the human gate ───────────────────────────────────────────
    approval = cli(
        env, "approval", "set", run_id,
        "--decision", "approved",
        "--note", "e2e smoke approval",
    )
    assert approval.get("decision") == "approved"

    # ── 12. receipt generate · mint on the per-org chain ───────────────────────
    receipt = cli(env, "receipt", "generate", run_id)
    receipt_id = receipt.get("receipt_id")
    assert receipt_id and receipt_id.startswith("DCR-"), f"bad receipt_id: {receipt_id}"
    assert len(receipt.get("receipt_sha256", "")) == 64, "receipt_sha256 should be 64-hex"
    assert len(receipt.get("parent_hash", "")) == 64, "parent_hash should be 64-hex"
    share_url = receipt.get("share_url", "")
    share_token = share_url.rstrip("/").split("/")[-1]
    assert share_token, f"no share token in URL: {share_url}"

    # ── 13. public verify · anyone can prove the hash without auth ─────────────
    verified = cli(env, "verify", share_token)
    assert verified.get("verified") is True, (
        f"the receipt we just minted failed hash verification: {verified}"
    )
    assert verified.get("receipt_id") == receipt_id, "share view returned a different receipt"

    # ── 14. ledger · new receipt is on the chain ───────────────────────────────
    entries = cli(env, "ledger", "ls") or []
    assert any(e.get("receipt_id") == receipt_id for e in entries), (
        f"new receipt {receipt_id} not in ledger ({len(entries)} entries)"
    )

    # ── 15. ledger verify · whole chain still passes ───────────────────────────
    chain = cli(env, "ledger", "verify")
    assert chain.get("ok") is True, f"chain integrity broke: {chain.get('errors')}"
