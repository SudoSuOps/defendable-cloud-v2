# Centralized Logging and Alerts

## Required Signals

- API request logs: method, route, status, latency, org/user id where available.
- Auth events: magic-link request, verify, invite accept, API key create/revoke.
- Admin events: membership approval, role update, invite create.
- Dataset events: catalog read, download grant, public download redirect, staging complete.
- Stripe events: checkout session created, webhook received, activation result.
- Storage events: failed head/get/put, staging upload failures.

## Alert Rules

- SEV-1: spike in 401/403 on auth routes, successful access from blocked geography, webhook signature failures, public receipt hash mismatch.
- SEV-2: dataset staging failures, download quota spikes, elevated 5xx, email delivery failures.
- SEV-3: build/deploy failures, sitemap/SEO regressions, degraded contact form.

## Destinations

- Provider logs for raw events.
- Long-retention object storage for security exports.
- Email or pager destination for SEV-1/SEV-2.
- Weekly review of auth, dataset grant, and WAF events during launch.
