"""Receipt — mint the hash-chained artifact. The killer button.

After a human has approved, this mints the receipt: per-org hash chain,
JSON + PDF + public share URL. Verifiable client-side via SHA-256.
"""
from __future__ import annotations

import typer

from ..client import Client
from ..output import emit_json, emit_kv

app = typer.Typer(help="Mint the eval receipt.")


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
