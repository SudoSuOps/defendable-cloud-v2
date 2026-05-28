"""Approval — the human gate. Receipts only mint on `approved`."""
from __future__ import annotations

import typer

from ..client import Client
from ..errors import CLIError
from ..output import emit_json, emit_kv

app = typer.Typer(help="Approve / reject / escalate a Run.")


_DECISIONS = ("approved", "rejected", "escalated")


@app.command("set")
def set_decision(
    run_id: str = typer.Argument(...),
    decision: str = typer.Option("approved", "--decision", "-d", help=f"One of: {', '.join(_DECISIONS)}."),
    note: str | None = typer.Option(None, "--note", "-n", help="Optional note."),
    output_json: bool = typer.Option(False, "--json"),
):
    """Set approval on a Run. Receipts only mint on decision='approved'."""
    if decision not in _DECISIONS:
        raise CLIError(f"decision must be one of: {', '.join(_DECISIONS)}")
    body = {"decision": decision}
    if note:
        body["note"] = note
    c = Client()
    r = c.post(f"/runs/{run_id}/approve", json=body)
    if output_json:
        emit_json(r)
        return
    emit_kv(
        {
            "decision": r.get("decision"),
            "approver_email": r.get("approver_email"),
            "note": r.get("note") or "—",
        },
        title=f"approval · {run_id}",
    )
