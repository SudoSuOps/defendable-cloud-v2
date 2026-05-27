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
        "checks_passed": v.checks_passed,
        "checks_failed": v.checks_failed,
        "created_at": iso(v.created_at),
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
    async with session_scope() as db:
        project = await db.get(Project, body.project_id)
        if project is None or project.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="project not found")
        rid = new_id()
        run = Run(
            id=rid,
            org_id=current.org_id,
            project_id=body.project_id,
            lane=body.lane,
            title=body.title.strip(),
            status="draft",
            inputs=body.inputs or {},
            created_by=current.id,
        )
        db.add(run)
        await db.flush()
        return {
            "id": run.id,
            "project_id": run.project_id,
            "lane": run.lane,
            "title": run.title,
            "status": run.status,
            "inputs": run.inputs,
            "created_at": iso(run.created_at),
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
    async with session_scope() as db:
        run = await _get_run(db, run_id, current.org_id)
        v = await _latest_verdict(db, run_id)
        a = await _latest_approval(db, run_id)
        receipt = (
            await db.execute(
                select(Receipt).where(Receipt.run_id == run_id).order_by(Receipt.created_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        return {
            "id": run.id,
            "project_id": run.project_id,
            "lane": run.lane,
            "title": run.title,
            "status": run.status,
            "inputs": run.inputs,
            "created_at": iso(run.created_at),
            "updated_at": iso(run.updated_at),
            "evidence": [_evidence_out(e) for e in sorted(run.evidence, key=lambda x: x.created_at)],
            "checks": [_check_out(c) for c in sorted(run.checks, key=lambda x: x.created_at)],
            "verdict": _verdict_out(v),
            "approval": _approval_out(a),
            "receipt": _receipt_out(receipt) if receipt else None,
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
    async with session_scope() as db:
        run = await _get_run(db, run_id, current.org_id)
        project = await db.get(Project, run.project_id)
        org = await db.get(Organization, current.org_id)
        v = await _latest_verdict(db, run_id)
        a = await _latest_approval(db, run_id)
        if v is None:
            raise HTTPException(status_code=409, detail="run a verification first")
        if a is None or a.decision != "approved":
            raise HTTPException(status_code=409, detail="a human must approve the run before a receipt is issued")

        # Hash chain: next org_seq + previous receipt hash.
        last = (
            await db.execute(
                select(Receipt).where(Receipt.org_id == current.org_id).order_by(Receipt.org_seq.desc()).limit(1)
            )
        ).scalar_one_or_none()
        org_seq = (last.org_seq + 1) if last else 0
        parent_hash = last.receipt_sha256 if last else ZERO_HASH

        receipt_id = f"DCR-{org_seq:06d}-{new_id()[:8]}"
        share_token = make_share_token()
        base = settings().api_base_url.rstrip("/")
        share_url = f"{base}/share/{share_token}"
        created_at = iso_now()

        payload = receipt_builder.build_payload(
            receipt_id=receipt_id,
            org_seq=org_seq,
            parent_hash=parent_hash,
            created_at=created_at,
            org={"id": org.id, "name": org.name},
            project={"id": project.id, "name": project.name},
            run={"id": run.id, "lane": run.lane, "title": run.title, "inputs": run.inputs or {}},
            evidence=[_evidence_out(e) for e in run.evidence],
            checks=[_check_out(c) for c in run.checks],
            verdict=_verdict_out(v),
            approval=_approval_out(a),
            share_url=share_url,
        )
        receipt_sha256 = sha256_hex(canonical(payload))

        rid = new_id()
        json_key = f"orgs/{current.org_id}/receipts/{receipt_id}.json"
        pdf_key = f"orgs/{current.org_id}/receipts/{receipt_id}.pdf"
        stored_json: Optional[str] = None
        stored_pdf: Optional[str] = None

        # Render PDF + best-effort durable upload to Tigris (serving regenerates if absent).
        pdf_bytes = receipt_builder.render_pdf(payload, receipt_sha256)
        json_bytes = canonical({**payload, "receipt_sha256": receipt_sha256})
        try:
            put_object(json_key, json_bytes, content_type="application/json")
            stored_json = json_key
            put_object(pdf_key, pdf_bytes, content_type="application/pdf")
            stored_pdf = pdf_key
        except Exception:
            pass

        receipt = Receipt(
            id=rid, org_id=current.org_id, run_id=run_id, receipt_id=receipt_id,
            org_seq=org_seq, parent_hash=parent_hash, receipt_sha256=receipt_sha256,
            share_token=share_token, payload=payload, json_key=stored_json, pdf_key=stored_pdf,
        )
        db.add(receipt)
        if stored_json:
            db.add(Artifact(id=new_id(), run_id=run_id, receipt_id=rid, kind="receipt_json",
                            tigris_key=json_key, sha256=sha256_hex(json_bytes), byte_size=len(json_bytes),
                            content_type="application/json"))
        if stored_pdf:
            db.add(Artifact(id=new_id(), run_id=run_id, receipt_id=rid, kind="receipt_pdf",
                            tigris_key=pdf_key, sha256=sha256_hex(pdf_bytes), byte_size=len(pdf_bytes),
                            content_type="application/pdf"))
        run.status = "receipted"
        await db.flush()
        return _receipt_out(receipt)
