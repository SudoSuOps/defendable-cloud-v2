# DefendableCore — Strategy & Build Plan

**DefendableCore is the engine room for business AI agents.**
*AI agents need somewhere to live. DefendableCore makes the stack real.*

Status: strategy v1 · 2026-05-27. Core does not exist as deployed infrastructure yet — this document defines what it is, what it must be honest about, and the smallest real first version. Where a capability depends on telemetry or hosting that is not yet built, this document says so out loud.

---

## 1. Executive summary

Businesses are being sold "AI agents" without being told what it takes to run one. An agent is not a chatbot — it is a worker, and a worker needs a workplace, power, tools, rules, supervision, incident handling, maintenance, and proof of work. Today that backend is a dark box: owners cannot see where the agent lives, what it costs at 2 a.m., or what happens when it fails.

**DefendableCore is the managed compute and runtime layer that makes the backend real and legible for small and mid-size businesses.** It plans the stack, deploys the runtime, manages updates and permissions, responds to incidents, and connects every run back to DefendableCloud for Proof of Execution.

It is one of four parts: **DefendableCore runs it · DefendableRouter routes it · DefendableOS verifies it · DefendableCloud proves it.** Core is the part nobody else packages cleanly for SMBs.

The wedge is not "rent a GPU" or "build an agent." It is **managed AI agent operations + compute fit + proof** — sized to a business that wants to participate in the AI economy without becoming an infrastructure team.

---

## 2. Market pain

The "agent" market is loud and fragmented:

- **Agent platforms** (Microsoft Foundry/Agent 365, AWS Bedrock AgentCore, CrewAI, LangSmith) — build/deploy/scale, aimed at enterprise engineering teams.
- **GPU/inference clouds** (RunPod, Modal, Baseten, Together, CoreWeave, Lambda) — compute and endpoints, not agent behavior or business risk.
- **Observability/security tools** — logs, traces, guardrails, policy.
- **MSPs/agencies** — implementation help, but no formal Proof of Execution, no eval receipts, no hardware/model fit scoring.

Every one of them solves a *piece*. None of them sits next to a small business owner and says: *"this agent belongs on your office box, that one needs hosted GPU, this one needs a 9B model, and none of them can send client-facing output without approval."*

Independent reporting backs the gap: agents need different observability than human-operated systems; self-running agents widen the attack surface and need inventories, baselines, and policy; and production agents remain hard to evaluate — many are still simple (short step counts, off-the-shelf prompting, human evaluation). The market knows ops and governance are needed. It is **not packaged for SMBs as managed agent operations.**

---

## 3. The small-business problem

A small business owner hears "get an AI agent" and pictures a hire. What they are not told:

- Where does it live — my computer, someone's cloud, both?
- What model does the job actually need — and what does "bigger" cost?
- Can my hardware run it, or do I need hosted GPU?
- What does 24/7 really cost — power, inference, storage, monitoring?
- What happens when it crashes at 2 a.m.?
- Who patches the OS and the runtime?
- What can it touch, and what is it forbidden to do?
- What happens if it goes rogue — wrong tool, runaway spend, repeated bad output?
- What proof do I have that the work was done, and done right?

These are operations questions, not prompt questions. The owner cannot answer them, and most sellers will not. **That information gap is DefendableCore's product.**

---

## 4. Why browser agents alone are not enough

A browser agent or a single installed "claw" is a demo, not an operation. Installed ≠ running. A production agent still needs:

- an identity, a role, and a bounded mission
- a model wired to a runtime that fits the hardware
- tools granted deliberately, with permissions
- task boundaries and approval rules
- a restart/failure plan and incident handling
- OS/runtime patching and uptime
- proof of what it did

A browser agent has none of this managed. It runs until it doesn't, touches what it can reach, and leaves no defensible record. That is fine for a demo and dangerous for a business. **Core is the difference between "it ran on my laptop once" and "it runs, it's watched, and every run has a receipt."**

---

## 5. Why owner-compute matters

Owner-compute = the agent runs on the business's own hardware (office workstation, mini PC, Jetson, ZimaBoard, local GPU box, NAS/server, or a purpose-built **Defendable Box**).

It matters because:

- **Privacy/sovereignty** — local files never leave the building.
- **Fixed cost** — hardware is a known number; no per-inference meter.
- **Edge/low-volume fit** — intake, extraction, file-watching, internal SOP assistance run well on small local models.

Honest limits: smaller models, smaller context, and the **owner becomes the operator** for power/internet/uptime unless Core manages it. Owner-compute is excellent for the right lanes and wrong for high-stakes reasoning or client-facing autonomy.

---

## 6. Why hosted compute matters

Hosted compute = the agent runs on managed GPU/endpoints.

It matters because:

- **Uptime** — 24/7 operation with strong reliability.
- **Stronger brains** — senior/anchor models that owner hardware can't load.
- **Volume + client-facing** — higher throughput, managed updates, monitoring.

Honest cost: a monthly bill plus usage-based inference. Hosted is the right call when the work needs reliability, a bigger brain, or client-facing output — and overkill (and overpriced) when the work is light and local.

---

## 7. Why hybrid is the likely winning model

Most SMB workloads are *mixed*: light intake plus occasional heavy reasoning. Hybrid matches the stack to each step:

- **Local edge agent** watches files, collects intake, extracts fields, prepares an evidence package — privately, cheaply, on owner hardware.
- **Hosted brain** (9B/27B) analyzes, drafts, and synthesizes only when needed.
- **DefendableOS** audits the work against the rulebook.
- **DefendableCloud** stores the receipt.

You pay for the big brain only on the hard jobs, keep private data local, and still get reliability and proof where it counts. For most small businesses this is the **cheapest stack that still does the hard work** — and the recommended default.

---

## 8. DefendableCore product definition

DefendableCore provides **managed compute infrastructure for business AI agents**. It plans the stack, deploys the runtime, monitors the agent, manages updates, controls permissions, responds to incidents, and connects every run to DefendableCloud for Proof of Execution — across **owner-compute, hosted, or hybrid** deployments.

Core answers ten questions, deterministically where possible:

1. Where should this agent run?
2. What compute stack is required?
3. What model size is required?
4. Can this run on owner-compute?
5. Does this require hosted GPU?
6. Is hybrid better?
7. What does 24/7 really cost?
8. What happens when the agent goes dark?
9. What happens when it goes rogue?
10. What proof is generated after work or failure?

Core language: **the engine room for business AI agents.**

---

## 9. Relationship to OS, Cloud, and Router

| Brand | Job | One line |
|---|---|---|
| **DefendableCore** | **run it** | compute · runtime · monitoring · incidents · maintenance |
| **DefendableRouter** | route it | sends work to the right agent/model/compute lane |
| **DefendableOS** | verify it | rulebook/referee — math, code, schema, thresholds, flags |
| **DefendableCloud** | prove it | vault — evals, lanes, receipts, incidents, client portal |

Maps one-to-one to the doctrine line: *a worker needs a **workplace** (Core), the right **assignment routed** to it (Router), **supervision** (OS), and **proof** (Cloud).*

Data flow: Core runs the agent and emits run + health telemetry → Router decides the lane → OS audits the output → Cloud issues the receipt. Cloud already holds `AgentProfile`, earned **lane authorizations**, the rulebook eval, **incidents**, and the hash-chained **receipt ledger**. **Core extends that ledger to compute and runtime** — the missing layer below the work.

---

## 10. Service packages

1. **Core Assessment** (one-time) — Agent Stack Assessment, Compute Fit Report, owner-vs-hosted recommendation, model tier, 24/7 cost model, risk findings, approved/restricted/blocked lanes, and a Proof-of-Execution receipt. *Sellable today; builds on the existing Stack Planner.*
2. **Core Setup** (deployment) — hardware/runtime setup, model + agent runtime install, Cloud connection, monitoring setup, governance policy, an initial eval run, receipt-vault connection.
3. **Core Managed** (monthly) — uptime monitoring, OS/runtime updates, agent health checks, model endpoint monitoring, incident receipts, repair queue, monthly Proof-of-Execution report, lane-authorization updates. *Requires telemetry (§15) to be real.*
4. **Core Hosted** (managed compute) — hosted GPU/model endpoint, managed agent runtime, queue/scheduler, secure tool access, spend controls, monitoring, incident response, Cloud receipts.
5. **Core Hybrid** — local edge setup + hosted reasoning, secure evidence handoff, rulebook audit, client proof vault, incident receipts. *The recommended SMB default.*

Honest sequencing: **Assessment and Setup are sellable now.** Managed and Hosted depend on the telemetry/hosting build in §18 — don't sell live monitoring before it exists.

---

## 11. Core object model

Already live in DefendableCloud: **AgentProfile** (harness/model/runtime/tier/tools/governance) and **Incident** (+ hash-chained incident receipts). Core adds the compute/runtime/model objects and the execution join.

- **ComputeProfile** — a hardware/runtime environment. `compute_profile_id · owner · deployment_type {owner_compute|hosted_compute|hybrid} · host_name · location · hardware_class · cpu · gpu · vram · ram · storage · network · os · container_runtime · inference_runtime · model_runtime · monitoring_status · uptime_status · last_heartbeat · update_status · security_policy · cost_profile`
- **RuntimeProfile** — the software stack. `runtime_profile_id · os · docker_enabled · ollama_enabled · vllm_enabled · llama_cpp_enabled · agent_framework · browser_automation_enabled · tool_server_enabled · logs_enabled · restart_policy · secrets_policy · network_policy`
- **ModelProfile** — the brain. `model_profile_id · model_name · model_family · size_class {3B|7B|9B|14B|27B|70B|frontier_api} · provider · local_or_api · context_window · structured_output_reliability · expected_latency · cost_per_run · recommended_lanes · blocked_lanes`
- **AgentProfile** *(exists in Cloud)* — the deployed worker. `agent_id · display_name · framework · model_profile_id · compute_profile_id · runtime_profile_id · instruction_profile · tool_policy · allowed/restricted/blocked_lanes · approval_rules · eval_history · recurring_flags · incident_history · lane_authorizations`
- **ExecutionProfile** — the combined stack for one workflow. `= AgentProfile + ModelProfile + ComputeProfile + RuntimeProfile + Assignment + FlightSheet + Rulebook`. `execution_profile_id · agent_id · model/compute/runtime_profile_id · assignment_id · flight_sheet_id · lane · lane_requirement · fit_status · risk_status · recommended_action`
- **LaneRequirement** — what a task demands. `lane_id · lane_name · minimum_model_class · recommended_model_class · minimum_compute_class · required_context_window · required_tools · required_uptime · owner_compute_allowed · hosted_compute_recommended · human_approval_required · blocked_if_missing`
- **IncidentProfile** *(Incident exists in Cloud)* — failures. `incident_id · agent_id · compute_profile_id · execution_profile_id · trigger · severity · status · response_actions · opened_at · resolved_at · incident_receipt_id`

Example lanes: `evidence_extraction · log_summary · local_file_intake · document_draft · compute_benchmark_review · dataset_quality_review · cre_math · cre_client_memo · outbound_client_action · autonomous_financial_decision`.

---

## 12. Agent stack assessment workflow

1. **Intake** — what jobs (lanes), cadence/24-7, client-facing?, high-stakes (math/finance/legal)?, data-local-only?, deployment preference, budget.
2. **Lane mapping** — each job → its `LaneRequirement` (min model class, min compute, context, tools, approval).
3. **Fit scoring** (§13) — compare requirements to a candidate ComputeProfile/ModelProfile → `fit_status`.
4. **Deployment recommendation** — owner / hosted / hybrid, with the gap stated if the owner's preference conflicts with the requirement.
5. **Cost model** (§14) — 24/7 estimate by category.
6. **Lanes** — approved / restricted / blocked for the recommended stack.
7. **Proof** — issue an Assessment receipt; the recommendation points to an eval. *Proof comes from running the rulebook, not from the recommendation.*

This is the **Stack Planner** already shipped in Cloud, extended with ComputeProfile/RuntimeProfile and a written Compute Fit Report.

---

## 13. Compute fit scoring model (deterministic)

No judge model. A declared comparison of requirement vs. available, per workflow:

```
model tiers (rank):   edge 3–4B < workhorse 7–14B < senior 27–34B < anchor 70B+
compute tiers (rank): owner_edge < owner_gpu < hosted_gpu < hosted_multi
                      (each compute tier declares the max model class it can host)

required_model = max(min_model_class) across the workflow's lanes
min_compute    = smallest compute tier whose max_model >= required_model

fit_status:
  FIT      — available compute hosts required_model AND context/tools/uptime met
  PARTIAL  — hosts the light lanes only (→ hybrid), or meets model but not uptime
  UNFIT    — required_model > available max_model, or a required tool/context is missing

escalators:
  needs_24_7 or client_facing and compute uptime != strong  → recommend hosted
  spans light + heavy lanes                                 → recommend hybrid
  required_model >= senior or (24-7 and client_facing)      → recommend hosted/cloud
```

Output: `fit_status`, `recommended_deployment`, `recommended_model/compute`, `owner_fit {strong|partial|none}`, blocked lanes (with the required tier), and reasons. A mismatch is a **finding**, not a failure — "the stack was below the lane requirement" is the §15 trigger `compute_undersized` / `model_class_below_lane_requirement`.

---

## 14. 24/7 cost model categories

Most sellers quote one line (the model). Core quotes the whole bill, in the open:

1. **Model** — per-run inference (API) or amortized local.
2. **Compute** — GPU/CPU hours; owner = hardware amortization + power; hosted = endpoint/instance.
3. **Storage** — evidence, receipts, artifacts, logs.
4. **Uptime & monitoring** — always-on multiplier (×24-7), health checks.
5. **Tools & API calls** — search, browser, third-party APIs.
6. **Human review** — approval gates on client-facing/high-stakes work.
7. **Maintenance & updates** — OS/runtime patching, model updates.
8. **Evaluation & receipts** — rulebook eval + Proof-of-Execution issuance.
9. **Failure & repair** — retries, incident handling, repair loops.

Estimation inputs: model size → VRAM → compute tier; cadence (event-triggered vs always-on); volume (runs/day); tool usage; approval load. Output a **band** (low / low–med / medium / high) with the always-on multiplier called out — not a false-precise number.

---

## 15. Incident response model

**Honest boundary first:** live "dark/rogue" detection requires the agent/runtime to **report telemetry** (heartbeats, tool calls, spend). That telemetry contract is a Core build item (§18) and **does not exist yet**. Until it does, do not claim live monitoring.

What is **real today** (in Cloud): a deterministic trigger from data we already have — a lane with **recurring critical flags** (blocked) → lock the lane + open an incident + issue an **incident receipt**, with response actions recorded. Verified live.

Incident types and the pipe they plug into:

| Trigger | Source | Status |
|---|---|---|
| `recurring_critical_flag` · `lane_lock_triggered` · `human_approval_blocked` | eval history (live now) | **built** |
| `tool_permission_violation` · `spend_cap_exceeded` | governance policy + runtime telemetry | needs telemetry |
| `agent_dark` · `heartbeat_missing` · `runtime_crash` · `model_endpoint_down` | ComputeProfile heartbeats | needs telemetry |
| `memory_limit_hit` · `context_window_insufficient` · `compute_undersized` | runtime metrics + fit check | needs telemetry / fit pre-check |

Response actions (recorded on the incident, receipted): `pause_agent · revoke_tool · lock_lane · require_approval · open_repair_task · notify_owner`. Every incident — like every run — mints a **hash-chained receipt** in the same ledger. *Everyone alerts; Core receipts the incident.*

---

## 16. Governance model

Declared, rulebook-driven, never a vague "AI governance" claim:

- **Tool policy** — allowed tools (the hands); everything else denied by default.
- **Approval rules** — `human_approval_required` for client-facing output, high-stakes math/finance/legal, and any autonomous external action.
- **Spend cap** — a hard per-period limit; exceed → incident.
- **Lane authorizations — earned, not granted.** An agent earns a lane by passing the rulebook on real assignments: **≥3 clean (honey) receipts and 0 critical (propolis) flags → approved · one propolis → restricted · recurring → blocked.** Receipts keep the record. *(Live in Cloud.)*
- **Lane locks** — operator or watchdog can hard-lock a lane regardless of history.

Doctrine: **agents earn their lanes.** Not approved because they exist; not trusted because the model is large; not enough because the box runs or the cloud scales. The *stack* is evaluated: task · model · compute · runtime · tools · cost · failure mode · proof.

---

## 17. First 5 customer use cases

1. **AI receptionist** (local service business) — intake, routing, appointment notes. Lanes: `local_file_intake`, `routing`. Stack: edge 3–7B on owner-compute or low-cost hosted. Approval: refunds/complaints gated. Cost: low.
2. **CRE deal intake + memo** (broker) — edge extracts the deal package; hosted 9–27B drafts the memo. Lanes: `evidence_extraction` (approved, edge) + `cre_math`/`cre_client_memo` (restricted, hosted, approval required). Stack: **hybrid**. Cost: medium ×24-7.
3. **Document classifier / file intake** (back office) — watch a folder, extract fields, flag missing inputs. Lanes: `local_file_intake`, `evidence_extraction`. Stack: owner edge. Cost: low. Strong owner-compute fit.
4. **Customer-support draft assistant** — draft replies from a knowledge base; human sends. Lanes: `document_draft` (restricted — client-facing, approval required). Stack: hosted 9–14B. Cost: low–medium.
5. **Dataset quality review** (data team) — check a dataset against rules before training. Lanes: `dataset_quality_review`. Stack: hosted workhorse, hybrid if data is private. Cost: medium.

Each returns: recommended stack · approved/restricted/blocked lanes · cost band · proof.

---

## 18. MVP build plan

Build on what Cloud already has (AgentProfile, lanes, eval, incidents, receipts, Stack Planner). Don't fake telemetry.

- **Phase 0 — Core Assessment (now).** Add `ComputeProfile`, `RuntimeProfile`, `ModelProfile`, `LaneRequirement`, `ExecutionProfile` objects. Extend the Stack Planner → a written **Compute Fit Report** + an Assessment receipt. *Sellable immediately; no new infra.*
- **Phase 1 — Lane requirements in the referee.** Flight sheets declare `LaneRequirement`; a pre-check compares the run's ExecutionProfile and throws `model_class_below_lane_requirement` / `compute_undersized` / `assignment_exceeds_agent_lane` as real flags. Makes "the stack failed" a receipted verdict.
- **Phase 2 — Telemetry contract.** A lightweight agent/runtime reporter posts heartbeats + run status + spend to Core → `ComputeProfile.last_heartbeat`, uptime, spend. *This is what unlocks live `agent_dark` / `spend_cap_exceeded` incidents into the existing incident→receipt pipe.* Until shipped, monitoring is "deterministic from receipts," not live.
- **Phase 3 — Core Setup tooling.** Scripted owner-compute setup (OS/runtime/Ollama/agent install + Cloud connection), and a managed hosted endpoint option.
- **Phase 4 — Core Managed dashboard.** Health, incidents, repair queue, monthly Proof-of-Execution report.

Site/brand: stand up `defendablecore.com` (mirror the proven Astro build) once Phase 0 is real.

---

## 19. Website hero copy

> **The engine room for business AI agents**
> # Somewhere reliable for your AI agents to live.
> Plan the stack. Deploy the runtime. Watch the agent. Prove the work.
> DefendableCore runs business AI agents on the right compute — owner, hosted, or hybrid — and connects every run to DefendableCloud for Proof of Execution.
> DefendableCore runs it. DefendableOS verifies it. DefendableCloud proves it.
> `[ Get a Core Assessment ]`  `[ See how the stack works ]`

Alt H1s: *"AI agents need infrastructure. DefendableCore keeps them running."* · *"Before your business depends on AI agents, make sure they have somewhere reliable to live."*

---

## 20. Sales one-liner

**AI agents need infrastructure. DefendableCore keeps them running.**

Sharper, consultative: *"Before your business depends on AI agents, make sure they have somewhere reliable to live."*

Closing line: **AI agents need somewhere to live. DefendableCore makes the stack real.**

---

## 21. Risks / limitations

- **We are not a hyperscaler.** Core curates and manages a stack; it does not compete with AWS/Azure on raw scale.
- **Owner-compute uptime is owner-dependent** unless explicitly managed (power, internet, hardware failure).
- **Live monitoring needs telemetry** that does not exist until Phase 2. Selling "24/7 monitoring" before then is dishonest.
- **Not autonomous-safe.** Client-facing and high-stakes work require human approval; Core reduces risk, it does not remove the human.
- **Hardware logistics** (procurement, shipping, on-site setup) add operational burden for owner-compute/Setup packages.
- **Support load** scales with managed customers; pricing must cover real ops time.
- **Model/runtime churn** — local model and runtime ecosystems move fast; profiles must be maintained.

---

## 22. What not to claim yet

- ❌ "Live monitoring" / "24/7 watch" — **not until telemetry (Phase 2) ships.** Today: deterministic-from-receipts.
- ❌ "Autonomous and safe" — human approval is still required for client-facing/high-stakes/autonomous lanes.
- ❌ "A browser agent is production infrastructure" — it is not; installed ≠ running.
- ❌ Vague "AI governance" claims — Core's governance is **declared policy + earned lanes + deterministic flags + human approval**, nothing fuzzier.
- ❌ "We run your whole business" — Core runs *evaluated, lane-authorized* workflows, with proof.
- ❌ False-precise cost numbers — quote **bands** with the always-on multiplier shown.
- ❌ "Bigger model = better" — fit is to the lane, proven by receipts.

Be precise, always: **owner-compute · hosted compute · hybrid compute · model tier · runtime · monitoring · incidents · receipts · lane authorization.**

---

*DefendableCore is the engine room for business AI agents. AI agents need somewhere to live. DefendableCore makes the stack real.*
