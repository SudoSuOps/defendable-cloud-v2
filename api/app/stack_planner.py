"""Agent Stack Planner — a DECLARED rulebook, not a judge model.

The buyer's real question under the agent buzz: where does it run, what brain
does the work need, what does it cost, what can it safely do? This maps it
deterministically:

  jobs → required model tier → required compute tier → deployment → cost band
       → approved / restricted / blocked lanes → human-approval rule

Edit the tables to tune the house view. No LLM opinion enters here — same inputs,
same recommendation, every time. Proof still comes from running the eval.
"""
from __future__ import annotations

# Brains, smallest → biggest. Rank is the only ordering that matters.
MODEL_TIERS = ["edge", "workhorse", "senior", "anchor"]
RANK = {t: i for i, t in enumerate(MODEL_TIERS)}
MODEL_LABEL = {
    "edge": "Edge (3–4B)", "workhorse": "Workhorse (7–14B)",
    "senior": "Senior (27–34B)", "anchor": "Anchor (70B+)",
}

# A job/lane → the minimum brain it deterministically requires. client_facing /
# high_stakes / autonomous carry their own guardrails regardless of size.
TASK_CLASSES: dict[str, dict] = {
    "intake":              {"label": "Intake / data entry",                 "min_model": "edge"},
    "evidence_extraction": {"label": "Evidence / field extraction",         "min_model": "edge"},
    "log_summary":         {"label": "Log / document summary",              "min_model": "edge"},
    "routing":             {"label": "Routing / classification",            "min_model": "edge"},
    "drafting":            {"label": "Document drafting (internal)",        "min_model": "workhorse"},
    "structured_analysis": {"label": "Structured analysis / underwriting",  "min_model": "workhorse"},
    "financial_math":      {"label": "Financial math (DSCR, cap rate…)",    "min_model": "workhorse", "high_stakes": True},
    "synthesis_memo":      {"label": "Synthesis / client memo",             "min_model": "senior",    "client_facing": True},
    "deep_research":       {"label": "Multi-doc / deep research",           "min_model": "senior"},
    "arbitration":         {"label": "High-stakes arbitration / enterprise","min_model": "anchor",    "high_stakes": True},
    "autonomous_action":   {"label": "Autonomous external action",          "min_model": "workhorse", "autonomous": True},
}

# Where it can live → biggest brain it hosts, cost band, 24/7 strength, owner-ownable.
COMPUTE_TIERS = {
    "owner_edge":   {"label": "Owner edge device (Jetson / Mini PC / CPU)", "max_model": "edge",      "cost": "low",    "owner": True,  "uptime": "fragile"},
    "owner_gpu":    {"label": "Owner GPU box (16–24GB)",                    "max_model": "workhorse", "cost": "low-med", "owner": True,  "uptime": "ok"},
    "hosted_gpu":   {"label": "Hosted GPU (24GB+)",                         "max_model": "senior",    "cost": "medium", "owner": False, "uptime": "strong"},
    "hosted_multi": {"label": "Hosted multi-GPU",                          "max_model": "anchor",    "cost": "high",   "owner": False, "uptime": "strong"},
}
_COMPUTE_ORDER = ["owner_edge", "owner_gpu", "hosted_gpu", "hosted_multi"]
COST_RANK = {"low": 0, "low-med": 1, "medium": 2, "high": 3}


def options() -> dict:
    return {
        "task_classes": [{"key": k, **v} for k, v in TASK_CLASSES.items()],
        "model_tiers": [{"key": k, "label": MODEL_LABEL[k]} for k in MODEL_TIERS],
        "compute_tiers": [{"key": k, **v} for k, v in COMPUTE_TIERS.items()],
    }


def _smallest_compute_for(model_tier: str, hosted_only: bool = False) -> str:
    for c in _COMPUTE_ORDER:
        if hosted_only and COMPUTE_TIERS[c]["owner"]:
            continue
        if RANK[COMPUTE_TIERS[c]["max_model"]] >= RANK[model_tier]:
            return c
    return "hosted_multi"


def assess(answers: dict, earned_lanes: list[dict] | None = None) -> dict:
    jobs = [j for j in (answers.get("jobs") or []) if j in TASK_CLASSES]
    if not jobs:
        return {"error": "pick at least one job"}

    needs_24_7 = bool(answers.get("needs_24_7"))
    client_facing = bool(answers.get("client_facing")) or any(TASK_CLASSES[j].get("client_facing") for j in jobs)
    high_stakes = bool(answers.get("high_stakes")) or any(TASK_CLASSES[j].get("high_stakes") for j in jobs)
    has_autonomous = any(TASK_CLASSES[j].get("autonomous") for j in jobs)
    data_local_only = bool(answers.get("data_local_only"))
    pref = answers.get("deployment_pref") or "no_pref"

    # required brain = the heaviest job's minimum
    req_rank = max(RANK[TASK_CLASSES[j]["min_model"]] for j in jobs)
    required_model = MODEL_TIERS[req_rank]
    recommended_model = required_model  # bump synthesis one notch for headroom
    if client_facing and req_rank >= RANK["senior"]:
        recommended_model = "senior"

    has_light = any(RANK[TASK_CLASSES[j]["min_model"]] == 0 for j in jobs)
    spans = has_light and req_rank >= RANK["workhorse"]

    reasons: list[str] = []

    # --- deployment decision (deterministic) ---
    if spans:
        deployment = "hybrid"
        reasons.append("Jobs span light intake and heavier reasoning — a local agent collects, a cloud brain analyzes.")
    elif req_rank <= RANK["edge"] and (data_local_only or pref == "owner"):
        deployment = "owner"
        reasons.append("All selected jobs are edge-class and data stays local — owner-compute is sufficient.")
    elif req_rank >= RANK["senior"] or (needs_24_7 and client_facing):
        deployment = "cloud"
        reasons.append("Senior-class reasoning and/or 24-7 client-facing uptime — hosted compute carries it reliably.")
    elif data_local_only or pref == "owner":
        deployment = "owner"
        reasons.append("Workhorse-class work that can stay on an owner GPU box; data stays local.")
    else:
        deployment = "cloud"
        reasons.append("Workhorse reasoning with reliability needs — hosted compute is the safer default.")

    if pref != "no_pref" and pref != deployment and not (pref == "hybrid" and spans):
        reasons.append(f"You preferred {pref}; the rulebook recommends {deployment} for this work — see the gap below.")

    # --- compute tier ---
    min_compute = _smallest_compute_for(required_model)
    rec_compute = min_compute
    if (needs_24_7 or client_facing) and COMPUTE_TIERS[min_compute]["uptime"] != "strong":
        rec_compute = _smallest_compute_for(recommended_model, hosted_only=True)
        reasons.append("24-7 / client-facing operation needs strong uptime — recommending hosted GPU over an owner box.")

    owner_can = COMPUTE_TIERS[min_compute]["owner"]
    owner_fit = "strong" if owner_can and req_rank <= RANK["workhorse"] else ("partial" if has_light else "none")
    cloud_fit = "strong"

    # --- cost band ---
    cost = COMPUTE_TIERS[rec_compute]["cost"]
    cost_band = {"low": "low", "low-med": "low–medium", "medium": "medium", "high": "high"}[cost]
    if needs_24_7 and COST_RANK[cost] < COST_RANK["high"]:
        cost_band += " (×24-7 always-on)"

    human_approval_required = client_facing or high_stakes or has_autonomous
    if human_approval_required:
        reasons.append("Client-facing / high-stakes / autonomous work — human approval is required before release.")

    # --- lanes vs the recommended stack ---
    stack_rank = RANK[COMPUTE_TIERS[rec_compute]["max_model"]]
    approved, restricted, blocked = [], [], []
    for j in jobs:
        t = TASK_CLASSES[j]
        entry = {"key": j, "label": t["label"], "min_model": t["min_model"]}
        if t.get("autonomous"):
            restricted.append({**entry, "why": "autonomous action — allowed only behind human approval"})
        elif RANK[t["min_model"]] <= stack_rank:
            (restricted if (t.get("client_facing") or t.get("high_stakes")) else approved).append(
                {**entry, "why": "human approval required before release"} if (t.get("client_facing") or t.get("high_stakes")) else entry
            )
        else:
            blocked.append({**entry, "why": f"needs {MODEL_LABEL[t['min_model']]} — above the recommended stack"})

    summary = (
        f"{deployment.title()} deployment · {MODEL_LABEL[recommended_model]} brain on "
        f"{COMPUTE_TIERS[rec_compute]['label']} · {cost_band} cost"
        + (" · human approval before client-facing output" if human_approval_required else "")
        + "."
    )

    return {
        "deployment": deployment,
        "required_model": required_model,
        "recommended_model": recommended_model,
        "min_compute": min_compute,
        "recommended_compute": rec_compute,
        "model_label": MODEL_LABEL[recommended_model],
        "compute_label": COMPUTE_TIERS[rec_compute]["label"],
        "owner_fit": owner_fit,
        "cloud_fit": cloud_fit,
        "cost_band": cost_band,
        "human_approval_required": human_approval_required,
        "approved_lanes": approved,
        "restricted_lanes": restricted,
        "blocked_lanes": blocked,
        "reasons": reasons,
        "summary": summary,
        "earned_lanes": earned_lanes or [],
        "next_step": "Run an eval on the matched flight sheet to prove the lane — proof comes from the rulebook, not the recommendation.",
    }
