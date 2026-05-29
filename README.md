# defendable-cloud-v2

**DefendableCloud** — hosted Proof of Execution for agentic work. The hosted proof vault.

> DefendableOS is the engine. DefendableCloud is the hosted proof vault.

Upload work → run checks → issue proof → store the artifact. One primitive: the **Defendable Run**
(`Inputs → Evidence → Execution → Checks → Verdict → Approval → Receipt`). Three lanes at launch —
Agent Work Receipts, Dataset Receipts, Compute Receipts. One button: **Generate Receipt**.

**Build law:** if a feature does not help *create, verify, approve, store, or share a Defendable Run*,
it does not go in v1.

## Monorepo

```
defendable-cloud-v2/
├── site/   Phase 1 · Astro marketing site → defendablecloud.com (CF Pages)
├── api/    Phase 2 · FastAPI backend (Runs/Checks/Receipts) → Fly.io  [live: api.defendablecloud.com]
└── app/    Phase 3 · React+Vite Vault portal → app.defendablecloud.com  [live: defendable-cloud-v2-app.pages.dev]
```

## app/ — the Vault portal (Phase 3, live)

React 18 + Vite + Tailwind SPA. Sign in (magic link) → dashboard → new run →
attach evidence → run checks → approve → **Generate Receipt** → share. Talks to
the API at `VITE_API_BASE` (default `https://api.defendablecloud.com`). Cloudflare
Pages headers live in `app/public/_headers`.

```bash
cd app
npm install
npm run dev      # http://localhost:5173
npm run build    # → app/dist  (deploy to CF Pages, SPA fallback via public/_redirects)
```

## site/ — marketing (Phase 1, live)

Astro + Tailwind, fully static. Same stack and design system as defendableos.com.
The site uses a pinned Node 22 build command because current patched Astro requires
Node 22. Cloudflare Pages should set `NODE_VERSION=22.12.0` or newer.

```bash
cd site
npm install
npm run dev      # http://localhost:4321
npm run build    # → site/dist
```

**Deploy (Cloudflare Pages):** root directory `site/`, build `npm run build`, output `site/dist`.
Contact form is a Pages Function (`site/functions/api/contact.ts`) → Resend → `build@defendableos.com`;
set `RESEND_API_KEY` as a project secret.

## Enterprise Guardrails

See `SECURITY.md`. Production API boot validates non-default JWT secrets, explicit
CORS, HTTPS URLs, email delivery, and dataset quota settings. Dataset downloads
are members-only, receipt-backed, short-lived, redacted on public proof views, and
capped by `DATASET_DOWNLOAD_DAILY_LIMIT`.

---

Swarm and Bee LLC · DBA Swarm & Bee AI · Florida · D-U-N-S 138652395
