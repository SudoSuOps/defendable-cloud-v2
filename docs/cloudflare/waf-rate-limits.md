# Cloudflare WAF and Rate Limit Baseline

Use these rules in front of `defendablecloud.com`, `app.defendablecloud.com`, and `api.defendablecloud.com`.

## WAF Managed Rules

- Enable Cloudflare Managed Ruleset.
- Enable OWASP Core Ruleset, paranoia level 1 to start.
- Challenge traffic with bot score below the account baseline.
- Block known credential stuffing, scanner, and exploit categories.

## API Rate Limits

Apply to `api.defendablecloud.com`.

- `POST /auth/request`: 5 requests per email/IP per 10 minutes, then managed challenge.
- `POST /auth/verify`: 20 requests per IP per 10 minutes, then block for 1 hour.
- `POST /auth/accept-invite`: 20 requests per IP per 10 minutes, then block for 1 hour.
- `POST /datasets/catalog/*/download`: 60 requests per org/IP per hour at the edge. The API also enforces `DATASET_DOWNLOAD_DAILY_LIMIT`.
- `GET /share/*/download`: 120 requests per token/IP per hour, then challenge.
- `POST /stripe/webhook`: allow Stripe IP/ray validation where available; otherwise strict signature verification remains the source of truth.
- `/internal/*`: allow only private/operator egress IPs when deployed; API still requires `X-Internal-Key`.

## Cache and Bot Posture

- Cache static assets aggressively.
- Do not cache authenticated API responses.
- Do not cache `/share/*/download` redirects.
- Keep Cloudflare Bot Fight/managed challenge enabled for public marketing/contact forms.

## Review Cadence

Review WAF events weekly during launch and after every traffic spike.
