"""policy — public policy surfaces. No auth required.

The first policy we publish is the training-data policy — the explicit
doctrine lock that customer-uploaded evidence + submissions NEVER enter the
SwarmJelly training pool. The body is FROZEN in code with a stable SHA-256.
"""
from __future__ import annotations

import typer

from ..client import Client
from ..output import console, emit_json, emit_kv

app = typer.Typer(help="Public policy surfaces · no sign-in required.")


@app.command("training-data")
def training_data(
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """The frozen doctrine — what enters and never enters the training corpus.

    > We learn from how agents fail. We never learn from what your business is doing.
    """
    c = Client(token="")
    pol = c.get("/policy/training-data", auth_required=False)
    if output_json:
        emit_json(pol)
        return

    console.print()
    console.print(
        f"[bold honey]Training-data policy[/bold honey]  "
        f"[dim]({pol.get('version', 'v?')} · effective {pol.get('effective_at', '—')})[/dim]"
    )
    console.print()
    console.print(f"  [italic]{pol.get('statement', '')}[/italic]")
    console.print()

    we_learn = pol.get("we_learn_from") or []
    if we_learn:
        console.print("[bold]We learn from[/bold]")
        for item in we_learn:
            console.print(f"  [green]✓[/green] {item}")
        console.print()

    we_dont = pol.get("we_dont_learn_from") or []
    if we_dont:
        console.print("[bold]We never learn from[/bold]")
        for item in we_dont:
            console.print(f"  [red]✗[/red] {item}")
        console.print()

    enforce = pol.get("enforcement") or []
    if enforce:
        console.print("[bold]How we enforce it[/bold]")
        for i, item in enumerate(enforce, 1):
            console.print(f"  [dim]{i:02d}[/dim] {item}")
        console.print()

    emit_kv(
        {
            "version": pol.get("version"),
            "effective_at": pol.get("effective_at"),
            "last_updated": pol.get("last_updated"),
            "sha256": pol.get("sha256"),
        },
        title="Policy receipt",
    )
