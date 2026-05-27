import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, apiBase } from "../lib/api";
import { Button, Card, ErrorNote, Spinner } from "../components/ui";

export interface Incident {
  id: string; kind: string; tier: string; title: string; detail: string | null;
  lane: string | null; response: string[]; status: string;
  agent_profile_id: string | null; agent_profile_name: string | null;
  run_id: string | null; receipt_id: string | null; share_token?: string | null;
  created_at: string; resolved_at: string | null;
}

const KIND_TONE: Record<string, string> = {
  rogue: "border-red-400/40 bg-red-400/10 text-red-300",
  dark: "border-zinc-400/40 bg-zinc-400/10 text-zinc-300",
  policy_violation: "border-amber-400/40 bg-amber-400/10 text-amber-300",
  recurring_flag: "border-red-400/40 bg-red-400/10 text-red-300",
};

export function IncidentCard({ inc, onChange }: { inc: Incident; onChange?: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  async function act(key: string, fn: () => Promise<unknown>) {
    setErr(null); setBusy(key);
    try { await fn(); onChange?.(); } catch (e: any) { setErr(e.message); } finally { setBusy(null); }
  }
  return (
    <li className="rounded-lg border border-white/8 bg-white/[0.02] p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase ${KIND_TONE[inc.kind] || "border-white/15 text-paper/60"}`}>{inc.kind.replace(/_/g, " ")}</span>
        <span className="text-sm font-medium text-paper/85">{inc.title}</span>
        <span className={`ml-auto font-mono text-[10px] uppercase ${inc.status === "open" ? "text-amber-300" : "text-emerald-300/70"}`}>{inc.status}</span>
      </div>
      <p className="mt-1 text-xs text-paper/45">
        {inc.agent_profile_name && <Link to={`/agents/${inc.agent_profile_id}`} className="hover:text-paper">{inc.agent_profile_name}</Link>}
        {inc.lane ? ` · ${inc.lane}` : ""} · {new Date(inc.created_at).toLocaleString()}
      </p>
      {inc.detail && <p className="mt-2 text-sm text-paper/60">{inc.detail}</p>}
      {inc.response?.length > 0 && (
        <p className="mt-2 font-mono text-[11px] text-paper/45">response: {inc.response.map((r) => r.replace(/_/g, " ")).join(" · ")}</p>
      )}
      {err && <div className="mt-2"><ErrorNote>{err}</ErrorNote></div>}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {inc.share_token ? (
          <>
            <a href={`/r/${inc.share_token}`} target="_blank" rel="noreferrer"><Button variant="ghost">View incident receipt</Button></a>
            <a href={`${apiBase}/share/${inc.share_token}/pdf`} target="_blank" rel="noreferrer"><Button variant="ghost">PDF</Button></a>
          </>
        ) : (
          <Button variant="ghost" disabled={busy === "rcpt"} onClick={() => act("rcpt", () => api(`/incidents/${inc.id}/receipt`, { method: "POST" }))}>{busy === "rcpt" ? "Issuing…" : "Issue incident receipt"}</Button>
        )}
        {inc.status === "open" && (
          <Button variant="ghost" disabled={busy === "res"} onClick={() => act("res", () => api(`/incidents/${inc.id}`, { method: "PATCH", body: { status: "resolved" } }))}>{busy === "res" ? "…" : "Resolve"}</Button>
        )}
      </div>
    </li>
  );
}

export function Incidents() {
  const [incidents, setIncidents] = useState<Incident[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = () => api<{ incidents: Incident[] }>("/incidents").then((r) => setIncidents(r.incidents)).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  if (err) return <ErrorNote>{err}</ErrorNote>;
  if (!incidents) return <Spinner label="Loading incidents…" />;

  const open = incidents.filter((i) => i.status === "open");
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight text-paper">Incidents</h1>
      <p className="mt-1 text-sm text-paper/55">Everyone alerts. We receipt the incident — what tripped, the response, hash-chained into the same ledger as the work.</p>

      {incidents.length === 0 ? (
        <Card className="mt-6"><p className="text-sm text-paper/55">No incidents. Run the watchdog on an agent profile to scan its earned lanes for recurring critical flags.</p></Card>
      ) : (
        <>
          {open.length > 0 && <p className="mt-6 text-xs font-semibold uppercase tracking-widest text-amber-300/80">{open.length} open</p>}
          <ul className="mt-3 space-y-3">
            {incidents.map((inc) => <IncidentCard key={inc.id} inc={inc} onChange={load} />)}
          </ul>
        </>
      )}
    </div>
  );
}
