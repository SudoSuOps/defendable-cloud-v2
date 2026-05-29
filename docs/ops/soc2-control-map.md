# SOC2-Style Control Map

This is not a SOC2 report. It is the control map DefendableCloud operates toward.

## Security

- Production boot checks for auth, CORS, HTTPS, email, and quotas.
- API keys hashed at rest.
- Magic-link tokens hashed at rest and one-time use.
- Owner/member RBAC for org management.
- Cloudflare WAF and rate-limit baseline.

## Availability

- Health endpoint.
- Static marketing/app deploys on Cloudflare Pages.
- Database and object storage restore drill defined.
- Status page and incident runbook.

## Confidentiality

- Public receipt projection redacts storage keys and principal IDs.
- Private staging paths omitted from public catalogs.
- Internal surfaces gated by shared key and deploy allowlists.

## Processing Integrity

- Hash-chained receipts.
- Per-org ledger verification.
- Dataset grants sealed into immutable receipts.
- CI build/test/audit gates.

## Privacy

- Privacy policy and DPA placeholders are published.
- Data minimization for public receipt views.
- Contact path for security/privacy requests.
