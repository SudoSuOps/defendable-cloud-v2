"""Schema-aware rendering for public receipt payloads.

Shared between `defendable verify <token>` and `defendable receipt show
<token>`. Receipts on the chain carry a `schema` field; this dispatcher
picks the appropriate section renderer and writes lift/identity/pin
blocks below the standard hash-verified header.

Conservative: each renderer reads only headline payload fields. The full
payload is always available via `--json`.
"""
from __future__ import annotations

from typing import Any

from ..output import console, emit_kv


SCHEMA_LABELS = {
    "defendablecloud.eval": "eval-receipt",
    "defendablecloud.cook": "cook-receipt",
    "defendablecloud.incident": "incident-receipt",
    "defendablecloud.dataset-download": "dataset-download-receipt",
    "defendablecloud.model-pin": "model-pin-receipt",
}


def render_public_receipt(r: dict[str, Any]) -> None:
    """Render the public receipt response from /share/{token}.

    Header:
      ✓ hash verified · schema · created_at
    Body:
      KV: receipt identity + integrity
      Schema-aware section: lift / pin / package / incident / etc.
    """
    payload = r.get("payload") or {}
    schema = str(payload.get("schema", ""))
    label = _label_for_schema(schema) or "receipt"

    badge = "[green]✓ hash verified[/green]" if r.get("verified") else "[red]✗ hash MISMATCH[/red]"
    console.print(f"{badge}  [dim]{label}[/dim]")

    emit_kv(
        {
            "receipt_id": r.get("receipt_id"),
            "org_seq": r.get("org_seq"),
            "parent_hash": r.get("parent_hash"),
            "receipt_sha256": r.get("receipt_sha256"),
            "created_at": r.get("created_at"),
            "verified": r.get("verified"),
        },
        title=f"receipt · {label}",
    )

    if schema.startswith("defendablecloud.eval"):
        _render_eval_section(payload)
    elif schema.startswith("defendablecloud.cook"):
        _render_cook_section(payload)
    elif schema.startswith("defendablecloud.incident"):
        _render_incident_section(payload)
    elif schema.startswith("defendablecloud.dataset-download"):
        _render_dataset_download_section(payload)
    elif schema.startswith("defendablecloud.model-pin"):
        _render_model_pin_section(payload)


def _label_for_schema(schema: str) -> str | None:
    for prefix, label in SCHEMA_LABELS.items():
        if schema.startswith(prefix):
            return label
    return None


def _pct(v: Any) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "—"


def _render_eval_section(p: dict[str, Any]) -> None:
    v = p.get("verdict") or {}
    run = p.get("run") or {}
    emit_kv(
        {
            "run": run.get("title") or "—",
            "outcome": v.get("outcome") or "—",
            "severity": v.get("severity") or "—",
            "score_100": v.get("score_100"),
            "summary": v.get("summary") or "",
        },
        title="verdict",
    )


def _render_cook_section(p: dict[str, Any]) -> None:
    c = p.get("cook") or {}
    run = p.get("run") or {}
    before = c.get("eval_before")
    after = c.get("eval_after")
    lift = c.get("lift")
    lift_str = (
        f"{lift:+.1%}" if isinstance(lift, (int, float)) else "—"
    )
    console.print()
    console.print(
        f"[bold]Eval[/bold]  [green]{_pct(before)}[/green] -> [green]{_pct(after)}[/green]   "
        f"({lift_str})"
    )
    emit_kv(
        {
            "run": run.get("title") or "—",
            "base_model": c.get("base_model") or "—",
            "dataset": c.get("dataset") or "—",
            "pairs": f'{(c.get("pairs") or 0):,}',
            "runner": c.get("runner") or "—",
            "compute_usd": c.get("compute_usd") if c.get("compute_usd") is not None else "—",
        },
        title="cook",
    )

    pin = p.get("pinned_model")
    if pin:
        emit_kv(
            {
                "slug": pin.get("slug") or "—",
                "name": pin.get("name") or "—",
                "base": pin.get("base") or "—",
                "params_b": pin.get("params_b") if pin.get("params_b") is not None else "—",
                "card_sha256": pin.get("card_sha256") or "—",
                "pinned_at": pin.get("pinned_at") or "—",
                "declaration": pin.get("declaration") or "—",
                "client_ref": pin.get("client_ref") or "—",
                "pin_receipt_id": pin.get("pin_receipt_id") or "—",
                "pin_receipt_sha256": pin.get("pin_receipt_sha256") or "—",
                "pin_share_url": pin.get("pin_share_url") or "—",
            },
            title="model declared via pin",
        )


def _render_incident_section(p: dict[str, Any]) -> None:
    emit_kv(
        {
            "kind": p.get("kind") or "—",
            "title": p.get("title") or "—",
            "severity": p.get("severity") or "—",
            "status": p.get("status") or "—",
        },
        title="incident",
    )


def _render_dataset_download_section(p: dict[str, Any]) -> None:
    pkg = p.get("package") or {}
    emit_kv(
        {
            "package": f'{pkg.get("name") or "—"} ({pkg.get("slug") or "—"})',
            "vertical": pkg.get("vertical") or "—",
            "tier": pkg.get("tier") or "—",
            "pairs": f'{(pkg.get("pairs") or 0):,}',
            "deed_anchored": pkg.get("deed_anchored"),
            "tigris_key": p.get("tigris_key") or "—",
            "ready_at_grant": p.get("ready_at_grant"),
            "expires_at": p.get("expires_at") or "—",
        },
        title="dataset download grant",
    )


def _render_model_pin_section(p: dict[str, Any]) -> None:
    m = p.get("model") or {}
    emit_kv(
        {
            "slug": m.get("slug") or "—",
            "name": m.get("name") or "—",
            "base": m.get("base") or "—",
            "params_b": m.get("params_b") if m.get("params_b") is not None else "—",
            "card_sha256": m.get("card_sha256") or "—",
            "pinned_at": p.get("pinned_at") or "—",
            "declaration": p.get("declaration") or "—",
            "client_ref": p.get("client_ref") or "—",
        },
        title="model pin",
    )
