import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, apiBase } from "../lib/api";
import { Badge, Button, Callout, Card, ErrorNote, ExampleList, Field, inputClass, Spinner } from "../components/ui";
import { EVIDENCE_KIND_HELP, VERIFICATION_HELP, laneGuide } from "../lib/guidance";

interface Evidence {
  id: string;
  kind: string;
  label: string;
  content: string | null;
  sha256: string | null;
  byte_size: number;
  content_type: string | null;
}
interface Check {
  check_key: string;
  label: string;
  category: string;
  status: string;
  detail: string | null;
}
interface Verdict {
  outcome: string;
  summary: string;
  score: number;
  checks_passed: number;
  checks_failed: number;
}
interface Approval {
  decision: string;
  approver_email: string | null;
  note: string | null;
}
interface Receipt {
  receipt_id: string;
  org_seq: number;
  receipt_sha256: string;
  parent_hash: string;
  share_token: string;
  pdf_url: string;
}
interface Run {
  id: string;
  lane: string;
  title: string;
  status: string;
  inputs: Record<string, unknown>;
  evidence: Evidence[];
  checks: Check[];
  verdict: Verdict | null;
  approval: Approval | null;
  receipt: Receipt | null;
}

const EVIDENCE_KINDS = ["note", "url", "observation", "tool_output", "model_output", "log"];

export function RunDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [run, setRun] = useState<Run | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    try {
      setRun(await api<Run>(`/runs/${id}`));
    } catch (e: any) {
      setErr(e.message);
    }
  }
  useEffect(() => {
    load();
  }, [id]);

  async function act(key: string, fn: () => Promise<unknown>) {
    setErr(null);
    setBusy(key);
    try {
      await fn();
      await load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  }

  if (err && !run) return <ErrorNote>{err}</ErrorNote>;
  if (!run) return <Spinner label="Loading run…" />;

  const hasVerdict = !!run.verdict;
  const approved = run.approval?.decision === "approved";
  const receipted = !!run.receipt;

  return (
    <div className="mx-auto max-w-3xl">
      <button onClick={() => nav("/")} className="mb-6 text-sm text-paper/50 hover:text-paper">← Dashboard</button>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs uppercase tracking-widest text-honey-300/70">{run.lane}</span>
            <Badge value={run.status} />
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-paper">{run.title}</h1>
        </div>
      </div>

      {err && <div className="mt-4"><ErrorNote>{err}</ErrorNote></div>}

      {/* Inputs */}
      {Object.keys(run.inputs || {}).length > 0 && (
        <Card className="mt-6" title="Inputs">
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            {Object.entries(run.inputs).map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs uppercase tracking-widest text-paper/40">{k}</dt>
                <dd className="text-paper/80">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}

      {/* Evidence */}
      <div className="mt-6">
        <EvidenceSection run={run} busy={busy} act={act} />
      </div>

      {/* Checks + Verdict */}
      <Card
        className="mt-6"
        title="Verification"
        actions={
          !receipted && (
            <Button variant="ghost" disabled={busy === "checks"} onClick={() => act("checks", () => api(`/runs/${run.id}/checks`, { method: "POST" }))}>
              {busy === "checks" ? "Running…" : hasVerdict ? "Re-run checks" : "Run verification"}
            </Button>
          )
        }
      >
        {!hasVerdict ? (
          <p className="text-sm text-paper/50">{VERIFICATION_HELP}</p>
        ) : (
          <div>
            <div className="flex items-center gap-3">
              <Badge value={run.verdict!.outcome} />
              <span className="text-sm text-paper/70">{run.verdict!.summary}</span>
            </div>
            <ul className="mt-4 space-y-1.5 font-mono text-xs">
              {run.checks.map((c) => (
                <li key={c.check_key} className="flex gap-2">
                  <Badge value={c.status} />
                  <span className="text-paper/70">
                    {c.label} <span className="text-paper/35">({c.category})</span> — {c.detail}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {/* Approval */}
      {hasVerdict && (
        <Card className="mt-6" title="Human approval">
          {run.approval ? (
            <div className="flex items-center gap-3 text-sm">
              <Badge value={run.approval.decision} />
              <span className="text-paper/60">
                {run.approval.approver_email}
                {run.approval.note ? ` · "${run.approval.note}"` : ""}
              </span>
            </div>
          ) : (
            <ApprovalForm runId={run.id} busy={busy} act={act} />
          )}
        </Card>
      )}

      {/* Receipt — the killer button / payoff */}
      <Card className="mt-6" title="Receipt">
        {receipted ? (
          <ReceiptPanel receipt={run.receipt!} />
        ) : approved ? (
          <div>
            <p className="mb-4 text-sm text-paper/60">Approved. Issue the hash-chained receipt — JSON + PDF, shareable.</p>
            <Button disabled={busy === "receipt"} onClick={() => act("receipt", () => api(`/runs/${run.id}/receipt`, { method: "POST" }))}>
              {busy === "receipt" ? "Generating…" : "Generate Receipt"}
            </Button>
          </div>
        ) : (
          <p className="text-sm text-paper/50">A human must approve the run before a receipt can be issued.</p>
        )}
      </Card>
    </div>
  );
}

function EvidenceSection({ run, busy, act }: { run: Run; busy: string | null; act: (k: string, fn: () => Promise<unknown>) => Promise<void> }) {
  const [kind, setKind] = useState("note");
  const [label, setLabel] = useState("");
  const [content, setContent] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const locked = !!run.receipt;

  function addNote() {
    if (!label.trim()) return;
    act("ev", async () => {
      await api(`/runs/${run.id}/evidence`, { method: "POST", body: { kind, label: label.trim(), content } });
      setLabel("");
      setContent("");
    });
  }
  function upload() {
    const f = fileRef.current?.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    act("upload", async () => {
      await api(`/runs/${run.id}/evidence/upload`, { method: "POST", formData: fd });
      if (fileRef.current) fileRef.current.value = "";
    });
  }

  const guide = laneGuide(run.lane);

  return (
    <Card title="Evidence" subtitle={`${run.evidence.length} item(s)`}>
      {!locked && (
        <div className="mb-5">
          <Callout title="What to attach">
            {guide.evidenceHint}
            <span className="mt-2 block text-xs text-paper/40">Good evidence for this run:</span>
            <ExampleList items={guide.evidenceExamples} />
          </Callout>
        </div>
      )}
      {run.evidence.length > 0 && (
        <ul className="mb-5 space-y-2">
          {run.evidence.map((e) => (
            <li key={e.id} className="flex items-center gap-2 text-sm">
              <span className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 font-mono text-[10px] uppercase text-paper/50">{e.kind}</span>
              <span className="text-paper/80">{e.label}</span>
              {e.sha256 && <span className="font-mono text-[10px] text-paper/30">{e.sha256.slice(0, 12)}…</span>}
            </li>
          ))}
        </ul>
      )}
      {!locked && (
        <div className="space-y-4 border-t border-white/5 pt-4">
          <div className="grid gap-3 sm:grid-cols-[140px_1fr]">
            <select className={inputClass} value={kind} onChange={(e) => setKind(e.target.value)}>
              {EVIDENCE_KINDS.map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
            <input className={inputClass} placeholder="Label" value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
          <p className="-mt-1 text-xs text-paper/40">{EVIDENCE_KIND_HELP[kind]}</p>
          <textarea className={inputClass} rows={2} placeholder="Content (note text, a URL, an output…)" value={content} onChange={(e) => setContent(e.target.value)} />
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="ghost" disabled={busy === "ev"} onClick={addNote}>{busy === "ev" ? "Adding…" : "Add evidence"}</Button>
            <span className="text-xs text-paper/30">or</span>
            <input ref={fileRef} type="file" className="text-xs text-paper/60 file:mr-3 file:rounded file:border-0 file:bg-white/10 file:px-3 file:py-1.5 file:text-paper" />
            <Button variant="ghost" disabled={busy === "upload"} onClick={upload}>{busy === "upload" ? "Uploading…" : "Upload file"}</Button>
          </div>
        </div>
      )}
    </Card>
  );
}

function ApprovalForm({ runId, busy, act }: { runId: string; busy: string | null; act: (k: string, fn: () => Promise<unknown>) => Promise<void> }) {
  const [note, setNote] = useState("");
  return (
    <div className="space-y-4">
      <Field label="Note (optional)">
        <input className={inputClass} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why you're approving or rejecting" />
      </Field>
      <div className="flex gap-3">
        <Button disabled={!!busy} onClick={() => act("approve", () => api(`/runs/${runId}/approve`, { method: "POST", body: { decision: "approved", note } }))}>
          {busy === "approve" ? "…" : "Approve"}
        </Button>
        <Button variant="danger" disabled={!!busy} onClick={() => act("reject", () => api(`/runs/${runId}/approve`, { method: "POST", body: { decision: "rejected", note } }))}>
          Reject
        </Button>
      </div>
    </div>
  );
}

function ReceiptPanel({ receipt }: { receipt: Receipt }) {
  const [copied, setCopied] = useState(false);
  const shareUrl = `${window.location.origin}/r/${receipt.share_token}`;
  return (
    <div>
      <div className="flex items-center gap-3">
        <Badge value="receipted" />
        <span className="font-mono text-sm text-paper/80">{receipt.receipt_id}</span>
      </div>
      <dl className="mt-4 space-y-2 font-mono text-xs">
        <Row k="receipt_sha256" v={receipt.receipt_sha256} />
        <Row k="parent_hash" v={receipt.parent_hash} />
        <Row k="org_seq" v={String(receipt.org_seq)} />
      </dl>
      <div className="mt-5 flex flex-wrap gap-3">
        <Button
          onClick={() => {
            navigator.clipboard.writeText(shareUrl);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? "Copied ✓" : "Copy share link"}
        </Button>
        <a href={`/r/${receipt.share_token}`} target="_blank" rel="noreferrer">
          <Button variant="ghost">Open proof page</Button>
        </a>
        <a href={receipt.pdf_url.startsWith("http") ? receipt.pdf_url : `${apiBase}/share/${receipt.share_token}/pdf`} target="_blank" rel="noreferrer">
          <Button variant="ghost">Download PDF</Button>
        </a>
        <a href={`${apiBase}/share/${receipt.share_token}`} target="_blank" rel="noreferrer">
          <Button variant="ghost">JSON</Button>
        </a>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-3">
      <dt className="w-32 shrink-0 text-paper/40">{k}</dt>
      <dd className="break-all text-paper/70">{v}</dd>
    </div>
  );
}
