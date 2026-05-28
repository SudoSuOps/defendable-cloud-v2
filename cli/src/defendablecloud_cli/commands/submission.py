"""Submission — paste the agent's structured output for a Run."""
from __future__ import annotations

import sys
from pathlib import Path

import typer

from ..client import Client
from ..errors import CLIError
from ..output import emit_json, emit_kv

app = typer.Typer(help="Submit the agent's output for a Run.")


@app.command("add")
def add(
    run_id: str = typer.Argument(...),
    output_file: Path | None = typer.Option(
        None, "--output-file", "-o", exists=True, dir_okay=False, readable=True, help="Read output_text from this file."
    ),
    output_text: str | None = typer.Option(
        None, "--output-text", help="Inline output_text. Use - to read from stdin."
    ),
    agent: str | None = typer.Option(None, "--agent", help="Agent name (e.g. claude-code, kimi-k2)."),
    model: str | None = typer.Option(None, "--model", help="Model name (e.g. hermes3:8b)."),
    provider: str | None = typer.Option(None, "--provider", help="Provider (e.g. ollama, anthropic)."),
    output_json: bool = typer.Option(False, "--json"),
):
    """Submit the agent's structured output for a Run. Pipe from stdin, file, or inline."""
    text: str | None = None
    if output_file is not None:
        text = output_file.read_text()
    elif output_text == "-":
        text = sys.stdin.read()
    elif output_text is not None:
        text = output_text
    if not text or not text.strip():
        raise CLIError("no output_text — pass --output-file, --output-text, or pipe via '-'")

    body = {"output_text": text}
    if agent:
        body["agent_name"] = agent
    if model:
        body["model_name"] = model
    if provider:
        body["provider"] = provider

    c = Client()
    r = c.post(f"/runs/{run_id}/submission", json=body)
    if output_json:
        emit_json(r)
        return
    emit_kv(
        {"id": r.get("id"), "sha256": r.get("sha256"), "submitted_at": r.get("submitted_at")},
        title="submission saved",
    )
