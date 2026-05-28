from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app import receipts as receipt_builder
from app.config import settings
from app.db import session_scope
from app.deps import require_runner
from app.ledger import mint_receipt
from app.models import Cook, Dataset, Organization, Run
from app.models_catalog import find_latest_active_pin
from app.routes.cooks import cook_out
from app.schemas import RunnerClaimIn, RunnerCompleteIn, RunnerFailIn, RunnerStatusIn

router = APIRouter(prefix="/runner", tags=["runner"], dependencies=[Depends(require_runner)])


@router.post("/cooks/next")
async def claim_next(body: RunnerClaimIn):
    """The rig claims the oldest queued cook. Returns the job + what to train on."""
    async with session_scope() as db:
        cook = (
            await db.execute(select(Cook).where(Cook.status == "queued").order_by(Cook.created_at.asc()).limit(1))
        ).scalar_one_or_none()
        if cook is None:
            return {"cook": None}
        cook.status = "claimed"
        cook.runner = body.runner
        dataset = await db.get(Dataset, cook.dataset_id)
        await db.flush()
        return {
            "cook": {
                "id": cook.id,
                "base_model": cook.base_model,
                "eval_before": cook.eval_before,
                "pairs": cook.pairs,
                "dataset": {
                    "id": dataset.id,
                    "slug": dataset.slug,
                    "name": dataset.name,
                    "pair_count": dataset.pair_count,
                    "domain": dataset.domain,
                } if dataset else None,
            }
        }


@router.post("/cooks/{cook_id}/status")
async def update_status(cook_id: str, body: RunnerStatusIn):
    async with session_scope() as db:
        cook = await db.get(Cook, cook_id)
        if cook is None:
            raise HTTPException(status_code=404, detail="cook not found")
        cook.status = body.status
        if body.metrics:
            cook.metrics = {**(cook.metrics or {}), **body.metrics}
        await db.flush()
        return {"ok": True, "status": cook.status}


@router.post("/cooks/{cook_id}/complete")
async def complete(cook_id: str, body: RunnerCompleteIn):
    async with session_scope() as db:
        cook = await db.get(Cook, cook_id)
        if cook is None:
            raise HTTPException(status_code=404, detail="cook not found")
        if cook.status == "succeeded":
            raise HTTPException(status_code=409, detail="cook already completed")

        run = await db.get(Run, cook.run_id)
        org = await db.get(Organization, cook.org_id)
        dataset = await db.get(Dataset, cook.dataset_id)

        lift = round(body.eval_after - cook.eval_before, 4)
        metrics = {**(cook.metrics or {}), **(body.metrics or {})}
        duration_sec = float(metrics.get("duration_sec", 0) or 0)
        compute_usd = round((duration_sec / 3600.0) * settings().rig_usd_per_hour, 4) if duration_sec else None

        cook.eval_after = body.eval_after
        cook.lift = lift
        cook.adapter_ref = body.adapter_ref
        cook.metrics = metrics
        cook.status = "succeeded"

        # If the org has previously pinned this base_model (exact slug match),
        # seal the most recent pin into the cook receipt. Read-only · no
        # mutation of the pin receipt. If no pin exists, pinned_model stays
        # absent from the payload.
        pinned = await find_latest_active_pin(
            db, org_id=cook.org_id, model_slug=cook.base_model
        )

        receipt = await mint_receipt(
            db,
            org_id=cook.org_id,
            run_id=cook.run_id,
            build=lambda rid, seq, parent, created, share: receipt_builder.build_cook_payload(
                receipt_id=rid, org_seq=seq, parent_hash=parent, created_at=created,
                org={"id": org.id, "name": org.name},
                run={"id": run.id, "lane": run.lane, "title": run.title},
                cook={
                    "base_model": cook.base_model,
                    "dataset": dataset.name if dataset else cook.dataset_id,
                    "pairs": cook.pairs,
                    "eval_before": cook.eval_before,
                    "eval_after": cook.eval_after,
                    "lift": lift,
                    "runner": cook.runner,
                    "metrics": metrics,
                    "compute_usd": compute_usd,
                },
                share_url=share,
                pinned_model=pinned,
            ),
        )
        cook.receipt_id = receipt.id
        await db.flush()
        return {**cook_out(cook, receipt.share_token), "receipt_sha256": receipt.receipt_sha256}


@router.post("/cooks/{cook_id}/fail")
async def fail(cook_id: str, body: RunnerFailIn):
    async with session_scope() as db:
        cook = await db.get(Cook, cook_id)
        if cook is None:
            raise HTTPException(status_code=404, detail="cook not found")
        cook.status = "failed"
        cook.error = body.error[:2000]
        await db.flush()
        return {"ok": True}
