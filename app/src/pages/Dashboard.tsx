import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Badge, Button, Card, ErrorNote, Spinner } from "../components/ui";
import { LANES } from "../lib/guidance";

interface RunRow {
  id: string;
  lane: string;
  title: string;
  status: string;
  verdict: string | null;
  created_at: string;
}

const LANE_LABEL: Record<string, string> = {
  agent: "Agent",
  dataset: "Dataset",
  compute: "Compute",
  other: "Other",
};

export function Dashboard() {
  const { me } = useAuth();
  const nav = useNavigate();
  const [runs, setRuns] = useState<RunRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<{ runs: RunRow[] }>("/runs")
      .then((r) => setRuns(r.runs))
      .catch((e) => setErr(e.message));
  }, []);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-widest text-honey-300">
            {me?.org_name || "Your workspace"}
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-paper">
            Create Proof of Execution for agentic work.
          </h1>
        </div>
        <Button onClick={() => nav("/runs/new")}>+ New Run</Button>
      </div>

      <div className="mt-10">
        <h2 className="mb-4 text-xs font-medium uppercase tracking-widest text-paper/40">Recent runs</h2>
        {err && <ErrorNote>{err}</ErrorNote>}
        {!runs && !err && <Spinner />}
        {runs && runs.length === 0 && (
          <Card>
            <p className="text-sm leading-relaxed text-paper/65">
              No runs yet. Every run is one primitive — <span className="text-paper/80">inputs → evidence → checks → verdict → approval → receipt</span>.
              Pick the kind of work you need to prove:
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {LANES.filter((l) => l.value !== "other").map((l) => (
                <div key={l.value} className="rounded-lg border border-white/8 bg-white/[0.02] p-4">
                  <div className="font-mono text-xs uppercase tracking-widest text-honey-300/70">{l.label}</div>
                  <p className="mt-1.5 text-xs leading-relaxed text-paper/55">{l.what}</p>
                  <p className="mt-2 text-xs italic text-paper/40">e.g. {l.examples[0]}</p>
                </div>
              ))}
            </div>
            <div className="mt-6">
              <Button onClick={() => nav("/runs/new")}>Create your first run</Button>
            </div>
          </Card>
        )}
        {runs && runs.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-white/8 bg-white/[0.02] divide-y divide-white/5">
            {runs.map((r) => (
              <Link
                key={r.id}
                to={`/runs/${r.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-white/[0.03]"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-honey-300/70">{LANE_LABEL[r.lane] || r.lane}</span>
                    <span className="truncate font-medium text-paper">{r.title}</span>
                  </div>
                  <div className="mt-0.5 text-xs text-paper/40">{new Date(r.created_at).toLocaleString()}</div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {r.verdict && <Badge value={r.verdict} />}
                  <Badge value={r.status} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
