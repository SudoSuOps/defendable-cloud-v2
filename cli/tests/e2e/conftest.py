"""E2E test fixtures.

Token acquisition order (first non-empty wins):
  1. DEFENDABLE_E2E_TOKEN env var — preferred for CI
  2. ~/.defendable/credentials.json on the host — local dev convenience
  3. neither → the entire e2e module is SKIPPED

Test isolation:
  Each test session writes credentials into a temp directory (DEFENDABLE_HOME
  override) so we never modify the developer's real ~/.defendable/credentials.json.
  Each subprocess call inherits this isolated env.

API target:
  DEFENDABLE_E2E_API env (default https://api.defendablecloud.com).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


def _acquire_token() -> tuple[str | None, str]:
    """Return (token, source) where source is 'env' | 'host_creds' | 'none'."""
    env_tok = os.environ.get("DEFENDABLE_E2E_TOKEN", "").strip()
    if env_tok:
        return env_tok, "env"

    host_creds = Path.home() / ".defendable" / "credentials.json"
    if host_creds.exists():
        try:
            data = json.loads(host_creds.read_text() or "{}")
            tok = (data.get("default") or {}).get("jwt")
            if tok:
                return tok, "host_creds"
        except (json.JSONDecodeError, OSError):
            pass

    return None, "none"


TOKEN, TOKEN_SOURCE = _acquire_token()

pytestmark = pytest.mark.skipif(
    TOKEN is None,
    reason=(
        "no DefendableCloud token. Set DEFENDABLE_E2E_TOKEN or sign in via "
        "`defendable auth login` + `defendable auth verify` first."
    ),
)


@pytest.fixture(scope="session")
def e2e_env(tmp_path_factory) -> dict[str, str]:
    """Isolated CLI env — separate DEFENDABLE_HOME so we don't touch ~/.defendable."""
    if TOKEN is None:
        pytest.skip("no token")

    home = tmp_path_factory.mktemp("defendable_e2e_home")
    api_base = os.environ.get("DEFENDABLE_E2E_API", "https://api.defendablecloud.com").rstrip("/")

    creds = {
        "default": {
            "api_base_url": api_base,
            "jwt": TOKEN,
            "user_email": "e2e@test.invalid",
            "signed_in_at": "1970-01-01T00:00:00Z",
        }
    }
    (home / "credentials.json").write_text(json.dumps(creds, indent=2))
    (home / "credentials.json").chmod(0o600)

    env = os.environ.copy()
    env["DEFENDABLE_HOME"] = str(home)
    env["DEFENDABLE_API"] = api_base
    # Make sure the subprocess doesn't accidentally inherit a different token.
    env.pop("DEFENDABLE_TOKEN", None)
    return env


def cli(env: dict[str, str], *args: str, expect_json: bool = True):
    """Run `defendable <args> --json` as a subprocess.

    Always appends --json so we get machine-readable output. Returns the parsed
    JSON or None if stdout was empty. Raises AssertionError with stderr if exit != 0.
    """
    argv = ["defendable", *args]
    if expect_json:
        argv.append("--json")
    res = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
    if res.returncode != 0:
        raise AssertionError(
            f"`{' '.join(argv)}` failed (exit {res.returncode})\n"
            f"--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}"
        )
    if not expect_json or not res.stdout.strip():
        return None
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"`{' '.join(argv)}` did not return JSON:\n{res.stdout}\n({e})")
