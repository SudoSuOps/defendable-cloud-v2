import { useEffect, useMemo, useState } from "react";
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

interface DatasetPackage {
  slug: string;
  name: string;
  vertical: string;
  tier: string;
  pkg_class: string;
  pairs: number;
  deed_anchored: boolean;
  deed: string;
}

interface DatasetCatalog {
  version: string;
  generated_at: string | null;
  catalog_sha256: string | null;
  packages_sha256: string | null;
  scorecard: {
    total_packages: number;
    total_pairs: number;
    deed_anchored: number;
  };
  verticals: Record<string, { packages: number; pairs: number; usd: number | null }>;
  packages: DatasetPackage[];
}

const TIER_LABEL: Record<string, string> = {
  royal_jelly: "Royal Jelly",
  honey: "Honey",
  jelly: "Jelly",
  canonical: "Canonical",
  master: "Master",
  propolis: "Propolis",
  mixed: "Mixed",
  train: "Train",
  eval: "Eval",
};

const VERTICAL_LABEL: Record<string, string> = {
  cre: "CRE",
  medical: "Medical",
  grants: "Grants",
  jelly: "Jelly",
  signal: "Signal",
  "capital-markets": "Capital Markets",
  "bee-hive": "Bee-Hive",
  legal: "Legal",
  finance: "Finance",
  aviation: "Aviation",
  openalex: "OpenAlex",
  failure: "Failure",
};

export function Datasets() {
  const [cookSets, setCookSets] = useState<Dataset[] | null>(null);
  const [catalog, setCatalog] = useState<DatasetCatalog | null>(null);
  const [catalogErr, setCatalogErr] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [vFilter, setVFilter] = useState<string | "all">("all");

  useEffect(() => {
    api<{ datasets: Dataset[] }>("/datasets")
      .then((r) => setCookSets(r.datasets))
      .catch((e) => setErr(e.message));
    api<DatasetCatalog>("/datasets/catalog")
      .then(setCatalog)
      .catch((e) => setCatalogErr(e.message));
  }, []);

  const filteredPackages = useMemo(() => {
    if (!catalog) return [] as DatasetPackage[];
    if (vFilter === "all") return catalog.packages;
    return catalog.packages.filter((p) => p.vertical === vFilter);
  }, [catalog, vFilter]);

  return (
    <div>
      <p className="text-sm font-medium uppercase tracking-widest text-honey-300">Datasets</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-paper">
        The members-only library.
      </h1>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-paper/60">
        Free with membership. Compute is the meter. We learn from how agents fail — never from what your business is doing.
      </p>

      {err && <div className="mt-6"><ErrorNote>{err}</ErrorNote></div>}

      {/* Catalog — the headline */}
      <section className="mt-10">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-paper/40">Master catalog</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight text-paper">
              Hash-anchored books-and-records
            </h2>
          </div>
          {catalog && (
            <div className="text-right font-mono text-xs text-paper/40">
              <div>{catalog.version} · generated {catalog.generated_at ? new Date(catalog.generated_at).toLocaleDateString() : "—"}</div>
              <div>
                packages_sha256 · <span className="text-paper/65">{(catalog.packages_sha256 || "").slice(0, 16)}…</span>
              </div>
            </div>
          )}
        </div>

        {catalogErr && (
          <div className="mt-4">
            <ErrorNote>
              {catalogErr.includes("membership") ? (
                <>
                  The catalog is members-only. <a className="text-honey-300 underline" href="/org">Apply for membership →</a>
                </>
              ) : (
                catalogErr
              )}
            </ErrorNote>
          </div>
        )}
        {!catalog && !catalogErr && <div className="mt-4"><Spinner label="Loading catalog…" /></div>}

        {catalog && (
          <>
            {/* Scorecard */}
            <Card className="mt-4">
              <div className="grid gap-x-8 gap-y-3 text-center sm:grid-cols-3">
                <Stat label="Total packages" value={catalog.scorecard.total_packages.toLocaleString()} />
                <Stat label="Training pairs" value={catalog.scorecard.total_pairs.toLocaleString()} />
                <Stat label="Deed-anchored" value={`${catalog.scorecard.deed_anchored} / ${catalog.scorecard.total_packages}`} />
              </div>
            </Card>

            {/* Vertical filter */}
            <div className="mt-6 flex flex-wrap gap-2">
              <FilterChip
                label={`All · ${catalog.packages.length}`}
                active={vFilter === "all"}
                onClick={() => setVFilter("all")}
              />
              {Object.entries(catalog.verticals)
                .sort((a, b) => b[1].pairs - a[1].pairs)
                .map(([v, info]) => (
                  <FilterChip
                    key={v}
                    label={`${VERTICAL_LABEL[v] || v} · ${info.packages}`}
                    active={vFilter === v}
                    onClick={() => setVFilter(v)}
                  />
                ))}
            </div>

            {/* Package table */}
            <div className="mt-5 overflow-hidden rounded-xl border border-white/8 bg-white/[0.02]">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-white/5 text-xs uppercase tracking-widest text-paper/40">
                  <tr>
                    <th className="px-4 py-3">Package</th>
                    <th className="px-4 py-3">Vertical</th>
                    <th className="px-4 py-3">Tier</th>
                    <th className="px-4 py-3 text-right">Pairs</th>
                    <th className="px-4 py-3 text-right">Deed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filteredPackages.slice(0, 100).map((p) => (
                    <tr key={p.slug} className="hover:bg-white/[0.03]">
                      <td className="px-4 py-3">
                        <div className="font-medium text-paper">{p.name}</div>
                        <div className="font-mono text-[10px] text-paper/35">{p.slug}</div>
                      </td>
                      <td className="px-4 py-3 text-paper/65">{VERTICAL_LABEL[p.vertical] || p.vertical}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-md border border-honey-400/30 bg-honey-300/[0.08] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-honey-200">
                          {TIER_LABEL[p.tier] || p.tier}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs text-paper/65">
                        {p.pairs.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {p.deed_anchored ? (
                          <span className="font-mono text-[10px] text-emerald-300/80">✓ anchored</span>
                        ) : (
                          <span className="font-mono text-[10px] text-paper/30">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredPackages.length > 100 && (
              <p className="mt-2 text-xs text-paper/40">
                Showing first 100 of {filteredPackages.length} — use the CLI for full programmatic access.
              </p>
            )}
          </>
        )}
      </section>

      {/* Cook datasets — the existing eval-aligned set */}
      <section className="mt-12">
        <p className="font-mono text-xs uppercase tracking-widest text-paper/40">Eval-aligned cook sets</p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-paper">
          Pre-baked for proving lift on a run
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-paper/60">
          When an eval finds a weakness, fine-tune one of our models on the matched dataset — then the
          run re-evals to prove the lift. You don't buy the data; you buy the proven improvement.
        </p>

        {!cookSets && !err && <div className="mt-6"><Spinner /></div>}

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {cookSets?.map((d) => (
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
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-2xl font-semibold text-paper">{value}</div>
      <div className="mt-0.5 text-xs uppercase tracking-widest text-paper/40">{label}</div>
    </div>
  );
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
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
