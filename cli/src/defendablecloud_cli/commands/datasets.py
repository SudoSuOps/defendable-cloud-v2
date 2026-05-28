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


@app.command("download")
def download(
    slug: str = typer.Argument(..., help="Package slug — e.g. `cre_cre_honey`"),
    expires_in_hours: int = typer.Option(
        24, "--ttl", "-t", min=1, max=168,
        help="Signed-URL TTL in hours (1-168). Receipt itself never expires.",
    ),
    output_json: bool = typer.Option(False, "--json"),
):
    """Request a download grant for a package. Mints a receipt on the per-org
    chain and returns a fresh download URL.

    The receipt is books-and-records — share_url is the public proof page.
    The download_url indirects through /share/{token}/download which 302s to
    a fresh Tigris signed URL each time. If `ready=False`, the file is still
    staging in our download bucket; re-request anytime via the share URL.
    """
    c = Client()
    grant = c.post(
        f"/datasets/catalog/{slug}/download",
        json={"expires_in_hours": expires_in_hours},
    )
    if output_json:
        emit_json(grant)
        return

    pkg = grant.get("package") or {}
    console.print()
    console.print(
        f"[bold honey]✓ download grant minted[/bold honey]  "
        f"[dim]{grant.get('receipt_id')} · org_seq {grant.get('org_seq')}[/dim]"
    )
    ready = grant.get("ready")
    if ready:
        console.print(f"  [green]ready[/green] · valid until {grant.get('expires_at')}")
    else:
        console.print(
            f"  [yellow]preparing[/yellow] · re-request via the share URL when staged"
        )
    console.print()

    emit_kv(
        {
            "package": f"{pkg.get('name')} ({pkg.get('slug')})",
            "vertical": pkg.get("vertical"),
            "tier": pkg.get("tier"),
            "pairs": f"{pkg.get('pairs', 0):,}",
            "deed_anchored": pkg.get("deed_anchored"),
            "share_url": grant.get("share_url"),
            "download_url": grant.get("download_url"),
            "expires_at": grant.get("expires_at"),
            "ready": ready,
            "receipt_sha256": grant.get("receipt_sha256"),
        },
        title="grant",
    )
