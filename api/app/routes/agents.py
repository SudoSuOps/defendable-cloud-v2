from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.db import session_scope
from app.deps import Principal, get_current_user
from app.models import AgentProfile, CheckResult, FlightSheet, Run, Verdict
from app.schemas import AgentProfileIn
from app.util import iso, new_id

router = APIRouter(tags=["agent-profiles"])

# Capability is EARNED, not declared — derived from the receipts a profile
# accumulates. No judge model: counts, pass-rates, and recurring flags only.
CAT_LABEL = {
    "schema": "Schema validity", "math": "Math accuracy", "evidence": "Evidence reference",
    "structure": "Structure", "policy": "Policy gates",
}


def _lane_status(honey: int, jelly: int, propolis: int) -> str:
    """Earned lane status (deterministic): ≥3 honey & 0 propolis → approved;
    one propolis → restricted; recurring propolis → blocked; else testing."""
    if propolis >= 2:
        return "blocked"
    if propolis >= 1:
        return "restricted"
    if honey >= 3:
        return "approved"
    return "testing"


async def compute_capability(db, profile: AgentProfile) -> dict:
    runs = (
        await db.execute(
            select(Run).where(Run.agent_profile_id == profile.id).order_by(Run.created_at.desc())
        )
    ).scalars().all()

    cat_pass: dict[str, int] = {}
    cat_total: dict[str, int] = {}
    flag_counts: dict[str, dict] = {}
    lanes: dict[str, dict] = {}
    vcounts = {"honey": 0, "jelly": 0, "propolis": 0}
    history: list[dict] = []
    latest = None

    for r in runs:
        v = (
            await db.execute(select(Verdict).where(Verdict.run_id == r.id).order_by(Verdict.created_at.desc()).limit(1))
        ).scalar_one_or_none()
        checks = (await db.execute(select(CheckResult).where(CheckResult.run_id == r.id))).scalars().all()
        for c in checks:
            if c.status in ("pass", "flag"):
                cat_total[c.category] = cat_total.get(c.category, 0) + 1
                if c.status == "pass":
                    cat_pass[c.category] = cat_pass.get(c.category, 0) + 1
                else:
                    fc = flag_counts.setdefault(c.label, {"count": 0, "severity": c.severity, "category": c.category})
                    fc["count"] += 1
        if v:
            sev = v.severity if v.severity in vcounts else "jelly"
            vcounts[sev] += 1
            if r.flight_sheet_id:
                fs = await db.get(FlightSheet, r.flight_sheet_id)
                ln = lanes.setdefault(r.flight_sheet_id, {
                    "name": fs.name if fs else r.title, "lane": fs.lane if fs else r.lane,
                    "honey": 0, "jelly": 0, "propolis": 0, "total": 0,
                })
                ln[sev] += 1
                ln["total"] += 1
            if latest is None:
                latest = {"run_id": r.id, "title": r.title, "severity": sev, "score_100": v.score_100, "created_at": iso(v.created_at)}
        history.append({
            "run_id": r.id, "title": r.title, "status": r.status,
            "severity": v.severity if v else None, "score_100": v.score_100 if v else None,
            "created_at": iso(r.created_at),
        })

    pass_rates = [
        {"category": k, "label": CAT_LABEL.get(k, k.title()), "rate": round(cat_pass.get(k, 0) / cat_total[k], 2), "n": cat_total[k]}
        for k in sorted(cat_total)
    ]
    recurring = sorted(
        [{"label": k, **vv} for k, vv in flag_counts.items()], key=lambda x: -x["count"]
    )[:6]
    lane_auth = [
        {"flight_sheet_id": fsid, "name": ln["name"], "lane": ln["lane"], "status": _lane_status(ln["honey"], ln["jelly"], ln["propolis"]),
         "honey": ln["honey"], "jelly": ln["jelly"], "propolis": ln["propolis"], "total": ln["total"]}
        for fsid, ln in lanes.items()
    ]
    lane_auth.sort(key=lambda x: x["name"])
    any_blocked = any(l["status"] in ("blocked", "restricted") for l in lane_auth)
    any_approved = any(l["status"] == "approved" for l in lane_auth)
    overall = "restricted" if any_blocked else ("approved" if any_approved else "testing")
    return {
        "evaluated_runs": sum(vcounts.values()),
        "total_runs": len(history),
        "verdict_counts": vcounts,
        "latest": latest,
        "pass_rates": pass_rates,
        "recurring_flags": recurring,
        "lane_authorizations": lane_auth,
        "overall_status": overall,
        "history": history[:25],
    }

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
        out = []
        for p in rows:
            cap = await compute_capability(db, p)
            out.append({
                **profile_out(p),
                "summary": {
                    "overall_status": cap["overall_status"],
                    "evaluated_runs": cap["evaluated_runs"],
                    "verdict_counts": cap["verdict_counts"],
                    "latest": cap["latest"],
                    "approved_lanes": [l["name"] for l in cap["lane_authorizations"] if l["status"] == "approved"],
                    "blocked_lanes": [l["name"] for l in cap["lane_authorizations"] if l["status"] in ("blocked", "restricted")],
                    "recurring_flags": cap["recurring_flags"][:3],
                },
            })
        return {"agent_profiles": out}


@router.get("/agent-profiles/{profile_id}")
async def get_profile(profile_id: str, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        p = await db.get(AgentProfile, profile_id)
        if p is None or p.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="agent profile not found")
        return {**profile_out(p), "capability": await compute_capability(db, p)}


@router.post("/agent-profiles")
async def create_profile(body: AgentProfileIn, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        p = AgentProfile(id=new_id(), org_id=current.org_id, active=True,
                         **{k: getattr(body, k) for k in _FIELDS})
        db.add(p)
        await db.flush()
        return profile_out(p)
