import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Card, ErrorNote, Spinner } from "../components/ui";

interface Dataset {
  id: string;
  slug: string;
  name: string;
  domain: string;
  lane: string;
  description: string;
  pair_count: number;
  tier: string;
  targets: string | null;
}

const TIER_LABEL: Record<string, string> = {
  royal_jelly: "Royal Jelly",
  honey: "Honey",
  jelly: "Jelly",
};

export function Datasets() {
  const [datasets, setDatasets] = useState<Dataset[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<{ datasets: Dataset[] }>("/datasets")
      .then((r) => setDatasets(r.datasets))
      .catch((e) => setErr(e.message));
  }, []);

  return (
    <div>
      <p className="text-sm font-medium uppercase tracking-widest text-honey-300">Datasets</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-paper">Pre-baked, eval-aligned datasets.</h1>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-paper/60">
        When an eval finds a weakness, fine-tune one of our models on the matched dataset — then the
        run re-evals to prove the lift. You don't buy the data; you buy the proven improvement.
      </p>

      {err && <div className="mt-6"><ErrorNote>{err}</ErrorNote></div>}
      {!datasets && !err && <div className="mt-6"><Spinner /></div>}

      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {datasets?.map((d) => (
          <Card key={d.id}>
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-semibold text-paper">{d.name}</h3>
              <span className="rounded-md border border-honey-400/30 bg-honey-300/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-honey-200">
                {TIER_LABEL[d.tier] || d.tier}
              </span>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-paper/65">{d.description}</p>
            {d.targets && (
              <p className="mt-3 text-xs text-paper/45">
                <span className="uppercase tracking-widest text-paper/35">Fixes</span> · {d.targets}
              </p>
            )}
            <div className="mt-4 flex items-center gap-3 font-mono text-xs text-paper/40">
              <span>{d.pair_count.toLocaleString()} pairs</span>
              <span>·</span>
              <span>{d.lane} lane</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
