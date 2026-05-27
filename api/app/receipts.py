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


def render_pdf(payload: dict, receipt_sha256: str) -> bytes:
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
