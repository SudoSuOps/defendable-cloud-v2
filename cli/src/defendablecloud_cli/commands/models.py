"""models — the members-only model card library surface.

  defendable models catalog                    list the 4-card library
  defendable models show <slug>                 single card detail
  defendable models pin <slug> [--note T] [--ref T]
                                                mint a model-pin receipt on
                                                the per-org chain

In-house only. Compute is the meter; this command is reference + pin.
"""
from __future__ import annotations

import typer

from ..client import Client
from ..output import console, emit_json, emit_kv, emit_table

app = typer.Typer(help="Members-only model card library · in-house cooks · pin to chain.")


@app.command("catalog")
def catalog(
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """List the in-house model card library."""
    c = Client()
    cv = c.get("/models/catalog")
    cards = cv.get("models") or []
    if output_json:
        emit_json(cv)
        return

    score = cv.get("scorecard") or {}
    console.print()
    console.print(
        f"[bold]Model card library[/bold]  "
        f"[dim]{cv.get('version', 'v?')} · generated {cv.get('generated_at', '—')}[/dim]"
    )
    console.print(
        f"  [green]{score.get('total_models', '—')}[/green] models · "
        f"[green]{score.get('in_house_models', 0)}[/green] in-house · "
        f"[green]{score.get('active_models', 0)}[/green] active"
    )
    h = (cv.get("models_sha256") or "")[:16]
    if h:
        console.print(f"  [dim]models_sha256 · {h}…[/dim]")
    console.print()

    if not cards:
        console.print("[dim]no model cards[/dim]")
        return

    emit_table(
        [
            {
                "slug": m.get("slug"),
                "name": m.get("name"),
                "base": m.get("base"),
                "params_b": m.get("params_b"),
                "context": m.get("context_window"),
                "status": m.get("status"),
            }
            for m in cards
        ],
        ["slug", "name", "base", "params_b", "context", "status"],
        title=f"models ({len(cards)})",
    )


@app.command("show")
def show(
    slug: str = typer.Argument(..., help="Model slug — e.g. `atlas-qwen-27b`"),
    output_json: bool = typer.Option(False, "--json"),
):
    """Show one model card's detail."""
    c = Client()
    card = c.get(f"/models/catalog/{slug}")
    if output_json:
        emit_json(card)
        return
    emit_kv(
        {
            "slug": card.get("slug"),
            "name": card.get("name"),
            "family": card.get("family"),
            "base": card.get("base"),
            "base_license": card.get("base_license"),
            "params_b": card.get("params_b"),
            "context_window": card.get("context_window"),
            "purpose": card.get("purpose"),
            "trained_on": ", ".join(card.get("trained_on") or []),
            "eval_notes": card.get("eval_notes"),
            "compute_class": card.get("compute_class"),
            "status": card.get("status"),
            "card_sha256": card.get("card_sha256"),
        },
        title=f"model · {slug}",
    )


@app.command("pin")
def pin(
    slug: str = typer.Argument(..., help="Model slug to pin · e.g. `atlas-qwen-27b`"),
    note: str | None = typer.Option(
        None, "--note", "-n",
        help="Free-text declaration · what is this model being pinned for?",
    ),
    client_ref: str | None = typer.Option(
        None, "--ref", "-r",
        help="Opaque member-side identifier (deal/agent/project tag).",
    ),
    output_json: bool = typer.Option(False, "--json"),
):
    """Pin a model card on your org's hash chain.

    Mints a `model-pin-receipt/v1` sealing the model identity + the card's
    content-hash at this exact instant. Shareable via the receipt's share URL;
    use for client-facing 'we used model X' provenance.
    """
    c = Client()
    body: dict = {}
    if note:
        body["declaration"] = note
    if client_ref:
        body["client_ref"] = client_ref
    res = c.post(f"/models/catalog/{slug}/pin", json=body or {})
    if output_json:
        emit_json(res)
        return

    m = res.get("model") or {}
    console.print()
    console.print(
        f"[bold honey]✓ pinned[/bold honey]  "
        f"[dim]{res.get('receipt_id')} · org_seq {res.get('org_seq')}[/dim]"
    )
    console.print()
    emit_kv(
        {
            "model": f"{m.get('name')} ({m.get('slug')})",
            "base": m.get("base"),
            "params_b": m.get("params_b"),
            "card_sha256": m.get("card_sha256"),
            "declaration": res.get("declaration") or "—",
            "client_ref": res.get("client_ref") or "—",
            "pinned_at": res.get("pinned_at"),
            "share_url": res.get("share_url"),
            "receipt_sha256": res.get("receipt_sha256"),
        },
        title="pin receipt",
    )
