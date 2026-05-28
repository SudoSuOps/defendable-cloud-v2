import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Card, ErrorNote, Spinner } from "../components/ui";

interface TrainingDataPolicy {
  version: string;
  statement: string;
  we_learn_from: string[];
  we_dont_learn_from: string[];
  enforcement: string[];
  effective_at: string;
  last_updated: string;
  sha256: string;
}

function Wordmark() {
  return (
    <Link to="/" className="flex items-center justify-center gap-2.5" aria-label="DefendableCloud Vault">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
        <rect width="32" height="32" rx="6" fill="#0a0a0a" stroke="#e6ab2a" strokeWidth="1" />
        <g fill="none" stroke="#f6c64b" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 6h12l4 4v16H8z" />
          <path d="M12 12h8M12 16h10M12 20h6" strokeWidth="1.2" opacity="0.7" />
        </g>
      </svg>
      <span className="text-lg font-semibold tracking-tight text-paper">
        DefendableCloud <span className="text-paper/40">Vault</span>
      </span>
    </Link>
  );
}

export function TrainingDataPolicy() {
  const [policy, setPolicy] = useState<TrainingDataPolicy | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<TrainingDataPolicy>("/policy/training-data", { auth: false })
      .then(setPolicy)
      .catch((e) => setErr(e.message || String(e)));
  }, []);

  return (
    <div className="relative min-h-screen px-6 py-12">
      <div className="absolute inset-0 brand-grid" aria-hidden="true" />
      <div className="relative mx-auto max-w-3xl">
        <Wordmark />

        <div className="mt-10">
          <p className="font-mono text-xs uppercase tracking-[0.35em] text-honey-300/80">
            Policy · training data
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-paper">
            What enters and never enters our training corpus.
          </h1>
        </div>

        {err && (
          <div className="mt-6">
            <ErrorNote>{err}</ErrorNote>
          </div>
        )}
        {!policy && !err && (
          <div className="mt-6">
            <Spinner label="Loading policy…" />
          </div>
        )}

        {policy && (
          <>
            {/* Statement — the doctrine */}
            <Card
              className="mt-8 border-honey-400/40"
              title="The doctrine"
              subtitle={`Effective ${new Date(policy.effective_at).toLocaleDateString()} · ${policy.version}`}
            >
              <p className="text-base leading-relaxed text-paper/85">{policy.statement}</p>
            </Card>

            {/* Categorical tables */}
            <div className="mt-6 grid gap-6 sm:grid-cols-2">
              <Card title="We learn from" subtitle="Allowed inputs to the corpus">
                <ul className="space-y-2 text-sm leading-relaxed text-paper/75">
                  {policy.we_learn_from.map((item, i) => (
                    <li key={i} className="flex gap-2.5">
                      <span aria-hidden="true" className="mt-1 text-emerald-300/70">✓</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </Card>
              <Card
                className="border-honey-400/20"
                title="We never learn from"
                subtitle="The customer-data gate"
              >
                <ul className="space-y-2 text-sm leading-relaxed text-paper/75">
                  {policy.we_dont_learn_from.map((item, i) => (
                    <li key={i} className="flex gap-2.5">
                      <span aria-hidden="true" className="mt-1 text-red-300/70">✗</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </div>

            {/* Enforcement */}
            <Card className="mt-6" title="How we enforce it" subtitle="The code lock, not the promise">
              <ol className="space-y-3 text-sm leading-relaxed text-paper/75">
                {policy.enforcement.map((item, i) => (
                  <li key={i} className="flex gap-3">
                    <span
                      aria-hidden="true"
                      className="font-mono text-xs text-honey-300/70 mt-0.5 shrink-0 w-5"
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ol>
            </Card>

            {/* Hash receipt */}
            <Card
              className="mt-6"
              title="Policy receipt"
              subtitle="Anyone can recompute this hash from the policy body"
            >
              <dl className="grid gap-x-8 gap-y-2 font-mono text-xs">
                <div className="flex flex-wrap justify-between gap-2">
                  <dt className="text-paper/45">version</dt>
                  <dd className="text-paper/85">{policy.version}</dd>
                </div>
                <div className="flex flex-wrap justify-between gap-2">
                  <dt className="text-paper/45">effective_at</dt>
                  <dd className="text-paper/85">{policy.effective_at}</dd>
                </div>
                <div className="flex flex-wrap justify-between gap-2">
                  <dt className="text-paper/45">last_updated</dt>
                  <dd className="text-paper/85">{policy.last_updated}</dd>
                </div>
                <div className="flex flex-wrap justify-between gap-2">
                  <dt className="text-paper/45 shrink-0">sha256</dt>
                  <dd className="break-all text-paper/85">{policy.sha256}</dd>
                </div>
              </dl>
            </Card>
          </>
        )}

        <p className="mt-10 text-center text-xs text-paper/30">
          <Link to="/" className="text-honey-300/60 hover:text-honey-200">
            ← back to DefendableCloud
          </Link>{" "}
          · to the shed
        </p>
      </div>
    </div>
  );
}
