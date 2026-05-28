import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button, Card, ErrorNote, Spinner } from "../components/ui";
import { RecentReceipts } from "../components/RecentReceipts";

interface ModelCard {
  slug: string;
  name: string;
  family: string;
  base: string;
  base_license: string;
  params_b: number;
  context_window: number;
  purpose: string;
  trained_on: string[];
  eval_notes: string | null;
  compute_class: string;
  status: string;
  deed: string | null;
  card_sha256: string;
}

interface ModelCatalog {
  version: string;
  generated_at: string | null;
  scope: string | null;
  doctrine_note: string | null;
  models_sha256: string;
  scorecard: {
    total_models: number;
    in_house_models: number;
    active_models: number;
  };
  models: ModelCard[];
}

interface PinReceipt {
  receipt_id: string;
  org_seq: number;
  receipt_sha256: string;
  share_url: string;
  pinned_at: string;
  model: {
    slug: string;
    name: string;
    base: string;
    params_b: number;
    card_sha256: string;
  };
  declaration: string | null;
  client_ref: string | null;
}

export function Models() {
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null);
  const [catalogErr, setCatalogErr] = useState<string | null>(null);
  const [pinTarget, setPinTarget] = useState<ModelCard | null>(null);
  const [receipt, setReceipt] = useState<PinReceipt | null>(null);

  useEffect(() => {
    api<ModelCatalog>("/models/catalog")
      .then(setCatalog)
      .catch((e) => setCatalogErr(e.message));
  }, []);

  return (
    <div>
      <p className="text-sm font-medium uppercase tracking-widest text-honey-300">Models</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-paper">
        The in-house cooks.
      </h1>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-paper/60">
        Reference cards for the sovereign models that run on our rig. Pin one
        to seal client-deliverable provenance — the receipt remembers the
        exact card hash you declared on this date.
      </p>

      {catalogErr && (
        <div className="mt-6">
          <ErrorNote>
            {catalogErr.includes("membership") ? (
              <>
                The model card library is members-only. <a className="text-honey-300 underline" href="/org">Apply for membership →</a>
              </>
            ) : (
              catalogErr
            )}
          </ErrorNote>
        </div>
      )}

      {!catalog && !catalogErr && <div className="mt-6"><Spinner label="Loading catalog…" /></div>}

      {catalog && (
        <>
          <section className="mt-10">
            <div className="mb-4 flex items-baseline justify-between gap-3">
              <h2 className="text-xs font-medium uppercase tracking-widest text-paper/40">Your pins</h2>
              <span className="font-mono text-[10px] text-paper/30">latest 5 on your chain</span>
            </div>
            <RecentReceipts
              schema="defendablecloud.model-pin-receipt/v1"
              limit={5}
              emptyHint="No pins yet · click 'Pin to chain' on any card below to mint your first."
            />
          </section>

          <section className="mt-10">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="font-mono text-xs uppercase tracking-widest text-paper/40">In-house catalog</p>
                <h2 className="mt-1 text-xl font-semibold tracking-tight text-paper">
                  Hash-anchored cards
                </h2>
              </div>
              <div className="text-right font-mono text-xs text-paper/40">
                <div>{catalog.version} · generated {catalog.generated_at ? new Date(catalog.generated_at).toLocaleDateString() : "—"}</div>
                <div>
                  models_sha256 · <span className="text-paper/65">{catalog.models_sha256.slice(0, 16)}…</span>
                </div>
              </div>
            </div>

            <Card className="mt-4">
              <div className="grid gap-x-8 gap-y-3 text-center sm:grid-cols-3">
                <Stat label="Total models" value={String(catalog.scorecard.total_models)} />
                <Stat label="In-house" value={String(catalog.scorecard.in_house_models)} />
                <Stat label="Active" value={String(catalog.scorecard.active_models)} />
              </div>
            </Card>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {catalog.models.map((m) => (
                <ModelCardTile key={m.slug} card={m} onPin={() => setPinTarget(m)} />
              ))}
            </div>
          </section>

          <section className="mt-10">
            <Card>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-xs uppercase tracking-widest text-paper/40">CLI</p>
                  <h3 className="mt-1 font-semibold text-paper">Programmatic pin</h3>
                  <p className="mt-2 max-w-xl text-sm leading-relaxed text-paper/65">
                    Pinning from a Run script keeps your books and records on the
                    same chain as your evals and cooks.
                  </p>
                </div>
                <pre className="overflow-x-auto rounded-md border border-white/10 bg-black/40 p-3 font-mono text-xs text-paper/75">
{`defendable models pin atlas-qwen-27b \\
  --note "agent A on deal X" \\
  --ref deal-2026-05-28`}
                </pre>
              </div>
            </Card>
          </section>
        </>
      )}

      {pinTarget && (
        <PinDialog
          card={pinTarget}
          onClose={() => setPinTarget(null)}
          onPinned={(r) => {
            setReceipt(r);
            setPinTarget(null);
          }}
        />
      )}

      {receipt && <ReceiptDialog receipt={receipt} onClose={() => setReceipt(null)} />}
    </div>
  );
}

function ModelCardTile({ card, onPin }: { card: ModelCard; onPin: () => void }) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-paper">{card.name}</h3>
          <p className="mt-0.5 font-mono text-[10px] text-paper/35">{card.slug}</p>
        </div>
        <span className="rounded-md border border-honey-400/30 bg-honey-300/[0.08] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-honey-200">
          {card.status}
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-paper/65">{card.purpose}</p>
      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 font-mono text-[11px] text-paper/55">
        <div><span className="text-paper/35">base</span> · {card.base}</div>
        <div><span className="text-paper/35">params</span> · {card.params_b}B</div>
        <div><span className="text-paper/35">ctx</span> · {card.context_window.toLocaleString()}</div>
        <div><span className="text-paper/35">license</span> · {card.base_license}</div>
      </div>
      {card.eval_notes && (
        <p className="mt-3 text-xs leading-relaxed text-paper/50">
          <span className="uppercase tracking-widest text-paper/35">Eval</span> · {card.eval_notes}
        </p>
      )}
      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="font-mono text-[10px] text-paper/35">
          card_sha256 · {card.card_sha256.slice(0, 16)}…
        </p>
        <Button onClick={onPin}>Pin to chain</Button>
      </div>
    </Card>
  );
}

function PinDialog({
  card,
  onClose,
  onPinned,
}: {
  card: ModelCard;
  onClose: () => void;
  onPinned: (r: PinReceipt) => void;
}) {
  const [declaration, setDeclaration] = useState("");
  const [clientRef, setClientRef] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    setSubmitting(true);
    setErr(null);
    try {
      const body: { declaration?: string; client_ref?: string } = {};
      if (declaration.trim()) body.declaration = declaration.trim();
      if (clientRef.trim()) body.client_ref = clientRef.trim();
      const r = await api<PinReceipt>(`/models/catalog/${card.slug}/pin`, {
        method: "POST",
        body,
      });
      onPinned(r);
    } catch (e: any) {
      setErr(e?.message || "pin failed");
      setSubmitting(false);
    }
  }

  return (
    <Backdrop onClose={onClose}>
      <div className="w-full max-w-lg rounded-xl border border-white/10 bg-ink p-6 shadow-2xl">
        <p className="font-mono text-[10px] uppercase tracking-widest text-honey-300/70">Pin to chain</p>
        <h3 className="mt-1 text-lg font-semibold text-paper">{card.name}</h3>
        <p className="mt-1 font-mono text-xs text-paper/40">{card.slug} · {card.base} · {card.params_b}B</p>

        <div className="mt-5 space-y-4">
          <label className="block">
            <span className="block text-xs font-medium uppercase tracking-widest text-paper/50">
              Declaration <span className="font-normal normal-case text-paper/35">(optional · 500 char)</span>
            </span>
            <textarea
              value={declaration}
              onChange={(e) => setDeclaration(e.target.value)}
              maxLength={500}
              placeholder="What is this model being pinned for?"
              rows={3}
              className="mt-2 w-full rounded-md border border-white/10 bg-white/[0.03] px-3.5 py-2.5 text-sm text-paper placeholder:text-paper/35 focus:border-honey-400/50 focus:outline-none focus:ring-1 focus:ring-honey-400/40"
            />
          </label>
          <label className="block">
            <span className="block text-xs font-medium uppercase tracking-widest text-paper/50">
              Client ref <span className="font-normal normal-case text-paper/35">(optional · 120 char)</span>
            </span>
            <input
              type="text"
              value={clientRef}
              onChange={(e) => setClientRef(e.target.value)}
              maxLength={120}
              placeholder="deal-2026-05-28"
              className="mt-2 w-full rounded-md border border-white/10 bg-white/[0.03] px-3.5 py-2.5 text-sm text-paper placeholder:text-paper/35 focus:border-honey-400/50 focus:outline-none focus:ring-1 focus:ring-honey-400/40"
            />
          </label>
        </div>

        {err && <div className="mt-4"><ErrorNote>{err}</ErrorNote></div>}

        <div className="mt-6 flex items-center justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={submitting}>Cancel</Button>
          <Button onClick={submit} disabled={submitting}>
            {submitting ? "Pinning…" : "Pin to chain"}
          </Button>
        </div>
        <p className="mt-4 text-xs text-paper/40">
          A new receipt mints on your org's chain. The card_sha256 above is
          sealed in — the catalog can evolve later; this receipt remembers what
          you pinned today.
        </p>
      </div>
    </Backdrop>
  );
}

function ReceiptDialog({ receipt, onClose }: { receipt: PinReceipt; onClose: () => void }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(receipt.share_url).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    });
  }

  return (
    <Backdrop onClose={onClose}>
      <div className="w-full max-w-lg rounded-xl border border-white/10 bg-ink p-6 shadow-2xl">
        <p className="font-mono text-[10px] uppercase tracking-widest text-honey-300/70">Pinned</p>
        <h3 className="mt-1 text-lg font-semibold text-paper">{receipt.model.name} is on chain.</h3>
        <p className="mt-1 font-mono text-xs text-paper/40">
          {receipt.receipt_id} · org_seq {receipt.org_seq}
        </p>

        <div className="mt-5 space-y-3 font-mono text-xs">
          <KV k="slug" v={receipt.model.slug} />
          <KV k="base" v={`${receipt.model.base} · ${receipt.model.params_b}B`} />
          <KV k="card_sha256" v={receipt.model.card_sha256} mono />
          <KV k="receipt_sha256" v={receipt.receipt_sha256} mono />
          <KV k="pinned_at" v={receipt.pinned_at} />
          {receipt.declaration && <KV k="declaration" v={receipt.declaration} />}
          {receipt.client_ref && <KV k="client_ref" v={receipt.client_ref} />}
        </div>

        <div className="mt-5 rounded-md border border-honey-400/20 bg-honey-300/[0.04] px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-widest text-honey-300/80">Share URL</p>
          <p className="mt-1 break-all font-mono text-[11px] text-paper/80">{receipt.share_url}</p>
          <div className="mt-3 flex items-center gap-3">
            <Button onClick={copy} variant="ghost">{copied ? "Copied ✓" : "Copy"}</Button>
            <a
              href={receipt.share_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-honey-200 underline underline-offset-2 hover:text-honey-100"
            >
              Open receipt →
            </a>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end">
          <Button onClick={onClose}>Close</Button>
        </div>
      </div>
    </Backdrop>
  );
}

function Backdrop({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 px-4 py-10"
      onClick={onClose}
    >
      <div onClick={(e) => e.stopPropagation()}>{children}</div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-2xl font-semibold text-paper">{value}</div>
      <div className="mt-0.5 text-xs uppercase tracking-widest text-paper/40">{label}</div>
    </div>
  );
}

function KV({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="shrink-0 text-paper/40">{k}</span>
      <span className={`break-all text-right ${mono ? "text-paper/75" : "text-paper/85"}`}>{v}</span>
    </div>
  );
}
