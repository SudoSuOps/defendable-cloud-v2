"""Receipt assembly: build the canonical payload and render the PDF.

The hash chain (org_seq, parent_hash, receipt_sha256) is computed by the route
that has the DB session; this module builds the payload and the PDF bytes.
"""
from __future__ import annotations

from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def build_payload(
    *,
    receipt_id: str,
    org_seq: int,
    parent_hash: str,
    created_at: str,
    org: dict,
    project: dict,
    run: dict,
    evidence: list[dict],
    checks: list[dict],
    verdict: dict,
    approval: dict,
    share_url: str,
) -> dict:
    """The canonical receipt body. receipt_sha256 is added by the caller after hashing this."""
    return {
        "schema": "defendablecloud.receipt/v1",
        "receipt_id": receipt_id,
        "org_seq": org_seq,
        "parent_hash": parent_hash,
        "created_at": created_at,
        "organization": {"id": org["id"], "name": org["name"]},
        "project": {"id": project["id"], "name": project["name"]},
        "run": {
            "id": run["id"],
            "lane": run["lane"],
            "title": run["title"],
            "inputs": run.get("inputs", {}),
        },
        "evidence": [
            {
                "kind": e["kind"],
                "label": e["label"],
                "sha256": e.get("sha256"),
                "content_type": e.get("content_type"),
                "byte_size": e.get("byte_size", 0),
            }
            for e in evidence
        ],
        "checks": [
            {
                "check_key": c["check_key"],
                "label": c["label"],
                "category": c["category"],
                "status": c["status"],
                "detail": c.get("detail", ""),
                "score": c.get("score"),
            }
            for c in checks
        ],
        "verdict": {
            "outcome": verdict["outcome"],
            "summary": verdict["summary"],
            "score": verdict["score"],
            "checks_passed": verdict["checks_passed"],
            "checks_failed": verdict["checks_failed"],
        },
        "approval": {
            "decision": approval["decision"],
            "approver": approval.get("approver_email"),
            "note": approval.get("note"),
            "approved_at": approval.get("created_at"),
        },
        "share_url": share_url,
    }


def _s(text: Any) -> str:
    """Latin-1 safe string for the core PDF fonts."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def build_cook_payload(
    *,
    receipt_id: str,
    org_seq: int,
    parent_hash: str,
    created_at: str,
    org: dict,
    run: dict,
    cook: dict,
    share_url: str,
) -> dict:
    """Receipt body for a fine-tune cook — proves the before→after lift."""
    return {
        "schema": "defendablecloud.cook-receipt/v1",
        "receipt_id": receipt_id,
        "org_seq": org_seq,
        "parent_hash": parent_hash,
        "created_at": created_at,
        "organization": {"id": org["id"], "name": org["name"]},
        "run": {"id": run["id"], "lane": run["lane"], "title": run["title"]},
        "cook": {
            "base_model": cook["base_model"],
            "dataset": cook["dataset"],
            "pairs": cook["pairs"],
            "eval_before": cook["eval_before"],
            "eval_after": cook["eval_after"],
            "lift": cook["lift"],
            "runner": cook.get("runner"),
            "metrics": cook.get("metrics", {}),
            "compute_usd": cook.get("compute_usd"),
        },
        "share_url": share_url,
    }


def build_eval_payload(
    *,
    receipt_id: str,
    org_seq: int,
    parent_hash: str,
    created_at: str,
    org: dict,
    run: dict,
    flight_sheet: dict,
    assignment_sha256: str,
    submission: dict,
    evidence: list[dict],
    findings: list[dict],
    verdict: dict,
    approval: dict,
    share_url: str,
) -> dict:
    """The Client Results Package — flight sheet, submission, findings, verdict, ownership."""
    return {
        "schema": "defendablecloud.eval-receipt/v1",
        "receipt_id": receipt_id,
        "org_seq": org_seq,
        "parent_hash": parent_hash,
        "created_at": created_at,
        "organization": {"id": org["id"], "name": org["name"]},
        "flight_sheet": {"name": flight_sheet["name"], "version": flight_sheet["version"]},
        "assignment": {"title": run["title"], "sha256": assignment_sha256},
        "submission": {
            "agent_name": submission.get("agent_name"),
            "model_name": submission.get("model_name"),
            "provider": submission.get("provider"),
            "sha256": submission.get("sha256"),
        },
        "evidence": [{"kind": e["kind"], "label": e["label"], "sha256": e.get("sha256")} for e in evidence],
        "findings": [
            {"label": f["label"], "category": f["category"], "status": f["status"], "severity": f.get("severity"), "detail": f.get("detail")}
            for f in findings
        ],
        "verdict": {
            "outcome": verdict["outcome"],
            "score_100": verdict["score_100"],
            "severity": verdict["severity"],
            "client_ready": verdict["client_ready"],
            "recommended_action": verdict["recommended_action"],
            "summary": verdict["summary"],
        },
        "ownership": {
            "agent_created": submission.get("agent_name") or submission.get("model_name"),
            "audited_by": "DefendableCloud Eval",
            "referee_logic": f'{flight_sheet["name"]} v{flight_sheet["version"]}',
            "final_authority": approval.get("approver_email"),
            "approval": approval.get("decision"),
        },
        "share_url": share_url,
    }


def render_pdf(payload: dict, receipt_sha256: str) -> bytes:
    schema = str(payload.get("schema", ""))
    if schema.startswith("defendablecloud.cook"):
        return _render_cook(payload, receipt_sha256)
    if schema.startswith("defendablecloud.eval"):
        return _render_eval(payload, receipt_sha256)
    return _render_run(payload, receipt_sha256)


def _render_run(payload: dict, receipt_sha256: str) -> bytes:
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    def line(text: str, h: float = 6) -> None:
        pdf.cell(0, h, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def wrap(text: str, h: float = 5) -> None:
        pdf.multi_cell(0, h, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Header
    pdf.set_text_color(168, 127, 51)
    pdf.set_font("Helvetica", "B", 9)
    line("DEFENDABLECLOUD  ·  PROOF OF EXECUTION")
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 18)
    line("Verification Receipt", h=10)
    pdf.set_font("Courier", "", 9)
    pdf.set_text_color(90, 90, 90)
    line(payload["receipt_id"], h=5)
    line(payload["created_at"], h=5)
    pdf.ln(3)

    def section(title: str) -> None:
        pdf.set_text_color(168, 127, 51)
        pdf.set_font("Helvetica", "B", 8)
        line(title.upper())
        pdf.set_text_color(20, 20, 20)

    def row(k: str, v: str) -> None:
        pdf.set_text_color(110, 110, 110)
        pdf.set_font("Helvetica", "B", 8)
        line(k.upper(), h=4.5)
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "", 10)
        wrap(v, h=5.5)
        pdf.ln(1)

    run = payload["run"]
    section("Run")
    row("Title", run["title"])
    row("Lane", run["lane"])
    row("Project", payload["project"]["name"])
    row("Organization", payload["organization"]["name"])
    pdf.ln(2)

    v = payload["verdict"]
    section("Verdict")
    row("Outcome", v["outcome"].upper())
    row("Score", f'{v["score"]} ({v["checks_passed"]} passed, {v["checks_failed"]} failed)')
    row("Summary", v["summary"])
    pdf.ln(2)

    section("Checks")
    pdf.set_font("Courier", "", 9)
    for c in payload["checks"]:
        mark = {"pass": "[PASS]", "fail": "[FAIL]", "risk": "[RISK]", "skip": "[skip]"}.get(c["status"], "[ ?? ]")
        wrap(f'{mark} {c["label"]} ({c["category"]}) - {c["detail"]}')
    pdf.ln(2)

    if payload["evidence"]:
        section("Evidence")
        pdf.set_font("Courier", "", 9)
        for e in payload["evidence"]:
            h = (e.get("sha256") or "")[:16]
            tail = f"  sha256:{h}" if h else ""
            wrap(f'- [{e["kind"]}] {e["label"]}{tail}')
        pdf.ln(2)

    ap = payload["approval"]
    section("Approval")
    row("Decision", ap["decision"].upper())
    row("Approver", ap.get("approver") or "-")
    if ap.get("note"):
        row("Note", ap["note"])
    pdf.ln(2)

    section("Integrity")
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(90, 90, 90)
    wrap(f'receipt_sha256: {receipt_sha256}', h=4.5)
    wrap(f'parent_hash:    {payload["parent_hash"]}', h=4.5)
    wrap(f'org_seq:        {payload["org_seq"]}', h=4.5)
    wrap(f'verify:         {payload["share_url"]}', h=4.5)
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    wrap(
        "DefendableCloud is the hosted proof vault. This receipt records what ran, what was "
        "checked, and who approved it. Verify the hash chain at the link above.",
        h=4.5,
    )

    out = pdf.output()
    return bytes(out)


def _render_cook(payload: dict, receipt_sha256: str) -> bytes:
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    def line(text: str, h: float = 6) -> None:
        pdf.cell(0, h, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def wrap(text: str, h: float = 5) -> None:
        pdf.multi_cell(0, h, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def section(title: str) -> None:
        pdf.set_text_color(168, 127, 51)
        pdf.set_font("Helvetica", "B", 8)
        line(title.upper())
        pdf.set_text_color(20, 20, 20)

    def row(k: str, v: str) -> None:
        pdf.set_text_color(110, 110, 110)
        pdf.set_font("Helvetica", "B", 8)
        line(k.upper(), h=4.5)
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "", 10)
        wrap(v, h=5.5)
        pdf.ln(1)

    c = payload["cook"]
    before = c["eval_before"]
    after = c.get("eval_after")
    lift = c.get("lift")

    pdf.set_text_color(168, 127, 51)
    pdf.set_font("Helvetica", "B", 9)
    line("DEFENDABLECLOUD  ·  PROOF OF EXECUTION")
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 18)
    line("Fine-tune Receipt", h=10)
    pdf.set_font("Courier", "", 9)
    pdf.set_text_color(90, 90, 90)
    line(payload["receipt_id"], h=5)
    line(payload["created_at"], h=5)
    pdf.ln(3)

    # The lift — the whole point.
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(20, 20, 20)
    lift_str = f"{lift:+.1%}" if isinstance(lift, (int, float)) else "—"
    b = f"{before:.1%}" if isinstance(before, (int, float)) else "—"
    a = f"{after:.1%}" if isinstance(after, (int, float)) else "—"
    line(f"Eval  {b}  ->  {a}   ({lift_str})", h=9)
    pdf.ln(2)

    section("Cook")
    row("Run", payload["run"]["title"])
    row("Base model", c["base_model"])
    row("Dataset", f'{c["dataset"]}  ·  {c["pairs"]} pairs')
    if c.get("runner"):
        row("Runner", c["runner"])
    if c.get("compute_usd") is not None:
        row("Compute (transparency)", f'${c["compute_usd"]}')
    row("Organization", payload["organization"]["name"])
    pdf.ln(2)

    section("Integrity")
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(90, 90, 90)
    wrap(f"receipt_sha256: {receipt_sha256}", h=4.5)
    wrap(f'parent_hash:    {payload["parent_hash"]}', h=4.5)
    wrap(f'org_seq:        {payload["org_seq"]}', h=4.5)
    wrap(f'verify:         {payload["share_url"]}', h=4.5)
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    wrap(
        "This receipt records a fine-tune cook and the measured change on the same eval, before "
        "and after. The lift is proven against the eval, not asserted. Verify the hash chain above.",
        h=4.5,
    )
    return bytes(pdf.output())


def _render_eval(payload: dict, receipt_sha256: str) -> bytes:
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    def line(text: str, h: float = 6) -> None:
        pdf.cell(0, h, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def wrap(text: str, h: float = 5) -> None:
        pdf.multi_cell(0, h, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def section(title: str) -> None:
        pdf.set_text_color(168, 127, 51)
        pdf.set_font("Helvetica", "B", 8)
        line(title.upper())
        pdf.set_text_color(20, 20, 20)

    def row(k: str, v: str) -> None:
        pdf.set_text_color(110, 110, 110)
        pdf.set_font("Helvetica", "B", 8)
        line(k.upper(), h=4.5)
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "", 10)
        wrap(v, h=5.5)
        pdf.ln(1)

    v = payload["verdict"]
    sub = payload["submission"]

    pdf.set_text_color(168, 127, 51)
    pdf.set_font("Helvetica", "B", 9)
    line("DEFENDABLECLOUD  ·  CLOUD-VAULT EVAL")
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 18)
    line("Eval Receipt", h=10)
    pdf.set_font("Courier", "", 9)
    pdf.set_text_color(90, 90, 90)
    line(payload["receipt_id"], h=5)
    line(payload["created_at"], h=5)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(20, 20, 20)
    line(f'Verdict: {v["outcome"].upper()}  ·  {v["score_100"]}/100  ·  {(v["severity"] or "").upper()}', h=9)
    pdf.set_font("Helvetica", "", 10)
    wrap(f'Client ready: {v["client_ready"]}', h=6)
    pdf.ln(2)

    section("Eval")
    row("Assignment", payload["assignment"]["title"])
    row("Flight sheet", f'{payload["flight_sheet"]["name"]} v{payload["flight_sheet"]["version"]}')
    row("Agent / model", f'{sub.get("agent_name") or "—"} · {sub.get("model_name") or "—"} ({sub.get("provider") or "—"})')
    pdf.ln(1)

    section("Referee flags")
    pdf.set_font("Courier", "", 9)
    for f in payload["findings"]:
        mark = {"pass": "[PASS]", "flag": "[FLAG]", "open": "[OPEN]", "skip": "[skip]"}.get(f["status"], "[ ?? ]")
        sev = f' {f.get("severity")}' if f["status"] == "flag" and f.get("severity") else ""
        wrap(f'{mark}{sev} {f["label"]} ({f["category"]}) - {f.get("detail") or ""}')
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 10)
    wrap(f'Recommended action: {v["recommended_action"]}', h=5.5)
    pdf.ln(2)

    section("Ownership / authority")
    o = payload["ownership"]
    row("Agent created the work", o.get("agent_created") or "—")
    row("Audited by", o.get("audited_by"))
    row("Referee logic", o.get("referee_logic"))
    row("Final authority", o.get("final_authority") or "—")
    row("Approval", (o.get("approval") or "pending").upper())
    pdf.ln(1)

    section("Integrity")
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(90, 90, 90)
    wrap(f"receipt_sha256:    {receipt_sha256}", h=4.5)
    wrap(f'parent_hash:       {payload["parent_hash"]}', h=4.5)
    wrap(f'assignment_sha256: {payload["assignment"]["sha256"]}', h=4.5)
    wrap(f'submission_sha256: {sub.get("sha256")}', h=4.5)
    wrap(f'verify:            {payload["share_url"]}', h=4.5)
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    wrap(
        "The agent did the work. DefendableCloud audited it against the flight sheet. The referee "
        "issued findings. A human held final authority. This receipt is the proof.",
        h=4.5,
    )
    return bytes(pdf.output())
