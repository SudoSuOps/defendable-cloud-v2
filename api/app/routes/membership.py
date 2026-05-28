"""/membership — members-only community gate.

Two endpoints:
  GET  /membership          — the org's current state + cap status + queue position
  POST /membership/apply    — submit an application; emails build@ for review

Hard cap on active seats (settings().membership_cap, default 100). When the
cap is hit at application time, status flips to `waitlisted` instead of
`pending` and `waitlist_position` is filled. Activation is manual today (SQL
in the email; admin endpoint lands later when scale warrants it).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.config import settings
from app.db import session_scope
from app.deps import Principal, get_current_user
from app.email import send_membership_application
from app.models import Organization
from app.schemas import (
    Membership,
    MembershipApplicationIn,
    MembershipApplicationView,
)
from app.util import iso

router = APIRouter(prefix="/membership", tags=["membership"])


async def _active_count(db) -> int:
    return (
        await db.execute(
            select(func.count(Organization.id)).where(
                Organization.membership_status == "active"
            )
        )
    ).scalar_one()


async def _waitlist_position(db, org_id: str) -> Optional[int]:
    """1 = next in line. Ordered by applied_at asc. None if org isn't waitlisted."""
    org = await db.get(Organization, org_id)
    if org is None or org.membership_status != "waitlisted":
        return None
    if org.membership_applied_at is None:
        return None
    earlier = (
        await db.execute(
            select(func.count(Organization.id)).where(
                Organization.membership_status == "waitlisted",
                Organization.membership_applied_at < org.membership_applied_at,
            )
        )
    ).scalar_one()
    return int(earlier) + 1


def _membership_payload(org: Organization, *, cap: int, active_count: int, queue: Optional[int]) -> dict:
    app_view: Optional[MembershipApplicationView] = None
    if org.membership_application:
        app_view = MembershipApplicationView(**org.membership_application).model_dump(exclude_none=True)
    return {
        "status": org.membership_status,
        "applied_at": iso(org.membership_applied_at) if org.membership_applied_at else None,
        "activated_at": iso(org.membership_activated_at) if org.membership_activated_at else None,
        "seat_number": org.membership_seat_number,
        "cap": cap,
        "active_count": active_count,
        "waitlist_position": queue,
        "application": app_view,
    }


@router.get("", response_model=Membership)
async def get_membership(current: Principal = Depends(get_current_user)):
    """Current org's membership state. Always returns a Membership — `pending`
    is the default for orgs that have never applied.
    """
    s = settings()
    async with session_scope() as db:
        org = await db.get(Organization, current.org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="org not found")
        active = await _active_count(db)
        queue = await _waitlist_position(db, org.id)
        return _membership_payload(org, cap=s.membership_cap, active_count=active, queue=queue)


@router.post("/apply", response_model=Membership, status_code=201)
async def apply_for_membership(
    body: MembershipApplicationIn,
    current: Principal = Depends(get_current_user),
):
    """Submit a membership application.

    Refuses to re-apply over an already-decided state (active / waitlisted /
    inactive). If the cap is full when the application lands, the org enters
    the waitlist rather than the pending queue — surfaced as `waitlisted` so
    the applicant knows they're behind a line.

    Sends an email to build@defendableos.com (or settings.membership_review_email)
    for human review. Approval happens manually until an admin endpoint lands.
    """
    s = settings()
    async with session_scope() as db:
        org = await db.get(Organization, current.org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="org not found")

        # Refuse re-apply over a non-pending state. Pending means either fresh or
        # under review — both are safe to overwrite with a new submission body.
        if org.membership_status not in ("pending",):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"already {org.membership_status} — re-applying isn't supported. "
                    "Contact build@defendableos.com to update your details."
                ),
            )

        # Compute cap headroom at apply time. Re-checked at activation by the admin.
        active = await _active_count(db)
        waitlisted = active >= s.membership_cap

        org.membership_application = body.model_dump(exclude_none=True)
        org.membership_applied_at = datetime.now(timezone.utc)
        org.membership_status = "waitlisted" if waitlisted else "pending"
        await db.flush()

        queue = await _waitlist_position(db, org.id)

        # Best-effort email. Application is saved regardless of email outcome.
        await send_membership_application(
            applicant_email=current.email,
            org_name=org.name,
            org_slug=org.slug,
            company_name=body.company_name,
            intended_use=body.intended_use,
            referral_source=body.referral_source,
            waitlisted=waitlisted,
            queue_position=queue,
        )

        # active_count already counted before we modified anything; waitlisted
        # applications don't change active count.
        return _membership_payload(org, cap=s.membership_cap, active_count=active, queue=queue)
