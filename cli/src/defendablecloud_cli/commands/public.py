"""Public — verify a receipt by share token. No auth required.

Mirrors the `/verify` page on app.defendablecloud.com: anyone can paste a
share URL or token and confirm the receipt's hash matches the per-org chain.
"""
from __future__ import annotations

import re

import typer

from ..client import Client
from ..errors import CLIError
from ..output import emit_json
from ._receipt_render import render_public_receipt

app = typer.Typer(help="Public receipt verification (no auth).")


def _extract_token(raw: str) -> str:
    s = raw.strip()
    m = re.search(r"/(?:r|share)/([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]+", s):
        return s
    raise CLIError(
        "not a valid share URL or token — expected /r/<token>, /share/<token>, or the token itself"
    )


@app.command()
def verify(
    token_or_url: str = typer.Argument(..., help="A share URL (https://.../r/<token>) or a raw token."),
    output_json: bool = typer.Option(False, "--json"),
):
    """Fetch a public receipt + confirm the server-side hash recompute matches.

    Works without auth — anyone holding a share URL can verify. Schema-aware
    rendering covers eval / cook / model-pin / dataset-download / incident;
    cook receipts surface the pinned_model block when one was sealed in.
    """
    token = _extract_token(token_or_url)
    c = Client(token="")  # public endpoint
    r = c.get(f"/share/{token}", auth_required=False)
    if output_json:
        emit_json(r)
        return
    render_public_receipt(r)
