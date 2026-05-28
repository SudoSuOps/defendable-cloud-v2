"""Local credential storage at ~/.defendable/credentials.json.

Single-profile in v1 — the "default" profile. Future profiles let an operator
switch between prod and a staging / sandbox vault without re-authing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROFILE = "default"
DEFAULT_API_BASE = "https://api.defendablecloud.com"


def creds_path() -> Path:
    base = Path(os.environ.get("DEFENDABLE_HOME", str(Path.home() / ".defendable")))
    base.mkdir(parents=True, exist_ok=True)
    return base / "credentials.json"


def load_all() -> dict[str, Any]:
    p = creds_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text() or "{}")
    except json.JSONDecodeError:
        return {}


def load_profile(profile: str = PROFILE) -> dict[str, Any]:
    return load_all().get(profile) or {}


def save_profile(data: dict[str, Any], profile: str = PROFILE) -> None:
    all_data = load_all()
    all_data[profile] = data
    p = creds_path()
    p.write_text(json.dumps(all_data, indent=2, sort_keys=True))
    # Lock down — JWT inside.
    try:
        p.chmod(0o600)
    except OSError:
        pass


def clear_profile(profile: str = PROFILE) -> bool:
    all_data = load_all()
    if profile not in all_data:
        return False
    del all_data[profile]
    creds_path().write_text(json.dumps(all_data, indent=2, sort_keys=True))
    return True


def api_base_url(override: str | None = None) -> str:
    """Resolution order: explicit override → env DEFENDABLE_API → stored profile → default."""
    if override:
        return override.rstrip("/")
    env = os.environ.get("DEFENDABLE_API")
    if env:
        return env.rstrip("/")
    profile = load_profile()
    return (profile.get("api_base_url") or DEFAULT_API_BASE).rstrip("/")


def stored_token() -> str | None:
    """Resolution order: env DEFENDABLE_TOKEN → stored profile → None."""
    env = os.environ.get("DEFENDABLE_TOKEN")
    if env:
        return env
    return load_profile().get("jwt")
