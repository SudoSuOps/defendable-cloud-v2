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
