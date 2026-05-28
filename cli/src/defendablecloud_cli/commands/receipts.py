"""receipts — per-org rollup over the chain.

  defendable receipts recent [--schema X] [--limit N]
                                                List the N most recent receipts
                                                on your org's chain · optional
                                                exact-match schema filter

Mirrors `GET /receipts/recent`. Each row carries identity + share URL + a
schema-aware compact summary projected from the payload — same data the
Vault dashboard tiles use.
"""
from __future__ import annotations

import typer

from ..client import Client
from ..output import console, emit_json, emit_kv

app = typer.Typer(help="Per-org receipt rollups.")


SCHEMA_SHORTCUTS = {
    "eval": "defendablecloud.eval-receipt/v1",
    "cook": "defendablecloud.cook-receipt/v1",
    "incident": "defendablecloud.incident-receipt/v1",
    "download": "defendablecloud.dataset-download-receipt/v1",
    "pin": "defendablecloud.model-pin-receipt/v1",
}


@app.command("recent")
def recent(
    schema: str | None = typer.Option(
        None, "--schema", "-s",
        help=(
            "Exact-match schema filter, or shortcut: "
            "eval · cook · incident · download · pin"
        ),
    ),
    limit: int = typer.Option(10, "--limit", "-n", min=1, max=50),
    output_json: bool = typer.Option(False, "--json"),
):
    """List the N most recent receipts on your org chain."""
    full_schema = SCHEMA_SHORTCUTS.get(schema or "", schema)
    params: dict = {"limit": limit}
    if full_schema:
        params["schema"] = full_schema

    c = Client()
    r = c.get("/receipts/recent", params=params)
    rollups = r.get("rollups") or []

    if output_json:
        emit_json(r)
        return

    console.print()
    filter_str = f" · schema={full_schema}" if full_schema else ""
    console.print(
        f"[bold]Recent receipts[/bold]  [dim]({r.get('count', 0)} returned · limit={limit}{filter_str})[/dim]"
    )
    console.print()

    if not rollups:
        if full_schema:
            console.print(f"[dim]no receipts for schema: {full_schema}[/dim]")
        else:
            console.print("[dim]no receipts on chain yet · mint your first[/dim]")
        return

    for row in rollups:
        _print_rollup_row(row)


def _print_rollup_row(row: dict) -> None:
    s = row.get("summary") or {}
    lane = str(s.get("lane") or "—")
    headline, sub = _headline_for(lane, s, row)
    org_seq = row.get("org_seq")
    when = row.get("created_at") or "—"

    console.print(
        f"  [honey]{lane}[/honey]  [bold]{headline}[/bold]   [dim]org_seq {org_seq} · {when}[/dim]"
    )
    if sub:
        console.print(f"    [dim]{sub}[/dim]")
    console.print(f"    [dim]share:[/dim] {row.get('share_url') or '—'}")
    console.print()


def _headline_for(lane: str, s: dict, row: dict) -> tuple[str, str | None]:
    """Render two lines per row · headline + optional sub. Reads only summary
    fields surfaced by the backend; falls back to receipt_id for unknown."""
    if lane == "model-pin":
        name = s.get("model_name") or s.get("model_slug") or "model"
        base = s.get("base")
        params = s.get("params_b")
        sub_parts = []
        if base:
            sub_parts.append(str(base))
        if params is not None:
            sub_parts.append(f"{params}B")
        if s.get("declaration"):
            sub_parts.append(str(s["declaration"]))
        return name, " · ".join(sub_parts) or None

    if lane == "cook":
        title = s.get("run_title") or s.get("base_model") or "cook"
        before = s.get("eval_before")
        after = s.get("eval_after")
        lift = s.get("lift")
        sub_parts = []
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            sub_parts.append(f"{before * 100:.1f}% → {after * 100:.1f}%")
        if isinstance(lift, (int, float)):
            sub_parts.append(f"({lift:+.1%})")
        if s.get("pinned_model_slug"):
            sub_parts.append(f"pin · {s['pinned_model_slug']}")
        return title, " · ".join(sub_parts) or None

    if lane == "eval":
        title = s.get("run_title") or "run"
        sub_parts = []
        if s.get("outcome"):
            sub_parts.append(str(s["outcome"]))
        if s.get("severity"):
            sub_parts.append(str(s["severity"]))
        if s.get("score_100") is not None:
            sub_parts.append(f"{s['score_100']}/100")
        return title, " · ".join(sub_parts) or None

    if lane == "incident":
        title = s.get("title") or s.get("kind") or "incident"
        sub_parts = [str(x) for x in (s.get("severity"), s.get("status")) if x]
        return title, " · ".join(sub_parts) or None

    if lane == "dataset-download":
        title = s.get("package_name") or s.get("package_slug") or "dataset"
        sub_parts = []
        if s.get("vertical"):
            sub_parts.append(str(s["vertical"]))
        if "ready_at_grant" in s:
            sub_parts.append("ready" if s.get("ready_at_grant") else "preparing")
        return title, " · ".join(sub_parts) or None

    # Fallback for unknown lane.
    return row.get("receipt_id") or "—", row.get("payload_schema") or None
