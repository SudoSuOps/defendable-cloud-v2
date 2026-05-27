from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import delete, select

from app import eval as eval_engine
from app.db import session_scope
from app.deps import Principal, get_current_user
from app.hashing import sha256_hex
from app.models import AgentSubmission, CheckResult, FlightSheet, Run, Verdict
from app.util import iso, new_id

router = APIRouter(tags=["eval"])


def flight_sheet_out(fs: FlightSheet) -> dict:
    return {
        "id": fs.id, "slug": fs.slug, "name": fs.name, "version": fs.version, "lane": fs.lane,
        "summary": fs.summary, "purpose": fs.purpose, "assignment_instructions": fs.assignment_instructions,
        "required_inputs": fs.required_inputs, "expected_outputs": fs.expected_outputs,
        "audit_checks": fs.audit_checks, "pass_threshold": fs.pass_threshold, "fail_threshold": fs.fail_threshold,
    }


@router.get("/flight-sheets")
async def list_flight_sheets(_: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        rows = (
            await db.execute(select(FlightSheet).where(FlightSheet.active == True).order_by(FlightSheet.name))  # noqa: E712
        ).scalars().all()
        return {"flight_sheets": [flight_sheet_out(f) for f in rows]}


async def _run(db, run_id: str, org_id: str) -> Run:
    r = await db.get(Run, run_id)
    if r is None or r.org_id != org_id:
        raise HTTPException(status_code=404, detail="eval run not found")
    return r


@router.post("/runs/{run_id}/submission")
async def add_submission(
    run_id: str,
    body: dict = Body(...),
    current: Principal = Depends(get_current_user),
):
    output = (body.get("output_text") or "").strip()
    if not output:
        raise HTTPException(status_code=400, detail="paste the agent output")
    async with session_scope() as db:
        run = await _run(db, run_id, current.org_id)
        sub = AgentSubmission(
            id=new_id(), run_id=run_id,
            agent_name=body.get("agent_name"), model_name=body.get("model_name"), provider=body.get("provider"),
            output_text=output, tool_logs=body.get("tool_logs"), notes=body.get("notes"),
            sha256=sha256_hex(output.encode("utf-8")),
        )
        db.add(sub)
        run.agent_name = body.get("agent_name")
        run.model_name = body.get("model_name")
        run.provider = body.get("provider")
        if run.status in ("draft", "assignment_issued"):
            run.status = "submitted"
        await db.flush()
        return {"id": sub.id, "sha256": sub.sha256, "submitted_at": iso(sub.submitted_at)}


@router.post("/runs/{run_id}/audit")
async def run_audit(run_id: str, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        run = await _run(db, run_id, current.org_id)
        if run.flight_sheet_id is None:
            raise HTTPException(status_code=409, detail="this run has no flight sheet")
        fs = await db.get(FlightSheet, run.flight_sheet_id)
        sub = (
            await db.execute(select(AgentSubmission).where(AgentSubmission.run_id == run_id).order_by(AgentSubmission.submitted_at.desc()).limit(1))
        ).scalar_one_or_none()
        if sub is None:
            raise HTTPException(status_code=409, detail="add the agent submission first")

        evidence = [{"kind": e.kind, "label": e.label, "sha256": e.sha256} for e in run.evidence]
        results = eval_engine.run_audit(flight_sheet_out(fs), sub.output_text, evidence)

        await db.execute(delete(CheckResult).where(CheckResult.run_id == run_id))
        await db.execute(delete(Verdict).where(Verdict.run_id == run_id))
        for r in results:
            db.add(CheckResult(
                id=new_id(), run_id=run_id, check_key=r["check_key"], label=r["label"],
                category=r["category"], status=r["status"], severity=r.get("severity"),
                source=r.get("source", "auto"), detail=r.get("detail"),
            ))
        needs_grading = any(r["status"] == "open" for r in results)
        run.status = "audited" if needs_grading else "findings_ready"
        await db.flush()
        return {"checks": results, "needs_grading": needs_grading}


@router.patch("/runs/{run_id}/checks/{check_id}")
async def grade_check(
    run_id: str,
    check_id: str,
    body: dict = Body(...),
    current: Principal = Depends(get_current_user),
):
    # The operator applies a declared rule: it is SATISFIED (pass) or it raises a
    # FLAG. Not a quality grade. The flag's severity is the rule's declared severity.
    status = body.get("status")
    if status not in ("pass", "flag"):
        raise HTTPException(status_code=400, detail="status must be pass (satisfied) | flag")
    async with session_scope() as db:
        await _run(db, run_id, current.org_id)
        chk = await db.get(CheckResult, check_id)
        if chk is None or chk.run_id != run_id:
            raise HTTPException(status_code=404, detail="rule not found")
        chk.status = status  # severity stays the rule's declared flag-severity
        chk.source = "operator"
        if body.get("detail"):
            chk.detail = body["detail"]
        await db.flush()
        return {"ok": True, "check_key": chk.check_key, "status": chk.status, "severity": chk.severity}


@router.post("/runs/{run_id}/findings")
async def finalize_findings(run_id: str, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        run = await _run(db, run_id, current.org_id)
        fs = await db.get(FlightSheet, run.flight_sheet_id) if run.flight_sheet_id else None
        checks = list(run.checks)
        if not checks:
            raise HTTPException(status_code=409, detail="run the audit first")
        open_rules = [c for c in checks if c.status == "open"]
        if open_rules:
            raise HTTPException(status_code=409, detail=f"{len(open_rules)} rule(s) still need to be applied (satisfied or flagged)")

        fsd = flight_sheet_out(fs) if fs else {"pass_threshold": 80, "fail_threshold": 60}
        v = eval_engine.compute_verdict(fsd, checks)

        await db.execute(delete(Verdict).where(Verdict.run_id == run_id))
        verdict = Verdict(
            id=new_id(), run_id=run_id, outcome=v["outcome"], summary=v["summary"], score=v["score"],
            score_100=v["score_100"], severity=v["severity"], client_ready=v["client_ready"],
            recommended_action=v["recommended_action"], checks_passed=v["checks_passed"], checks_failed=v["checks_failed"],
        )
        db.add(verdict)
        run.status = "findings_ready"
        await db.flush()
        return v
