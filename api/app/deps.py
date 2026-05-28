from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import Header, HTTPException
from sqlalchemy import select

from app.config import settings
from app.security import decode_jwt, hash_token


@dataclass
class Principal:
    id: str
    org_id: str
    email: str


# API keys are prefixed `dc_` so they're easy to spot in logs and pastes,
# and so the bearer middleware can route them to the API-key path without
# trying to decode them as JWT first.
API_KEY_PREFIX = "dc_"


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")

    # API key path — `dc_*` is the wire signal.
    if token.startswith(API_KEY_PREFIX):
        return await _principal_from_api_key(token)

    # JWT path — magic-link sign-in token (eyJ...).
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


async def _principal_from_api_key(token: str) -> Principal:
    """Look up an `ApiKey` by its 12-char prefix and verify the hash.

    Touches `last_used_at` on success. Imports are local to avoid a circular
    `deps -> models -> db -> deps` cycle at startup.
    """
    from app.db import session_scope
    from app.models import ApiKey, User

    prefix = token[:12]
    token_hash = hash_token(token)

    async with session_scope() as db:
        ak = (
            await db.execute(
                select(ApiKey).where(
                    ApiKey.key_prefix == prefix,
                    ApiKey.key_hash == token_hash,
                    ApiKey.revoked_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if ak is None:
            raise HTTPException(status_code=401, detail="invalid or revoked API key")
        ak.last_used_at = datetime.now(timezone.utc)

        email = "api-key"
        if ak.created_by:
            owner = await db.get(User, ak.created_by)
            if owner:
                email = owner.email
        # Principal.id encodes the api key for downstream checks (e.g. routes
        # that need to refuse re-issue of more keys via an existing API key).
        return Principal(id=f"apikey:{ak.id}", org_id=ak.org_id, email=email)


async def require_runner(authorization: Optional[str] = Header(default=None)) -> None:
    """Bearer auth for the GPU rig's cook runner (shared RUNNER_TOKEN)."""
    expected = settings().runner_token
    if not expected:
        raise HTTPException(status_code=503, detail="runner not configured")
    if not authorization or authorization.removeprefix("Bearer ").strip() != expected:
        raise HTTPException(status_code=401, detail="invalid runner token")
