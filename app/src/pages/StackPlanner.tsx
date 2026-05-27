import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Button, Card, ErrorNote, Field, inputClass, Spinner } from "../components/ui";

interface TaskClass { key: string; label: string; min_model: string; client_facing?: boolean; high_stakes?: boolean; autonomous?: boolean; }
interface Lane { key: string; label: string; min_model: string; why?: string; }
interface Earned { profile: string; tier: string | null; lane: string; status: string; }
interface Assessment {
  deployment: string; model_label: string; compute_label: string;
  owner_fit: string; cloud_fit: string; cost_band: string; human_approval_required: boolean;
  approved_lanes: Lane[]; restricted_lanes: Lane[]; blocked_lanes: Lane[];
  reasons: string[]; summary: string; earned_lanes: Earned[]; next_step: string;
}

const DEPLOY_TONE: Record<string, string> = {
  owner: "border-sky-400/40 bg-sky-400/10 text-sky-300",
  cloud: "border-honey-400/40 bg-honey-300/10 text-honey-200",
  hybrid: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
};
const FIT_TONE: Record<string, string> = { strong: "text-emerald-300", partial: "text-amber-300", none: "text-red-300" };

export function StackPlanner() {
  const [tasks, setTasks] = useState<TaskClass[]>([]);
  const [jobs, setJobs] = useState<Set<string>>(new Set());
  const [flags, setFlags] = useState({ needs_24_7: false, client_facing: false, high_stakes: false, data_local_only: false });
  const [pref, setPref] = useState("no_pref");
  const [budget, setBudget] = useState("");
  const [result, setResult] = useState<Assessment | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { api<{ task_classes: TaskClass[] }>("/stack-planner/options").then((r) => setTasks(r.task_classes)).catch((e) => setErr(e.message)); }, []);

  const toggleJob = (k: string) => setJobs((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });

  async function assess() {
    setErr(null); setBusy(true); setResult(null);
    try {
      const body = { jobs: [...jobs], ...flags, deployment_pref: pref, budget: budget || null };
      setResult(await api<Assessment>("/stack-assessment", { method: "POST", body }));
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  const LaneList = ({ title, tone, items }: { title: string; tone: string; items: Lane[] }) =>
    items.length === 0 ? null : (
      <div>
        <p className={`text-xs font-semibold uppercase tracking-widest ${tone}`}>{title}</p>
        <ul className="mt-1.5 space-y-1 text-sm">
          {items.map((l) => <li key={l.key} className="text-paper/75">{l.label}{l.why && <span className="text-paper/40"> — {l.why}</span>}</li>)}
        </ul>
      </div>
    );

  if (!tasks.length && !err) return <Spinner label="Loading the planner…" />;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight text-paper">Agent Stack Planner</h1>
      <p className="mt-2 text-sm text-paper/60">
        AI agents don't run on magic. Tell us the work — we map it to the brain, the compute, the deployment, the cost,
        and the lanes it can safely run. Rulebook-driven, not opinion. Proof comes from running the eval.
      </p>

      <Card className="mt-6" title="What should the agent do?" subtitle="Pick every job you expect it to handle">
        <div className="grid gap-2 sm:grid-cols-2">
          {tasks.map((t) => {
            const on = jobs.has(t.key);
            return (
              <button key={t.key} onClick={() => toggleJob(t.key)}
                className={`rounded-lg border px-3 py-2.5 text-left text-sm transition-colors ${on ? "border-honey-400/60 bg-honey-300/[0.06] text-paper" : "border-white/8 bg-white/[0.02] text-paper/70 hover:border-white/20"}`}>
                <span className="flex items-center justify-between gap-2">
                  {t.label}
                  <span className="font-mono text-[9px] uppercase text-paper/35">{t.min_model}</span>
                </span>
              </button>
            );
          })}
        </div>
      </Card>

      <Card className="mt-6" title="How will it run?">
        <div className="grid gap-3 sm:grid-cols-2">
          {([["needs_24_7", "Runs 24/7"], ["client_facing", "Output is client-facing"], ["high_stakes", "Math / finance / legal involved"], ["data_local_only", "Data must stay local (privacy)"]] as const).map(([k, label]) => (
            <label key={k} className="flex items-center gap-2.5 rounded-lg border border-white/8 bg-white/[0.02] px-3 py-2.5 text-sm text-paper/75">
              <input type="checkbox" checked={(flags as any)[k]} onChange={(e) => setFlags((f) => ({ ...f, [k]: e.target.checked }))} className="h-4 w-4 accent-honey-400" />
              {label}
            </label>
          ))}
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Field label="Deployment preference">
            <select className={inputClass} value={pref} onChange={(e) => setPref(e.target.value)}>
              <option value="no_pref">No preference</option>
              <option value="owner">Owner-compute (my hardware)</option>
              <option value="cloud">Cloud-compute (hosted)</option>
              <option value="hybrid">Hybrid</option>
            </select>
          </Field>
          <Field label="Budget (optional)">
            <select className={inputClass} value={budget} onChange={(e) => setBudget(e.target.value)}>
              <option value="">—</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </Field>
        </div>
      </Card>

      {err && <div className="mt-6"><ErrorNote>{err}</ErrorNote></div>}
      <div className="mt-6"><Button disabled={busy || jobs.size === 0} onClick={assess}>{busy ? "Assessing…" : "Assess the stack"}</Button></div>

      {result && (
        <Card className="mt-8" title="Stack assessment" subtitle="Deterministic — same inputs, same answer, every time">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`rounded-md border px-3 py-1 text-sm font-semibold uppercase ${DEPLOY_TONE[result.deployment] || "border-white/15 text-paper/70"}`}>{result.deployment} deployment</span>
            {result.human_approval_required && <span className="rounded-md border border-amber-400/30 bg-amber-400/10 px-2.5 py-1 text-xs font-semibold uppercase text-amber-300">human approval required</span>}
          </div>
          <p className="mt-3 text-sm font-medium text-paper/85">{result.summary}</p>

          <dl className="mt-4 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
            <div className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">Brain</dt><dd className="text-paper/80">{result.model_label}</dd></div>
            <div className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">Compute</dt><dd className="text-paper/80">{result.compute_label}</dd></div>
            <div className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">Cost band</dt><dd className="text-paper/80">{result.cost_band}</dd></div>
            <div className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">Owner-compute fit</dt><dd className={FIT_TONE[result.owner_fit]}>{result.owner_fit}</dd></div>
          </dl>

          <div className="mt-5 space-y-4">
            <LaneList title="Approved lanes" tone="text-emerald-300/80" items={result.approved_lanes} />
            <LaneList title="Restricted (approval / limits)" tone="text-amber-300/80" items={result.restricted_lanes} />
            <LaneList title="Blocked — needs a bigger stack" tone="text-red-300/80" items={result.blocked_lanes} />
          </div>

          {result.reasons.length > 0 && (
            <div className="mt-5 rounded-md border border-white/8 bg-white/[0.02] p-3">
              <p className="text-xs font-semibold uppercase tracking-widest text-paper/35">Why</p>
              <ul className="mt-1.5 space-y-1 text-sm text-paper/70">{result.reasons.map((r, i) => <li key={i}>· {r}</li>)}</ul>
            </div>
          )}

          {result.earned_lanes.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-paper/35">You've already earned</p>
              <ul className="mt-1.5 space-y-1 text-sm text-paper/70">
                {result.earned_lanes.map((e, i) => <li key={i}>· <span className="text-paper/85">{e.profile}</span>{e.tier ? ` (${e.tier})` : ""} — {e.lane} <span className={e.status === "approved" ? "text-emerald-300/80" : "text-amber-300/80"}>[{e.status}]</span></li>)}
              </ul>
            </div>
          )}

          <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-white/5 pt-4">
            <Link to="/runs/new"><Button>Run an eval to prove it</Button></Link>
            <span className="text-xs text-paper/40">{result.next_step}</span>
          </div>
        </Card>
      )}
    </div>
  );
}
