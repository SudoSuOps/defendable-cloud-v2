from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.db import session_scope
from app.deps import Principal, get_current_user
from app.models import Project, Run
from app.schemas import ProjectIn
from app.util import iso, new_id, slugify

router = APIRouter(prefix="/projects", tags=["projects"])


def _out(p: Project, run_count: int = 0) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "run_count": run_count,
        "created_at": iso(p.created_at),
    }


@router.post("")
async def create_project(body: ProjectIn, current: Principal = Depends(get_current_user)):
    pid = new_id()
    async with session_scope() as db:
        p = Project(
            id=pid,
            org_id=current.org_id,
            name=body.name.strip(),
            slug=f"{slugify(body.name)}-{pid[:6]}",
            created_by=current.id,
        )
        db.add(p)
        await db.flush()
        return _out(p)


@router.get("")
async def list_projects(current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(Project).where(Project.org_id == current.org_id).order_by(Project.created_at.desc())
            )
        ).scalars().all()
        out = []
        for p in rows:
            n = (
                await db.execute(select(Run.id).where(Run.project_id == p.id))
            ).scalars().all()
            out.append(_out(p, run_count=len(n)))
        return {"projects": out}
