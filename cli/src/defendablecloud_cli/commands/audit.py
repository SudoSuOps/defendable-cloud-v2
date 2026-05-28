"""Audit — run the rulebook against the agent submission.

The referee is a rulebook, not a judge. Each rule passes or raises a flag —
deterministic, no opinion grade. After the audit, any `open` checklist rules
must be applied (satisfied / flag) before the verdict can be finalized.
"""
from __future__ import annotations

import typer

from ..client import Client
from ..errors import CLIError
from ..output import console, emit_json, emit_kv, emit_severity, emit_status, emit_table

app = typer.Typer(help="Run the rulebook engine + finalize the verdict.")


@app.command("run")
def run(
    run_id: str = typer.Argument(...),
    output_json: bool = typer.Option(False, "--json"),
):
    """Apply the Flight Sheet's rulebook to the latest submission."""
    c = Client()
    r = c.post(f"/runs/{run_id}/audit")
    if output_json:
        emit_json(r)
        return

    deterministic = r.get("deterministic")
    needs_grading = r.get("needs_grading")
    checks = r.get("checks") or []
    v = r.get("verdict")

    console.print(
        f"[dim]ruleset audit · {'deterministic' if deterministic else 'heuristic'} · "
        f"{len(checks)} check(s) applied[/dim]"
    )
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
        title="checks",
    )

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
    if needs_grading:
        console.print(
            "\n[yellow]some rules are checklist-only and need a human to apply them.[/yellow]\n"
            "  use [bold]defendable audit grade <run-id> <check-id> [pass|flag][/bold]\n"
            "  then [bold]defendable audit finalize <run-id>[/bold]"
        )


@app.command("grade")
def grade(
    run_id: str = typer.Argument(...),
    check_id: str = typer.Argument(..., help="The check id from `defendable runs checks <run-id> --json`."),
    status: str = typer.Argument(..., help="'pass' (satisfied) or 'flag' (raise a flag)."),
    detail: str | None = typer.Option(None, "--detail", help="Optional detail string (e.g. why you flagged)."),
    output_json: bool = typer.Option(False, "--json"),
):
    """Apply a checklist rule — operator says satisfied (pass) or raises a flag.

    This is a binary rule, not a quality grade. The flag's severity is the
    rule's declared severity from the Flight Sheet, not something the operator
    chooses here.
    """
    if status not in ("pass", "flag"):
        raise CLIError("status must be 'pass' (satisfied) or 'flag'")
    body = {"status": status}
    if detail:
        body["detail"] = detail
    c = Client()
    r = c.patch(f"/runs/{run_id}/checks/{check_id}", json=body)
    if output_json:
        emit_json(r)
        return
    emit_kv(
        {"check_key": r.get("check_key"), "status": emit_status(r.get("status")), "severity": emit_severity(r.get("severity"))},
        title="check graded",
    )


@app.command("finalize")
def finalize(
    run_id: str = typer.Argument(...),
    output_json: bool = typer.Option(False, "--json"),
):
    """Finalize the flags → mint the verdict. Errors if any rule is still `open`."""
    c = Client()
    v = c.post(f"/runs/{run_id}/findings")
    if output_json:
        emit_json(v)
        return
    emit_kv(
        {
            "outcome": v.get("outcome"),
            "severity": v.get("severity"),
            "score_100": v.get("score_100"),
            "client_ready": v.get("client_ready"),
            "recommended_action": v.get("recommended_action"),
            "summary": v.get("summary"),
        },
        title="verdict finalized",
    )
