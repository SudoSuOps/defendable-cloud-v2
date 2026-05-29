# External Security Review Plan

## Scope

- API auth, invites, RBAC, API keys, internal-key surfaces.
- Public receipt projection and dataset download grants.
- Cloudflare WAF/rate-limit configuration.
- Stripe checkout and webhook activation.
- Object storage access and signed URL flow.
- CI/dependency gates and production secret handling.

## Evidence Package

- Architecture diagram.
- Environment variable list with redacted values.
- API OpenAPI schema.
- Alembic migration history.
- Recent CI run.
- Security headers from production.
- WAF/rate-limit export.
- Backup/restore drill receipt.

## Frequency

- Before first regulated enterprise customer.
- After material auth/storage redesign.
- Annually after enterprise GA.
