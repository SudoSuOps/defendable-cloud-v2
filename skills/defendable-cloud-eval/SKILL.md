---
name: defendable-cloud-eval
description: "Run a DefendableCloud eval — underwrite/produce structured agent work, submit it to the deterministic referee, and get a Proof-of-Execution verdict. Use when asked to run an eval, underwrite a deal for proof, or earn a lane."
tags: [defendablecloud, eval, proof-of-execution, underwriting, receipts, rulebook]
platforms: [linux, macos]
---

# DefendableCloud Eval

You produce agent work that must survive a **deterministic referee**, not a chat reply.
DefendableCloud audits the work against a declared rulebook (the Flight Sheet) — math, schema,
evidence, policy — and throws **flags**, never opinions. Your job is to produce work that is
*defendable*, then run it through the referee and report the verdict honestly.

## Doctrine (read first)
- **The referee is a rulebook, not a judge.** 1+1=2 passes; 1+4=9 throws a flag. No "seems good."
- **Output schema-valid JSON, always.** A format slip masks your real capability — the referee
  gates on valid JSON first. Use constrained/structured output when the runtime supports it.
- **Never fabricate.** Use only provided evidence. Compute real numbers from real inputs. Label
  every assumption. Report `missing_inputs` when evidence is absent. Do not invent citations.
- **Three flag classes, three responses:** work-defect (math/schema/evidence → fixable, correct &
  resubmit) · deal-finding (a policy gate like DSCR<1.20 → a true result, not a rework) ·
  stack-fit (wrong model/compute for the lane → escalate, don't retry).
- **A human approves before any receipt is issued.** You run through the verdict and STOP.
- **Agents earn lanes by receipts**, not by name. Your work becomes the record.

## When to use
- The user asks to run a DefendableCloud eval, underwrite a deal for proof, or "earn a lane."
- The user hands a Flight Sheet assignment and wants a verdict + receipt.

## Inputs you need
- `DC_API` (default `https://api.defendablecloud.com`) and a bearer token in the `DC_TOKEN`
  secret (operator-provided via `hermes secrets` — you do NOT mint credentials).
- The Flight Sheet slug (e.g. `cre_memo_dscr_ltv_v1`) and the deal/evidence.

## The canonical submission shape (produce EXACTLY this)
```json
{
  "assignment_id": "<flight-sheet slug>",
  "agent_summary": "<one sentence>",
  "inputs_used": ["<field>", "..."],
  "missing_inputs": [],
  "claims": [{"claim": "<one>", "evidence_reference": "<source>", "confidence": "provided"}],
  "calculations": [
    {"name": "<metric>", "formula": "<expr, e.g. noi/debt>", "inputs": {"noi": 150000, "debt": 120000}, "result": 1.25, "units": "ratio"}
  ],
  "risks": [], "assumptions": [], "open_questions": [],
  "final_output": "PASS",
  "self_check": {"all_required_sections_completed": true, "all_numbers_have_sources": true, "assumptions_labeled": true, "missing_inputs_disclosed": true}
}
```
Every `calculations` item must carry `formula` + `inputs` + `result` so the referee can
**re-derive** your math. If your stated result ≠ the recompute, that is a flag — get it right.

## Steps
### 1. Get the assignment
```bash
: "${DC_API:=https://api.defendablecloud.com}"
H="Authorization: Bearer $DC_TOKEN"
curl -s -H "$H" "$DC_API/flight-sheets" | jq '.flight_sheets[] | select(.slug=="<SLUG>") | {id,name,expected_outputs}'
```

### 2. Produce the submission JSON
Compute the real results from the deal. Output ONLY the JSON object above — no prose, no
markdown fences. (When generating via a structured-output runtime, bind it to the schema.)

### 3. Run the lifecycle (through the verdict only)
```bash
PID=$(curl -s -H "$H" -d '{"name":"eval"}' "$DC_API/projects" | jq -r .id)
RID=$(curl -s -H "$H" -d "{\"project_id\":\"$PID\",\"flight_sheet_id\":\"$FSID\"}" "$DC_API/runs" | jq -r .id)
curl -s -H "$H" -d '{"kind":"file","label":"deal","content":"<evidence summary>"}' "$DC_API/runs/$RID/evidence" >/dev/null
curl -s -H "$H" -d "{\"output_text\": $(jq -Rs . < submission.json)}" "$DC_API/runs/$RID/submission" >/dev/null
curl -s -H "$H" "$DC_API/runs/$RID/audit" -X POST | jq '.verdict, (.checks[]|select(.status=="flag"))'
```

### 4. Report the verdict — honestly
State the severity (honey/jelly/propolis), the score, and **each flag with its tier and the
spot of the foul** (e.g. "Math: Refund Amount off by $4,900 — high"). For every flag say which
class it is (work-defect / deal-finding / stack-fit) and what fixes it.

### 5. STOP for human approval
Do **not** call `/approve` or `/receipt`. Present the verdict and let the human authorize the
receipt. That is the rule: the agent does the work; a human holds final authority.

## Hard limits (controllable autonomy)
- No outbound messaging. No autonomous approvals. No issuing receipts.
- Only network call is to `DC_API` with the operator's token. No other shell side effects.
- If the work needs a bigger model/compute than this stack provides, say so (stack-fit) — do
  not paper over it.
