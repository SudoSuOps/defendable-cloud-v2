import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiBase } from "../lib/api";
import { Badge, Button, Card, ErrorNote, Spinner } from "../components/ui";

interface PublicReceipt {
  receipt_id: string;
  org_seq: number;
  parent_hash: string;
  receipt_sha256: string;
  verified: boolean;
  created_at: string;
  payload: any;
}

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

            <Card className="mt-6" title="Verdict">
              <div className="flex items-center gap-3">
                <Badge value={r.payload?.verdict?.outcome} />
                <span className="text-sm text-paper/70">{r.payload?.verdict?.summary}</span>
              </div>
            </Card>

            <Card className="mt-6" title="Checks">
              <ul className="space-y-1.5 font-mono text-xs">
                {(r.payload?.checks || []).map((c: any) => (
                  <li key={c.check_key} className="flex gap-2">
                    <Badge value={c.status} />
                    <span className="text-paper/70">{c.label} <span className="text-paper/35">({c.category})</span> — {c.detail}</span>
                  </li>
                ))}
              </ul>
            </Card>

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

            <Card className="mt-6" title="Approval">
              <div className="flex items-center gap-3 text-sm">
                <Badge value={r.payload?.approval?.decision} />
                <span className="text-paper/60">{r.payload?.approval?.approver}</span>
              </div>
            </Card>

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
