"""`defendable` — the CLI entry point.

  defendable auth login --email you@org.com
  defendable auth verify <TOKEN-FROM-EMAIL>
  defendable runs ls
  defendable runs new --project <id> --flight-sheet cre_memo_dscr_ltv_v1
  defendable evidence add <run-id> --kind note --label "the deal" --content "…"
  defendable submission add <run-id> --output-file output.json
  defendable audit run <run-id>
  defendable approval set <run-id> --decision approved
  defendable receipt generate <run-id>
  defendable verify <share-url-or-token>

> The referee is a rulebook, not a judge. To the shed.
"""
from __future__ import annotations

import sys

import typer

from . import __version__
from .commands import (
    approval,
    audit,
    auth,
    datasets,
    evidence,
    flight_sheets,
    ledger,
    policy,
    projects,
    public,
    receipt,
    runs,
    submission,
)
from .errors import CLIError
from .output import console

app = typer.Typer(
    name="defendable",
    help=(
        "DefendableCloud CLI — drive the proof vault from your terminal.\n\n"
        "Every command exercises an API endpoint locked by Pydantic. "
        "The referee is a rulebook, not a judge. To the shed."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(auth.app, name="auth")
app.add_typer(projects.app, name="projects")
app.add_typer(flight_sheets.app, name="flight-sheets")
app.add_typer(runs.app, name="runs")
app.add_typer(evidence.app, name="evidence")
app.add_typer(submission.app, name="submission")
app.add_typer(audit.app, name="audit")
app.add_typer(approval.app, name="approval")
app.add_typer(receipt.app, name="receipt")
app.add_typer(ledger.app, name="ledger")
app.add_typer(datasets.app, name="datasets")
app.add_typer(policy.app, name="policy")
# Public verify is a top-level shortcut: `defendable verify <url-or-token>`
app.add_typer(public.app, name="verify")


def _version_callback(value: bool):
    if value:
        print(f"defendable {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback, is_eager=True, help="Print version and exit."
    ),
):
    """Drive the DefendableCloud proof vault from the command line."""


def main():
    try:
        app()
    except CLIError as e:
        console.print(f"[red]error:[/red] {e}")
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
