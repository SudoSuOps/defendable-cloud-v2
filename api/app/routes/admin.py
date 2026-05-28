"""/admin — in-app operator surface.

Gated by ADMIN_EMAILS config (lowercase, comma-separated). For v1 this
is just the membership approval review queue. The X-Internal-Key path
on /membership/approve stays available for scripts and CLI.

Sprint 18 surface:
  GET  /admin/applications              the pending+waitlisted queue
  POST /admin/applications/{slug}/approve  flip a row to `approved`

The approve endpoint shares its body logic with /membership/approve via
the `_approve_org_by_slug` helper, so the cap-race behavior is identical
across both entry points.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.db import session_scope
from app.deps import Principal, require_admin
from app.models import Organization, User
from app.routes.membership import _approve_org_by_slug
from app.schemas import (
    AdminApplicationList,
    AdminApplicationRow,
    Membership,
)
from app.util import iso

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/applications", response_model=AdminApplicationList)
async def list_applications(_: Principal = Depends(require_admin)):
    """Return all pending + waitlisted applications, oldest-first.

    Each row carries enough for the operator to make an approve / hold
    decision without a second fetch: org identity, applicant email
    (joined via the owner User row), the application body, and the
    waitlist position when applicable.
    """
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(Organization)
                .where(Organization.membership_status.in_(("pending", "waitlisted")))
                .order_by(
                    Organization.membership_applied_at.is_(None).desc(),
                    Organization.membership_applied_at.asc(),
                    Organization.created_at.asc(),
                )
            )
        ).scalars().all()

        # Owner emails · we fetch all owners in one query to avoid N+1.
        org_ids = [o.id for o in rows]
        owners: dict[str, str] = {}
        if org_ids:
            owner_rows = (
                await db.execute(
                    select(User.org_id, User.email).where(
                        User.org_id.in_(org_ids), User.role == "owner"
                    )
                )
            ).all()
            owners = {row.org_id: row.email for row in owner_rows}

        items: List[dict] = []
        for o in rows:
            app_body = o.membership_application or {}
            queue: Optional[int] = None
            if o.membership_status == "waitlisted":
                # 1-based · earlier applied_at = higher in line.
                queue = sum(
                    1
                    for r in rows
                    if r.membership_status == "waitlisted"
                    and r.membership_applied_at is not None
                    and o.membership_applied_at is not None
                    and r.membership_applied_at < o.membership_applied_at
                ) + 1
            items.append(
                {
                    "org_id": o.id,
                    "org_slug": o.slug,
                    "org_name": o.name,
                    "applicant_email": owners.get(o.id),
                    "status": o.membership_status,
                    "applied_at": iso(o.membership_applied_at) if o.membership_applied_at else None,
                    "waitlist_position": queue,
                    "company_name": app_body.get("company_name"),
                    "intended_use": app_body.get("intended_use"),
                    "referral_source": app_body.get("referral_source"),
                }
            )

    return {"applications": items, "count": len(items)}


@router.post(
    "/applications/{slug}/approve", response_model=Membership, status_code=200,
)
async def approve_application(slug: str, _: Principal = Depends(require_admin)):
    """Flip a pending or waitlisted application to `approved`.

    Shares the cap-race-aware helper with /membership/approve. Caller is the
    in-app Admin UI; the X-Internal-Key path remains for scripts.
    """
    async with session_scope() as db:
        return await _approve_org_by_slug(db, slug)


@router.get("/health")
async def admin_health(current: Principal = Depends(require_admin)):
    """Quick sanity check for the Admin UI · confirms the JWT is admin-grade.
    Returns the calling email so the operator can verify they're acting as
    the right account."""
    return {"ok": True, "admin_email": current.email}
