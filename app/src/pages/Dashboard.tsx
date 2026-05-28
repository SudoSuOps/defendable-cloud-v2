import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Badge, Button, Card, ErrorNote, Spinner } from "../components/ui";
import { RecentReceipts } from "../components/RecentReceipts";
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

// Per-lane receipt filter chips · keep the order from highest-frequency to
// most-occasional so the dashboard ramp feels natural · the v1 lineup is:
// eval (runs) → cook (lifts) → pin (declarations) → incident → download.
const RECEIPT_LANES: { value: string | null; label: string }[] = [
  { value: null, label: "All" },
  { value: "defendablecloud.eval-receipt/v1", label: "Eval" },
  { value: "defendablecloud.cook-receipt/v1", label: "Cook" },
  { value: "defendablecloud.model-pin-receipt/v1", label: "Pin" },
  { value: "defendablecloud.incident-receipt/v1", label: "Incident" },
  { value: "defendablecloud.dataset-download-receipt/v1", label: "Download" },
];

export function Dashboard() {
  const { me } = useAuth();
  const nav = useNavigate();
  const [runs, setRuns] = useState<RunRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [schemaFilter, setSchemaFilter] = useState<string | null>(null);

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
        <div className="mb-3 flex items-baseline justify-between gap-3">
          <h2 className="text-xs font-medium uppercase tracking-widest text-paper/40">Recent receipts</h2>
          <span className="font-mono text-[10px] text-paper/30">on your org chain · latest 5</span>
        </div>
        <div className="mb-3 flex flex-wrap gap-2">
          {RECEIPT_LANES.map((opt) => (
            <ChipButton
              key={opt.label}
              label={opt.label}
              active={schemaFilter === opt.value}
              onClick={() => setSchemaFilter(opt.value)}
            />
          ))}
        </div>
        <RecentReceipts
          schema={schemaFilter || undefined}
          limit={5}
          emptyHint={
            schemaFilter
              ? `No ${RECEIPT_LANES.find((l) => l.value === schemaFilter)?.label.toLowerCase()} receipts yet on this chain.`
              : "No receipts on chain yet · approve your first run, pin a model, or download a dataset to mint one."
          }
        />
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

function ChipButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        active
          ? "rounded-md border border-honey-400/50 bg-honey-300/[0.08] px-3 py-1 font-mono text-xs text-honey-200"
          : "rounded-md border border-white/10 bg-white/[0.02] px-3 py-1 font-mono text-xs text-paper/55 hover:border-white/25 hover:text-paper"
      }
    >
      {label}
    </button>
  );
}
