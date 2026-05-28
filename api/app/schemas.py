from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ── Doctrine literals — the locked vocabulary ─────────────────────────────────
#
# These are the type-level vocabulary of the rulebook engine. Every schema
# below references them; OpenAPI emits them as named string-enum components.
# Once they're declared here, the next person can't accidentally rename a
# value (e.g. ship "warning" instead of "jelly") without breaking the type
# check at the route boundary. The referee is a rulebook, not a judge.

Lane = Literal["agent", "dataset", "compute", "other"]
EvidenceKind = Literal["file", "note", "url", "observation", "tool_output", "model_output", "log"]
CapabilityTier = Literal["edge", "small", "mid", "frontier"]

# Severity — the verdict-level severity. Flag-driven, never opinion.
#   honey    = no flags + approved (or low-tier only with notes)
#   jelly    = mid-tier flag(s) only — usable with limitations / after repair
#   propolis = any high-tier flag — game-changer, do not release
Severity = Literal["honey", "jelly", "propolis"]

# Verdict outcome — the high-level shape of the verdict.
VerdictOutcome = Literal["pass", "risk", "fail"]

# TierLevel — the rule's pre-weighted risk tier. Drives flag weight + verdict.
TierLevel = Literal["low", "mid", "high"]

# CheckStatus — the result of applying a single rule.
#   pass = rule satisfied
#   flag = rule violated (a thrown flag)
#   open = rule applies but a human must apply it (checklist) — not yet decided
#   skip = rule's condition cannot be machine-evaluated in this version
CheckStatus = Literal["pass", "flag", "open", "skip"]

# CheckCategory — what kind of rule it is (drives three-bucket attribution).
#   work-defect = math / schema / structure / evidence  (fixable, resubmit)
#   deal-finding = policy                                (the math is right; the rule says no)
CheckCategory = Literal["structure", "schema", "math", "evidence", "policy"]

# CheckKind — who applies the rule.
#   auto      = the engine decides pass | flag deterministically
#   checklist = a human operator applies a declared binary rule (satisfied | flag)
CheckKind = Literal["auto", "checklist"]

# CheckSource — origin of the applied result on a CheckResult row.
CheckSource = Literal["auto", "operator"]

# ApprovalDecision — what a human operator decides at the approval gate.
ApprovalDecision = Literal["approved", "rejected", "escalated"]

# RuleSeverity — the severity a *rule* declares on a Flight Sheet.
#
# This is distinct from `Severity` (the *verdict* rollup honey/jelly/propolis).
# RuleSeverity is the rule's *pre-weight* — what the rulebook author said
# about how bad it is when this rule is violated. `tier_of()` normalizes any
# of these into a TierLevel (low/mid/high).
#
# The union below is the closed set of every value that has ever appeared in a
# Flight Sheet author's hand:
#   - new tier-shaped values:          high | mid | medium | low
#   - Kimi Library V1 vocabulary:      critical | noncritical
#   - verdict vocabulary leak (legacy): honey | jelly | propolis | minor
#
# Anything outside this union is a Flight Sheet authoring bug; the API
# refuses to serialize it (Pydantic validation) so drift surfaces at the
# contract boundary instead of being silently coerced.
RuleSeverity = Literal[
    "high", "mid", "medium", "low",
    "critical", "noncritical",
    "honey", "jelly", "propolis",
    "minor",
]

# IncidentKind — operational-state incident classes (Agent Ops governance).
#
# These are *operational* incidents — events that cross out of "this Run had a
# flag" into "this is an operational problem with the agent/lane itself."
#
#   rogue            = agent took unauthorized action (tool use outside its
#                      declared grant, exfil attempt, declined-policy override)
#   dark             = agent is unreachable / not heartbeating beyond SLO
#   policy_violation = a declared governance gate breached (spend cap, blocked
#                      lane, client_output-without-approval). A *single* critical
#                      flag becomes an incident via this lane if the lane policy
#                      declares it; otherwise a single flag stays a Run-level
#                      work-defect or deal-finding handled by the repair plan.
#   recurring_flag   = the same rule has flagged ≥N times → operational pattern,
#                      not a one-off
#
# Note: there is intentionally NO `single_flag` member. A single flag is a
# Run-level concern (the repair plan owns it). Crossing into incident-land
# requires either a declared policy violation or a recurring pattern. See
# `policy_violation` for the single-flag-becomes-incident path.
IncidentKind = Literal["rogue", "dark", "policy_violation", "recurring_flag"]


class HealthOut(BaseModel):
    ok: bool
    service: str
    version: str
    db: bool
    storage: bool
    email_configured: bool
    bucket: str


class MagicRequestIn(BaseModel):
    email: str


class MagicVerifyIn(BaseModel):
    token: str


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class RunIn(BaseModel):
    project_id: str
    flight_sheet_id: Optional[str] = None
    agent_profile_id: Optional[str] = None
    lane: Optional[Lane] = None
    title: Optional[str] = Field(default=None, max_length=300)
    inputs: Dict[str, Any] = Field(default_factory=dict)


class StackAssessmentIn(BaseModel):
    jobs: list[str] = Field(default_factory=list)
    needs_24_7: bool = False
    client_facing: bool = False
    high_stakes: bool = False
    data_local_only: bool = False
    deployment_pref: Optional[Literal["owner", "cloud", "hybrid", "no_pref"]] = "no_pref"
    budget: Optional[Literal["low", "medium", "high"]] = None


class AgentProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    harness: Optional[str] = Field(default=None, max_length=80)
    harness_version: Optional[str] = Field(default=None, max_length=40)
    model: Optional[str] = Field(default=None, max_length=120)
    model_provider: Optional[str] = Field(default=None, max_length=80)
    served_by: Optional[str] = Field(default=None, max_length=40)
    runtime_host: Optional[str] = Field(default=None, max_length=120)
    runtime_os: Optional[str] = Field(default=None, max_length=80)
    runtime_hardware: Optional[str] = Field(default=None, max_length=160)
    tools: list[str] = Field(default_factory=list)
    context_window: Optional[int] = None
    capability_tier: Optional[CapabilityTier] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    governance: Optional[Dict[str, Any]] = None  # {requires_approval_client_output, spend_cap_usd, blocked_lanes:[name], notes}


class IncidentIn(BaseModel):
    """Open an operational-state incident against an agent profile or Run.

    See `IncidentKind` for the closed taxonomy (rogue | dark | policy_violation |
    recurring_flag) and why a single flag is intentionally not its own member.
    """

    agent_profile_id: Optional[str] = None
    run_id: Optional[str] = None
    kind: IncidentKind = "policy_violation"
    tier: Optional[TierLevel] = "high"
    title: str = Field(min_length=1, max_length=300)
    detail: Optional[str] = Field(default=None, max_length=4000)
    lane: Optional[str] = Field(default=None, max_length=200)
    response: list[str] = Field(default_factory=list)


class EvidenceIn(BaseModel):
    kind: EvidenceKind = "note"
    label: str = Field(min_length=1, max_length=300)
    content: Optional[str] = None


class ApprovalIn(BaseModel):
    decision: Literal["approved", "rejected", "escalated"]
    note: Optional[str] = None


class CookRequestIn(BaseModel):
    dataset_id: str
    base_model: str = "swarm/curator-9b"


class RunnerClaimIn(BaseModel):
    runner: str = "rig"


class RunnerStatusIn(BaseModel):
    status: Literal["running", "claimed"] = "running"
    metrics: Dict[str, Any] = Field(default_factory=dict)


class RunnerCompleteIn(BaseModel):
    eval_after: float
    adapter_ref: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class RunnerFailIn(BaseModel):
    error: str


# ──────────────────────────────────────────────────────────────────────────────
# Doctrine response schemas — the named contracts the API speaks.
#
# These promote the doctrine concepts to named components in the OpenAPI doc
# so the next person editing a route can't accidentally rename a field. Every
# field below is matched to the current wire shape; ConfigDict(extra="allow")
# is used on composite schemas during this migration so a route producing one
# additional field doesn't get filtered.
# ──────────────────────────────────────────────────────────────────────────────


class FlightSheetRule(BaseModel):
    """A single rule on a Flight Sheet. The flight sheet's `audit_checks[]`."""

    model_config = ConfigDict(extra="allow")
    key: str
    label: str
    category: Optional[str] = None
    kind: Optional[CheckKind] = None
    severity: Optional[RuleSeverity] = Field(
        default=None,
        description=(
            "The rule's pre-weight. `tier_of()` normalizes any RuleSeverity value to "
            "a TierLevel (low/mid/high). Wire-locked to the RuleSeverity literal so "
            "a Flight Sheet authoring drift surfaces at the contract boundary."
        ),
    )


class FlightSheet(BaseModel):
    """The declared rulebook for an Eval Run lane. Source of truth = `flight_sheet_out()`."""

    model_config = ConfigDict(extra="allow")
    id: str
    slug: str
    name: str
    version: str
    lane: Lane
    summary: Optional[str] = None
    purpose: Optional[str] = None
    assignment_instructions: Optional[str] = None
    required_inputs: List[str] = Field(default_factory=list)
    expected_outputs: List[str] = Field(default_factory=list)
    audit_checks: List[FlightSheetRule] = Field(default_factory=list)
    pass_threshold: int
    fail_threshold: int


class FlightSheetList(BaseModel):
    """`GET /flight-sheets` wrapper."""

    flight_sheets: List[FlightSheet]


class Submission(BaseModel):
    """The agent's structured output for a Run. Sealed at submission time by sha256."""

    model_config = ConfigDict(extra="allow")
    agent_name: Optional[str] = None
    model_name: Optional[str] = None
    provider: Optional[str] = None
    output_text: str
    tool_logs: Optional[str] = None
    notes: Optional[str] = None
    sha256: str
    submitted_at: Optional[str] = Field(
        default=None, description="ISO-8601 datetime."
    )


class Check(BaseModel):
    """One applied rule from the rulebook engine.

    Each rule passes or raises a flag. There is no opinion grade. `status` is
    the deterministic outcome; `severity` and `category` come from the rule's
    declaration on the Flight Sheet.

    `severity` here is the *rule's* pre-weight (a `RuleSeverity`), NOT the
    verdict severity (which is honey/jelly/propolis — see `Severity` and
    `Verdict.severity`). The rolled-up verdict severity is computed by
    `compute_verdict()` from all the flag-status checks on the Run.
    """

    model_config = ConfigDict(extra="allow")
    id: Optional[str] = None
    check_key: str
    label: str
    category: Optional[str] = Field(
        default=None,
        description="structure | schema | math | evidence | policy (may be empty on legacy rows).",
    )
    status: CheckStatus
    severity: Optional[RuleSeverity] = Field(
        default=None,
        description="The *rule's* declared pre-weight. tier_of() normalizes to TierLevel.",
    )
    source: Optional[CheckSource] = None
    detail: Optional[str] = None
    score: Optional[float] = None


class Finding(Check):
    """A `Check` whose status is `flag`.

    Distinct named type so the doctrine surfaces in OpenAPI: a *finding* is a
    *located defect*, sorted into one of three buckets by `category`:
        work-defect  → math / schema / structure / evidence  (correct & resubmit)
        deal-finding → policy                                 (the math is right; the rule says no)
        stack-fit    → attributed by the run's agent_profile capability tier
    """


class Verdict(BaseModel):
    """The deterministic verdict produced by the referee from the applied rules.

    Score is the **% of declared rules satisfied**, weighted by tier — NOT a
    quality grade. Severity is flag-driven: any high-tier flag → propolis;
    mid-tier flag(s) only → jelly; otherwise → honey.
    """

    model_config = ConfigDict(extra="allow")
    outcome: VerdictOutcome
    summary: Optional[str] = None
    score: Optional[float] = Field(default=None, description="0.0 – 1.0")
    score_100: Optional[int] = Field(default=None, description="0 – 100, weighted by tier.")
    severity: Optional[Severity] = None
    client_ready: Optional[str] = None
    recommended_action: Optional[str] = None
    checks_passed: int
    checks_failed: int
    created_at: Optional[str] = None
    risk_breakdown: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="{high: [...], mid: [...], low: [...]} — populated by compute_verdict.",
    )


class Approval(BaseModel):
    """The human approval gate for a Run. Receipts only mint on `decision='approved'`."""

    decision: ApprovalDecision
    approver_email: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[str] = None


class Receipt(BaseModel):
    """A minted receipt — the artifact + the hash chain coordinates returned to the operator.

    `share_url` and `pdf_url` are operator-facing; the actual chain bytes are
    in the persisted payload. Public consumers (no auth) get `PublicReceipt`.
    """

    receipt_id: str
    org_seq: int
    parent_hash: str
    receipt_sha256: str
    share_token: str
    share_url: str
    pdf_url: str
    created_at: Optional[str] = None


class LedgerEntry(BaseModel):
    """A single row of the per-org hash chain. The chain coordinates without the payload.

    `parent_hash` of row N points at `receipt_sha256` of row N-1. Row 0's
    parent_hash is the canonical ZERO_HASH (sixty-four zeros).
    """

    receipt_id: str
    org_seq: int
    parent_hash: str
    receipt_sha256: str
    created_at: Optional[str] = None


class LedgerList(BaseModel):
    """`GET /ledger` wrapper — the per-org chain in org_seq order."""

    entries: List[LedgerEntry]


class ChecksList(BaseModel):
    """`GET /runs/{id}/checks` wrapper — all applied rules for a Run, in author order."""

    checks: List[Check]


class FlagsList(BaseModel):
    """`GET /runs/{id}/flags` wrapper — the subset of checks with status='flag'.

    Each item is a `Finding` — a located defect. Clients sort into the three
    buckets via the `category` field (work-defect: math/schema/structure/evidence;
    deal-finding: policy; stack-fit: attributed by the Run's agent_profile tier).
    """

    flags: List[Finding]


class LedgerError(BaseModel):
    """A single integrity failure surfaced by `GET /ledger/verify`."""

    org_seq: int
    error: str


class LedgerVerifyResult(BaseModel):
    """`GET /ledger/verify` — walks the per-org chain client-side-equivalent."""

    ok: bool
    receipts_checked: int
    errors: List[LedgerError]


class PublicReceipt(BaseModel):
    """`GET /share/{token}` — the public-facing view of a receipt. No auth required.

    `verified` is computed server-side as the SHA-256 of the canonical payload
    compared to the stored `receipt_sha256` — anyone can recompute it client-side.
    """

    model_config = ConfigDict(extra="allow")
    receipt_id: str
    org_seq: int
    parent_hash: str
    receipt_sha256: str
    verified: bool
    created_at: Optional[str] = None
    payload: Dict[str, Any]


# ──────────────────────────────────────────────────────────────────────────────
# Org / client-dashboard schemas (Phase 4 of the pre-finality sprint)
# ──────────────────────────────────────────────────────────────────────────────


# Plan tier — placeholder until Phase 5 (Stripe) wires real billing.
PlanTier = Literal["free", "pro", "enterprise"]


class Org(BaseModel):
    """`GET /org` — the signed-in user's organization, with light stats."""

    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    slug: str
    member_count: int = 1
    receipt_count: int = 0
    plan: PlanTier = "free"
    created_at: Optional[str] = None


class ApiKey(BaseModel):
    """A redacted view of an API key. NO secret — the secret only ships once,
    inside `ApiKeyCreated` on the POST response. After that, only the short
    `key_prefix` is shown for display.
    """

    id: str
    name: str
    key_prefix: str = Field(description="The first 12 characters of the key — safe to display.")
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None
    revoked: bool = False


class ApiKeyList(BaseModel):
    """`GET /org/api-keys`"""

    api_keys: List[ApiKey]


class ApiKeyCreated(BaseModel):
    """`POST /org/api-keys` response — returned ONCE on creation. The plaintext
    `secret` is never shown again; subsequent reads return `ApiKey` (no secret).
    """

    id: str
    name: str
    key_prefix: str
    secret: str = Field(
        description=(
            "The full API key in plaintext. Format `dc_<random>`. SAVE IT NOW — "
            "this is the only time the secret is returned. Lost keys must be revoked + recreated."
        )
    )
    created_at: Optional[str] = None


class ApiKeyIn(BaseModel):
    """`POST /org/api-keys` body — name the key for human discovery."""

    name: str = Field(min_length=1, max_length=200)


class UsageStats(BaseModel):
    """`GET /org/usage` — receipt minting + chain position. Placeholder for
    metered billing in Phase 5; today reports raw counts so the dashboard can
    show usage even before Stripe lands.
    """

    model_config = ConfigDict(extra="allow")
    receipts_lifetime: int
    receipts_this_month: int
    org_seq: int = Field(description="The next org_seq the chain will assign — equals receipts_lifetime today.")
    earned_lanes: int = Field(default=0, description="Count of agent profiles with ≥3 honey + 0 propolis on any lane.")
