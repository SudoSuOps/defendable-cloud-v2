from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.db import session_scope
from app.deps import Principal, get_current_user
from app.models import Dataset

router = APIRouter(tags=["datasets"])


def _out(d: Dataset) -> dict:
    return {
        "id": d.id,
        "slug": d.slug,
        "name": d.name,
        "domain": d.domain,
        "lane": d.lane,
        "description": d.description,
        "pair_count": d.pair_count,
        "tier": d.tier,
        "targets": d.targets,
    }


@router.get("/datasets")
async def list_datasets(_: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        rows = (
            await db.execute(select(Dataset).where(Dataset.active == True).order_by(Dataset.name))  # noqa: E712
        ).scalars().all()
        return {"datasets": [_out(d) for d in rows]}
