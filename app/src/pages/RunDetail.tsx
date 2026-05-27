import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, apiBase } from "../lib/api";
import { Badge, Button, Callout, Card, ErrorNote, ExampleList, Field, inputClass, Spinner } from "../components/ui";
import { EVIDENCE_KIND_HELP, laneGuide } from "../lib/guidance";

interface Evidence { id: string; kind: string; label: string; sha256: string | null; }
interface Check { id: string; check_key: string; label: string; category: string; status: string; severity: string | null; source: string; detail: string | null; }
interface Verdict { outcome: string; summary: string; score_100: number; severity: string | null; client_ready: string | null; recommended_action: string | null; checks_passed: number; checks_failed: number; }
interface Approval { decision: string; approver_email: string | null; note: string | null; }
interface Receipt { receipt_id: string; receipt_sha256: string; parent_hash: string; org_seq: number; share_token: string; pdf_url: string; }
interface Submission { agent_name: string | null; model_name: string | null; provider: string | null; output_text: string; sha256: string; }
interface FlightSheet { id: string; name: string; version: string; lane: string; expected_outputs: string[]; pass_threshold: number; fail_threshold: number; }
interface Ownership { agent_created: string | null; audited_by: string; referee_logic: string; final_authority: string | null; approval_status: string; receipt_status: string; }
interface Run {
  id: string; lane: string; title: string; status: string;
  assignment_text: string | null; flight_sheet: FlightSheet | null; submission: Submission | null;
  evidence: Evidence[]; checks: Check[]; verdict: Verdict | null; approval: Approval | null;
  receipt: Receipt | null; ownership: Ownership;
}

export function RunDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [run, setRun] = useState<Run | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [resub, setResub] = useState(false);

  async function load() {
    try { setRun(await api<Run>(`/runs/${id}`)); } catch (e: any) { setErr(e.message); }
  }
  useEffect(() => { load(); }, [id]);

  async function act(key: string, fn: () => Promise<unknown>) {
    setErr(null); setBusy(key);
    try { await fn(); await load(); } catch (e: any) { setErr(e.message); } finally { setBusy(null); }
  }

  if (err && !run) return <ErrorNote>{err}</ErrorNote>;
  if (!run) return <Spinner label="Loading eval run…" />;

  const hasVerdict = !!run.verdict;
  const approved = run.approval?.decision === "approved";
  const receipted = !!run.receipt;

  return (
    <div className="mx-auto max-w-3xl">
      <button onClick={() => nav("/")} className="mb-6 text-sm text-paper/50 hover:text-paper">← Runs</button>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            {run.flight_sheet && <span className="font-mono text-xs uppercase tracking-widest text-honey-300/70">{run.flight_sheet.name} v{run.flight_sheet.version}</span>}
            <Badge value={run.status.replace(/_/g, " ")} />
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-paper">{run.title}</h1>
        </div>
      </div>
      {err && <div className="mt-4"><ErrorNote>{err}</ErrorNote></div>}

      {/* 1 · Assignment */}
      {run.assignment_text && <AssignmentCard text={run.assignment_text} />}

      {/* 2 · Evidence */}
      <div className="mt-6"><EvidenceSection run={run} busy={busy} act={act} /></div>

      {/* 3 · Agent submission */}
      <div id="submission" className="mt-6"><SubmissionSection run={run} busy={busy} act={act} resub={resub} setResub={setResub} /></div>

      {/* 4 · Audit + Referee Findings */}
      <div className="mt-6"><AuditSection run={run} busy={busy} act={act} /></div>

      {/* 4.5 · Repair plan — "it failed, now what?" */}
      <RepairPlan run={run} setResub={setResub} />

      {/* 5 · Ownership / authority */}
      <OwnershipPanel o={run.ownership} />

      {/* 6 · Fine-tune (Phase 4) — lift the eval */}
      {hasVerdict && <CookSection run={run} reload={load} />}

      {/* 7 · Approval */}
      {hasVerdict && (
        <Card className="mt-6" title="Human approval" subtitle="The operator owns the final trust decision">
          {run.approval ? (
            <div className="flex items-center gap-3 text-sm">
              <Badge value={run.approval.decision} />
              <span className="text-paper/60">{run.approval.approver_email}{run.approval.note ? ` · "${run.approval.note}"` : ""}</span>
            </div>
          ) : <ApprovalForm runId={run.id} busy={busy} act={act} />}
        </Card>
      )}

      {/* 8 · Receipt */}
      <Card className="mt-6" title="Client Results Package">
        {receipted ? <ReceiptPanel receipt={run.receipt!} /> : approved ? (
          <div>
            <p className="mb-4 text-sm text-paper/60">Approved. Issue the eval receipt — findings, verdict, ownership, hashed JSON + PDF, shareable.</p>
            <Button disabled={busy === "receipt"} onClick={() => act("receipt", () => api(`/runs/${run.id}/receipt`, { method: "POST" }))}>
              {busy === "receipt" ? "Issuing…" : "Issue Receipt"}
            </Button>
          </div>
        ) : <p className="text-sm text-paper/50">A human must approve before the receipt can be issued.</p>}
      </Card>
    </div>
  );
}

type Act = (k: string, fn: () => Promise<unknown>) => Promise<void>;

function AssignmentCard({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Card className="mt-6" title="Assignment" subtitle="Send this to the agent (Kimi, Claude, GPT, Qwen, Atlas…)"
      actions={<Button variant="ghost" onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>{copied ? "Copied ✓" : "Copy assignment"}</Button>}>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-md border border-white/8 bg-black/30 p-3 font-mono text-xs leading-relaxed text-paper/70">{text}</pre>
    </Card>
  );
}

function EvidenceSection({ run, busy, act }: { run: Run; busy: string | null; act: Act }) {
  const [kind, setKind] = useState("note");
  const [label, setLabel] = useState("");
  const [content, setContent] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const locked = !!run.receipt;
  const guide = laneGuide(run.lane);

  return (
    <Card title="Evidence" subtitle={`${run.evidence.length} item(s) · the inputs the agent was given`}>
      {!locked && (
        <div className="mb-5">
          <Callout title="What to attach">{guide.evidenceHint}<ExampleList items={guide.evidenceExamples} /></Callout>
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
              {Object.keys(EVIDENCE_KIND_HELP).filter((k) => k !== "file").map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
            <input className={inputClass} placeholder="Label" value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
          <p className="-mt-1 text-xs text-paper/40">{EVIDENCE_KIND_HELP[kind]}</p>
          <textarea className={inputClass} rows={2} placeholder="Content (note, URL, output…)" value={content} onChange={(e) => setContent(e.target.value)} />
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="ghost" disabled={busy === "ev"} onClick={() => label.trim() && act("ev", async () => { await api(`/runs/${run.id}/evidence`, { method: "POST", body: { kind, label: label.trim(), content } }); setLabel(""); setContent(""); })}>{busy === "ev" ? "Adding…" : "Add evidence"}</Button>
            <span className="text-xs text-paper/30">or</span>
            <input ref={fileRef} type="file" className="text-xs text-paper/60 file:mr-3 file:rounded file:border-0 file:bg-white/10 file:px-3 file:py-1.5 file:text-paper" />
            <Button variant="ghost" disabled={busy === "up"} onClick={() => { const f = fileRef.current?.files?.[0]; if (!f) return; const fd = new FormData(); fd.append("file", f); act("up", async () => { await api(`/runs/${run.id}/evidence/upload`, { method: "POST", formData: fd }); if (fileRef.current) fileRef.current.value = ""; }); }}>{busy === "up" ? "Uploading…" : "Upload file"}</Button>
          </div>
        </div>
      )}
    </Card>
  );
}

function SubmissionSection({ run, busy, act, resub, setResub }: { run: Run; busy: string | null; act: Act; resub: boolean; setResub: (v: boolean) => void }) {
  const [agent, setAgent] = useState(run.submission?.agent_name || "");
  const [model, setModel] = useState(run.submission?.model_name || "");
  const [provider, setProvider] = useState(run.submission?.provider || "");
  const [output, setOutput] = useState("");

  if (run.submission && !resub) {
    const s = run.submission;
    return (
      <Card title="Agent submission" subtitle="What the agent returned"
        actions={!run.receipt && <Button variant="ghost" onClick={() => setResub(true)}>Submit corrected version</Button>}>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-semibold text-paper">{s.agent_name || "Agent"}</span>
          <span className="text-paper/50">· {s.model_name || "—"} ({s.provider || "—"})</span>
          <span className="font-mono text-[10px] text-paper/30">{s.sha256.slice(0, 16)}…</span>
        </div>
        <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-white/8 bg-black/30 p-3 font-mono text-xs text-paper/65">{s.output_text}</pre>
      </Card>
    );
  }
  const correcting = !!run.submission;
  return (
    <Card title="Agent submission" subtitle={correcting ? "Paste the corrected output — the referee re-checks the same rules" : "Paste the agent's output"}
      actions={correcting && <Button variant="ghost" onClick={() => setResub(false)}>Cancel</Button>}>
      <div className="grid gap-3 sm:grid-cols-3">
        <input className={inputClass} placeholder="Agent (e.g. Kimi)" value={agent} onChange={(e) => setAgent(e.target.value)} />
        <input className={inputClass} placeholder="Model (e.g. K2.6)" value={model} onChange={(e) => setModel(e.target.value)} />
        <input className={inputClass} placeholder="Provider (e.g. Moonshot)" value={provider} onChange={(e) => setProvider(e.target.value)} />
      </div>
      <textarea className={`mt-3 ${inputClass}`} rows={6} placeholder={correcting ? "Paste the corrected agent output…" : "Paste the agent output here…"} value={output} onChange={(e) => setOutput(e.target.value)} />
      <div className="mt-4">
        <Button disabled={busy === "sub" || !output.trim()} onClick={() => act("sub", async () => { await api(`/runs/${run.id}/submission`, { method: "POST", body: { agent_name: agent, model_name: model, provider, output_text: output } }); setResub(false); setOutput(""); })}>{busy === "sub" ? "Saving…" : correcting ? "Submit correction" : "Save submission"}</Button>
        {correcting && <span className="ml-3 text-xs text-paper/40">Then re-run the ruleset audit to re-verify.</span>}
      </div>
    </Card>
  );
}

// "It failed — now what?" Every flag is a located defect, so fixability is a
// real answer, not an opinion. Two kinds of flag, told apart by category:
//   defects in the WORK (math/schema/structure/evidence) → fixable: correct & resubmit
//   findings about the DEAL (policy gates) → not a rework: the work is right, the rule says no
const DEFECT_CATS = new Set(["math", "schema", "structure", "evidence"]);

function RepairPlan({ run, setResub }: { run: Run; setResub: (v: boolean) => void }) {
  const v = run.verdict;
  if (!v || v.outcome === "pass" || run.receipt) return null;
  const flags = run.checks.filter((c) => c.status === "flag");
  if (!flags.length) return null;
  const byTier = (a: Check, b: Check) => TIER_RANK[tierOf(a.severity)] - TIER_RANK[tierOf(b.severity)];
  const defects = flags.filter((c) => DEFECT_CATS.has(c.category)).sort(byTier);
  const findings = flags.filter((c) => !DEFECT_CATS.has(c.category)).sort(byTier);

  const headline = !findings.length
    ? `Fixable. ${defects.length} defect${defects.length > 1 ? "s" : ""} in the work — correct and resubmit; the referee re-checks the same rules.`
    : !defects.length
      ? "Not a rework. These are true findings about the deal — the work is correct, the rule returns no."
      : `Partly fixable. Correct ${defects.length} work-defect${defects.length > 1 ? "s" : ""}; ${findings.length} finding${findings.length > 1 ? "s are" : " is a"} real result about the deal, not an error to redo.`;

  const Group = ({ title, note, items }: { title: string; note: string; items: Check[] }) => (
    <div className="mt-4">
      <p className="text-xs font-semibold uppercase tracking-widest text-paper/45">{title}</p>
      <p className="mt-0.5 text-xs text-paper/40">{note}</p>
      <ul className="mt-2 space-y-2">
        {items.map((c) => (
          <li key={c.id} className="flex flex-wrap items-center gap-2 text-sm">
            <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase ${TIER_TONE[tierOf(c.severity)]}`}>{TIER_LABEL[tierOf(c.severity)]}</span>
            <span className="text-paper/80">{c.label}</span>
            {c.detail && <span className="w-full pl-1 text-xs text-paper/45">{c.detail}</span>}
          </li>
        ))}
      </ul>
    </div>
  );

  return (
    <Card className="mt-6" title="It failed — now what?" subtitle="We don't judge. Every flag is a located defect; fix it and the referee re-verifies.">
      <p className="text-sm font-medium text-paper/85">{headline}</p>
      {defects.length > 0 && <Group title="Fix the work" note="Correct these in the agent's output, then resubmit." items={defects} />}
      {findings.length > 0 && <Group title="Findings about the deal / output" note="The work is correct — the rule says no. Not fixed by redoing the work." items={findings} />}
      {defects.length > 0 && !run.receipt && (
        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-white/5 pt-4">
          <Button onClick={() => { setResub(true); document.getElementById("submission")?.scrollIntoView({ behavior: "smooth" }); }}>Submit corrected version</Button>
          <span className="text-xs text-paper/40">Resubmit → re-run audit. When the flags clear, it passes — deterministic, not a second opinion.</span>
        </div>
      )}
    </Card>
  );
}

const SEV_TONE: Record<string, string> = {
  honey: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  jelly: "border-amber-400/30 bg-amber-400/10 text-amber-300",
  propolis: "border-red-400/30 bg-red-400/10 text-red-300",
};

// Phase 9 · three risk tiers — not all penalties are equal. The flight sheet
// pre-weights each rule; the math/approx referee scales by the size of the miss.
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
const TIER_LABEL: Record<string, string> = { high: "HIGH-RISK", mid: "mid-risk", low: "low-risk" };
const TIER_RANK: Record<string, number> = { high: 0, mid: 1, low: 2 };

function AuditSection({ run, busy, act }: { run: Run; busy: string | null; act: Act }) {
  const hasSubmission = !!run.submission;
  // Game-changers first: flags ranked high→mid→low, then open rules, then passes/skips.
  const STATUS_RANK: Record<string, number> = { flag: 0, open: 1, pass: 2, review: 3, skip: 4 };
  const checks = [...run.checks].sort((a, b) =>
    (STATUS_RANK[a.status] ?? 5) - (STATUS_RANK[b.status] ?? 5) ||
    TIER_RANK[tierOf(a.severity)] - TIER_RANK[tierOf(b.severity)],
  );
  const flags = checks.filter((c) => c.status === "flag");
  const tierCount = (t: string) => flags.filter((c) => tierOf(c.severity) === t).length;
  const openLeft = checks.filter((c) => c.status === "open").length;
  const v = run.verdict;

  return (
    <Card title="Referee" subtitle="Rulebook applied · flags thrown · human holds authority"
      actions={hasSubmission && !run.receipt && (
        <Button variant="ghost" disabled={busy === "audit"} onClick={() => act("audit", () => api(`/runs/${run.id}/audit`, { method: "POST" }))}>{busy === "audit" ? "Auditing…" : checks.length ? "Re-run ruleset audit" : "Run ruleset audit"}</Button>
      )}>
      {!hasSubmission ? (
        <p className="text-sm text-paper/50">Add the agent submission, then run the ruleset audit. The referee applies the flight sheet's rules and throws flags — it does not judge.</p>
      ) : !checks.length ? (
        <p className="text-sm text-paper/50">Run the ruleset audit to apply the flight sheet's rules to the submission.</p>
      ) : (
        <div>
          {v && (
            <div className="mb-5 rounded-lg border border-white/8 bg-white/[0.02] p-4">
              <div className="flex flex-wrap items-center gap-3">
                {v.severity && <span className={`rounded-md border px-2.5 py-1 text-sm font-semibold uppercase ${SEV_TONE[v.severity] || ""}`}>{v.severity}</span>}
                <span className="text-sm text-paper/70">{v.checks_passed} of {v.checks_passed + v.checks_failed} rules passed · {v.checks_failed} flag(s)</span>
                <span className="text-sm text-paper/45">· client-ready: {v.client_ready}</span>
              </div>
              {/* Risk readout — the clear view of the penalties by tier */}
              {flags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {(["high", "mid", "low"] as const).map((t) => (
                    <span key={t} className={`rounded-md border px-2 py-0.5 font-mono text-xs ${tierCount(t) ? TIER_TONE[t] : "border-white/10 text-paper/25"}`}>
                      {tierCount(t)} {TIER_LABEL[t]}
                    </span>
                  ))}
                  <span className="rounded-md border border-white/10 px-2 py-0.5 font-mono text-xs text-paper/45">{v.score_100}/100 weighted</span>
                </div>
              )}
              {v.recommended_action && <p className="mt-3 text-sm text-paper/70"><span className="uppercase tracking-widest text-paper/35 text-xs">Recommended</span> · {v.recommended_action}</p>}
            </div>
          )}
          <ul className="space-y-2">
            {checks.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-2 text-sm">
                <Badge value={c.status} />
                {c.status === "flag" && (
                  <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase ${TIER_TONE[tierOf(c.severity)]}`}>{TIER_LABEL[tierOf(c.severity)]}</span>
                )}
                <span className="text-paper/75">{c.label}</span>
                <span className="text-paper/35 text-xs">
                  ({c.category}{c.source === "operator" ? " · checklist rule" : " · auto rule"})
                </span>
                {c.detail && <span className="w-full pl-1 text-xs text-paper/40">{c.detail}</span>}
                {c.status === "open" && !run.receipt && (
                  <span className="flex gap-1.5">
                    <button disabled={!!busy} onClick={() => act("grade", () => api(`/runs/${run.id}/checks/${c.id}`, { method: "PATCH", body: { status: "pass" } }))}
                      className="rounded border border-emerald-400/30 px-2 py-0.5 font-mono text-[10px] uppercase text-emerald-300/80 hover:bg-emerald-400/10">Satisfied</button>
                    <button disabled={!!busy} onClick={() => act("grade", () => api(`/runs/${run.id}/checks/${c.id}`, { method: "PATCH", body: { status: "flag" } }))}
                      className="rounded border border-red-400/30 px-2 py-0.5 font-mono text-[10px] uppercase text-red-300/80 hover:bg-red-400/10">Raise flag</button>
                  </span>
                )}
              </li>
            ))}
          </ul>
          {openLeft > 0 ? (
            <p className="mt-4 text-xs text-paper/45">{openLeft} rule(s) still need to be applied — mark satisfied or raise a flag.</p>
          ) : !v && (
            <div className="mt-4"><Button disabled={busy === "fin"} onClick={() => act("fin", () => api(`/runs/${run.id}/findings`, { method: "POST" }))}>{busy === "fin" ? "Finalizing…" : "Finalize flags"}</Button></div>
          )}
        </div>
      )}
    </Card>
  );
}

function OwnershipPanel({ o }: { o: Ownership }) {
  const rows: [string, string | null][] = [
    ["Agent created the work", o.agent_created],
    ["Audited by", o.audited_by],
    ["Referee logic", o.referee_logic],
    ["Final authority", o.final_authority],
    ["Approval", o.approval_status],
    ["Receipt", o.receipt_status],
  ];
  return (
    <Card className="mt-6" title="Ownership & authority" subtitle="The agent does not approve itself">
      <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
        {rows.map(([k, val]) => (
          <div key={k} className="flex justify-between gap-3 border-b border-white/5 py-1">
            <dt className="text-paper/45">{k}</dt>
            <dd className="text-right text-paper/80">{val || "—"}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function ApprovalForm({ runId, busy, act }: { runId: string; busy: string | null; act: Act }) {
  const [note, setNote] = useState("");
  return (
    <div className="space-y-4">
      <Field label="Note (optional)"><input className={inputClass} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why you're approving or rejecting" /></Field>
      <div className="flex gap-3">
        <Button disabled={!!busy} onClick={() => act("approve", () => api(`/runs/${runId}/approve`, { method: "POST", body: { decision: "approved", note } }))}>{busy === "approve" ? "…" : "Approve"}</Button>
        <Button variant="danger" disabled={!!busy} onClick={() => act("reject", () => api(`/runs/${runId}/approve`, { method: "POST", body: { decision: "rejected", note } }))}>Reject</Button>
      </div>
    </div>
  );
}

function ReceiptPanel({ receipt }: { receipt: Receipt }) {
  const [copied, setCopied] = useState(false);
  const shareUrl = `${window.location.origin}/r/${receipt.share_token}`;
  return (
    <div>
      <div className="flex items-center gap-3"><Badge value="receipted" /><span className="font-mono text-sm text-paper/80">{receipt.receipt_id}</span></div>
      <dl className="mt-4 space-y-2 font-mono text-xs">
        <div className="flex gap-3"><dt className="w-32 shrink-0 text-paper/40">receipt_sha256</dt><dd className="break-all text-paper/70">{receipt.receipt_sha256}</dd></div>
        <div className="flex gap-3"><dt className="w-32 shrink-0 text-paper/40">parent_hash</dt><dd className="break-all text-paper/70">{receipt.parent_hash}</dd></div>
      </dl>
      <div className="mt-5 flex flex-wrap gap-3">
        <Button onClick={() => { navigator.clipboard.writeText(shareUrl); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>{copied ? "Copied ✓" : "Copy share link"}</Button>
        <a href={`/r/${receipt.share_token}`} target="_blank" rel="noreferrer"><Button variant="ghost">Open proof page</Button></a>
        <a href={`${apiBase}/share/${receipt.share_token}/pdf`} target="_blank" rel="noreferrer"><Button variant="ghost">PDF</Button></a>
        <a href={`${apiBase}/share/${receipt.share_token}`} target="_blank" rel="noreferrer"><Button variant="ghost">JSON</Button></a>
      </div>
    </div>
  );
}

// ── Phase 4 cook (unchanged behavior) ───────────────────────────────────────
interface Dataset { id: string; name: string; lane: string; pair_count: number; }
interface Cook { id: string; status: string; base_model: string; eval_before: number; eval_after: number | null; lift: number | null; pairs: number; runner: string | null; error: string | null; share_token: string | null; }
const BASE_MODELS = ["swarm/curator-9b", "swarm/curator-27b"];
const COOK_PRICE = "$49";
const pct = (v: number | null) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

function CookSection({ run, reload }: { run: Run; reload: () => Promise<void> }) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [cook, setCook] = useState<Cook | null>(null);
  const [datasetId, setDatasetId] = useState("");
  const [baseModel, setBaseModel] = useState(BASE_MODELS[0]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<{ datasets: Dataset[] }>("/datasets").then((r) => { const lane = r.datasets.filter((d) => d.lane === run.lane); const list = lane.length ? lane : r.datasets; setDatasets(list); if (list[0]) setDatasetId(list[0].id); });
    api<{ cooks: any[] }>("/cooks").then((r) => { const mine = r.cooks.filter((c) => c.run_id === run.id); if (mine[0]) setCook(mine[0]); });
  }, [run.id]);

  useEffect(() => {
    if (!cook || ["succeeded", "failed"].includes(cook.status)) return;
    const t = setInterval(async () => { try { const c = await api<Cook>(`/cooks/${cook.id}`); setCook(c); if (["succeeded", "failed"].includes(c.status)) reload(); } catch { /* */ } }, 4000);
    return () => clearInterval(t);
  }, [cook?.id, cook?.status]);

  async function start() {
    setErr(null); setBusy(true);
    try { setCook(await api<Cook>(`/runs/${run.id}/cook`, { method: "POST", body: { dataset_id: datasetId, base_model: baseModel } })); }
    catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  const rec = run.verdict?.outcome === "pass" ? "Optional — the eval passed. Fine-tune to push the score higher." : "Recommended — fine-tune one of our models on a matched dataset, then re-eval to prove the lift.";

  return (
    <Card className="mt-6" title="Fine-tune" subtitle="Lift the eval, then prove it">
      {cook ? (
        cook.status === "succeeded" ? (
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-lg font-semibold text-paper">{pct(cook.eval_before)} <span className="text-paper/40">→</span> {pct(cook.eval_after)}</span>
              <span className={`rounded-md border px-2 py-0.5 font-mono text-xs ${(cook.lift ?? 0) >= 0 ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300" : "border-red-400/30 bg-red-400/10 text-red-300"}`}>{cook.lift != null ? `${cook.lift >= 0 ? "+" : ""}${(cook.lift * 100).toFixed(1)}%` : "—"}</span>
            </div>
            <p className="mt-2 text-sm text-paper/55">{cook.base_model} · {cook.pairs} pairs{cook.runner ? ` · ${cook.runner}` : ""}</p>
            {cook.share_token && <div className="mt-4 flex gap-3"><a href={`/r/${cook.share_token}`} target="_blank" rel="noreferrer"><Button variant="ghost">View lift proof</Button></a><a href={`${apiBase}/share/${cook.share_token}/pdf`} target="_blank" rel="noreferrer"><Button variant="ghost">PDF</Button></a></div>}
          </div>
        ) : cook.status === "failed" ? (
          <div><ErrorNote>Cook failed: {cook.error}</ErrorNote><div className="mt-3"><Button variant="ghost" onClick={() => setCook(null)}>Try another cook</Button></div></div>
        ) : (
          <div className="flex items-center gap-3"><Spinner label={`Cooking… (${cook.status})`} /><span className="text-xs text-paper/40">on {cook.runner || "the rig"}</span></div>
        )
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-paper/60">{rec}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Dataset"><select className={inputClass} value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>{datasets.map((d) => <option key={d.id} value={d.id}>{d.name} · {d.pair_count} pairs</option>)}</select></Field>
            <Field label="Base model"><select className={inputClass} value={baseModel} onChange={(e) => setBaseModel(e.target.value)}>{BASE_MODELS.map((m) => <option key={m} value={m}>{m}</option>)}</select></Field>
          </div>
          <div className="flex flex-wrap items-center gap-4 border-t border-white/5 pt-4">
            <Button disabled={busy || !datasetId} onClick={start}>{busy ? "Starting…" : `Start fine-tune cook · ${COOK_PRICE}`}</Button>
            <span className="text-xs text-paper/40">Flat per cook — tune + re-eval + proof. Compute on the receipt.</span>
          </div>
          {err && <ErrorNote>{err}</ErrorNote>}
        </div>
      )}
    </Card>
  );
}
