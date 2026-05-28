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
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.db import session_scope
from app.deps import Principal, get_current_user
from app.models import ApiKey as ApiKeyModel
from app.models import Organization, Receipt, User
from app.schemas import (
    ApiKey as ApiKeyOut,
    ApiKeyCreated,
    ApiKeyIn,
    ApiKeyList,
    Org,
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
async def list_api_keys(current: Principal = Depends(get_current_user)):
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
async def revoke_api_key(key_id: str, current: Principal = Depends(get_current_user)):
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
