from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException
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


async def require_admin(current: Principal = Depends(get_current_user)) -> Principal:
    """Gate behind the configured ADMIN_EMAILS list. Used by the in-app Admin
    Approval UI (/admin/*). The X-Internal-Key path on /membership/approve
    remains for scripts and CLI; this dep is for member-auth-with-admin-email
    only.

    Fails 403 if no admin emails are configured (fail-closed) OR if the
    current user's email isn't in the list.
    """
    if not settings().is_admin_email(current.email):
        raise HTTPException(
            status_code=403,
            detail="admin access required — contact build@defendableos.com",
        )
    return current


async def require_internal(
    x_internal_key: Optional[str] = Header(default=None, alias="X-Internal-Key"),
) -> None:
    """Shared-key auth for the rails-side dataset stager (INTERNAL_API_KEY).

    Fail-closed: if INTERNAL_API_KEY isn't configured in the API process, the
    /internal/* surface refuses all calls (503). This prevents a misconfigured
    dev/staging env from silently accepting unauthenticated calls.
    """
    expected = settings().internal_api_key
    if not expected:
        raise HTTPException(status_code=503, detail="internal surface not configured")
    if not x_internal_key or x_internal_key.strip() != expected:
        raise HTTPException(status_code=401, detail="invalid internal key")


async def require_member(current: Principal = Depends(get_current_user)) -> Principal:
    """Gate behind active membership. Used by dataset + cook routes (PR-2+).

    Datasets are free with membership; non-members get the doctrine reason in
    the 403 body so the UX can route them to the apply flow without ambiguity.
    """
    from app.db import session_scope
    from app.models import Organization

    async with session_scope() as db:
        org = await db.get(Organization, current.org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="org not found")
        if org.membership_status != "active":
            raise HTTPException(
                status_code=403,
                detail=(
                    f"membership required (current status: {org.membership_status}). "
                    "Apply via POST /membership/apply or the dashboard at /org."
                ),
            )
        return current
