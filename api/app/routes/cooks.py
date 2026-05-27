from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.db import session_scope
from app.deps import Principal, get_current_user
from app.models import Cook, Dataset, Receipt, Run, Verdict
from app.schemas import CookRequestIn
from app.util import iso, new_id

router = APIRouter(tags=["cooks"])


def cook_out(c: Cook, share_token: str | None = None) -> dict:
    return {
        "id": c.id,
        "run_id": c.run_id,
        "dataset_id": c.dataset_id,
        "base_model": c.base_model,
        "status": c.status,
        "eval_before": c.eval_before,
        "eval_after": c.eval_after,
        "lift": c.lift,
        "pairs": c.pairs,
        "runner": c.runner,
        "metrics": c.metrics,
        "error": c.error,
        "receipt_id": c.receipt_id,
        "share_token": share_token,
        "created_at": iso(c.created_at),
        "updated_at": iso(c.updated_at),
    }


@router.post("/runs/{run_id}/cook")
async def request_cook(run_id: str, body: CookRequestIn, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        run = await db.get(Run, run_id)
        if run is None or run.org_id != current.org_id:
            raise HTTPException(status_code=404, detail="run not found")
        verdict = (
            await db.execute(select(Verdict).where(Verdict.run_id == run_id).order_by(Verdict.created_at.desc()).limit(1))
        ).scalar_one_or_none()
        if verdict is None:
            raise HTTPException(status_code=409, detail="run a verification first — the cook tunes against the eval")
        dataset = await db.get(Dataset, body.dataset_id)
        if dataset is None or not dataset.active:
            raise HTTPException(status_code=404, detail="dataset not found")

        cook = Cook(
            id=new_id(),
            org_id=current.org_id,
            run_id=run_id,
            dataset_id=dataset.id,
            base_model=body.base_model,
            status="queued",
            eval_before=verdict.score,
            pairs=dataset.pair_count,
            created_by=current.id,
        )
        db.add(cook)
        await db.flush()
        return cook_out(cook)


async def _get_cook(db, cook_id: str, org_id: str) -> Cook:
    c = await db.get(Cook, cook_id)
    if c is None or c.org_id != org_id:
        raise HTTPException(status_code=404, detail="cook not found")
    return c


@router.get("/cooks/{cook_id}")
async def get_cook(cook_id: str, current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        c = await _get_cook(db, cook_id, current.org_id)
        share_token = None
        if c.receipt_id:
            r = await db.get(Receipt, c.receipt_id)
            share_token = r.share_token if r else None
        return cook_out(c, share_token)


@router.get("/cooks")
async def list_cooks(current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        rows = (
            await db.execute(select(Cook).where(Cook.org_id == current.org_id).order_by(Cook.created_at.desc()).limit(100))
        ).scalars().all()
        return {"cooks": [cook_out(c) for c in rows]}
