"""datasets — the members-only library surface.

  defendable datasets catalog [--vertical <v>]   list the 99-package library
  defendable datasets show <slug>                 single package detail

Datasets are free with membership. Compute is the meter. Members can verify
the API mirror matches the books-and-records source by re-computing the
catalog SHA-256 over the canonical packages list.
"""
from __future__ import annotations

import typer

from ..client import Client
from ..output import console, emit_json, emit_kv, emit_table

app = typer.Typer(help="Members-only dataset library · free with membership.")


@app.command("catalog")
def catalog(
    vertical: str | None = typer.Option(
        None, "--vertical", "-v",
        help="Filter by vertical: cre · medical · grants · jelly · signal · capital-markets · bee-hive · legal · finance · aviation · openalex · failure",
    ),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """List the members-only dataset library catalog (99 packages, 12 verticals)."""
    c = Client()
    cv = c.get("/datasets/catalog")
    pkgs = cv.get("packages") or []
    if vertical:
        pkgs = [p for p in pkgs if p.get("vertical") == vertical]
    if output_json:
        emit_json({**cv, "packages": pkgs})
        return

    score = cv.get("scorecard") or {}
    console.print()
    console.print(
        f"[bold]Master catalog[/bold]  [dim]{cv.get('version', 'v?')} · "
        f"generated {cv.get('generated_at', '—')}[/dim]"
    )
    console.print(
        f"  [green]{score.get('total_packages', '—')}[/green] packages · "
        f"[green]{score.get('total_pairs', 0):,}[/green] training pairs · "
        f"[green]{score.get('deed_anchored', 0)}[/green] deed-anchored"
    )
    cat_hash = (cv.get("packages_sha256") or "")[:16]
    if cat_hash:
        console.print(f"  [dim]packages_sha256 · {cat_hash}…[/dim]")
    console.print()

    if not pkgs:
        console.print(f"[dim]no packages for filter: {vertical}[/dim]")
        return

    emit_table(
        [
            {
                "slug": p.get("slug"),
                "name": p.get("name"),
                "vertical": p.get("vertical"),
                "tier": p.get("tier"),
                "pairs": f"{p.get('pairs', 0):,}",
                "deed": "✓" if p.get("deed_anchored") else "—",
            }
            for p in pkgs
        ],
        ["slug", "name", "vertical", "tier", "pairs", "deed"],
        title=f"packages ({len(pkgs)})" + (f" · {vertical}" if vertical else ""),
    )


@app.command("show")
def show(
    slug: str = typer.Argument(..., help="Package slug — e.g. `cre_cre_honey`"),
    output_json: bool = typer.Option(False, "--json"),
):
    """Show one package's detail."""
    c = Client()
    pkg = c.get(f"/datasets/catalog/{slug}")
    if output_json:
        emit_json(pkg)
        return
    emit_kv(
        {
            "slug": pkg.get("slug"),
            "name": pkg.get("name"),
            "vertical": pkg.get("vertical"),
            "tier": pkg.get("tier"),
            "pkg_class": pkg.get("pkg_class"),
            "pairs": f"{pkg.get('pairs', 0):,}",
            "deed_anchored": pkg.get("deed_anchored"),
            "deed": pkg.get("deed"),
        },
        title=f"package · {slug}",
    )
