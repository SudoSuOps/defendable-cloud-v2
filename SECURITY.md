# DefendableCloud Security Posture

DefendableCloud is a proof and dataset access system. Production deploys must fail closed.

## Production Protocols

- Set `APP_ENV=production`.
- Set a unique `JWT_SECRET` with at least 32 random characters.
- Set `RESEND_API_KEY`; production never returns magic-link URLs inline.
- Set explicit `CORS_ORIGINS`; wildcard CORS is development-only.
- Use HTTPS `APP_BASE_URL` and `API_BASE_URL`.
- Set `CHECKOUT_RETURN_ORIGINS` for any approved preview domains.
- Keep `INTERNAL_API_KEY`, `RUNNER_TOKEN`, Stripe secrets, and S3 credentials in the deployment secret store.
- Keep private storage paths, LAN addresses, and operator hostnames out of public catalog snapshots.

## Dataset Access Controls

- Dataset catalog access requires active membership.
- Every dataset download request mints an immutable receipt.
- Download grants are capped by `DATASET_DOWNLOAD_DAILY_LIMIT` per email/principal over a rolling 24-hour window.
- Public receipt views redact storage keys and internal principal IDs.
- Signed download URLs are short-lived and rotate through `/share/{token}/download`.

## Public Surface Controls

- Cloudflare Pages ships `_headers` for HSTS, `nosniff`, frame denial, referrer policy, permissions policy, and CSP.
- Static marketing pages expose `/.well-known/security.txt`.
- API responses set baseline browser security headers.

## Operational Runbooks

- Cloudflare WAF/rate limits: `docs/cloudflare/waf-rate-limits.md`
- Incident response: `docs/ops/incident-runbook.md`
- Logging and alerts: `docs/ops/logging-alerting.md`
- Backup and restore drills: `docs/ops/backups-restore.md`
- Secrets rotation: `docs/ops/secrets-rotation.md`
- SSO/SAML/OIDC roadmap: `docs/ops/sso-saml-oidc.md`
- External security review plan: `docs/ops/external-security-review.md`
- SOC2-style control map: `docs/ops/soc2-control-map.md`

## Reporting

Report security issues to `build@defendableos.com`.
