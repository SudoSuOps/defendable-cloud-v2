"""Authentication — magic-link flow on the CLI.

Workflow:
  1. `defendable auth login --email you@org.com` triggers POST /auth/request.
     A magic link is emailed to that address.
  2. Open the email. Copy the `token=<TOKEN>` value out of the link URL.
  3. `defendable auth verify <TOKEN>` calls POST /auth/verify and saves the JWT
     to ~/.defendable/credentials.json.
  4. Every subsequent command sends `Authorization: Bearer <JWT>`.

v2 will polish this into a single `defendable auth login` that opens a browser
and captures the JWT via a local callback — but v1 is two commands and works
without any browser dance.
"""
from __future__ import annotations

import typer
from datetime import datetime, timezone

from ..client import Client
from ..credentials import (
    PROFILE,
    api_base_url,
    clear_profile,
    load_profile,
    save_profile,
)
from ..errors import CLIError
from ..output import console, emit_json, emit_kv

app = typer.Typer(help="Sign in / out of the DefendableCloud vault.")


@app.command("login")
def login(
    email: str = typer.Option(..., "--email", "-e", help="Your email — magic link gets sent here."),
    api_base: str | None = typer.Option(None, "--api", help="Override API base URL."),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """Request a magic-link sign-in email. Then run `defendable auth verify <TOKEN>`."""
    c = Client(base_url=api_base, token="")  # auth not required for /auth/request
    r = c.post("/auth/request", json={"email": email}, auth_required=False)
    if output_json:
        emit_json(r)
        return
    if r.get("sent"):
        console.print(
            f"[green]✓[/green] sign-in link sent to [bold]{email}[/bold]\n"
            "open the email, copy the [bold]token=…[/bold] value from the URL, then run:\n"
            "  [bold]defendable auth verify <TOKEN>[/bold]"
        )
    elif r.get("dev_link"):
        console.print(
            "[yellow]email not configured server-side — using dev link[/yellow]\n"
            f"  dev link: {r['dev_link']}\n"
            "copy the token= value and run [bold]defendable auth verify <TOKEN>[/bold]"
        )
    else:
        console.print("[yellow]link requested[/yellow]")


@app.command("verify")
def verify(
    token: str = typer.Argument(..., help="The token= value from the magic-link URL."),
    api_base: str | None = typer.Option(None, "--api", help="Override API base URL."),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
):
    """Trade a magic-link token for a JWT. Saves to ~/.defendable/credentials.json."""
    c = Client(base_url=api_base, token="")
    r = c.post("/auth/verify", json={"token": token}, auth_required=False)
    jwt = r.get("access_token")
    user = r.get("user") or {}
    if not jwt:
        raise CLIError("API returned no access_token — verification failed")

    save_profile(
        {
            "api_base_url": api_base_url(api_base),
            "jwt": jwt,
            "user_email": user.get("email"),
            "user_id": user.get("id"),
            "org_id": user.get("org_id"),
            "signed_in_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if output_json:
        emit_json({"profile": PROFILE, "user": user})
        return
    console.print(
        f"[green]✓ signed in as[/green] [bold]{user.get('email')}[/bold]\n"
        f"  org: {user.get('org_id', '—')}\n"
        f"  credentials saved to ~/.defendable/credentials.json"
    )


@app.command("status")
def status(output_json: bool = typer.Option(False, "--json", help="Machine-readable output.")):
    """Show the current signed-in user and API base."""
    prof = load_profile()
    if not prof.get("jwt"):
        if output_json:
            emit_json({"signed_in": False})
        else:
            console.print("[yellow]not signed in[/yellow] — run `defendable auth login --email you@org.com`")
        raise typer.Exit(code=2)

    # Confirm the token still works.
    try:
        c = Client()
        me = c.get("/auth/me")
    except CLIError as e:
        if output_json:
            emit_json({"signed_in": False, "error": str(e)})
            return
        raise

    if output_json:
        emit_json(me)
        return
    emit_kv(
        {
            "email": me.get("email"),
            "user_id": me.get("id"),
            "org_id": me.get("org_id"),
            "org_name": me.get("org_name"),
            "role": me.get("role"),
            "api": prof.get("api_base_url"),
        },
        title="signed in",
    )


@app.command("logout")
def logout(output_json: bool = typer.Option(False, "--json", help="Machine-readable output.")):
    """Forget the stored credentials. Does not revoke server-side; the JWT lives out its TTL."""
    cleared = clear_profile()
    if output_json:
        emit_json({"cleared": cleared})
        return
    if cleared:
        console.print("[green]✓ signed out[/green] — credentials removed locally")
    else:
        console.print("[dim]no credentials to clear[/dim]")
