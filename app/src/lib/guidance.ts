// Client-facing guidance — what each run type is, when to use it, and what
// good evidence looks like. Surfaced throughout the vault so a client knows
// what to do without reading docs.

export interface LaneGuide {
  value: string;
  label: string;
  what: string;
  examples: string[];
  evidenceHint: string;
  evidenceExamples: string[];
  inputs: { key: string; label: string; placeholder: string }[];
}

export const LANES: LaneGuide[] = [
  {
    value: "agent",
    label: "Agent work",
    what: "An AI agent did a task. Prove what it did, what it relied on, and whether the result holds up to review.",
    examples: [
      "A support agent drafted a refund decision",
      "A coding agent opened a pull request",
      "A CRE agent reviewed an LOI or lease",
    ],
    evidenceHint: "Attach what a reviewer needs to trust the agent: the instruction it was given, the output it produced, the tools it called, and any sources it used.",
    evidenceExamples: [
      "model_output — the agent's final answer or draft",
      "tool_output — results from a tool/API the agent called",
      "url — a source document the agent cited",
      "note — the prompt or instruction the agent was given",
    ],
    inputs: [{ key: "task", label: "Task", placeholder: "e.g. Review the attached LOI and flag non-standard terms" }],
  },
  {
    value: "dataset",
    label: "Dataset",
    what: "A dataset to verify — where it came from, how it was checked, and whether it is training-grade.",
    examples: [
      "A fine-tune set you assembled in-house",
      "A vendor dataset you're vetting before you buy",
      "A labeled corpus headed for training",
    ],
    evidenceHint: "Attach the provenance and the proof of quality: where the rows came from, a sample, and how it was cleaned and checked.",
    evidenceExamples: [
      "file — a sample of rows (JSONL/CSV) — it gets hashed",
      "note — the source and how it was collected",
      "log — dedup / labeling / validation output",
      "url — the source dataset or manifest",
    ],
    inputs: [
      { key: "source", label: "Source", placeholder: "e.g. internal-cre-corpus / vendor X" },
      { key: "row_count", label: "Row count", placeholder: "e.g. 42000" },
    ],
  },
  {
    value: "compute",
    label: "Compute",
    what: "A machine or benchmark to validate before you sell it, rent it, or trust its numbers.",
    examples: [
      "An RTX 5090 rig benchmark before resale",
      "A GPU node's power and thermal run",
      "A server you're listing on a marketplace",
    ],
    evidenceHint: "Attach the machine identity and the proof of performance: what it is, what it scored, and the conditions it ran under.",
    evidenceExamples: [
      "tool_output — nvidia-smi (GPU identity, power, temp)",
      "log — the benchmark run (fio, MLPerf, etc.)",
      "note — power state, cooling, test conditions",
      "file — the spec sheet or full report",
    ],
    inputs: [
      { key: "machine", label: "Machine", placeholder: "e.g. RTX 5090 · rig-whale" },
      { key: "benchmark_score", label: "Benchmark score", placeholder: "e.g. 9412" },
    ],
  },
  {
    value: "other",
    label: "Other",
    what: "Any work you need to put proof behind — a document check, a valuation, a compliance review.",
    examples: ["A document review", "A valuation workflow", "A compliance sign-off"],
    evidenceHint: "Attach the inputs, the output, and anything a reviewer would need to trust the result.",
    evidenceExamples: [
      "note — what was done and why",
      "file — the document or worksheet",
      "url — the system or record involved",
    ],
    inputs: [],
  },
];

export function laneGuide(value: string): LaneGuide {
  return LANES.find((l) => l.value === value) || LANES[3];
}

export const EVIDENCE_KIND_HELP: Record<string, string> = {
  note: "A written observation or context",
  url: "A link to a source, document, or system",
  observation: "Something noticed during the run",
  tool_output: "Raw output from a tool or API",
  model_output: "The AI's generated output",
  log: "A benchmark or run log / console output",
  file: "Upload a file — it gets hashed for integrity",
};

export const VERIFICATION_HELP =
  "Checks test your inputs and evidence against schema, math, evidence, and policy rules — deterministically, no AI guessing. The verdict is pass, risk, or fail. A human still approves before a receipt is issued.";
