from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException

from app.config import settings
from app.security import decode_jwt


@dataclass
class Principal:
    id: str
    org_id: str
    email: str


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_jwt(token)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    uid = payload.get("sub")
    org = payload.get("org")
    email = payload.get("email")
    if not uid or not org:
        raise HTTPException(status_code=401, detail="malformed token")
    return Principal(id=uid, org_id=org, email=email or "")


async def require_runner(authorization: Optional[str] = Header(default=None)) -> None:
    """Bearer auth for the GPU rig's cook runner (shared RUNNER_TOKEN)."""
    expected = settings().runner_token
    if not expected:
        raise HTTPException(status_code=503, detail="runner not configured")
    if not authorization or authorization.removeprefix("Bearer ").strip() != expected:
        raise HTTPException(status_code=401, detail="invalid runner token")
