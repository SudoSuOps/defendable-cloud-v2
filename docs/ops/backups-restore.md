# Backups and Restore Tests

## Postgres

- Daily encrypted backups.
- Point-in-time recovery where the provider supports it.
- Monthly restore test into an isolated environment.
- Verify migrated schema, user/org counts, receipt counts, and latest org chains.

## Object Storage

- Versioning enabled where supported.
- Lifecycle policy for stale temporary objects.
- Monthly manifest sample: select recent receipt artifacts and dataset objects, verify SHA-256/ETag expectations.

## Restore Drill

1. Restore database backup to isolated DB.
2. Point a staging API at restored DB and staging bucket.
3. Run `/healthz`, `/ledger/verify`, and a sample `/share/{token}`.
4. Verify one dataset-download receipt and one run receipt PDF/JSON.
5. Record drill date, duration, and gaps in a Defendable Run.
