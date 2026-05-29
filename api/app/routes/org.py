"""/org — the client dashboard surface.

Five endpoints covering org info, API key CRUD, and usage stats. All
authenticated via the standard `get_current_user` dependency, which accepts
either a JWT bearer (magic-link sign-in) OR an API key bearer (`dc_*`).

The plan field is a placeholder until Phase 5 (Stripe) wires real billing.
Every endpoint is wrapped in a named Pydantic schema so the surface is
contract-locked from day one.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.config import settings
from app.db import session_scope
from app.deps import Principal, get_current_user, require_org_owner
from app.models import ApiKey as ApiKeyModel
from app.models import OrgInvite as OrgInviteModel
from app.models import Organization, Receipt, User
from app.schemas import (
    ApiKey as ApiKeyOut,
    ApiKeyCreated,
    ApiKeyIn,
    ApiKeyList,
    Org,
    OrgInvite,
    OrgInviteCreated,
    OrgInviteIn,
    OrgInviteList,
    OrgMember,
    OrgMemberList,
    OrgMemberRoleUpdate,
    UsageStats,
)
from app.security import hash_token
from app.util import iso, new_id

router = APIRouter(prefix="/org", tags=["org"])


@router.get("", response_model=Org)
async def get_org(current: Principal = Depends(get_current_user)):
    """Org info + light stats for the client dashboard."""
    async with session_scope() as db:
        org = await db.get(Organization, current.org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="org not found")

        member_count = (
            await db.execute(select(func.count(User.id)).where(User.org_id == org.id))
        ).scalar_one()
        receipt_count = (
            await db.execute(select(func.count(Receipt.id)).where(Receipt.org_id == org.id))
        ).scalar_one()

        return {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "member_count": member_count,
            "receipt_count": receipt_count,
            "plan": "free",  # placeholder until Phase 5 — Stripe lands
            "created_at": iso(org.created_at) if org.created_at else None,
        }


# ── API keys ─────────────────────────────────────────────────────────────────


@router.get("/api-keys", response_model=ApiKeyList)
async def list_api_keys(current: Principal = Depends(require_org_owner)):
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(ApiKeyModel)
                .where(ApiKeyModel.org_id == current.org_id)
                .order_by(ApiKeyModel.created_at.desc())
            )
        ).scalars().all()
        return {
            "api_keys": [
                {
                    "id": k.id,
                    "name": k.name,
                    "key_prefix": k.key_prefix,
                    "created_at": iso(k.created_at) if k.created_at else None,
                    "last_used_at": iso(k.last_used_at) if k.last_used_at else None,
                    "revoked": k.revoked_at is not None,
                }
                for k in rows
            ]
        }


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(body: ApiKeyIn, current: Principal = Depends(get_current_user)):
    """Mint a new API key. The plaintext `secret` is returned ONCE here and never again.

    Refuses to mint when the caller's principal is itself an API key — only a
    signed-in human (JWT) can issue keys. That's the trust boundary: API keys
    can do work, they can't issue more keys.
    """
    if current.id.startswith("apikey:"):
        raise HTTPException(status_code=403, detail="API keys cannot mint API keys — sign in to issue keys")
    await require_org_owner(current)

    # dc_ + 32 url-safe base64 chars = ~46 chars total. Prefix is the first 12.
    secret = "dc_" + secrets.token_urlsafe(32)
    prefix = secret[:12]

    async with session_scope() as db:
        ak = ApiKeyModel(
            id=new_id(),
            org_id=current.org_id,
            name=body.name.strip(),
            key_prefix=prefix,
            key_hash=hash_token(secret),
            created_by=current.id,
        )
        db.add(ak)
        await db.flush()
        return {
            "id": ak.id,
            "name": ak.name,
            "key_prefix": prefix,
            "secret": secret,
            "created_at": iso(ak.created_at),
        }


@router.delete("/api-keys/{key_id}", response_model=ApiKeyOut)
async def revoke_api_key(key_id: str, current: Principal = Depends(require_org_owner)):
    """Revoke (soft delete) an API key. Sets revoked_at; the row stays for audit."""
    async with session_scope() as db:
        ak = await db.get(ApiKeyModel, key_id)
        if ak is None or ak.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="api key not found")
        if ak.revoked_at is None:
            ak.revoked_at = datetime.now(timezone.utc)
            await db.flush()
        return {
            "id": ak.id,
            "name": ak.name,
            "key_prefix": ak.key_prefix,
            "created_at": iso(ak.created_at) if ak.created_at else None,
            "last_used_at": iso(ak.last_used_at) if ak.last_used_at else None,
            "revoked": True,
        }


# ── Members + invites ─────────────────────────────────────────────────────────


def _member_out(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "created_at": iso(u.created_at) if u.created_at else None,
    }


@router.get("/members", response_model=OrgMemberList)
async def list_members(current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(User).where(User.org_id == current.org_id).order_by(User.created_at.asc())
            )
        ).scalars().all()
        return {"members": [_member_out(u) for u in rows]}


@router.put("/members/{user_id}/role", response_model=OrgMember)
async def update_member_role(
    user_id: str,
    body: OrgMemberRoleUpdate,
    current: Principal = Depends(require_org_owner),
):
    async with session_scope() as db:
        target = await db.get(User, user_id)
        if target is None or target.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="member not found")
        if target.id == current.id and body.role != "owner":
            raise HTTPException(status_code=409, detail="owners cannot demote themselves")
        if target.role == "owner" and body.role != "owner":
            owners = (
                await db.execute(
                    select(func.count(User.id)).where(
                        User.org_id == current.org_id,
                        User.role == "owner",
                    )
                )
            ).scalar_one()
            if int(owners) <= 1:
                raise HTTPException(status_code=409, detail="organization must keep at least one owner")
        target.role = body.role
        await db.flush()
        return _member_out(target)


@router.post("/invites", response_model=OrgInviteCreated, status_code=201)
async def create_invite(body: OrgInviteIn, current: Principal = Depends(require_org_owner)):
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="enter a valid email")

    raw_token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    async with session_scope() as db:
        existing = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="email already has an account")
        invite = OrgInviteModel(
            id=new_id(),
            org_id=current.org_id,
            email=email,
            role=body.role,
            token_hash=hash_token(raw_token),
            invited_by=current.id,
            expires_at=expires,
        )
        db.add(invite)
        await db.flush()
        invite_url = f"{settings().app_base_url.rstrip('/')}/auth/callback?invite={raw_token}"
        return {
            "id": invite.id,
            "email": invite.email,
            "role": invite.role,
            "invite_url": invite_url,
            "expires_at": iso(invite.expires_at),
            "created_at": iso(invite.created_at),
        }


@router.get("/invites", response_model=OrgInviteList)
async def list_invites(current: Principal = Depends(require_org_owner)):
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(OrgInviteModel)
                .where(OrgInviteModel.org_id == current.org_id)
                .order_by(OrgInviteModel.created_at.desc())
            )
        ).scalars().all()
        return {
            "invites": [
                {
                    "id": i.id,
                    "email": i.email,
                    "role": i.role,
                    "expires_at": iso(i.expires_at),
                    "accepted_at": iso(i.accepted_at) if i.accepted_at else None,
                    "created_at": iso(i.created_at) if i.created_at else None,
                }
                for i in rows
            ]
        }


# ── Usage ────────────────────────────────────────────────────────────────────


@router.get("/usage", response_model=UsageStats)
async def get_usage(current: Principal = Depends(get_current_user)):
    """Org-level usage. Placeholder for metered billing in Phase 5."""
    from app.models import AgentProfile, Verdict, Run

    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    async with session_scope() as db:
        receipts_lifetime = (
            await db.execute(select(func.count(Receipt.id)).where(Receipt.org_id == current.org_id))
        ).scalar_one()
        receipts_this_month = (
            await db.execute(
                select(func.count(Receipt.id)).where(
                    Receipt.org_id == current.org_id,
                    Receipt.created_at >= month_start,
                )
            )
        ).scalar_one()

        # Earned lanes — count of (agent_profile, flight_sheet) pairs with ≥3 honey
        # and 0 propolis verdicts. Cheap aggregation over verdicts joined to runs.
        earned_lanes = (
            await db.execute(
                select(func.count())
                .select_from(
                    select(
                        Run.agent_profile_id, Run.flight_sheet_id,
                    )
                    .join(Verdict, Verdict.run_id == Run.id)
                    .where(
                        Run.org_id == current.org_id,
                        Run.agent_profile_id.is_not(None),
                        Run.flight_sheet_id.is_not(None),
                    )
                    .group_by(Run.agent_profile_id, Run.flight_sheet_id)
                    .having(func.sum(func.case((Verdict.severity == "honey", 1), else_=0)) >= 3)
                    .having(func.sum(func.case((Verdict.severity == "propolis", 1), else_=0)) == 0)
                    .subquery()
                )
            )
        ).scalar_one()

        return {
            "receipts_lifetime": receipts_lifetime,
            "receipts_this_month": receipts_this_month,
            "org_seq": receipts_lifetime,  # next chain position
            "earned_lanes": earned_lanes or 0,
        }
