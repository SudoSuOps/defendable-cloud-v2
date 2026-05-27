from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.config import settings
from app.db import session_scope
from app.deps import Principal, get_current_user
from app.email import send_magic_link
from app.models import MagicToken, Organization, User
from app.schemas import MagicRequestIn, MagicVerifyIn
from app.security import hash_token, issue_jwt, make_magic_token
from app.util import iso, new_id, slugify

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request")
async def magic_request(body: MagicRequestIn):
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="enter a valid email")

    s = settings()
    token = make_magic_token()
    expires = datetime.now(timezone.utc) + timedelta(minutes=s.magic_ttl_minutes)
    async with session_scope() as db:
        db.add(MagicToken(id=new_id(), email=email, token_hash=hash_token(token), expires_at=expires))

    link = f"{s.app_base_url.rstrip('/')}/auth/callback?token={token}"
    sent = await send_magic_link(email, link)
    out = {"ok": True, "sent": sent}
    if not sent:
        # Dev / email-not-configured: surface the link so login still works.
        out["dev_link"] = link
    return out


@router.post("/verify")
async def magic_verify(body: MagicVerifyIn):
    th = hash_token(body.token.strip())
    now = datetime.now(timezone.utc)
    async with session_scope() as db:
        mt = (
            await db.execute(select(MagicToken).where(MagicToken.token_hash == th))
        ).scalar_one_or_none()
        if mt is None or mt.used_at is not None or mt.expires_at < now:
            raise HTTPException(status_code=401, detail="invalid or expired link")
        mt.used_at = now
        email = mt.email

        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            org_id = new_id()
            domain = email.split("@")[-1]
            org = Organization(
                id=org_id,
                name=domain,
                slug=f"{slugify(domain)}-{org_id[:6]}",
            )
            db.add(org)
            user = User(id=new_id(), org_id=org_id, email=email, role="owner")
            db.add(user)

        token = issue_jwt(user.id, user.org_id, user.email)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user.id, "email": user.email, "org_id": user.org_id, "name": user.name},
        }


@router.get("/me")
async def me(current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        user = await db.get(User, current.id)
        if user is None:
            raise HTTPException(status_code=401, detail="user not found")
        org = await db.get(Organization, user.org_id)
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "org_id": user.org_id,
            "org_name": org.name if org else None,
            "created_at": iso(user.created_at),
        }
