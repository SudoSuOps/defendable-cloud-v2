"""Projects — the organizational scope under which Runs live."""
from __future__ import annotations

import typer

from ..client import Client
from ..output import emit_json, emit_kv, emit_table

app = typer.Typer(help="Projects — organizational scope for Runs.")


@app.command("ls")
def ls(output_json: bool = typer.Option(False, "--json", help="Machine-readable output.")):
    """List your org's projects."""
    c = Client()
    r = c.get("/projects")
    projects = r.get("projects") if isinstance(r, dict) else r
    if output_json:
        emit_json(projects)
        return
    emit_table(projects or [], ["id", "name", "created_at"], title="projects")


@app.command("create")
def create(
    name: str = typer.Option(..., "--name", "-n", help="Project name."),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """Create a new project."""
    c = Client()
    r = c.post("/projects", json={"name": name})
    if output_json:
        emit_json(r)
        return
    emit_kv({"id": r.get("id"), "name": r.get("name"), "created_at": r.get("created_at")}, title="created")
