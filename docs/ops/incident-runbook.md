# Incident Runbook

## Severity

- SEV-1: data exposure, unauthorized access, payment/webhook compromise, unavailable API.
- SEV-2: degraded auth, broken dataset downloads, failed receipt minting, delayed staging.
- SEV-3: marketing/app partial outage, non-critical UX regression.

## First 15 Minutes

1. Declare incident owner.
2. Freeze deploys unless rollback is the fix.
3. Capture affected routes, domains, orgs, and time window.
4. Preserve logs before rotation.
5. If credentials may be exposed, rotate first and analyze second.

## Containment

- Revoke exposed API keys.
- Rotate `JWT_SECRET` only with an active session invalidation plan.
- Rotate `INTERNAL_API_KEY`, `RUNNER_TOKEN`, Stripe webhook secret, and S3 credentials if operator paths are involved.
- Disable affected Cloudflare route or add temporary WAF rule.
- Pause dataset stager timer if storage integrity is uncertain.

## Evidence

Store a Defendable Run for the incident containing:

- timeline
- affected systems
- logs and receipts
- containment actions
- customer impact
- final verdict
- follow-up controls

## Communications

- Update `/status` for SEV-1 and SEV-2.
- Email affected customers directly when data, account access, or paid service is impacted.
- Publish post-incident notes after root cause is known.
