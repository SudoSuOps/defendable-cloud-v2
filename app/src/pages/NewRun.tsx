import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { Button, Card, ErrorNote, Field, inputClass, Spinner } from "../components/ui";

interface Project {
  id: string;
  name: string;
}
interface FlightSheet {
  id: string;
  name: string;
  version: string;
  lane: string;
  summary: string;
  expected_outputs: string[];
  audit_checks: { kind: string }[];
}

const LANE_LABEL: Record<string, string> = { agent: "Agent Work", dataset: "Dataset", compute: "Compute", other: "Document" };

interface AgentProfile { id: string; name: string; capability_tier: string | null; harness: string | null; model: string | null; }
const TIERS = ["edge", "small", "mid", "frontier"];
const emptyProfile = { name: "", harness: "", harness_version: "", model: "", model_provider: "", served_by: "", runtime_host: "", runtime_os: "", runtime_hardware: "", capability_tier: "" };

export function NewRun() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [sheets, setSheets] = useState<FlightSheet[]>([]);
  const [profiles, setProfiles] = useState<AgentProfile[]>([]);
  const [projectId, setProjectId] = useState("");
  const [newProject, setNewProject] = useState("");
  const [sheetId, setSheetId] = useState("");
  const [profileId, setProfileId] = useState("");
  const [np, setNp] = useState({ ...emptyProfile });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api<{ projects: Project[] }>("/projects"),
      api<{ flight_sheets: FlightSheet[] }>("/flight-sheets"),
      api<{ agent_profiles: AgentProfile[] }>("/agent-profiles"),
    ])
      .then(([p, f, ap]) => {
        setProjects(p.projects);
        setProjectId(p.projects[0]?.id ?? "__new__");
        setSheets(f.flight_sheets);
        setProfiles(ap.agent_profiles);
        const pre = params.get("profile");
        if (pre && ap.agent_profiles.some((x) => x.id === pre)) setProfileId(pre);
      })
      .catch((e) => setErr(e.message));
  }, []);

  const setNpField = (k: keyof typeof emptyProfile, v: string) => setNp((s) => ({ ...s, [k]: v }));

  async function create() {
    setErr(null);
    setBusy(true);
    try {
      let pid = projectId;
      if (pid === "__new__") {
        if (!newProject.trim()) throw new Error("name the project");
        pid = (await api<Project>("/projects", { method: "POST", body: { name: newProject.trim() } })).id;
      }
      let apid: string | undefined = profileId && profileId !== "__new__" ? profileId : undefined;
      if (profileId === "__new__") {
        if (!np.name.trim()) throw new Error("name the agent profile");
        const body: Record<string, unknown> = { name: np.name.trim() };
        (Object.keys(emptyProfile) as (keyof typeof emptyProfile)[]).forEach((k) => { if (k !== "name" && np[k]) body[k] = np[k]; });
        apid = (await api<AgentProfile>("/agent-profiles", { method: "POST", body })).id;
      }
      const run = await api<{ id: string }>("/runs", { method: "POST", body: { project_id: pid, flight_sheet_id: sheetId, agent_profile_id: apid } });
      nav(`/runs/${run.id}`);
    } catch (e: any) {
      setErr(e.message);
      setBusy(false);
    }
  }

  if (!projects && !err) return <Spinner label="Loading flight sheets…" />;

  return (
    <div className="mx-auto max-w-3xl">
      <button onClick={() => nav("/")} className="mb-6 text-sm text-paper/50 hover:text-paper">← Runs</button>
      <h1 className="text-2xl font-semibold tracking-tight text-paper">New Eval Run</h1>
      <p className="mt-2 text-sm text-paper/60">
        Pick a flight sheet — the game plan. It defines the assignment, the audit checks, and the
        pass thresholds. Give the agent the assignment, paste back its output, run the referee.
      </p>

      <Card className="mt-6">
        <Field label="Project">
          <select className={inputClass} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            {projects?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            <option value="__new__">+ New project…</option>
          </select>
        </Field>
        {projectId === "__new__" && (
          <div className="mt-4">
            <Field label="New project name">
              <input className={inputClass} value={newProject} onChange={(e) => setNewProject(e.target.value)} placeholder="e.g. IC Reviews" />
            </Field>
          </div>
        )}
      </Card>

      <Card className="mt-6">
        <Field label="Agent profile (the stack — optional)">
          <select className={inputClass} value={profileId} onChange={(e) => setProfileId(e.target.value)}>
            <option value="">— none / decide at submission —</option>
            {profiles.map((p) => <option key={p.id} value={p.id}>{p.name}{p.capability_tier ? ` · ${p.capability_tier}` : ""}</option>)}
            <option value="__new__">+ New profile…</option>
          </select>
        </Field>
        {profileId === "__new__" && (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <input className={`${inputClass} sm:col-span-2`} value={np.name} onChange={(e) => setNpField("name", e.target.value)} placeholder="Profile name (e.g. Kimi-Claw-Jetson-3B)" />
            <input className={inputClass} value={np.harness} onChange={(e) => setNpField("harness", e.target.value)} placeholder="Harness / body (claw, claude-code…)" />
            <input className={inputClass} value={np.model} onChange={(e) => setNpField("model", e.target.value)} placeholder="Model / brain (qwen2.5:9b, kimi-k2…)" />
            <input className={inputClass} value={np.model_provider} onChange={(e) => setNpField("model_provider", e.target.value)} placeholder="Model provider (ollama, anthropic…)" />
            <input className={inputClass} value={np.served_by} onChange={(e) => setNpField("served_by", e.target.value)} placeholder="Served by (ollama, api, vllm)" />
            <input className={inputClass} value={np.runtime_host} onChange={(e) => setNpField("runtime_host", e.target.value)} placeholder="Runtime host (sigedge, mac-studio…)" />
            <input className={inputClass} value={np.runtime_hardware} onChange={(e) => setNpField("runtime_hardware", e.target.value)} placeholder="Hardware (Jetson Orin · 8GB shared)" />
            <select className={`${inputClass} sm:col-span-2`} value={np.capability_tier} onChange={(e) => setNpField("capability_tier", e.target.value)}>
              <option value="">Capability tier (declared — proven by receipts)…</option>
              {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        )}
        <p className="mt-3 text-xs text-paper/40">The harness is the body, the model the brain, the runtime the ground. Same harness + bigger runtime = a bigger brain — so capability is <em>proven by receipts</em>, not the name.</p>
      </Card>

      <h2 className="mt-8 mb-3 text-xs font-medium uppercase tracking-widest text-paper/40">Choose a flight sheet</h2>
      <div className="grid gap-4 md:grid-cols-2">
        {sheets.map((s) => {
          const sel = sheetId === s.id;
          return (
            <button
              key={s.id}
              onClick={() => setSheetId(s.id)}
              className={`rounded-xl border p-5 text-left transition-colors ${sel ? "border-honey-400/60 bg-honey-300/[0.06]" : "border-white/8 bg-white/[0.02] hover:border-white/20"}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-widest text-honey-300/70">{LANE_LABEL[s.lane] || s.lane}</span>
                <span className="font-mono text-[10px] text-paper/30">v{s.version}</span>
              </div>
              <h3 className="mt-2 font-semibold text-paper">{s.name}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-paper/60">{s.summary}</p>
              <p className="mt-3 font-mono text-[10px] text-paper/35">
                {s.expected_outputs.length} sections · {s.audit_checks.length} checks
              </p>
            </button>
          );
        })}
      </div>

      {err && <div className="mt-6"><ErrorNote>{err}</ErrorNote></div>}
      <div className="mt-8">
        <Button disabled={busy || !sheetId} onClick={create}>{busy ? "Creating…" : "Create Eval Run"}</Button>
      </div>
    </div>
  );
}
