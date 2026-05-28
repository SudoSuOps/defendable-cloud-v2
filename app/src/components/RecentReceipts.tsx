// Per-org recent-receipts rollup tile · drives the dashboards and the
// "Your pins" section on /models. Backed by GET /receipts/recent.
//
// Each tile is schema-aware: it dispatches on the rollup's `payload_schema`
// field and surfaces 2-3 headline values plus a one-click share link.

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Spinner, ErrorNote } from "./ui";

export interface ReceiptRollup {
  receipt_id: string;
  org_seq: number;
  payload_schema: string;
  receipt_sha256: string;
  share_url: string;
  created_at: string | null;
  summary: Record<string, any>;
}

interface Props {
  /** Optional exact-match schema filter (e.g. "defendablecloud.model-pin-receipt/v1"). */
  schema?: string;
  /** How many rollups to fetch. Default 5; max 50. */
  limit?: number;
  /** What to render when there's nothing on chain yet. */
  emptyHint?: string;
}

export function RecentReceipts({ schema, limit = 5, emptyHint }: Props) {
  const [rollups, setRollups] = useState<ReceiptRollup[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const qs = new URLSearchParams();
    if (schema) qs.set("schema", schema);
    qs.set("limit", String(limit));
    api<{ rollups: ReceiptRollup[] }>(`/receipts/recent?${qs.toString()}`)
      .then((r) => setRollups(r.rollups))
      .catch((e) => setErr(e.message));
  }, [schema, limit]);

  if (err) {
    return (
      <ErrorNote>
        {err.includes("membership") ? (
          <>
            The receipt rollup is members-only. <a className="text-honey-300 underline" href="/org">Apply for membership →</a>
          </>
        ) : (
          err
        )}
      </ErrorNote>
    );
  }
  if (!rollups) return <Spinner />;
  if (rollups.length === 0) {
    return (
      <p className="text-sm text-paper/45">
        {emptyHint || "No receipts yet · your chain starts as soon as you mint your first."}
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {rollups.map((r) => (
        <RollupTile key={r.receipt_id} rollup={r} />
      ))}
    </ul>
  );
}

function RollupTile({ rollup }: { rollup: ReceiptRollup }) {
  const href = toAppReceiptUrl(rollup.share_url);
  const { laneLabel, line1, line2, badges } = renderForSchema(rollup);
  return (
    <li>
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="block rounded-md border border-white/8 bg-white/[0.02] px-4 py-3 transition-colors hover:border-white/20 hover:bg-white/[0.04]"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="rounded border border-honey-400/30 bg-honey-300/[0.08] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-honey-200">
              {laneLabel}
            </span>
            <span className="text-sm font-medium text-paper">{line1}</span>
          </div>
          <span className="font-mono text-[10px] text-paper/35">
            {rollup.created_at ? new Date(rollup.created_at).toLocaleString() : "—"}
          </span>
        </div>
        {line2 && <p className="mt-1 text-xs text-paper/55">{line2}</p>}
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {badges.map((b, i) => (
            <span
              key={i}
              className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${b.tone}`}
            >
              {b.label}
            </span>
          ))}
          <span className="ml-auto font-mono text-[10px] text-paper/30">
            org_seq {rollup.org_seq}
          </span>
        </div>
      </a>
    </li>
  );
}

interface RenderResult {
  laneLabel: string;
  line1: string;
  line2: string | null;
  badges: { label: string; tone: string }[];
}

function renderForSchema(r: ReceiptRollup): RenderResult {
  const s = r.summary || {};
  const lane = String(s.lane || "");
  switch (lane) {
    case "model-pin":
      return {
        laneLabel: "pin",
        line1: `${s.model_name || s.model_slug || "model"}`,
        line2: [s.declaration, s.client_ref].filter(Boolean).join(" · ") || s.model_slug || null,
        badges: [
          s.base && { label: s.base, tone: "border-white/10 text-paper/55" },
          s.params_b != null && { label: `${s.params_b}B`, tone: "border-white/10 text-paper/55" },
        ].filter(Boolean) as { label: string; tone: string }[],
      };
    case "cook":
      return {
        laneLabel: "cook",
        line1: s.run_title || s.base_model || "cook",
        line2: `${pct(s.eval_before)} → ${pct(s.eval_after)} · ${s.base_model || "—"}`,
        badges: [
          typeof s.lift === "number" && {
            label: `${s.lift >= 0 ? "+" : ""}${(s.lift * 100).toFixed(1)}%`,
            tone:
              s.lift >= 0
                ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                : "border-red-400/30 bg-red-400/10 text-red-300",
          },
          s.pinned_model_slug && {
            label: `pin · ${s.pinned_model_slug}`,
            tone: "border-honey-400/30 bg-honey-300/[0.08] text-honey-200",
          },
        ].filter(Boolean) as { label: string; tone: string }[],
      };
    case "eval":
      return {
        laneLabel: "eval",
        line1: s.run_title || "run",
        line2: typeof s.score_100 === "number" ? `${s.score_100}/100` : null,
        badges: [
          s.outcome && { label: s.outcome, tone: outcomeTone(s.outcome) },
          s.severity && { label: s.severity, tone: severityTone(s.severity) },
        ].filter(Boolean) as { label: string; tone: string }[],
      };
    case "incident":
      return {
        laneLabel: "incident",
        line1: s.title || s.kind || "incident",
        line2: s.kind || null,
        badges: [
          s.severity && { label: s.severity, tone: severityTone(s.severity) },
          s.status && { label: s.status, tone: "border-white/10 text-paper/55" },
        ].filter(Boolean) as { label: string; tone: string }[],
      };
    case "dataset-download":
      return {
        laneLabel: "download",
        line1: s.package_name || s.package_slug || "dataset",
        line2: s.vertical || null,
        badges: [
          s.ready_at_grant !== undefined && {
            label: s.ready_at_grant ? "ready" : "preparing",
            tone: s.ready_at_grant
              ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
              : "border-amber-400/30 bg-amber-400/10 text-amber-300",
          },
        ].filter(Boolean) as { label: string; tone: string }[],
      };
    default:
      return {
        laneLabel: lane || "receipt",
        line1: r.receipt_id,
        line2: r.payload_schema || null,
        badges: [],
      };
  }
}

function outcomeTone(o: string): string {
  const k = (o || "").toLowerCase();
  if (k === "pass") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-300";
  if (k === "fail") return "border-red-400/30 bg-red-400/10 text-red-300";
  return "border-amber-400/30 bg-amber-400/10 text-amber-300";
}

function severityTone(sev: string): string {
  const k = (sev || "").toLowerCase();
  if (k === "honey") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-300";
  if (k === "propolis") return "border-red-400/30 bg-red-400/10 text-red-300";
  return "border-amber-400/30 bg-amber-400/10 text-amber-300";
}

function pct(v: any): string {
  return typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "—";
}

// API share URL → app public-receipt URL.
function toAppReceiptUrl(apiShareUrl: string): string {
  try {
    const u = new URL(apiShareUrl);
    const parts = u.pathname.split("/").filter(Boolean);
    const i = parts.indexOf("share");
    if (i >= 0 && parts[i + 1]) {
      return `${window.location.origin}/r/${parts[i + 1]}`;
    }
  } catch {
    /* fall through */
  }
  return apiShareUrl;
}
