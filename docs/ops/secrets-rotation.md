# Secrets Rotation Protocol

## Rotate Immediately

- suspected leak
- employee/operator offboarding
- failed secret scan
- public repo exposure
- provider incident

## Rotation Order

1. Add new secret in deployment provider.
2. Deploy/readiness check.
3. Revoke old secret.
4. Verify logs for failed old-secret attempts.
5. Record the rotation receipt.

## Secrets

- `JWT_SECRET`: rotate with planned session invalidation.
- `INTERNAL_API_KEY`: rotate API and stager together.
- `RUNNER_TOKEN`: rotate API and runner together.
- `STRIPE_WEBHOOK_SECRET`: update Stripe endpoint and API secret.
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: create new scoped key, deploy, revoke old key.
- `RESEND_API_KEY`: replace in app/site/API providers.

Never store live secrets in repo docs, shell history, issue trackers, or screenshots.
