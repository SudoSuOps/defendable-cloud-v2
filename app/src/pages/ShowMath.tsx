import fixture from "../wacc_run_fixture.json";
import { Badge, Card, Callout } from "../components/ui";

// "Show the Math" — the referee's deterministic checks rendered with the work shown.
// Not a judge model's opinion: every number is re-derived from the agent's own
// formula + inputs, and you can verify 1+1=2 yourself. No "trust me."

type MathCheck = {
  name: string;
  formula: string;
  inputs: Record<string, number>;
  substituted: string;
  stated: number | string;
  recomputed: number | null;
  status: string;
  severity?: string | null;
  detail: string;
};
type Check = { check_key: string; label?: string; category: string; status: string; severity?: string | null; detail: string };

const fx = fixture as unknown as {
  flight_sheet: { name: string; slug: string };
  verdict: { outcome: string; severity: string; score_100: number; summary?: string; recommended_action?: string };
  checks: Check[];
  math_view: MathCheck[];
};

function num(v: number | string | null): string {
  if (v === null || v === undefined) return "—";
  const n = typeof v === "string" ? Number(v) : v;
  if (Number.isNaN(n)) return String(v);
  if (Math.abs(n) >= 1000) return n.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return String(parseFloat(n.toFixed(6)));
}

function MathRow({ m }: { m: MathCheck }) {
  const ok = m.status === "pass";
  const tone = ok ? "border-emerald-400/25 bg-emerald-400/[0.03]" : "border-red-400/30 bg-red-400/[0.05]";
  return (
    <div className={`rounded-lg border ${tone} p-4`}>
      <div className="flex items-center justify-between gap-3">
        <div className="font-mono text-sm font-semibold text-paper">{m.name}</div>
        <Badge value={m.status === "pass" ? "pass" : "flag"} />
      </div>
      {/* the re-derivation — read it left to right and check it yourself */}
      <div className="mt-3 space-y-1.5 font-mono text-sm">
        <div className="text-paper/45">
          <span className="text-paper/30">rule&nbsp;&nbsp;</span>
          {m.formula}
        </div>
        <div className="text-paper/90">
          <span className="text-paper/30">compute&nbsp;</span>
          <span>{m.substituted}</span>
          <span className="text-honey-300"> = {num(m.recomputed)}</span>
        </div>
        <div className={ok ? "text-emerald-300" : "text-red-300"}>
          <span className="text-paper/30">stated&nbsp;&nbsp;</span>
          {num(m.stated)}
          <span className="ml-2">
            {ok ? "✓ matches the re-derivation" : `✗ ${m.detail.split("—").slice(-1)[0].trim()}`}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function ShowMath() {
  const passes = fx.math_view.filter((m) => m.status === "pass").length;
  const flags = fx.math_view.filter((m) => m.status !== "pass").length;
  const other = fx.checks.filter((c) => c.category !== "math");
  const skipped = other.filter((c) => c.status === "skip").length;

  return (
    <div className="min-h-screen brand-grid">
      <div className="mx-auto max-w-3xl px-5 py-12">
        <div className="mb-2 text-xs font-semibold uppercase tracking-widest text-honey-300/80">
          Defendable Run · Referee · Show the Math
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-paper">{fx.flight_sheet.name}</h1>
        <p className="mt-1 text-sm text-paper/50">
          The referee is a <span className="text-paper/80">rulebook, not a judge model</span>. Every number below is
          re-derived from the agent&apos;s own formula and inputs. Read it left to right — verify 1+1=2 yourself.
        </p>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Badge value={fx.verdict.severity} />
          <Badge value={fx.verdict.outcome} />
          <span className="font-mono text-sm text-paper/60">{fx.verdict.score_100}/100 weighted</span>
          <span className="text-sm text-paper/50">
            · {passes} re-derivations verified · <span className="text-red-300">{flags} flag</span>
          </span>
        </div>

        {flags > 0 && (
          <div className="mt-5">
            <Callout title="Why this run failed">
              {fx.verdict.recommended_action ||
                "A calculation does not re-derive from its own inputs. The referee flagged it — see the red row."}
            </Callout>
          </div>
        )}

        <div className="mt-7">
          <div className="mb-3 text-xs font-semibold uppercase tracking-widest text-paper/40">
            The math · {fx.math_view.length} calculations re-derived
          </div>
          <div className="space-y-3">
            {fx.math_view.map((m) => (
              <MathRow key={m.name} m={m} />
            ))}
          </div>
        </div>

        <div className="mt-8">
          <Card title="The rest of the rulebook" subtitle={`${other.length} checks · ${skipped} not machine-evaluable in v1 (shown honestly, not hidden)`}>
            <div className="space-y-1.5">
              {other.map((c) => (
                <div key={c.check_key} className="flex items-center justify-between gap-3 font-mono text-xs">
                  <span className="text-paper/70">{c.check_key}</span>
                  <span className="flex items-center gap-2">
                    <span className="text-paper/40">{c.detail.slice(0, 52)}</span>
                    <Badge value={c.status} />
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <p className="mt-8 text-center text-xs text-paper/30">
          Math and code, visible. No trust required — re-run the formulas yourself. 🐝 to the shed.
        </p>
      </div>
    </div>
  );
}
