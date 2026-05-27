import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Badge, Button, Card, ErrorNote, Spinner } from "../components/ui";
import { IncidentCard, type Incident } from "./Incidents";

interface Lane { flight_sheet_id: string; name: string; lane: string; status: string; honey: number; jelly: number; propolis: number; total: number; }
interface FlagCount { label: string; count: number; severity: string | null; category: string; }
interface Latest { run_id: string; title: string; severity: string; score_100: number; created_at: string; }
interface Capability {
  evaluated_runs: number; total_runs: number;
  verdict_counts: { honey: number; jelly: number; propolis: number };
  latest: Latest | null;
  pass_rates: { category: string; label: string; rate: number; n: number }[];
  recurring_flags: FlagCount[];
  lane_authorizations: Lane[];
  overall_status: string;
  history: { run_id: string; title: string; status: string; severity: string | null; score_100: number | null; created_at: string }[];
}
interface Profile {
  id: string; name: string; harness: string | null; harness_version: string | null;
  model: string | null; model_provider: string | null; served_by: string | null;
  runtime_host: string | null; runtime_os: string | null; runtime_hardware: string | null;
  tools: string[]; context_window: number | null; capability_tier: string | null; notes: string | null;
  governance?: { requires_approval_client_output?: boolean; spend_cap_usd?: number; blocked_lanes?: string[]; notes?: string };
  summary?: { overall_status: string; evaluated_runs: number; verdict_counts: { honey: number; jelly: number; propolis: number }; latest: Latest | null; approved_lanes: string[]; blocked_lanes: string[]; recurring_flags: FlagCount[]; };
  capability?: Capability;
}

const STATUS_TONE: Record<string, string> = {
  approved: "border-emerald-400/40 bg-emerald-400/10 text-emerald-300",
  testing: "border-sky-400/30 bg-sky-400/10 text-sky-300",
  restricted: "border-amber-400/40 bg-amber-400/10 text-amber-300",
  blocked: "border-red-400/40 bg-red-400/10 text-red-300",
};
const SEV_TONE: Record<string, string> = {
  honey: "text-emerald-300", jelly: "text-amber-300", propolis: "text-red-300",
};
const TIER_TONE: Record<string, string> = {
  edge: "border-red-400/40 bg-red-400/10 text-red-300",
  small: "border-amber-400/40 bg-amber-400/10 text-amber-300",
  mid: "border-sky-400/30 bg-sky-400/10 text-sky-300",
  frontier: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
};
const stack = (p: Profile) => [p.harness, p.model, p.runtime_hardware].filter(Boolean).join(" · ");
const StatusPill = ({ s }: { s: string }) => <span className={`rounded-md border px-2 py-0.5 text-xs font-semibold uppercase ${STATUS_TONE[s] || "border-white/15 text-paper/60"}`}>{s}</span>;

export function AgentProfiles() {
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api<{ agent_profiles: Profile[] }>("/agent-profiles").then((r) => setProfiles(r.agent_profiles)).catch((e) => setErr(e.message)); }, []);

  if (err) return <ErrorNote>{err}</ErrorNote>;
  if (!profiles) return <Spinner label="Loading agent profiles…" />;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-paper">Agent Profiles</h1>
          <p className="mt-1 text-sm text-paper/55">Agents earn their lanes. A model name isn't trust — a track record under the rulebook is.</p>
        </div>
        <Link to="/runs/new"><Button variant="ghost">New eval</Button></Link>
      </div>

      {profiles.length === 0 ? (
        <Card className="mt-6"><p className="text-sm text-paper/55">No agent profiles yet. Define one when you create a New Run — the stack that did the work.</p></Card>
      ) : (
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {profiles.map((p) => {
            const s = p.summary;
            return (
              <Link key={p.id} to={`/agents/${p.id}`} className="block rounded-xl border border-white/8 bg-white/[0.02] p-5 transition-colors hover:border-white/20">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-semibold text-paper">{p.name}</h3>
                  {s && <StatusPill s={s.overall_status} />}
                </div>
                <p className="mt-1 font-mono text-[11px] text-paper/45">{stack(p) || "—"}{p.capability_tier ? ` · ${p.capability_tier}` : ""}</p>
                {s && (
                  <div className="mt-3 space-y-1.5 text-sm">
                    <p className="text-paper/55">{s.evaluated_runs} eval(s) · <span className={SEV_TONE.honey}>{s.verdict_counts.honey}H</span> <span className={SEV_TONE.jelly}>{s.verdict_counts.jelly}J</span> <span className={SEV_TONE.propolis}>{s.verdict_counts.propolis}P</span></p>
                    {s.approved_lanes.length > 0 && <p className="text-xs text-emerald-300/80">Approved: {s.approved_lanes.join(", ")}</p>}
                    {s.blocked_lanes.length > 0 && <p className="text-xs text-amber-300/80">Watch/blocked: {s.blocked_lanes.join(", ")}</p>}
                    {s.recurring_flags.length > 0 && <p className="text-xs text-paper/40">Recurring: {s.recurring_flags.map((f) => `${f.label} ×${f.count}`).join(" · ")}</p>}
                  </div>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AgentProfileDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [p, setP] = useState<Profile | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  function load() {
    api<Profile>(`/agent-profiles/${id}`).then(setP).catch((e) => setErr(e.message));
    api<{ incidents: Incident[] }>(`/incidents?agent_profile_id=${id}`).then((r) => setIncidents(r.incidents)).catch(() => {});
  }
  useEffect(() => { load(); }, [id]);
  async function watchdog() {
    setErr(null); setBusy("watchdog");
    try { await api(`/agent-profiles/${id}/watchdog`, { method: "POST" }); load(); }
    catch (e: any) { setErr(e.message); } finally { setBusy(null); }
  }

  if (err && !p) return <ErrorNote>{err}</ErrorNote>;
  if (!p || !p.capability) return <Spinner label="Loading profile…" />;
  const cap = p.capability;
  const gov = p.governance || {};
  const locked = gov.blocked_lanes || [];

  const stackRows: [string, string | null][] = [
    ["Harness — the body", p.harness ? `${p.harness}${p.harness_version ? ` v${p.harness_version}` : ""}` : null],
    ["Model — the brain", p.model ? `${p.model}${p.model_provider ? ` · ${p.model_provider}` : ""}${p.served_by ? ` · ${p.served_by}` : ""}` : null],
    ["Runtime — the ground", [p.runtime_host, p.runtime_hardware, p.runtime_os].filter(Boolean).join(" · ") || null],
    ["Tools — the hands", p.tools?.length ? p.tools.join(", ") : null],
    ["Context window", p.context_window ? `${p.context_window.toLocaleString()} tokens` : null],
  ];

  return (
    <div className="mx-auto max-w-3xl">
      <button onClick={() => nav("/agents")} className="mb-6 text-sm text-paper/50 hover:text-paper">← Agent Profiles</button>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            {p.capability_tier && <span className={`rounded-md border px-2 py-0.5 text-xs font-semibold uppercase ${TIER_TONE[p.capability_tier] || "border-white/15 text-paper/60"}`}>{p.capability_tier} tier</span>}
            <StatusPill s={cap.overall_status} />
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-paper">{p.name}</h1>
          <p className="mt-1 font-mono text-xs text-paper/45">{stack(p)}</p>
        </div>
        <Link to={`/runs/new?profile=${p.id}`}><Button>Run new eval</Button></Link>
      </div>

      {/* Stack */}
      <Card className="mt-6" title="The stack">
        <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
          {stackRows.filter(([, v]) => v).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">{k}</dt><dd className="text-right font-mono text-xs text-paper/80">{v}</dd></div>
          ))}
        </dl>
        {p.notes && <p className="mt-3 text-sm text-paper/55">{p.notes}</p>}
      </Card>

      {/* Earned lanes */}
      <Card className="mt-6" title="Lane authorizations" subtitle="Earned from receipts — ≥3 honey & 0 propolis = approved · 1 propolis = restricted · recurring = blocked">
        {cap.lane_authorizations.length === 0 ? (
          <p className="text-sm text-paper/50">No evaluated runs yet — run an eval to start earning lanes.</p>
        ) : (
          <ul className="space-y-2">
            {cap.lane_authorizations.map((l) => (
              <li key={l.flight_sheet_id} className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 py-2 text-sm">
                <span className="text-paper/80">{l.name}</span>
                <span className="flex items-center gap-3">
                  <span className="font-mono text-[11px] text-paper/45"><span className={SEV_TONE.honey}>{l.honey}H</span> <span className={SEV_TONE.jelly}>{l.jelly}J</span> <span className={SEV_TONE.propolis}>{l.propolis}P</span></span>
                  <StatusPill s={l.status} />
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* Agent Ops — governance + incidents */}
      <Card className="mt-6" title="Agent Ops" subtitle="Everyone alerts; we receipt the incident"
        actions={<Button variant="ghost" disabled={busy === "watchdog"} onClick={watchdog}>{busy === "watchdog" ? "Scanning…" : "Run watchdog scan"}</Button>}>
        <p className="text-sm text-paper/55">Watchdog locks any lane with recurring critical flags and opens an incident — deterministic, straight from the receipts. Live dark/rogue triggers plug in when Core reports heartbeats.</p>
        <dl className="mt-4 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
          <div className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">Locked lanes</dt><dd className={`text-right ${locked.length ? "text-red-300" : "text-paper/60"}`}>{locked.length ? locked.join(", ") : "none"}</dd></div>
          <div className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">Client-output approval</dt><dd className="text-right text-paper/70">{gov.requires_approval_client_output ? "required" : "—"}</dd></div>
          {gov.spend_cap_usd != null && <div className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">Spend cap</dt><dd className="text-right text-paper/70">${gov.spend_cap_usd}</dd></div>}
          <div className="flex justify-between gap-3 border-b border-white/5 py-1"><dt className="text-paper/45">Tools (hands)</dt><dd className="text-right font-mono text-xs text-paper/70">{p.tools?.length ? p.tools.join(", ") : "—"}</dd></div>
        </dl>
        {incidents.length > 0 && (
          <ul className="mt-4 space-y-3">
            {incidents.map((inc) => <IncidentCard key={inc.id} inc={inc} onChange={load} />)}
          </ul>
        )}
      </Card>

      {/* Capability — pass rates */}
      {cap.pass_rates.length > 0 && (
        <Card className="mt-6" title="Capability (measured)" subtitle={`${cap.evaluated_runs} evaluated run(s) · pass-rate by check class`}>
          <div className="space-y-3">
            {cap.pass_rates.map((r) => (
              <div key={r.category}>
                <div className="flex justify-between text-xs"><span className="text-paper/65">{r.label}</span><span className="font-mono text-paper/50">{Math.round(r.rate * 100)}% · n={r.n}</span></div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/8">
                  <div className={`h-full ${r.rate >= 0.85 ? "bg-emerald-400/70" : r.rate >= 0.6 ? "bg-amber-400/70" : "bg-red-400/70"}`} style={{ width: `${Math.round(r.rate * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
          {cap.recurring_flags.length > 0 && (
            <div className="mt-5 border-t border-white/5 pt-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-paper/40">Recurring flags</p>
              <ul className="mt-2 space-y-1 text-sm">
                {cap.recurring_flags.map((f) => (
                  <li key={f.label} className="flex justify-between gap-3"><span className="text-paper/70">{f.label} <span className="text-paper/35">({f.category})</span></span><span className="font-mono text-xs text-paper/45">×{f.count}</span></li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* History */}
      <Card className="mt-6" title="Eval history">
        {cap.history.length === 0 ? <p className="text-sm text-paper/50">No runs yet.</p> : (
          <ul className="space-y-1.5">
            {cap.history.map((h) => (
              <li key={h.run_id}>
                <Link to={`/runs/${h.run_id}`} className="flex flex-wrap items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-white/5">
                  <span className="text-paper/75">{h.title}</span>
                  <span className="flex items-center gap-3">
                    {h.severity ? <span className={`font-mono text-xs ${SEV_TONE[h.severity] || "text-paper/50"}`}>{h.severity} · {h.score_100}/100</span> : <Badge value={h.status.replace(/_/g, " ")} />}
                    <span className="font-mono text-[10px] text-paper/30">{new Date(h.created_at).toLocaleDateString()}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
