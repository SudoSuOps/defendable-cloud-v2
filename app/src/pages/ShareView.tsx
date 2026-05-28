import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiBase } from "../lib/api";
import { Badge, Button, Card, ErrorNote, Spinner } from "../components/ui";
import { PinnedModelBlock } from "../components/PinnedModelBlock";

interface PublicReceipt {
  receipt_id: string;
  org_seq: number;
  parent_hash: string;
  receipt_sha256: string;
  verified: boolean;
  created_at: string;
  payload: any;
}

// Phase 9 · three risk tiers — game-changers surfaced first.
function tierOf(sev: string | null): "high" | "mid" | "low" {
  const s = (sev || "").toLowerCase();
  if (s === "high" || s === "critical" || s === "propolis") return "high";
  if (s === "low" || s === "honey" || s === "minor") return "low";
  return "mid";
}
const TIER_TONE: Record<string, string> = {
  high: "border-red-400/40 bg-red-400/10 text-red-300",
  mid: "border-amber-400/40 bg-amber-400/10 text-amber-300",
  low: "border-sky-400/30 bg-sky-400/10 text-sky-300",
};
const SEV_TONE: Record<string, string> = {
  honey: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  jelly: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  propolis: "border-red-400/30 bg-red-400/10 text-red-300",
};
const TIER_LABEL: Record<string, string> = { high: "HIGH-RISK", mid: "mid-risk", low: "low-risk" };
const TIER_RANK: Record<string, number> = { high: 0, mid: 1, low: 2 };
const STATUS_RANK: Record<string, number> = { flag: 0, fail: 0, open: 1, pass: 2, risk: 2, review: 3, skip: 4 };
const isFlag = (s: string) => s === "flag" || s === "fail";
// defects in the WORK are fixable; findings about the DEAL (policy gates) are not a rework.
const DEFECT_CATS = new Set(["math", "schema", "structure", "evidence"]);

export function ShareView() {
  const { token } = useParams();
  const [r, setR] = useState<PublicReceipt | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<PublicReceipt>(`/share/${token}`, { auth: false })
      .then(setR)
      .catch((e) => setErr(e.message));
  }, [token]);

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/5">
        <div className="mx-auto flex max-w-3xl items-center gap-2.5 px-6 py-3.5">
          <svg viewBox="0 0 32 32" className="h-6 w-6" aria-hidden="true">
            <rect width="32" height="32" rx="6" fill="#0a0a0a" stroke="#e6ab2a" strokeWidth="1" />
            <g fill="none" stroke="#f6c64b" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8 6h12l4 4v16H8z" />
              <path d="M12 12h8M12 16h10M12 20h6" strokeWidth="1.2" opacity="0.7" />
            </g>
          </svg>
          <span className="text-sm font-semibold tracking-tight text-paper">DefendableCloud</span>
          <span className="text-sm text-paper/40">Proof of Execution</span>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-10">
        {err && <ErrorNote>{err}</ErrorNote>}
        {!r && !err && <Spinner label="Verifying receipt…" />}
        {r && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-mono text-sm text-honey-300/80">{r.receipt_id}</p>
                <h1 className="mt-1 text-2xl font-semibold tracking-tight text-paper">{r.payload?.run?.title}</h1>
                <p className="mt-1 text-xs text-paper/40">{new Date(r.created_at).toLocaleString()}</p>
              </div>
              <span
                className={`rounded-md border px-3 py-1 text-sm font-medium ${
                  r.verified
                    ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                    : "border-red-400/30 bg-red-400/10 text-red-300"
                }`}
              >
                {r.verified ? "✓ Hash verified" : "✗ Hash mismatch"}
              </span>
            </div>

            {r.payload?.cook && (
              <Card className="mt-6" title="Fine-tune lift" subtitle="Eval before → eval after on the same harness">
                <CookSummary cook={r.payload.cook} />
              </Card>
            )}

            {r.payload?.pinned_model && <PinnedModelBlock pin={r.payload.pinned_model} className="mt-6" />}

            {r.payload?.verdict && (() => {
              const v = r.payload?.verdict || {};
              const items = [...(r.payload?.findings || r.payload?.checks || [])].sort(
                (a: any, b: any) =>
                  (STATUS_RANK[a.status] ?? 5) - (STATUS_RANK[b.status] ?? 5) ||
                  TIER_RANK[tierOf(a.severity)] - TIER_RANK[tierOf(b.severity)],
              );
              const flags = items.filter((c: any) => isFlag(c.status));
              const tierCount = (t: string) => flags.filter((c: any) => tierOf(c.severity) === t).length;
              const defects = flags.filter((c: any) => DEFECT_CATS.has(c.category)).length;
              const findings = flags.length - defects;
              const fixability = flags.length === 0 ? "" :
                findings === 0 ? `Fixable — ${defects} defect${defects > 1 ? "s" : ""} in the work. Correct and resubmit; the same rules re-run.`
                : defects === 0 ? "Not a rework — these are true findings about the deal. The work is correct; the rule returns no."
                : `Partly fixable — ${defects} work-defect${defects > 1 ? "s" : ""} to correct; ${findings} finding${findings > 1 ? "s" : ""} about the deal itself.`;
              return (
                <>
                  <Card className="mt-6" title="Verdict">
                    <div className="flex flex-wrap items-center gap-3">
                      {v.severity && <span className={`rounded-md border px-2.5 py-1 text-sm font-semibold uppercase ${SEV_TONE[v.severity] || ""}`}>{v.severity}</span>}
                      <Badge value={v.outcome} />
                      {typeof v.score_100 === "number" && <span className="font-mono text-sm text-paper/60">{v.score_100}/100</span>}
                      {v.client_ready && <span className="text-sm text-paper/45">· client-ready: {v.client_ready}</span>}
                    </div>
                    {flags.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(["high", "mid", "low"] as const).map((t) => (
                          <span key={t} className={`rounded-md border px-2 py-0.5 font-mono text-xs ${tierCount(t) ? TIER_TONE[t] : "border-white/10 text-paper/25"}`}>
                            {tierCount(t)} {TIER_LABEL[t]}
                          </span>
                        ))}
                      </div>
                    )}
                    {v.summary && <p className="mt-3 text-sm text-paper/70">{v.summary}</p>}
                    {fixability && <p className="mt-2 text-sm text-paper/75"><span className="uppercase tracking-widest text-paper/35 text-xs">Is it fixable</span> · {fixability}</p>}
                    {v.recommended_action && <p className="mt-2 text-sm text-paper/60"><span className="uppercase tracking-widest text-paper/35 text-xs">Recommended</span> · {v.recommended_action}</p>}
                  </Card>

                  <Card className="mt-6" title="Referee findings">
                    <ul className="space-y-1.5 font-mono text-xs">
                      {items.map((c: any, i: number) => (
                        <li key={c.check_key || i} className="flex flex-wrap items-center gap-2">
                          <Badge value={c.status} />
                          {isFlag(c.status) && <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase ${TIER_TONE[tierOf(c.severity)]}`}>{TIER_LABEL[tierOf(c.severity)]}</span>}
                          <span className="text-paper/70">{c.label} <span className="text-paper/35">({c.category})</span> — {c.detail}</span>
                        </li>
                      ))}
                    </ul>
                  </Card>
                </>
              );
            })()}

            {r.payload?.agent_profile && (() => {
              const ap = r.payload.agent_profile;
              const rows: [string, string | null][] = [
                ["Harness — the body", ap.harness ? `${ap.harness}${ap.harness_version ? ` v${ap.harness_version}` : ""}` : null],
                ["Model — the brain", ap.model ? `${ap.model}${ap.model_provider ? ` · ${ap.model_provider}` : ""}${ap.served_by ? ` · ${ap.served_by}` : ""}` : null],
                ["Runtime — the ground", [ap.runtime_host, ap.runtime_hardware, ap.runtime_os].filter(Boolean).join(" · ") || null],
                ["Tools — the hands", ap.tools?.length ? ap.tools.join(", ") : null],
              ];
              return (
                <Card className="mt-6" title="Agent profile" actions={ap.capability_tier && <span className="rounded-md border border-white/15 px-2.5 py-1 text-xs font-semibold uppercase text-paper/70">{ap.capability_tier} tier</span>}>
                  <div className="mb-3 text-base font-semibold text-paper">{ap.name}</div>
                  <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
                    {rows.filter(([, v]) => v).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">{k}</dt><dd className="text-right font-mono text-xs text-paper/80">{v}</dd></div>
                    ))}
                  </dl>
                </Card>
              );
            })()}

            {(r.payload?.evidence || []).length > 0 && (
              <Card className="mt-6" title="Evidence">
                <ul className="space-y-1.5 text-sm">
                  {r.payload.evidence.map((e: any, i: number) => (
                    <li key={i} className="flex items-center gap-2">
                      <span className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 font-mono text-[10px] uppercase text-paper/50">{e.kind}</span>
                      <span className="text-paper/80">{e.label}</span>
                      {e.sha256 && <span className="font-mono text-[10px] text-paper/30">{String(e.sha256).slice(0, 12)}…</span>}
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            {r.payload?.approval && (
              <Card className="mt-6" title="Approval">
                <div className="flex items-center gap-3 text-sm">
                  <Badge value={r.payload?.approval?.decision} />
                  <span className="text-paper/60">{r.payload?.approval?.approver}</span>
                </div>
              </Card>
            )}

            <Card className="mt-6" title="Integrity">
              <dl className="space-y-2 font-mono text-xs">
                <div className="flex gap-3"><dt className="w-32 shrink-0 text-paper/40">receipt_sha256</dt><dd className="break-all text-paper/70">{r.receipt_sha256}</dd></div>
                <div className="flex gap-3"><dt className="w-32 shrink-0 text-paper/40">parent_hash</dt><dd className="break-all text-paper/70">{r.parent_hash}</dd></div>
                <div className="flex gap-3"><dt className="w-32 shrink-0 text-paper/40">org_seq</dt><dd className="text-paper/70">{r.org_seq}</dd></div>
              </dl>
              <div className="mt-5 flex gap-3">
                <a href={`${apiBase}/share/${token}/pdf`} target="_blank" rel="noreferrer"><Button variant="ghost">Download PDF</Button></a>
                <a href={`${apiBase}/share/${token}`} target="_blank" rel="noreferrer"><Button variant="ghost">JSON</Button></a>
              </div>
            </Card>
          </>
        )}
      </main>
      <footer className="mx-auto max-w-3xl px-6 py-8 text-center font-mono text-xs uppercase tracking-[0.35em] text-honey-300/40">
        // to the shed
      </footer>
    </div>
  );
}

function CookSummary({ cook }: { cook: any }) {
  const pct = (v: any) => (typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "—");
  const lift = cook?.lift;
  const liftTone =
    typeof lift === "number" && lift >= 0
      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
      : "border-red-400/30 bg-red-400/10 text-red-300";
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-lg font-semibold text-paper">
          {pct(cook.eval_before)} <span className="text-paper/40">→</span> {pct(cook.eval_after)}
        </span>
        <span className={`rounded-md border px-2 py-0.5 font-mono text-xs ${liftTone}`}>
          {typeof lift === "number" ? `${lift >= 0 ? "+" : ""}${(lift * 100).toFixed(1)}%` : "—"}
        </span>
      </div>
      <dl className="mt-4 grid gap-x-8 gap-y-1 font-mono text-xs sm:grid-cols-2">
        <KV k="base_model" v={cook.base_model || "—"} />
        <KV k="dataset" v={cook.dataset || "—"} />
        <KV k="pairs" v={typeof cook.pairs === "number" ? cook.pairs.toLocaleString() : "—"} />
        {cook.runner && <KV k="runner" v={cook.runner} />}
        {cook.compute_usd != null && <KV k="compute_usd" v={`$${cook.compute_usd}`} />}
      </dl>
    </>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-white/5 py-1">
      <dt className="text-paper/45">{k}</dt>
      <dd className="text-right text-paper/85">{v}</dd>
    </div>
  );
}
