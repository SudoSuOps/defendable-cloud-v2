from __future__ import annotations

import httpx

from app.config import settings


async def send_magic_link(to_email: str, link: str) -> bool:
    """Send the one-time sign-in link via Resend. Returns True if accepted.

    In dev (no RESEND_API_KEY), returns False so the caller can surface the
    link directly instead of silently dropping it.
    """
    s = settings()
    if not s.resend_api_key:
        return False

    subject = "Your DefendableCloud sign-in link"
    html = (
        '<div style="font-family:ui-sans-serif,system-ui,Segoe UI,Roboto,Arial,sans-serif;'
        'max-width:480px;color:#1c1917;line-height:1.55">'
        '<p style="font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:#a87f33;'
        'font-weight:600;margin:0 0 8px">DefendableCloud</p>'
        '<p style="font-size:16px;font-weight:600;margin:0 0 12px">Sign in to your vault</p>'
        '<p style="margin:0 0 18px">Click the button below to sign in. This link expires shortly '
        "and can be used once.</p>"
        f'<p style="margin:0 0 18px"><a href="{link}" '
        'style="display:inline-block;background:#f6c64b;color:#0a0a0a;text-decoration:none;'
        'font-weight:600;padding:11px 22px;border-radius:6px">Sign in to DefendableCloud</a></p>'
        f'<p style="font-size:12px;color:#78716c;margin:0">Or paste this link: {link}</p>'
        '<p style="font-size:12px;color:#78716c;margin:18px 0 0">If you didn\'t request this, '
        "ignore this email.</p></div>"
    )
    text = f"Sign in to DefendableCloud:\n\n{link}\n\nThis link expires shortly and can be used once."

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {s.resend_api_key}"},
                json={
                    "from": s.email_from,
                    "to": [to_email],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
            )
            return r.status_code < 300
    except Exception:
        return False


async def send_dataset_ready(
    *,
    to_email: str,
    package_name: str,
    package_slug: str,
    pairs: int,
    share_url: str,
    download_url: str,
    expires_at: str,
) -> bool:
    """Notify a member that a dataset they requested is now staged in Tigris.

    Sent by /internal/stage-complete when the rails-side stager finishes
    uploading a package the member previously had a `ready=False` grant on.
    The share_url is the durable handle; download_url is the convenience
    redirect that rotates the underlying signed URL on each access.
    """
    s = settings()
    if not s.resend_api_key:
        return False

    subject = f"Your dataset is ready · {package_name}"
    html = (
        '<div style="font-family:ui-sans-serif,system-ui,Segoe UI,Roboto,Arial,sans-serif;'
        'max-width:520px;color:#1c1917;line-height:1.55">'
        '<p style="font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:#a87f33;'
        'font-weight:600;margin:0 0 8px">DefendableCloud · members-only library</p>'
        f'<p style="font-size:18px;font-weight:600;margin:0 0 12px">{package_name} is staged.</p>'
        '<p style="margin:0 0 16px">The file you requested is now in the download bucket. '
        f"Your grant is valid until <strong>{expires_at}</strong>.</p>"
        '<table style="border-collapse:collapse;margin:0 0 18px;font-size:14px;color:#44403c">'
        f'<tr><td style="padding:4px 12px 4px 0">slug</td><td style="font-family:ui-monospace,monospace">{package_slug}</td></tr>'
        f'<tr><td style="padding:4px 12px 4px 0">pairs</td><td>{pairs:,}</td></tr>'
        "</table>"
        f'<p style="margin:0 0 18px"><a href="{download_url}" '
        'style="display:inline-block;background:#f6c64b;color:#0a0a0a;text-decoration:none;'
        'font-weight:600;padding:11px 22px;border-radius:6px">Download now</a></p>'
        f'<p style="font-size:12px;color:#78716c;margin:0">Or paste this link: {download_url}</p>'
        f'<p style="font-size:12px;color:#78716c;margin:12px 0 0">Share + receipt (books-and-records): <a href="{share_url}">{share_url}</a></p>'
        '<p style="font-size:12px;color:#78716c;margin:18px 0 0">'
        "Datasets are free with membership. Compute is the meter. — Mr. Defendable"
        "</p></div>"
    )
    text = (
        f"{package_name} is staged ({package_slug}, {pairs:,} pairs).\n"
        f"Valid until: {expires_at}\n\n"
        f"Download: {download_url}\n"
        f"Receipt:  {share_url}\n\n"
        "Datasets are free with membership. Compute is the meter."
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {s.resend_api_key}"},
                json={
                    "from": s.email_from,
                    "to": [to_email],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
            )
            return r.status_code < 300
    except Exception:
        return False


async def send_membership_application(
    *,
    applicant_email: str,
    org_name: str,
    org_slug: str,
    company_name: str,
    intended_use: str | None,
    referral_source: str | None,
    waitlisted: bool,
    queue_position: int | None,
) -> bool:
    """Email the review inbox (settings.membership_review_email) when a new
    application lands. Plain-text body so it's easy to read in any client;
    subject is grep-able for the operator's inbox triage. Returns True if
    Resend accepted; the application is saved regardless.
    """
    s = settings()
    if not s.resend_api_key:
        return False

    queue_line = (
        f"WAITLISTED — queue position #{queue_position}.\n"
        if waitlisted and queue_position is not None
        else "Open for approval.\n"
    )

    subject = f"Membership application · {company_name} · {applicant_email}"
    text = (
        "DefendableCloud · new membership application\n"
        "------------------------------------------\n\n"
        f"Email          : {applicant_email}\n"
        f"Org name       : {org_name}\n"
        f"Org slug       : {org_slug}\n"
        f"Company        : {company_name}\n"
        f"Intended use   : {intended_use or '—'}\n"
        f"Referral source: {referral_source or '—'}\n\n"
        f"Status         : {queue_line}"
        "\nApprove via direct SQL (admin endpoint lands later):\n\n"
        "  UPDATE organizations SET membership_status='active', "
        "membership_activated_at=NOW(), "
        "membership_seat_number=("
        "SELECT COALESCE(MAX(membership_seat_number),0)+1 FROM organizations "
        "WHERE membership_status='active') "
        f"WHERE slug='{org_slug}';\n\n"
        "To the shed."
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {s.resend_api_key}"},
                json={
                    "from": s.email_from,
                    "to": [s.membership_review_email],
                    "reply_to": applicant_email,
                    "subject": subject,
                    "text": text,
                },
            )
            return r.status_code < 300
    except Exception:
        return False
