import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Button, Callout, Card, ErrorNote, ExampleList, Field, inputClass, Spinner } from "../components/ui";
import { LANES, laneGuide } from "../lib/guidance";

interface Project {
  id: string;
  name: string;
}

export function NewRun() {
  const nav = useNavigate();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [projectId, setProjectId] = useState<string>("");
  const [newProject, setNewProject] = useState("");
  const [lane, setLane] = useState("agent");
  const [title, setTitle] = useState("");
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<{ projects: Project[] }>("/projects")
      .then((r) => {
        setProjects(r.projects);
        if (r.projects.length) setProjectId(r.projects[0].id);
        else setProjectId("__new__");
      })
      .catch((e) => setErr(e.message));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      let pid = projectId;
      if (pid === "__new__") {
        if (!newProject.trim()) throw new Error("name the project");
        const p = await api<Project>("/projects", { method: "POST", body: { name: newProject.trim() } });
        pid = p.id;
      }
      const run = await api<{ id: string }>("/runs", {
        method: "POST",
        body: { project_id: pid, lane, title: title.trim(), inputs },
      });
      nav(`/runs/${run.id}`);
    } catch (e: any) {
      setErr(e.message || "could not create the run");
      setBusy(false);
    }
  }

  if (!projects && !err) return <Spinner label="Loading projects…" />;

  return (
    <div className="mx-auto max-w-xl">
      <button onClick={() => nav("/")} className="mb-6 text-sm text-paper/50 hover:text-paper">← Dashboard</button>
      <h1 className="text-2xl font-semibold tracking-tight text-paper">New Run</h1>
      <p className="mt-2 text-sm text-paper/60">Everything is a Run. Pick the kind of work and give it a title.</p>

      <Card className="mt-6">
        <form onSubmit={submit} className="space-y-5">
          <Field label="Project">
            <select className={inputClass} value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects?.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
              <option value="__new__">+ New project…</option>
            </select>
          </Field>
          {projectId === "__new__" && (
            <Field label="New project name">
              <input className={inputClass} value={newProject} onChange={(e) => setNewProject(e.target.value)} placeholder="e.g. CRE Memo Reviews" />
            </Field>
          )}

          <Field label="Lane">
            <select
              className={inputClass}
              value={lane}
              onChange={(e) => {
                setLane(e.target.value);
                setInputs({});
              }}
            >
              {LANES.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </Field>

          <Callout title={`${laneGuide(lane).label} run`}>
            {laneGuide(lane).what}
            <span className="mt-2 block text-xs text-paper/40">For example:</span>
            <ExampleList items={laneGuide(lane).examples} />
          </Callout>

          <Field label="Title">
            <input className={inputClass} required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="What this run is" />
          </Field>

          {laneGuide(lane).inputs.map((f) => (
            <Field key={f.key} label={f.label}>
              <input
                className={inputClass}
                value={inputs[f.key] || ""}
                onChange={(e) => setInputs((s) => ({ ...s, [f.key]: e.target.value }))}
                placeholder={f.placeholder}
              />
            </Field>
          ))}

          {err && <ErrorNote>{err}</ErrorNote>}
          <Button type="submit" disabled={busy}>{busy ? <Spinner label="Creating…" /> : "Create run"}</Button>
        </form>
      </Card>
    </div>
  );
}
