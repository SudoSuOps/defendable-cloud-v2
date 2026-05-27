# DefendableCloud API

Hosted Proof of Execution — the backend behind the **Defendable Run**.

`Inputs → Evidence → Execution → Checks → Verdict → Approval → Receipt`

FastAPI · async SQLAlchemy · Postgres · Tigris (S3) · magic-link auth (JWT) ·
deterministic check engine · hash-chained receipts (JSON + PDF). Modeled on
`defendable-api-fly-tigris`; deploys to Fly.io.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | service + db + storage health |
| POST | `/auth/request` | email → magic link (Resend) |
| POST | `/auth/verify` | one-time token → JWT |
| GET | `/auth/me` | current user |
| POST/GET | `/projects` | create / list projects |
| POST/GET | `/runs`, `/runs/{id}` | create / list / read runs |
| POST | `/runs/{id}/evidence` | attach note/url/output evidence |
| POST | `/runs/{id}/evidence/upload` | attach a file (→ Tigris, sha256) |
| POST | `/runs/{id}/checks` | run the verification engine → verdict |
| POST | `/runs/{id}/approve` | human approve / reject |
| POST | `/runs/{id}/receipt` | issue the hash-chained receipt |
| GET | `/share/{token}` | public receipt JSON (verifies hash) |
| GET | `/share/{token}/pdf` | public receipt PDF |
| GET | `/ledger/verify` | walk + verify the org's receipt chain |

## Run locally

```bash
cd api
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Postgres (docker): defendable/defendable on :5432, db defendable_cloud
cp .env.example .env            # fill DATABASE_URL etc.
alembic upgrade head
uvicorn app.main:app --reload --port 8080

pytest                          # pure-logic tests (no DB needed)
```

With `RESEND_API_KEY` unset, `/auth/request` returns a `dev_link` in the
response so you can log in without sending email.

## Deploy (Fly.io)

```bash
fly apps create defendable-cloud-api
fly postgres create --name defendable-cloud-db   # then attach
fly secrets set DATABASE_URL=... AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \
                JWT_SECRET=$(openssl rand -hex 32) RESEND_API_KEY=re_...
fly deploy
```

Tigris bucket: `defendable-cloud`. Custom domain: `api.defendablecloud.com`.
PDFs are regenerated deterministically from the stored payload, so serving
works even before object storage is wired.

## Design law

If a feature does not help **create, verify, approve, store, or share a
Defendable Run**, it does not go in v1. Checks are deterministic on purpose —
a receipt is only as defensible as the checks behind it.
