"""Output formatting — table for lists, pretty key/value for single objects, JSON for scripts.

Every command supports `--json` to bypass the human format and emit machine-readable output.
"""
from __future__ import annotations

import json as _json
from typing import Any, Iterable

from rich.console import Console
from rich.table import Table

console = Console()


def emit_json(obj: Any) -> None:
    """Stdout JSON for scripting. Sorted keys + indent = stable diffs in CI."""
    print(_json.dumps(obj, indent=2, sort_keys=True, default=str))


def emit_table(rows: Iterable[dict[str, Any]], columns: list[str], *, title: str | None = None) -> None:
    table = Table(title=title, show_header=True, header_style="bold")
    for c in columns:
        table.add_column(c)
    n = 0
    for row in rows:
        table.add_row(*[str(row.get(c, "") if row.get(c) is not None else "—") for c in columns])
        n += 1
    if n == 0:
        console.print("[dim]— no rows —[/dim]")
        return
    console.print(table)


def emit_kv(obj: dict[str, Any], *, title: str | None = None) -> None:
    """Pretty single-object output. Two-column key/value, dim keys."""
    if title:
        console.print(f"[bold]{title}[/bold]")
    width = max((len(k) for k in obj.keys()), default=0)
    for k, v in obj.items():
        if isinstance(v, (dict, list)):
            v_str = _json.dumps(v, default=str)
            if len(v_str) > 80:
                v_str = v_str[:77] + "…"
        elif v is None:
            v_str = "[dim]—[/dim]"
        else:
            v_str = str(v)
        console.print(f"  [dim]{k.ljust(width)}[/dim]  {v_str}")


def emit_severity(sev: str | None) -> str:
    """Color-coded severity badge. Locked vocabulary: honey / jelly / propolis."""
    if not sev:
        return "[dim]—[/dim]"
    s = sev.lower()
    if s == "honey":
        return f"[bold green]{sev}[/bold green]"
    if s == "jelly":
        return f"[bold yellow]{sev}[/bold yellow]"
    if s == "propolis":
        return f"[bold red]{sev}[/bold red]"
    return sev


def emit_status(status: str | None) -> str:
    """Color-coded check status badge. Locked vocabulary: pass / flag / open / skip."""
    if not status:
        return "[dim]—[/dim]"
    s = status.lower()
    if s == "pass":
        return f"[green]{status}[/green]"
    if s == "flag":
        return f"[red]{status}[/red]"
    if s == "open":
        return f"[yellow]{status}[/yellow]"
    return f"[dim]{status}[/dim]"


def confirm(msg: str, *, default: bool = False) -> bool:
    """Y/n prompt for destructive actions. Default is no."""
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        ans = input(f"{msg} {suffix} ").strip().lower()
    except EOFError:
        return default
    if not ans:
        return default
    return ans in ("y", "yes")
