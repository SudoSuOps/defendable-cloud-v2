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
├── api/    Phase 2 · FastAPI backend (Runs/Checks/Receipts) → Fly.io  [planned]
└── app/    Phase 3 · React+Vite Vault portal → app.defendablecloud.com  [planned]
```

## site/ — marketing (Phase 1, live)

Astro + Tailwind, fully static. Same stack and design system as defendableos.com.

```bash
cd site
npm install
npm run dev      # http://localhost:4321
npm run build    # → site/dist
```

**Deploy (Cloudflare Pages):** root directory `site/`, build `npm run build`, output `site/dist`.
Contact form is a Pages Function (`site/functions/api/contact.ts`) → Resend → `build@defendableos.com`;
set `RESEND_API_KEY` as a project secret.

---

Swarm and Bee LLC · DBA Swarm & Bee AI · Florida · D-U-N-S 138652395
