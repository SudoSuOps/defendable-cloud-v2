"""Evidence — what the agent was given. Hashed at upload, joins the receipt."""
from __future__ import annotations

from pathlib import Path

import typer

from ..client import Client
from ..errors import CLIError
from ..output import emit_json, emit_kv

app = typer.Typer(help="Attach evidence to a Run — every artifact gets hashed.")

_KINDS = ("note", "url", "observation", "tool_output", "model_output", "log", "file")


@app.command("add")
def add(
    run_id: str = typer.Argument(..., help="Run id."),
    kind: str = typer.Option("note", "--kind", "-k", help=f"One of: {', '.join(_KINDS)}."),
    label: str = typer.Option(..., "--label", "-l", help="What this evidence is."),
    content: str | None = typer.Option(None, "--content", help="Text content (note / url / observation)."),
    output_json: bool = typer.Option(False, "--json"),
):
    """Add a piece of text/url/note evidence. Use `evidence upload` for files."""
    if kind not in _KINDS or kind == "file":
        raise CLIError(f"kind must be one of: {', '.join(k for k in _KINDS if k != 'file')}")
    c = Client()
    body = {"kind": kind, "label": label}
    if content is not None:
        body["content"] = content
    r = c.post(f"/runs/{run_id}/evidence", json=body)
    if output_json:
        emit_json(r)
        return
    emit_kv(
        {"id": r.get("id"), "kind": r.get("kind"), "label": r.get("label"), "sha256": r.get("sha256")},
        title="evidence added",
    )


@app.command("upload")
def upload(
    run_id: str = typer.Argument(..., help="Run id."),
    file: Path = typer.Option(..., "--file", "-f", exists=True, dir_okay=False, readable=True),
    label: str | None = typer.Option(None, "--label", "-l", help="Override the filename as the label."),
    output_json: bool = typer.Option(False, "--json"),
):
    """Upload a file as evidence (25 MB max). The file is hashed and stored."""
    c = Client()
    r = c.upload(f"/runs/{run_id}/evidence/upload", file_path=file, label=label)
    if output_json:
        emit_json(r)
        return
    emit_kv(
        {
            "id": r.get("id"),
            "kind": r.get("kind"),
            "label": r.get("label"),
            "byte_size": r.get("byte_size"),
            "sha256": r.get("sha256"),
        },
        title="file uploaded",
    )
