from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select

from app import receipts as receipt_builder
from app.db import session_scope
from app.deps import Principal, get_current_user
from app.models import AgentProfile, Incident, Organization, Receipt
from app.schemas import IncidentIn
from app.util import iso, new_id

router = APIRouter(tags=["incidents"])


def incident_out(i: Incident, profile_name: str | None = None) -> dict:
    return {
        "id": i.id, "kind": i.kind, "tier": i.tier, "title": i.title, "detail": i.detail,
        "lane": i.lane, "response": i.response or [], "status": i.status,
        "agent_profile_id": i.agent_profile_id, "agent_profile_name": profile_name,
        "run_id": i.run_id, "receipt_id": i.receipt_id,
        "created_at": iso(i.created_at), "resolved_at": iso(i.resolved_at) if i.resolved_at else None,
    }


@router.get("/incidents")
async def list_incidents(agent_profile_id: str | None = None, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        q = select(Incident).where(Incident.org_id == current.org_id)
        if agent_profile_id:
            q = q.where(Incident.agent_profile_id == agent_profile_id)
        rows = (await db.execute(q.order_by(Incident.created_at.desc()))).scalars().all()
        names: dict[str, str] = {}
        out = []
        for i in rows:
            if i.agent_profile_id and i.agent_profile_id not in names:
                p = await db.get(AgentProfile, i.agent_profile_id)
                names[i.agent_profile_id] = p.name if p else "—"
            row = incident_out(i, names.get(i.agent_profile_id))
            if i.receipt_id:
                rc = await db.get(Receipt, i.receipt_id)
                row["share_token"] = rc.share_token if rc else None
            out.append(row)
        return {"incidents": out}


@router.post("/incidents")
async def open_incident(body: IncidentIn, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        if body.agent_profile_id:
            p = await db.get(AgentProfile, body.agent_profile_id)
            if p is None or p.org_id != current.org_id:
                raise HTTPException(status_code=404, detail="agent profile not found")
        inc = Incident(
            id=new_id(), org_id=current.org_id, agent_profile_id=body.agent_profile_id, run_id=body.run_id,
            kind=body.kind, tier=body.tier or "high", title=body.title.strip(), detail=body.detail,
            lane=body.lane, response=body.response or [], status="open",
        )
        db.add(inc)
        await db.flush()
        return incident_out(inc)


@router.patch("/incidents/{incident_id}")
async def resolve_incident(incident_id: str, body: dict = Body(default={}), current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        inc = await db.get(Incident, incident_id)
        if inc is None or inc.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="incident not found")
        inc.status = body.get("status", "resolved")
        if inc.status == "resolved":
            inc.resolved_at = datetime.now(timezone.utc)
        await db.flush()
        return incident_out(inc)


@router.post("/incidents/{incident_id}/receipt")
async def incident_receipt(incident_id: str, current: Principal = Depends(get_current_user)):
    from app.ledger import mint_receipt
    from app.routes.agents import profile_out

    async with session_scope() as db:
        inc = await db.get(Incident, incident_id)
        if inc is None or inc.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="incident not found")
        org = await db.get(Organization, current.org_id)
        ap = await db.get(AgentProfile, inc.agent_profile_id) if inc.agent_profile_id else None
        ap_payload = profile_out(ap) if ap else None
        inc_payload = incident_out(inc)

        def build(receipt_id, org_seq, parent_hash, created_at, share_url):
            return receipt_builder.build_incident_payload(
                receipt_id=receipt_id, org_seq=org_seq, parent_hash=parent_hash, created_at=created_at,
                org={"id": org.id, "name": org.name}, incident=inc_payload,
                agent_profile=ap_payload, share_url=share_url,
            )

        receipt = await mint_receipt(db, org_id=current.org_id, run_id=inc.run_id, build=build)
        inc.receipt_id = receipt.id
        await db.flush()
        return {"receipt_id": receipt.receipt_id, "receipt_sha256": receipt.receipt_sha256,
                "share_token": receipt.share_token, "org_seq": receipt.org_seq}


@router.post("/agent-profiles/{profile_id}/watchdog")
async def watchdog_scan(profile_id: str, current: Principal = Depends(get_current_user)):
    """Deterministic ops pass: a lane with recurring critical flags (blocked) gets
    locked and an incident opened — straight from the capability profile, no telemetry."""
    from app.routes.agents import compute_capability

    async with session_scope() as db:
        p = await db.get(AgentProfile, profile_id)
        if p is None or p.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="agent profile not found")
        cap = await compute_capability(db, p)
        existing = (
            await db.execute(
                select(Incident).where(
                    Incident.org_id == current.org_id,
                    Incident.agent_profile_id == profile_id,
                    Incident.kind == "recurring_flag",
                    Incident.status == "open",
                )
            )
        ).scalars().all()
        open_lanes = {i.lane for i in existing}

        opened = []
        locked = set((p.governance or {}).get("blocked_lanes") or [])
        for lane in cap["lane_authorizations"]:
            if lane["status"] != "blocked" or lane["name"] in open_lanes:
                continue
            inc = Incident(
                id=new_id(), org_id=current.org_id, agent_profile_id=profile_id, kind="recurring_flag",
                tier="high", title=f"Recurring critical flag on lane '{lane['name']}'",
                detail=f"{lane['propolis']} propolis verdict(s) on this lane ({lane['honey']}H {lane['jelly']}J {lane['propolis']}P). Lane locked pending repair.",
                lane=lane["name"], response=["lane_locked", "human_approval_required", "repair_task_recommended"], status="open",
            )
            db.add(inc)
            locked.add(lane["name"])
            opened.append(inc)

        if opened:
            gov = dict(p.governance or {})
            gov["blocked_lanes"] = sorted(locked)
            p.governance = gov
        await db.flush()
        return {"opened": [incident_out(i, p.name) for i in opened], "scanned_lanes": len(cap["lane_authorizations"]), "blocked_lanes": sorted(locked)}
