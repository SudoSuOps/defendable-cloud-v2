import { Link } from "react-router-dom";
import { Button } from "../components/ui";
import { LANES } from "../lib/guidance";

function Wordmark() {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="DefendableCloud Vault">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
        <rect width="32" height="32" rx="6" fill="#0a0a0a" stroke="#e6ab2a" strokeWidth="1" />
        <g fill="none" stroke="#f6c64b" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 6h12l4 4v16H8z" />
          <path d="M12 12h8M12 16h10M12 20h6" strokeWidth="1.2" opacity="0.7" />
        </g>
      </svg>
      <span className="text-base font-semibold tracking-tight text-paper">
        DefendableCloud <span className="text-paper/40">Vault</span>
      </span>
    </Link>
  );
}

function LaneCard({ label, what, example }: { label: string; what: string; example: string }) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] p-5">
      <div className="font-mono text-xs uppercase tracking-widest text-honey-300/80">{label}</div>
      <p className="mt-2 text-sm leading-relaxed text-paper/70">{what}</p>
      <p className="mt-3 text-xs italic leading-relaxed text-paper/40">e.g. {example}</p>
    </div>
  );
}

function Step({ n, label }: { n: number; label: string }) {
  return (
    <li className="flex items-center gap-3 whitespace-nowrap">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-honey-400/30 bg-honey-300/[0.08] font-mono text-[10px] text-honey-200">
        {n}
      </span>
      <span className="text-sm text-paper/75">{label}</span>
    </li>
  );
}

export function Landing() {
  return (
    <div className="relative min-h-screen">
      <div className="absolute inset-0 brand-grid" aria-hidden="true" />
      <div className="relative">
        <header className="border-b border-white/5">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3.5">
            <Wordmark />
            <div className="flex items-center gap-5 text-sm">
              <Link to="/verify" className="text-paper/60 transition-colors hover:text-paper">
                Verify a receipt
              </Link>
              <a
                href="https://defendabledocs.com"
                target="_blank"
                rel="noreferrer"
                className="hidden text-paper/60 transition-colors hover:text-paper sm:inline"
              >
                Docs
              </a>
              <Link to="/login">
                <Button>Sign in</Button>
              </Link>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-5xl px-6 pt-14 pb-20">
          {/* Hero */}
          <section className="max-w-3xl">
            <p className="font-mono text-xs uppercase tracking-[0.35em] text-honey-300/80">
              DefendableCloud · the vault
            </p>
            <h1 className="mt-5 text-4xl font-semibold leading-tight tracking-tight text-paper sm:text-5xl">
              Proof of execution for agentic work.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-paper/65">
              Run the rulebook against your agent's work. Every check passes or raises a flag.
              Every receipt is hash-chained, shareable, and verifiable client-side. No judge model.
              No quality vibes. A human approves before anything mints.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link to="/login">
                <Button>Sign in to the vault</Button>
              </Link>
              <Link to="/verify">
                <Button variant="ghost">Verify a receipt</Button>
              </Link>
              <a
                href="https://defendabledocs.com"
                target="_blank"
                rel="noreferrer"
                className="text-sm text-paper/55 transition-colors hover:text-paper"
              >
                Read the docs →
              </a>
            </div>
          </section>

          {/* The one primitive */}
          <section className="mt-20">
            <p className="font-mono text-xs uppercase tracking-widest text-paper/40">The one primitive</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-paper">The Defendable Run</h2>
            <p className="mt-3 max-w-3xl text-sm leading-relaxed text-paper/60">
              Every receipt the vault mints follows the same seven stages. The lane changes. The
              rulebook changes. The shape does not.
            </p>
            <ol className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-3 rounded-xl border border-white/8 bg-white/[0.02] p-5">
              <Step n={1} label="Inputs" />
              <span className="text-paper/25" aria-hidden="true">→</span>
              <Step n={2} label="Evidence" />
              <span className="text-paper/25" aria-hidden="true">→</span>
              <Step n={3} label="Execution" />
              <span className="text-paper/25" aria-hidden="true">→</span>
              <Step n={4} label="Checks" />
              <span className="text-paper/25" aria-hidden="true">→</span>
              <Step n={5} label="Verdict" />
              <span className="text-paper/25" aria-hidden="true">→</span>
              <Step n={6} label="Approval" />
              <span className="text-paper/25" aria-hidden="true">→</span>
              <Step n={7} label="Receipt" />
            </ol>
          </section>

          {/* Three lanes */}
          <section className="mt-16">
            <p className="font-mono text-xs uppercase tracking-widest text-paper/40">Three lanes at launch</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-paper">
              Pick the kind of work you need to prove.
            </h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              {LANES.filter((l) => l.value !== "other").map((l) => (
                <LaneCard key={l.value} label={l.label} what={l.what} example={l.examples[0]} />
              ))}
            </div>
          </section>

          {/* Doctrine band */}
          <section className="mt-16 rounded-xl border border-honey-400/20 bg-honey-300/[0.04] px-6 py-7">
            <p className="font-mono text-xs uppercase tracking-widest text-honey-300/80">Doctrine</p>
            <ul className="mt-3 grid gap-2 text-sm leading-relaxed text-paper/80 sm:grid-cols-3">
              <li>The referee is a rulebook, not a judge.</li>
              <li>Agents earn their lanes.</li>
              <li>A human holds final authority.</li>
            </ul>
          </section>

          {/* CTA tail */}
          <section className="mt-16 flex flex-wrap items-center justify-between gap-4 border-t border-white/5 pt-10">
            <div>
              <p className="text-sm text-paper/60">
                Sign in to mint a receipt. Or verify one anyone has shared with you.
              </p>
              <p className="mt-1 font-mono text-xs uppercase tracking-widest text-honey-300/70">
                ring ring · to the shed
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/verify">
                <Button variant="ghost">Verify a receipt</Button>
              </Link>
              <Link to="/login">
                <Button>Sign in</Button>
              </Link>
            </div>
          </section>
        </main>

        <footer className="border-t border-white/5">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-6 text-xs text-paper/35">
            <span>Swarm and Bee LLC · DBA Swarm &amp; Bee AI · Florida</span>
            <span className="font-mono uppercase tracking-[0.35em] text-honey-300/40">
              // to the shed
            </span>
          </div>
        </footer>
      </div>
    </div>
  );
}
