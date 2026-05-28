"""Ledger — walk the per-org hash chain."""
from __future__ import annotations

import typer

from ..client import Client
from ..output import console, emit_json, emit_table

app = typer.Typer(help="Per-org hash chain — list + verify.")


@app.command("ls")
def ls(output_json: bool = typer.Option(False, "--json")):
    """List the per-org chain in `org_seq` order (no payload, just coordinates)."""
    c = Client()
    r = c.get("/ledger")
    entries = r.get("entries") or []
    if output_json:
        emit_json(entries)
        return
    emit_table(
        [
            {
                "org_seq": e.get("org_seq"),
                "receipt_id": e.get("receipt_id"),
                "parent_hash": (e.get("parent_hash") or "")[:16] + "…",
                "receipt_sha256": (e.get("receipt_sha256") or "")[:16] + "…",
                "created_at": e.get("created_at"),
            }
            for e in entries
        ],
        ["org_seq", "receipt_id", "parent_hash", "receipt_sha256", "created_at"],
        title=f"ledger ({len(entries)})",
    )


@app.command("verify")
def verify(output_json: bool = typer.Option(False, "--json")):
    """Walk the chain and verify hash integrity + parent linkage."""
    c = Client()
    r = c.get("/ledger/verify")
    if output_json:
        emit_json(r)
        return
    if r.get("ok"):
        console.print(
            f"[green]✓ chain verified[/green] · "
            f"{r.get('receipts_checked')} receipt(s) · no errors"
        )
    else:
        console.print(
            f"[red]✗ chain has integrity errors[/red] · "
            f"{r.get('receipts_checked')} receipt(s) · {len(r.get('errors') or [])} error(s)"
        )
        for e in r.get("errors") or []:
            console.print(f"  org_seq={e.get('org_seq')} → {e.get('error')}")
