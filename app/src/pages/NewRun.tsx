import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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

export function NewRun() {
  const nav = useNavigate();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [sheets, setSheets] = useState<FlightSheet[]>([]);
  const [projectId, setProjectId] = useState("");
  const [newProject, setNewProject] = useState("");
  const [sheetId, setSheetId] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api<{ projects: Project[] }>("/projects"),
      api<{ flight_sheets: FlightSheet[] }>("/flight-sheets"),
    ])
      .then(([p, f]) => {
        setProjects(p.projects);
        setProjectId(p.projects[0]?.id ?? "__new__");
        setSheets(f.flight_sheets);
      })
      .catch((e) => setErr(e.message));
  }, []);

  async function create() {
    setErr(null);
    setBusy(true);
    try {
      let pid = projectId;
      if (pid === "__new__") {
        if (!newProject.trim()) throw new Error("name the project");
        pid = (await api<Project>("/projects", { method: "POST", body: { name: newProject.trim() } })).id;
      }
      const run = await api<{ id: string }>("/runs", { method: "POST", body: { project_id: pid, flight_sheet_id: sheetId } });
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
