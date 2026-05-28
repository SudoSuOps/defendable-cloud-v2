"""Receipt — mint the hash-chained artifact and view one by share token.

After a human has approved, `generate` mints the receipt: per-org hash chain,
JSON + PDF + public share URL. Verifiable client-side via SHA-256.

`show` displays any receipt by its share token with schema-aware rendering
(eval / cook / model-pin / dataset-download / incident), including the
pinned_model block when a cook was minted against a previously-pinned model.
"""
from __future__ import annotations

import re

import typer

from ..client import Client
from ..errors import CLIError
from ..output import emit_json, emit_kv
from ._receipt_render import render_public_receipt

app = typer.Typer(help="Mint or view receipts on the hash chain.")


@app.command("generate")
def generate(
    run_id: str = typer.Argument(...),
    output_json: bool = typer.Option(False, "--json"),
):
    """Generate Receipt — mints the JSON + PDF on the per-org hash chain."""
    c = Client()
    r = c.post(f"/runs/{run_id}/receipt")
    if output_json:
        emit_json(r)
        return
    emit_kv(
        {
            "receipt_id": r.get("receipt_id"),
            "org_seq": r.get("org_seq"),
            "parent_hash": r.get("parent_hash"),
            "receipt_sha256": r.get("receipt_sha256"),
            "share_url": r.get("share_url"),
            "pdf_url": r.get("pdf_url"),
        },
        title="receipt minted",
    )


def _extract_token(raw: str) -> str:
    """Accept a raw token, a /r/<token> URL, or a /share/<token> URL."""
    s = raw.strip()
    m = re.search(r"/(?:r|share)/([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]+", s):
        return s
    raise CLIError(
        "not a valid share URL or token — expected /r/<token>, /share/<token>, or the token itself"
    )


@app.command("show")
def show(
    token_or_url: str = typer.Argument(
        ..., help="A share URL (https://.../r/<token>) or a raw token."
    ),
    output_json: bool = typer.Option(False, "--json"),
):
    """Show any receipt by its share token (no auth required).

    Picks the right renderer based on the receipt's `schema` field. For cook
    receipts, surfaces the `pinned_model` block when sealed in.
    """
    token = _extract_token(token_or_url)
    c = Client(token="")  # public endpoint
    r = c.get(f"/share/{token}", auth_required=False)
    if output_json:
        emit_json(r)
        return
    render_public_receipt(r)
