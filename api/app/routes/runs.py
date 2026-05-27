from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, func, select

from app.checks import run_checks
from app.config import settings
from app.db import session_scope
from app.deps import Principal, get_current_user
from app.hashing import ZERO_HASH, canonical, sha256_hex
from app.models import (
    Approval,
    Artifact,
    CheckResult,
    EvidenceItem,
    Organization,
    Project,
    Receipt,
    Run,
    Verdict,
)
from app import receipts as receipt_builder
from app.schemas import ApprovalIn, EvidenceIn, RunIn
from app.security import make_share_token
from app.storage import put_object
from app.util import iso, iso_now, new_id

router = APIRouter(tags=["runs"])


# ── serializers ───────────────────────────────────────────────────────────────


def _evidence_out(e: EvidenceItem) -> dict:
    return {
        "id": e.id,
        "kind": e.kind,
        "label": e.label,
        "content": e.content,
        "sha256": e.sha256,
        "byte_size": e.byte_size,
        "content_type": e.content_type,
        "created_at": iso(e.created_at),
    }


def _check_out(c: CheckResult) -> dict:
    return {
        "check_key": c.check_key,
        "label": c.label,
        "category": c.category,
        "status": c.status,
        "detail": c.detail,
        "score": c.score,
    }


def _verdict_out(v: Verdict | None) -> dict | None:
    if v is None:
        return None
    return {
        "outcome": v.outcome,
        "summary": v.summary,
        "score": v.score,
        "score_100": v.score_100,
        "severity": v.severity,
        "client_ready": v.client_ready,
        "recommended_action": v.recommended_action,
        "checks_passed": v.checks_passed,
        "checks_failed": v.checks_failed,
        "created_at": iso(v.created_at),
    }


def _check_out_full(c: CheckResult) -> dict:
    return {
        "id": c.id,
        "check_key": c.check_key,
        "label": c.label,
        "category": c.category,
        "status": c.status,
        "severity": c.severity,
        "source": c.source,
        "detail": c.detail,
    }


def _approval_out(a: Approval | None) -> dict | None:
    if a is None:
        return None
    return {
        "decision": a.decision,
        "approver_email": a.approver_email,
        "note": a.note,
        "created_at": iso(a.created_at),
    }


def _receipt_out(r: Receipt) -> dict:
    base = settings().api_base_url.rstrip("/")
    return {
        "receipt_id": r.receipt_id,
        "org_seq": r.org_seq,
        "parent_hash": r.parent_hash,
        "receipt_sha256": r.receipt_sha256,
        "share_token": r.share_token,
        "share_url": f"{base}/share/{r.share_token}",
        "pdf_url": f"{base}/share/{r.share_token}/pdf",
        "created_at": iso(r.created_at),
    }


async def _latest_verdict(db, run_id: str) -> Verdict | None:
    return (
        await db.execute(
            select(Verdict).where(Verdict.run_id == run_id).order_by(Verdict.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()


async def _latest_approval(db, run_id: str) -> Approval | None:
    return (
        await db.execute(
            select(Approval).where(Approval.run_id == run_id).order_by(Approval.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()


async def _get_run(db, run_id: str, org_id: str) -> Run:
    run = await db.get(Run, run_id)
    if run is None or run.org_id != org_id:
        raise HTTPException(status_code=404, detail="run not found")
    return run


# ── runs ───────────────────────────────────────────────────────────────────────


@router.post("/runs")
async def create_run(body: RunIn, current: Principal = Depends(get_current_user)):
    from app import eval as eval_engine
    from app.models import FlightSheet
    from app.routes.eval import flight_sheet_out

    async with session_scope() as db:
        project = await db.get(Project, body.project_id)
        if project is None or project.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="project not found")

        lane = body.lane or "agent"
        title = (body.title or "").strip()
        assignment_text = None
        fs_id = None
        if body.flight_sheet_id:
            fs = await db.get(FlightSheet, body.flight_sheet_id)
            if fs is None or not fs.active:
                raise HTTPException(status_code=404, detail="flight sheet not found")
            fs_id = fs.id
            lane = fs.lane
            if not title:
                title = fs.name
            assignment_text = eval_engine.build_assignment(flight_sheet_out(fs))
        if not title:
            raise HTTPException(status_code=400, detail="title required")

        ap_id = agent_name = model_name = provider = None
        if body.agent_profile_id:
            from app.models import AgentProfile
            ap = await db.get(AgentProfile, body.agent_profile_id)
            if ap is None or ap.org_id != current.org_id:
                raise HTTPException(status_code=404, detail="agent profile not found")
            ap_id, agent_name, model_name, provider = ap.id, ap.name, ap.model, ap.model_provider

        rid = new_id()
        run = Run(
            id=rid, org_id=current.org_id, project_id=body.project_id,
            flight_sheet_id=fs_id, agent_profile_id=ap_id, lane=lane, title=title,
            status="assignment_issued" if assignment_text else "draft",
            inputs=body.inputs or {}, assignment_text=assignment_text, created_by=current.id,
            agent_name=agent_name, model_name=model_name, provider=provider,
        )
        db.add(run)
        await db.flush()
        return {
            "id": run.id, "project_id": run.project_id, "flight_sheet_id": run.flight_sheet_id,
            "lane": run.lane, "title": run.title, "status": run.status, "inputs": run.inputs,
            "assignment_text": run.assignment_text, "created_at": iso(run.created_at),
        }


@router.get("/runs")
async def list_runs(current: Principal = Depends(get_current_user), limit: int = 50):
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(Run).where(Run.org_id == current.org_id).order_by(Run.created_at.desc()).limit(min(limit, 200))
            )
        ).scalars().all()
        out = []
        for r in rows:
            v = await _latest_verdict(db, r.id)
            out.append({
                "id": r.id,
                "project_id": r.project_id,
                "lane": r.lane,
                "title": r.title,
                "status": r.status,
                "verdict": v.outcome if v else None,
                "created_at": iso(r.created_at),
            })
        return {"runs": out}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, current: Principal = Depends(get_current_user)):
    from app.models import AgentSubmission, FlightSheet

    async with session_scope() as db:
        run = await _get_run(db, run_id, current.org_id)
        v = await _latest_verdict(db, run_id)
        a = await _latest_approval(db, run_id)
        receipt = (
            await db.execute(
                select(Receipt).where(Receipt.run_id == run_id).order_by(Receipt.created_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        fs = await db.get(FlightSheet, run.flight_sheet_id) if run.flight_sheet_id else None
        sub = (
            await db.execute(select(AgentSubmission).where(AgentSubmission.run_id == run_id).order_by(AgentSubmission.submitted_at.desc()).limit(1))
        ).scalar_one_or_none()
        from app.models import AgentProfile
        from app.routes.agents import profile_out
        ap = await db.get(AgentProfile, run.agent_profile_id) if run.agent_profile_id else None

        approved = a.decision == "approved" if a else False
        return {
            "id": run.id,
            "project_id": run.project_id,
            "lane": run.lane,
            "title": run.title,
            "status": run.status,
            "inputs": run.inputs,
            "assignment_text": run.assignment_text,
            "agent_name": run.agent_name,
            "model_name": run.model_name,
            "provider": run.provider,
            "created_at": iso(run.created_at),
            "updated_at": iso(run.updated_at),
            "flight_sheet": {
                "id": fs.id, "name": fs.name, "version": fs.version, "lane": fs.lane,
                "summary": fs.summary, "expected_outputs": fs.expected_outputs,
                "pass_threshold": fs.pass_threshold, "fail_threshold": fs.fail_threshold,
            } if fs else None,
            "agent_profile": profile_out(ap) if ap else None,
            "submission": {
                "agent_name": sub.agent_name, "model_name": sub.model_name, "provider": sub.provider,
                "output_text": sub.output_text, "tool_logs": sub.tool_logs, "notes": sub.notes,
                "sha256": sub.sha256, "submitted_at": iso(sub.submitted_at),
            } if sub else None,
            "evidence": [_evidence_out(e) for e in sorted(run.evidence, key=lambda x: x.created_at)],
            "checks": [_check_out_full(c) for c in sorted(run.checks, key=lambda x: x.created_at)],
            "verdict": _verdict_out(v),
            "approval": _approval_out(a),
            "receipt": _receipt_out(receipt) if receipt else None,
            "ownership": {
                "agent_created": run.agent_name or (sub.agent_name if sub else None),
                "audited_by": "DefendableCloud Eval",
                "referee_logic": f"{fs.name} v{fs.version}" if fs else "deterministic checks",
                "final_authority": a.approver_email if a else current.email,
                "approval_status": a.decision if a else "pending",
                "receipt_status": "issued" if receipt else "draft",
            },
        }


# ── evidence ────────────────────────────────────────────────────────────────────


@router.post("/runs/{run_id}/evidence")
async def add_evidence(run_id: str, body: EvidenceIn, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        await _get_run(db, run_id, current.org_id)
        content = body.content or ""
        e = EvidenceItem(
            id=new_id(),
            run_id=run_id,
            kind=body.kind,
            label=body.label.strip(),
            content=content or None,
            sha256=sha256_hex(content.encode("utf-8")) if content else None,
            byte_size=len(content.encode("utf-8")),
            content_type="text/plain" if content else None,
        )
        db.add(e)
        await db.flush()
        return _evidence_out(e)


@router.post("/runs/{run_id}/evidence/upload")
async def upload_evidence(
    run_id: str,
    file: UploadFile = File(...),
    label: Optional[str] = Form(default=None),
    current: Principal = Depends(get_current_user),
):
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file too large (25MB max)")
    digest = sha256_hex(data)
    eid = new_id()
    key = f"orgs/{current.org_id}/runs/{run_id}/evidence/{eid}/{file.filename or 'file'}"
    stored_key: Optional[str] = None
    try:
        put_object(key, data, content_type=file.content_type or "application/octet-stream")
        stored_key = key
    except Exception:
        stored_key = None  # storage not configured; metadata + hash still recorded

    async with session_scope() as db:
        await _get_run(db, run_id, current.org_id)
        e = EvidenceItem(
            id=eid,
            run_id=run_id,
            kind="file",
            label=(label or file.filename or "file").strip(),
            tigris_key=stored_key,
            sha256=digest,
            byte_size=len(data),
            content_type=file.content_type or "application/octet-stream",
        )
        db.add(e)
        await db.flush()
        return _evidence_out(e)


# ── checks / verdict ──────────────────────────────────────────────────────────


@router.post("/runs/{run_id}/checks")
async def run_run_checks(run_id: str, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        run = await _get_run(db, run_id, current.org_id)
        evidence = [_evidence_out(e) for e in run.evidence]
        results, verdict = run_checks(run.lane, run.inputs or {}, evidence)

        # Replace prior check/verdict state for this run.
        await db.execute(delete(CheckResult).where(CheckResult.run_id == run_id))
        await db.execute(delete(Verdict).where(Verdict.run_id == run_id))

        for r in results:
            db.add(CheckResult(
                id=new_id(), run_id=run_id, check_key=r.check_key, label=r.label,
                category=r.category, status=r.status, detail=r.detail, score=r.score,
            ))
        v = Verdict(
            id=new_id(), run_id=run_id, outcome=verdict.outcome, summary=verdict.summary,
            score=verdict.score, checks_passed=verdict.checks_passed, checks_failed=verdict.checks_failed,
        )
        db.add(v)
        run.status = "checked"
        await db.flush()
        return {"verdict": _verdict_out(v), "checks": [_check_out_data(r) for r in results]}


def _check_out_data(r) -> dict:
    return {
        "check_key": r.check_key, "label": r.label, "category": r.category,
        "status": r.status, "detail": r.detail, "score": r.score,
    }


# ── approval ─────────────────────────────────────────────────────────────────


@router.post("/runs/{run_id}/approve")
async def approve_run(run_id: str, body: ApprovalIn, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        run = await _get_run(db, run_id, current.org_id)
        v = await _latest_verdict(db, run_id)
        if v is None:
            raise HTTPException(status_code=409, detail="run a verification before approving")
        a = Approval(
            id=new_id(), run_id=run_id, decision=body.decision,
            approver_user_id=current.id, approver_email=current.email, note=body.note,
        )
        db.add(a)
        run.status = {"approved": "approved", "rejected": "rejected"}.get(body.decision, "checked")
        await db.flush()
        return _approval_out(a)


# ── receipt ──────────────────────────────────────────────────────────────────


@router.post("/runs/{run_id}/receipt")
async def generate_receipt(run_id: str, current: Principal = Depends(get_current_user)):
    from app.ledger import mint_receipt
    from app.models import AgentSubmission, FlightSheet

    async with session_scope() as db:
        run = await _get_run(db, run_id, current.org_id)
        project = await db.get(Project, run.project_id)
        org = await db.get(Organization, current.org_id)
        v = await _latest_verdict(db, run_id)
        a = await _latest_approval(db, run_id)
        if v is None:
            raise HTTPException(status_code=409, detail="run the audit / findings first")
        if a is None or a.decision != "approved":
            raise HTTPException(status_code=409, detail="a human must approve before a receipt is issued")

        fs = await db.get(FlightSheet, run.flight_sheet_id) if run.flight_sheet_id else None
        sub = (
            await db.execute(select(AgentSubmission).where(AgentSubmission.run_id == run_id).order_by(AgentSubmission.submitted_at.desc()).limit(1))
        ).scalar_one_or_none()
        from app.models import AgentProfile
        from app.routes.agents import profile_out
        ap = await db.get(AgentProfile, run.agent_profile_id) if run.agent_profile_id else None
        ap_payload = profile_out(ap) if ap else None

        def build(receipt_id, org_seq, parent_hash, created_at, share_url):
            if fs is not None:
                return receipt_builder.build_eval_payload(
                    receipt_id=receipt_id, org_seq=org_seq, parent_hash=parent_hash, created_at=created_at,
                    org={"id": org.id, "name": org.name},
                    run={"id": run.id, "lane": run.lane, "title": run.title},
                    flight_sheet={"name": fs.name, "version": fs.version},
                    agent_profile=ap_payload,
                    assignment_sha256=sha256_hex((run.assignment_text or "").encode("utf-8")),
                    submission={
                        "agent_name": sub.agent_name, "model_name": sub.model_name,
                        "provider": sub.provider, "sha256": sub.sha256,
                    } if sub else {},
                    evidence=[_evidence_out(e) for e in run.evidence],
                    findings=[_check_out_full(c) for c in run.checks],
                    verdict=_verdict_out(v),
                    approval=_approval_out(a),
                    share_url=share_url,
                )
            return receipt_builder.build_payload(
                receipt_id=receipt_id, org_seq=org_seq, parent_hash=parent_hash, created_at=created_at,
                org={"id": org.id, "name": org.name},
                project={"id": project.id, "name": project.name},
                run={"id": run.id, "lane": run.lane, "title": run.title, "inputs": run.inputs or {}},
                evidence=[_evidence_out(e) for e in run.evidence],
                checks=[_check_out(c) for c in run.checks],
                verdict=_verdict_out(v),
                approval=_approval_out(a),
                share_url=share_url,
            )

        receipt = await mint_receipt(db, org_id=current.org_id, run_id=run_id, build=build)
        run.status = "receipted"
        await db.flush()
        return _receipt_out(receipt)
