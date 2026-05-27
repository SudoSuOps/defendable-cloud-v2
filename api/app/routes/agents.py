from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.db import session_scope
from app.deps import Principal, get_current_user
from app.models import AgentProfile
from app.schemas import AgentProfileIn
from app.util import iso, new_id

router = APIRouter(tags=["agent-profiles"])

_FIELDS = (
    "name", "harness", "harness_version", "model", "model_provider", "served_by",
    "runtime_host", "runtime_os", "runtime_hardware", "tools", "context_window",
    "capability_tier", "notes",
)


def profile_out(p: AgentProfile) -> dict:
    return {
        "id": p.id, "name": p.name,
        "harness": p.harness, "harness_version": p.harness_version,
        "model": p.model, "model_provider": p.model_provider, "served_by": p.served_by,
        "runtime_host": p.runtime_host, "runtime_os": p.runtime_os, "runtime_hardware": p.runtime_hardware,
        "tools": p.tools or [], "context_window": p.context_window,
        "capability_tier": p.capability_tier, "notes": p.notes,
        "created_at": iso(p.created_at),
    }


@router.get("/agent-profiles")
async def list_profiles(current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(AgentProfile)
                .where(AgentProfile.org_id == current.org_id, AgentProfile.active == True)  # noqa: E712
                .order_by(AgentProfile.created_at.desc())
            )
        ).scalars().all()
        return {"agent_profiles": [profile_out(p) for p in rows]}


@router.post("/agent-profiles")
async def create_profile(body: AgentProfileIn, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        p = AgentProfile(id=new_id(), org_id=current.org_id, active=True,
                         **{k: getattr(body, k) for k in _FIELDS})
        db.add(p)
        await db.flush()
        return profile_out(p)
