---
name: defendable-cloud-eval
description: "Produce defendable, schema-valid agent work for a DefendableCloud eval. Use when asked to run an eval, underwrite a deal for proof, or earn a lane. You author the work; a separate operator-controlled runner submits it to the referee."
tags: [defendablecloud, eval, proof-of-execution, underwriting, rulebook]
platforms: [linux, macos]
---

# DefendableCloud Eval

You produce agent work that must survive a **deterministic referee**, not a chat reply.
DefendableCloud audits work against a declared rulebook (the Flight Sheet) — math, schema,
evidence, policy — and throws **flags**, never opinions. Your job: produce work that is
*defendable*. You do **not** submit it yourself — a separate, operator-controlled runner does
that. This skill makes your output pass the referee on capability, not get tripped on format.

## Doctrine (read first)
- **The referee is a rulebook, not a judge.** 1+1=2 passes; 1+4=9 throws a flag. No "seems good."
- **Output schema-valid JSON, always.** A format slip masks real capability — the referee gates
  on valid JSON first. Emit exactly the shape below, nothing around it.
- **Never fabricate.** Use only provided evidence. Compute real numbers from real inputs. Label
  every assumption. List `missing_inputs` when evidence is absent. Do not invent citations.
- **Make your math re-derivable.** Every calculation carries its `formula` + `inputs` + `result`
  so the referee can recompute it. If your result ≠ the recompute, that is a flag — get it right.
- **Three flag classes, three responses:** work-defect (math/schema/evidence → fixable, correct &
  resubmit) · deal-finding (a policy gate like DSCR<1.20 → a true result, not a rework) ·
  stack-fit (the model/compute is below the lane → say so, do not paper over it).
- **A human holds final authority.** You produce the work and report; you never approve or issue
  a receipt.

## When to use
- The user asks to run a DefendableCloud eval, underwrite a deal for proof, or "earn a lane."
- The user hands a Flight Sheet assignment (a slug like `cre_memo_dscr_ltv_v1`) and the deal.

## Output — produce EXACTLY this object, JSON only
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

## How to do it
1. **Read the assignment.** Identify the required calculations and the evidence you were given.
2. **Compute, don't guess.** For each metric, write the `formula`, the literal `inputs`, and the
   computed `result`. Recheck each: does `result` equal `formula` applied to `inputs`?
3. **Fill the schema.** Cite evidence on every claim. Label assumptions. Disclose missing inputs.
   `final_output` is `PASS` only if the work is complete and self-consistent.
4. **Emit JSON only** — no prose, no markdown fences. The operator's runner takes it from here:
   it submits to the referee under a controlled token and returns the verdict.
5. **On the verdict**, report each flag with its tier and the spot of the foul (e.g. "Math:
   Refund Amount off by $4,900 — high"), and say which class it is and what fixes it. Then STOP —
   a human approves and issues the receipt.

## Hard limits (controllable autonomy)
- You do not submit, approve, or issue receipts; you do not handle credentials or call networks.
- No outbound messaging. Produce the work, report the verdict, defer to the human.
- If the work needs a bigger model/compute than this stack provides, name it (stack-fit) — never
  paper over a capability gap to force a PASS.
