"""Flight Sheets — the declared rulebooks the referee applies.

A Flight Sheet is what makes a Run defendable: it declares the assignment,
the audit_checks (each one a rule that passes or raises a flag), and the
pass/fail thresholds.
"""
from __future__ import annotations

import typer

from ..client import Client
from ..errors import CLIError
from ..output import emit_json, emit_kv, emit_table

app = typer.Typer(help="Flight Sheets — the declared rulebooks.")


@app.command("ls")
def ls(
    lane: str | None = typer.Option(None, "--lane", help="Filter: agent | dataset | compute | other"),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """List the active Flight Sheet library."""
    c = Client()
    r = c.get("/flight-sheets")
    sheets = r.get("flight_sheets") or []
    if lane:
        sheets = [s for s in sheets if s.get("lane") == lane]
    if output_json:
        emit_json(sheets)
        return
    emit_table(
        [
            {
                "slug": s.get("slug"),
                "name": s.get("name"),
                "lane": s.get("lane"),
                "version": s.get("version"),
                "rules": len(s.get("audit_checks") or []),
            }
            for s in sheets
        ],
        ["slug", "name", "lane", "version", "rules"],
        title=f"flight sheets ({len(sheets)})",
    )


@app.command("show")
def show(
    slug_or_id: str = typer.Argument(..., help="Slug (preferred) or full id of the Flight Sheet."),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """Show a single Flight Sheet — assignment text, expected outputs, every rule + tier."""
    c = Client()
    sheets = (c.get("/flight-sheets") or {}).get("flight_sheets") or []
    needle = slug_or_id.strip().lower()
    sheet = next((s for s in sheets if s.get("slug") == needle or s.get("id") == slug_or_id), None)
    if sheet is None:
        raise CLIError(f"flight sheet not found: {slug_or_id}")
    if output_json:
        emit_json(sheet)
        return
    emit_kv(
        {
            "slug": sheet.get("slug"),
            "name": sheet.get("name"),
            "version": sheet.get("version"),
            "lane": sheet.get("lane"),
            "summary": sheet.get("summary"),
            "pass_threshold": sheet.get("pass_threshold"),
            "fail_threshold": sheet.get("fail_threshold"),
            "expected_outputs": ", ".join(sheet.get("expected_outputs") or []),
        },
        title=f"flight sheet · {sheet.get('slug')}",
    )
    rules = sheet.get("audit_checks") or []
    emit_table(
        [
            {
                "key": r.get("key"),
                "label": r.get("label"),
                "category": r.get("category"),
                "kind": r.get("kind"),
                "severity": r.get("severity"),
            }
            for r in rules
        ],
        ["key", "label", "category", "kind", "severity"],
        title=f"rules ({len(rules)})",
    )
