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
from app.deps import Principal, get_current_user, require_internal
from app.email import send_membership_application
from app.models import Organization
from app.schemas import (
    Membership,
    MembershipApplicationIn,
    MembershipApplicationView,
    MembershipApproveIn,
    MembershipCheckoutIn,
    MembershipCheckoutOut,
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


@router.post("/approve", response_model=Membership, dependencies=[Depends(require_internal)])
async def approve_membership(body: MembershipApproveIn):
    """Admin endpoint · flip a pending application to `approved`.

    Gated by `INTERNAL_API_KEY` (`X-Internal-Key`) since the operator surface
    is the same one the rails-side stager uses — fail-closed without it.
    Once approved, the member can hit /membership/checkout to pay the
    annual $100 and land on `active`.

    Re-applies the cap check before approving — if the cap has filled
    between application and approval, the org goes to `waitlisted`.
    """
    s = settings()
    async with session_scope() as db:
        # Look up by slug for operator convenience (the email template
        # already pastes the slug into the approval SQL).
        org = (
            await db.execute(
                select(Organization).where(Organization.slug == body.org_slug)
            )
        ).scalar_one_or_none()
        if org is None:
            raise HTTPException(status_code=404, detail=f"org not found: {body.org_slug}")

        if org.membership_status == "active":
            # Re-approving an active org is a no-op; surface the current state.
            active = await _active_count(db)
            queue = await _waitlist_position(db, org.id)
            return _membership_payload(
                org, cap=s.membership_cap, active_count=active, queue=queue,
            )
        if org.membership_status not in ("pending", "waitlisted"):
            raise HTTPException(
                status_code=409,
                detail=f"can't approve from state: {org.membership_status}",
            )

        active = await _active_count(db)
        if active >= s.membership_cap:
            # Cap filled between application and approval. Hold them on the
            # waitlist; admin can re-run approve when a seat opens.
            org.membership_status = "waitlisted"
            await db.flush()
            queue = await _waitlist_position(db, org.id)
            return _membership_payload(
                org, cap=s.membership_cap, active_count=active, queue=queue,
            )

        org.membership_status = "approved"
        await db.flush()
        queue = await _waitlist_position(db, org.id)
        return _membership_payload(
            org, cap=s.membership_cap, active_count=active, queue=queue,
        )


@router.post(
    "/checkout", response_model=MembershipCheckoutOut, status_code=201,
)
async def create_checkout_session(
    body: MembershipCheckoutIn | None = None,
    current: Principal = Depends(get_current_user),
):
    """Create a Stripe Checkout Session for the $100/yr one-time payment.

    Only orgs in `approved` state can check out · this matches the doctrine
    locked 2026-05-28: apply → admin approves → pay → active. Already-active
    members get a 409 (no double-purchase). Pending/waitlisted get a 403 with
    the reason so the UI can route them.

    Returns the Stripe-hosted checkout URL; the frontend redirects there.
    Success / cancel routes back to /org via STRIPE_SUCCESS_PATH /
    STRIPE_CANCEL_PATH (defaults in config).
    """
    s = settings()
    if not (s.stripe_api_key and s.stripe_price_id):
        # Fail-closed — refuse rather than silently mis-configure.
        raise HTTPException(status_code=503, detail="stripe not configured")

    import stripe

    stripe.api_key = s.stripe_api_key

    async with session_scope() as db:
        org = await db.get(Organization, current.org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="org not found")

        if org.membership_status == "active":
            raise HTTPException(
                status_code=409, detail="already active — no further payment due",
            )
        if org.membership_status != "approved":
            raise HTTPException(
                status_code=403,
                detail=(
                    f"membership not yet approved (current: {org.membership_status}). "
                    "Apply via POST /membership/apply and wait for admin review."
                ),
            )

    # Build success/cancel URLs against the app, not the API. We honor
    # body.return_to_origin if the caller supplied it (defaults to the app
    # base URL) so the same backend can serve preview deploys.
    return_origin = (body and body.return_to_origin) or s.app_base_url
    return_origin = return_origin.rstrip("/")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",  # one-time, not subscription · doctrine 2026-05-28
            line_items=[{"price": s.stripe_price_id, "quantity": 1}],
            success_url=f"{return_origin}{s.stripe_success_path}",
            cancel_url=f"{return_origin}{s.stripe_cancel_path}",
            # Sealed into the session so the webhook can find the org without
            # a Stripe-side lookup.
            client_reference_id=current.org_id,
            metadata={"org_id": current.org_id, "org_slug": org.slug},
            customer_email=current.email or None,
            # Force collection of billing details for receipts; we don't keep
            # cards on file (one-time payment).
            payment_intent_data={"metadata": {"org_id": current.org_id}},
        )
    except stripe.error.StripeError as e:  # type: ignore[attr-defined]
        raise HTTPException(status_code=502, detail=f"stripe: {str(e)[:200]}")

    return {
        "url": session.url,
        "session_id": session.id,
        "expires_at": session.expires_at,
    }
