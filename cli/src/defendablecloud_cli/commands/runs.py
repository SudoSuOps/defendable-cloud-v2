"""Runs — the Defendable Run primitive.

Inputs → Evidence → Execution → Checks → Verdict → Approval → Receipt.

Every CLI command in this module maps to an API endpoint we've already
locked with response_model= and asserted in test_openapi.py.
"""
from __future__ import annotations

import typer

from ..client import Client
from ..errors import CLIError
from ..output import (
    console,
    emit_json,
    emit_kv,
    emit_severity,
    emit_status,
    emit_table,
)

app = typer.Typer(help="Defendable Runs — the core primitive.")


@app.command("ls")
def ls(
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project id."),
    limit: int = typer.Option(50, "--limit", "-n", help="Max rows."),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """List recent Runs in your org."""
    c = Client()
    params = {"limit": limit}
    if project:
        params["project_id"] = project
    r = c.get("/runs", params=params)
    runs = r.get("runs") or []
    if output_json:
        emit_json(runs)
        return
    emit_table(
        [
            {
                "id": run.get("id"),
                "lane": run.get("lane"),
                "title": run.get("title"),
                "status": run.get("status"),
                "verdict": run.get("verdict") or "—",
                "created_at": run.get("created_at"),
            }
            for run in runs
        ],
        ["id", "lane", "title", "status", "verdict", "created_at"],
        title=f"runs ({len(runs)})",
    )


@app.command("new")
def new(
    project: str = typer.Option(..., "--project", "-p", help="Project id (use `defendable projects ls`)."),
    flight_sheet: str = typer.Option(..., "--flight-sheet", "-f", help="Flight Sheet slug or id."),
    agent_profile: str | None = typer.Option(None, "--agent-profile", help="Optional AgentProfile id."),
    title: str | None = typer.Option(None, "--title", help="Override the Flight Sheet's default title."),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """Create a new Run from a Flight Sheet."""
    c = Client()
    # Resolve slug → id if needed.
    fs_id = flight_sheet
    if "_" in flight_sheet or "-" in flight_sheet:
        sheets = (c.get("/flight-sheets") or {}).get("flight_sheets") or []
        match = next((s for s in sheets if s.get("slug") == flight_sheet or s.get("id") == flight_sheet), None)
        if match is None:
            raise CLIError(f"flight sheet not found: {flight_sheet}")
        fs_id = match["id"]
    body: dict = {"project_id": project, "flight_sheet_id": fs_id}
    if agent_profile:
        body["agent_profile_id"] = agent_profile
    if title:
        body["title"] = title
    r = c.post("/runs", json=body)
    if output_json:
        emit_json(r)
        return
    emit_kv(
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "lane": r.get("lane"),
            "status": r.get("status"),
        },
        title="run created",
    )


@app.command("show")
def show(
    run_id: str = typer.Argument(..., help="Run id."),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """Show full Run detail — assignment, evidence, submission, checks, verdict, approval, receipt."""
    c = Client()
    r = c.get(f"/runs/{run_id}")
    if output_json:
        emit_json(r)
        return
    emit_kv(
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "lane": r.get("lane"),
            "status": r.get("status"),
            "flight_sheet": (r.get("flight_sheet") or {}).get("name") or "—",
        },
        title=f"run · {run_id}",
    )

    sub = r.get("submission")
    if sub:
        emit_kv(
            {"agent": sub.get("agent_name") or "—", "model": sub.get("model_name") or "—", "sha256": sub.get("sha256")},
            title="submission",
        )

    checks = r.get("checks") or []
    if checks:
        emit_table(
            [
                {
                    "key": ch.get("check_key"),
                    "label": ch.get("label"),
                    "category": ch.get("category"),
                    "status": emit_status(ch.get("status")),
                    "severity": emit_severity(ch.get("severity")),
                }
                for ch in checks
            ],
            ["key", "label", "category", "status", "severity"],
            title=f"checks ({len(checks)})",
        )

    v = r.get("verdict")
    if v:
        emit_kv(
            {
                "outcome": v.get("outcome"),
                "severity": v.get("severity"),
                "score_100": v.get("score_100"),
                "client_ready": v.get("client_ready"),
                "recommended_action": v.get("recommended_action"),
            },
            title="verdict",
        )

    receipt = r.get("receipt")
    if receipt:
        emit_kv(
            {
                "receipt_id": receipt.get("receipt_id"),
                "org_seq": receipt.get("org_seq"),
                "receipt_sha256": receipt.get("receipt_sha256"),
                "share_url": receipt.get("share_url"),
            },
            title="receipt",
        )


# ── projections — one per doctrine concept (matches the GET endpoints) ───────


@app.command("submission")
def submission(
    run_id: str = typer.Argument(...),
    output_json: bool = typer.Option(False, "--json"),
):
    """Show the latest agent submission for a Run."""
    c = Client()
    s = c.get(f"/runs/{run_id}/submission")
    if output_json:
        emit_json(s)
        return
    emit_kv(
        {
            "agent_name": s.get("agent_name"),
            "model_name": s.get("model_name"),
            "provider": s.get("provider"),
            "sha256": s.get("sha256"),
            "submitted_at": s.get("submitted_at"),
        },
        title=f"submission · {run_id}",
    )
    out = s.get("output_text") or ""
    if out:
        console.print("[dim]output_text:[/dim]")
        console.print(out)


@app.command("checks")
def checks(
    run_id: str = typer.Argument(...),
    output_json: bool = typer.Option(False, "--json"),
):
    """List all applied rules for a Run — each passes or raises a flag."""
    c = Client()
    r = c.get(f"/runs/{run_id}/checks")
    items = r.get("checks") or []
    if output_json:
        emit_json(items)
        return
    emit_table(
        [
            {
                "key": ch.get("check_key"),
                "label": ch.get("label"),
                "category": ch.get("category"),
                "status": emit_status(ch.get("status")),
                "severity": emit_severity(ch.get("severity")),
                "source": ch.get("source") or "—",
            }
            for ch in items
        ],
        ["key", "label", "category", "status", "severity", "source"],
        title=f"checks ({len(items)})",
    )


@app.command("flags")
def flags(
    run_id: str = typer.Argument(...),
    output_json: bool = typer.Option(False, "--json"),
):
    """The thrown flags — Findings, sorted by tier."""
    c = Client()
    r = c.get(f"/runs/{run_id}/flags")
    items = r.get("flags") or []
    if output_json:
        emit_json(items)
        return
    if not items:
        console.print("[green]no flags — clean run[/green]")
        return
    emit_table(
        [
            {
                "key": f.get("check_key"),
                "label": f.get("label"),
                "category": f.get("category"),
                "severity": emit_severity(f.get("severity")),
                "detail": (f.get("detail") or "")[:60],
            }
            for f in items
        ],
        ["key", "label", "category", "severity", "detail"],
        title=f"findings ({len(items)})",
    )


@app.command("verdict")
def verdict(
    run_id: str = typer.Argument(...),
    output_json: bool = typer.Option(False, "--json"),
):
    """Show the latest verdict — score = % of declared rules satisfied, weighted by tier."""
    c = Client()
    v = c.get(f"/runs/{run_id}/verdict")
    if output_json:
        emit_json(v)
        return
    emit_kv(
        {
            "outcome": v.get("outcome"),
            "severity": v.get("severity"),
            "score_100": v.get("score_100"),
            "checks_passed": v.get("checks_passed"),
            "checks_failed": v.get("checks_failed"),
            "client_ready": v.get("client_ready"),
            "recommended_action": v.get("recommended_action"),
            "summary": v.get("summary"),
        },
        title="verdict",
    )
