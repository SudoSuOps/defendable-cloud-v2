"""/stripe/webhook — Stripe → us · activates membership on successful payment.

Listens for `checkout.session.completed`. Signature-verified via the
`Stripe-Signature` header against STRIPE_WEBHOOK_SECRET. The session's
`client_reference_id` is set to the org_id when we create the session, so
we look the org up directly without any Stripe-side query.

Idempotency:
  - The session's payment_intent_id is unique per cycle; we record it on
    the Organization (stripe_payment_intent_id is a UNIQUE column). A
    duplicate webhook delivery either finds the row already advanced
    (returns 200 no-op) or hits the unique constraint on the INSERT and
    gracefully no-ops.

Cap enforcement:
  - We re-check the active count INSIDE the activation transaction. If the
    cap filled while the user was on the Stripe-hosted page, we land them
    in `waitlisted` and NOT flip to `active` — the operator can refund
    out-of-band (rare race · 100-seat cap is generous).

Email:
  - Best-effort welcome via Resend (reuses the existing send helpers).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import func, select

from app.config import settings
from app.db import session_scope
from app.models import Organization

router = APIRouter(prefix="/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    s = settings()
    if not (s.stripe_api_key and s.stripe_webhook_secret):
        # Fail-closed — same posture as /internal/*.
        raise HTTPException(status_code=503, detail="stripe webhook not configured")

    import stripe

    stripe.api_key = s.stripe_api_key

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="missing Stripe-Signature header")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=s.stripe_webhook_secret,
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:  # type: ignore[attr-defined]
        # 400 keeps Stripe retrying with backoff (correct behavior for the
        # rare body-truncation case); never auto-200 on invalid signature.
        raise HTTPException(status_code=400, detail=f"invalid signature: {e}")

    event_type = event.get("type")
    if event_type != "checkout.session.completed":
        # We only care about one event for v1. Return 200 so Stripe doesn't
        # retry for events we explicitly chose not to handle.
        return {"received": True, "ignored_type": event_type}

    session = (event.get("data") or {}).get("object") or {}
    org_id = session.get("client_reference_id")
    payment_intent_id = session.get("payment_intent")
    customer_id = session.get("customer")
    payment_status = session.get("payment_status")

    if not org_id:
        raise HTTPException(
            status_code=400, detail="checkout.session missing client_reference_id"
        )
    if payment_status not in ("paid", "no_payment_required"):
        # Don't activate on unpaid sessions (shouldn't happen for mode=payment,
        # but defense-in-depth).
        return {"received": True, "ignored_payment_status": payment_status}

    activated = False
    waitlisted_due_to_race = False

    async with session_scope() as db:
        org = await db.get(Organization, org_id)
        if org is None:
            # Don't 500 · log and ack so Stripe doesn't retry forever for a
            # missing org. (Possible if the org was deleted post-checkout.)
            return {"received": True, "ignored_unknown_org": org_id}

        # Idempotency · if this PI is already recorded, it's a duplicate
        # delivery. No-op.
        if payment_intent_id and org.stripe_payment_intent_id == payment_intent_id:
            return {"received": True, "idempotent": True, "org_id": org_id}

        # Re-check cap inside the activation transaction.
        active_count = (
            await db.execute(
                select(func.count(Organization.id)).where(
                    Organization.membership_status == "active"
                )
            )
        ).scalar_one()

        if active_count >= s.membership_cap:
            # Cap filled during the user's Stripe session. Hold them on
            # waitlist; an operator handles the refund out-of-band. The
            # PI is still recorded so a duplicate delivery is a no-op.
            org.membership_status = "waitlisted"
            org.stripe_payment_intent_id = payment_intent_id
            if customer_id and not org.stripe_customer_id:
                org.stripe_customer_id = customer_id
            await db.flush()
            waitlisted_due_to_race = True
        else:
            # Assign the next seat number deterministically.
            max_seat = (
                await db.execute(
                    select(func.coalesce(func.max(Organization.membership_seat_number), 0)).where(
                        Organization.membership_status == "active"
                    )
                )
            ).scalar_one()

            now = datetime.now(timezone.utc)
            org.membership_status = "active"
            org.membership_activated_at = now
            org.membership_seat_number = int(max_seat) + 1
            # One-year cycle · matches the one-time annual doctrine. Manual
            # renewal at lapse.
            org.membership_renewal_at = now + timedelta(days=365)
            org.stripe_payment_intent_id = payment_intent_id
            if customer_id and not org.stripe_customer_id:
                org.stripe_customer_id = customer_id
            await db.flush()
            activated = True

    if activated:
        # Best-effort welcome email · doesn't block the webhook ack.
        try:
            from app import email as email_helpers

            await email_helpers.send_membership_activated(
                to_email=session.get("customer_details", {}).get("email")
                or session.get("customer_email")
                or "",
                org_slug=(await _slug_for(org_id)) or "—",
                seat_number=(await _seat_for(org_id)) or 0,
            )
        except Exception:
            # Activation already committed; email is non-blocking.
            pass

    return {
        "received": True,
        "activated": activated,
        "waitlisted_due_to_cap_race": waitlisted_due_to_race,
        "org_id": org_id,
    }


async def _slug_for(org_id: str) -> str | None:
    async with session_scope() as db:
        org = await db.get(Organization, org_id)
        return org.slug if org else None


async def _seat_for(org_id: str) -> int | None:
    async with session_scope() as db:
        org = await db.get(Organization, org_id)
        return org.membership_seat_number if org else None
