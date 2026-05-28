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


# Phase 9 · risk tiers for the printed report — game-changers first.
_TIER_RANK = {"high": 0, "mid": 1, "low": 2}
_TIER_LABEL = {"high": "HIGH-RISK", "mid": "MID-RISK", "low": "LOW-RISK"}


def _tier(severity: Any) -> str:
    s = str(severity or "").strip().lower()
    if s in ("high", "critical", "propolis"):
        return "high"
    if s in ("low", "honey", "minor"):
        return "low"
    return "mid"


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
    pinned_model: dict | None = None,
) -> dict:
    """Receipt body for a fine-tune cook — proves the before→after lift.

    If the org has a prior `model-pin-receipt/v1` for the same model slug
    (matched against `cook["base_model"]`), the most recent pin is sealed in
    here as `pinned_model` — a books-and-records pointer from the cook to
    the declaration the member made about *which model* this run used.

    The pinned_model block carries enough to verify out-of-band:
      - slug + name + base + params_b + card_sha256 (sealed snapshot)
      - pinned_at + declaration + client_ref (member-supplied context)
      - pin_receipt_id + pin_receipt_sha256 + pin_share_url (anchor pointer)
    """
    body: dict = {
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
    if pinned_model is not None:
        # Seal only the durable fields. The pin's pin_receipt_sha256 makes the
        # pointer tamper-evident: a future reader can fetch the pin via
        # pin_share_url and confirm the hash.
        body["pinned_model"] = {
            "slug": pinned_model.get("slug"),
            "name": pinned_model.get("name"),
            "base": pinned_model.get("base"),
            "params_b": pinned_model.get("params_b"),
            "card_sha256": pinned_model.get("card_sha256"),
            "pinned_at": pinned_model.get("pinned_at"),
            "declaration": pinned_model.get("declaration"),
            "client_ref": pinned_model.get("client_ref"),
            "pin_receipt_id": pinned_model.get("pin_receipt_id"),
            "pin_receipt_sha256": pinned_model.get("pin_receipt_sha256"),
            "pin_share_url": pinned_model.get("pin_share_url"),
        }
    return body


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
    agent_profile: dict | None = None,
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
        "agent_profile": agent_profile,
        "share_url": share_url,
    }


def build_incident_payload(
    *, receipt_id: str, org_seq: int, parent_hash: str, created_at: str,
    org: dict, incident: dict, agent_profile: dict | None, share_url: str,
) -> dict:
    """Books-and-records for a failure: what tripped, the response, hashed + chained."""
    return {
        "schema": "defendablecloud.incident-receipt/v1",
        "receipt_id": receipt_id,
        "org_seq": org_seq,
        "parent_hash": parent_hash,
        "created_at": created_at,
        "organization": {"id": org["id"], "name": org["name"]},
        "incident": {
            "id": incident["id"], "kind": incident["kind"], "tier": incident.get("tier"),
            "title": incident["title"], "detail": incident.get("detail"),
            "lane": incident.get("lane"), "response": incident.get("response") or [],
            "status": incident.get("status"), "opened_at": incident.get("created_at"),
        },
        "agent_profile": agent_profile,
        "share_url": share_url,
    }


def build_dataset_download_payload(
    *, receipt_id: str, org_seq: int, parent_hash: str, created_at: str,
    org: dict, package: dict, tigris_key: str, ready_at_grant: bool,
    expires_at: str, granted_to_user_id: str | None, share_url: str,
) -> dict:
    """Books-and-records for a dataset-download grant: who got what, when, with
    what expiry · hashed + chained on the per-org receipt rail. The download
    URL itself is operational and NOT in the payload (it rotates with each
    access). The receipt records the GRANT facts.
    """
    return {
        "schema": "defendablecloud.dataset-download-receipt/v1",
        "receipt_id": receipt_id,
        "org_seq": org_seq,
        "parent_hash": parent_hash,
        "created_at": created_at,
        "organization": {"id": org["id"], "name": org["name"]},
        "package": {
            "slug": package["slug"],
            "name": package["name"],
            "vertical": package["vertical"],
            "tier": package["tier"],
            "pkg_class": package["pkg_class"],
            "pairs": package["pairs"],
            "deed_anchored": package["deed_anchored"],
        },
        "tigris_key": tigris_key,
        "ready_at_grant": ready_at_grant,
        "expires_at": expires_at,
        "granted_to_user_id": granted_to_user_id,
        "share_url": share_url,
    }


def build_model_pin_payload(
    *, receipt_id: str, org_seq: int, parent_hash: str, created_at: str,
    org: dict, card: dict, pinned_by_user_id: str | None,
    declaration: str | None, client_ref: str | None, share_url: str,
) -> dict:
    """Books-and-records for a model card pin · who declared which model on
    what date, with what content-hash, sealed onto the per-org chain.

    Only the durable identity fields go in the payload: slug, name, base,
    params, the card's content-hash at pin time. The card body itself can
    evolve in subsequent catalog deploys; this receipt remembers the EXACT
    card hash that was in effect on the pin date.
    """
    return {
        "schema": "defendablecloud.model-pin-receipt/v1",
        "receipt_id": receipt_id,
        "org_seq": org_seq,
        "parent_hash": parent_hash,
        "created_at": created_at,
        "organization": {"id": org["id"], "name": org["name"]},
        "model": {
            "slug": card["slug"],
            "name": card["name"],
            "base": card["base"],
            "params_b": card["params_b"],
            "card_sha256": card["card_sha256"],
        },
        "pinned_at": created_at,
        "pinned_by_user_id": pinned_by_user_id,
        "declaration": declaration,
        "client_ref": client_ref,
        "share_url": share_url,
    }


def render_pdf(payload: dict, receipt_sha256: str) -> bytes:
    schema = str(payload.get("schema", ""))
    if schema.startswith("defendablecloud.cook"):
        return _render_cook(payload, receipt_sha256)
    if schema.startswith("defendablecloud.eval"):
        return _render_eval(payload, receipt_sha256)
    if schema.startswith("defendablecloud.incident"):
        return _render_incident(payload, receipt_sha256)
    if schema.startswith("defendablecloud.dataset-download"):
        return _render_dataset_download(payload, receipt_sha256)
    if schema.startswith("defendablecloud.model-pin"):
        return _render_model_pin(payload, receipt_sha256)
    return _render_run(payload, receipt_sha256)


def _render_model_pin(payload: dict, receipt_sha256: str) -> bytes:
    """Minimal PDF for a model card pin · books-and-records grade. The
    member, the model, the card hash, the declaration, the chain coordinates.
    """
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

    pdf.set_font("Helvetica", "B", 14)
    line("DefendableCloud — Model Pin Receipt")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    line(f"Receipt: {payload.get('receipt_id')}  (org_seq {payload.get('org_seq')})")
    line(f"Pinned: {payload.get('pinned_at') or payload.get('created_at')}")
    pdf.ln(2)

    section("Organization")
    pdf.set_font("Helvetica", "", 10)
    org = payload.get("organization") or {}
    line(f"{org.get('name', '—')} ({org.get('id', '—')})")
    pdf.ln(1)

    section("Model")
    model = payload.get("model") or {}
    pdf.set_font("Helvetica", "B", 11)
    line(model.get("name", "—"))
    pdf.set_font("Helvetica", "", 10)
    line(f"slug: {model.get('slug', '—')}")
    line(f"base: {model.get('base', '—')}    params: {model.get('params_b', '—')}B")
    pdf.ln(1)

    section("Declaration")
    if payload.get("declaration"):
        pdf.set_font("Helvetica", "", 10)
        wrap(payload["declaration"])
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(120, 120, 120)
        line("(no declaration supplied)")
        pdf.set_text_color(20, 20, 20)
    if payload.get("client_ref"):
        pdf.set_font("Helvetica", "", 9)
        line(f"client_ref: {payload['client_ref']}")
    pdf.ln(1)

    section("Integrity")
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(90, 90, 90)
    wrap(f"receipt_sha256:  {receipt_sha256}", h=4.5)
    wrap(f"parent_hash:     {payload.get('parent_hash', '—')}", h=4.5)
    wrap(f"card_sha256:     {model.get('card_sha256', '—')}", h=4.5)
    wrap(f"verify:          {payload.get('share_url', '—')}", h=4.5)
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    wrap(
        "This receipt seals the model card identity at pin time. Even if the "
        "catalog card content evolves later, the card_sha256 above is the exact "
        "snapshot the member declared on this date. Compute is the meter; this "
        "receipt is the books-and-records.",
        h=4.5,
    )
    return bytes(pdf.output())


def _render_dataset_download(payload: dict, receipt_sha256: str) -> bytes:
    """Minimal PDF for a dataset-download grant. Books-and-records grade — the
    member who got the grant, what package, what TTL, the chain coordinates.
    """
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

    pdf.set_font("Helvetica", "B", 14)
    line("DefendableCloud — Dataset Download Receipt")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    line(f"Receipt: {payload.get('receipt_id')}  (org_seq {payload.get('org_seq')})")
    line(f"Granted: {payload.get('created_at')}")
    pdf.ln(2)

    section("Organization")
    pdf.set_font("Helvetica", "", 10)
    org = payload.get("organization") or {}
    line(f"{org.get('name', '—')} ({org.get('id', '—')})")
    pdf.ln(1)

    section("Package")
    pkg = payload.get("package") or {}
    pdf.set_font("Helvetica", "B", 11)
    line(pkg.get("name", "—"))
    pdf.set_font("Helvetica", "", 10)
    line(f"slug: {pkg.get('slug', '—')}")
    line(f"vertical: {pkg.get('vertical', '—')}    tier: {pkg.get('tier', '—')}    class: {pkg.get('pkg_class', '—')}")
    line(f"pairs: {pkg.get('pairs', 0):,}    deed-anchored: {'yes' if pkg.get('deed_anchored') else 'no'}")
    pdf.ln(1)

    section("Access grant")
    line(f"Tigris key:   {payload.get('tigris_key', '—')}")
    line(f"Ready at grant: {'yes' if payload.get('ready_at_grant') else 'no (staging)'}")
    line(f"Signed URL expires: {payload.get('expires_at', '—')}")
    if payload.get("granted_to_user_id"):
        line(f"Granted to user: {payload.get('granted_to_user_id')}")
    pdf.ln(1)

    section("Integrity")
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(90, 90, 90)
    wrap(f"receipt_sha256:  {receipt_sha256}", h=4.5)
    wrap(f"parent_hash:     {payload.get('parent_hash', '—')}", h=4.5)
    wrap(f"verify:          {payload.get('share_url', '—')}", h=4.5)
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    wrap(
        "Datasets are free with membership. This receipt records the access grant — "
        "the package identity, the staging key, and the chain coordinates. The download "
        "URL itself rotates with each access via /share/{token}/download.",
        h=4.5,
    )
    return bytes(pdf.output())


def _render_incident(payload: dict, receipt_sha256: str) -> bytes:
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

    inc = payload["incident"]
    ap = payload.get("agent_profile")
    pdf.set_text_color(168, 127, 51)
    pdf.set_font("Helvetica", "B", 9)
    line("DEFENDABLECLOUD  ·  AGENT OPS")
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 18)
    line("Incident Receipt", h=10)
    pdf.set_font("Courier", "", 9)
    pdf.set_text_color(90, 90, 90)
    line(payload["receipt_id"], h=5)
    line(payload["created_at"], h=5)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(20, 20, 20)
    line(f'{inc["kind"].replace("_", " ").upper()}  ·  {(inc.get("tier") or "").upper()}  ·  {(inc.get("status") or "").upper()}', h=9)
    pdf.set_font("Helvetica", "", 10)
    wrap(inc["title"], h=6)
    pdf.ln(2)

    section("Incident")
    if ap:
        row("Agent", f'{ap.get("name") or "—"}  ·  tier {(ap.get("capability_tier") or "—").upper()}')
    if inc.get("lane"):
        row("Lane", inc["lane"])
    if inc.get("detail"):
        row("Detail", inc["detail"])
    pdf.ln(1)

    section("Response")
    pdf.set_font("Courier", "", 9)
    for r in (inc.get("response") or []):
        wrap(f'- {str(r).replace("_", " ")}')
    if not inc.get("response"):
        wrap("- (none recorded)")
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
        "Everyone alerts; this is the proof. An incident records what tripped and the response "
        "taken, hash-chained into the same ledger as the work receipts. Verify the chain above.",
        h=4.5,
    )
    return bytes(pdf.output())


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

    # Pin pointer — if the org has a prior model-pin-receipt for this slug,
    # the join was sealed at mint time. Surface it so the reader can verify
    # the model claim out-of-band.
    pin = payload.get("pinned_model")
    if pin:
        section("Model declared via pin")
        row("Slug", pin.get("slug") or "—")
        if pin.get("pinned_at"):
            row("Pinned at", pin["pinned_at"])
        if pin.get("declaration"):
            row("Declaration", pin["declaration"])
        if pin.get("client_ref"):
            row("Client ref", pin["client_ref"])
        if pin.get("pin_share_url"):
            row("Pin receipt", pin["pin_share_url"])
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

    # Risk readout — the clear view of the penalties by tier.
    _flags = [f for f in payload["findings"] if f.get("status") == "flag"]
    if _flags:
        _c = {t: sum(1 for f in _flags if _tier(f.get("severity")) == t) for t in ("high", "mid", "low")}
        pdf.set_font("Helvetica", "B", 10)
        line(f'Risk: {_c["high"]} high-risk  ·  {_c["mid"]} mid  ·  {_c["low"]} low', h=6)
    pdf.ln(2)

    section("Eval")
    row("Assignment", payload["assignment"]["title"])
    row("Flight sheet", f'{payload["flight_sheet"]["name"]} v{payload["flight_sheet"]["version"]}')
    row("Agent / model", f'{sub.get("agent_name") or "—"} · {sub.get("model_name") or "—"} ({sub.get("provider") or "—"})')
    pdf.ln(1)

    ap = payload.get("agent_profile")
    if ap:
        section("Agent profile (the stack)")
        row("Profile", f'{ap.get("name") or "—"}  ·  tier {(ap.get("capability_tier") or "—").upper()}')
        hv = f' v{ap["harness_version"]}' if ap.get("harness_version") else ""
        row("Harness (body)", f'{ap.get("harness") or "—"}{hv}')
        row("Model (brain)", f'{ap.get("model") or "—"}  ({ap.get("model_provider") or "—"} · {ap.get("served_by") or "—"})')
        rt = "  ·  ".join(x for x in [ap.get("runtime_host"), ap.get("runtime_hardware"), ap.get("runtime_os")] if x)
        row("Runtime (ground)", rt or "—")
        pdf.ln(1)

    section("Referee findings")
    pdf.set_font("Courier", "", 9)
    _status_rank = {"flag": 0, "open": 1, "pass": 2, "review": 3, "skip": 4}
    findings = sorted(
        payload["findings"],
        key=lambda f: (_status_rank.get(f.get("status"), 5), _TIER_RANK.get(_tier(f.get("severity")), 1)),
    )
    for f in findings:
        mark = {"pass": "[PASS]", "flag": "[FLAG]", "open": "[OPEN]", "skip": "[skip]"}.get(f["status"], "[ ?? ]")
        tier = f' {_TIER_LABEL[_tier(f.get("severity"))]}' if f["status"] == "flag" else ""
        wrap(f'{mark}{tier} {f["label"]} ({f["category"]}) - {f.get("detail") or ""}')
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
