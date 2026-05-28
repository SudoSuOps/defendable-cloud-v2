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


# ──────────────────────────────────────────────────────────────────────────────
# Membership schemas — the members-only community gate.
#
# DefendableCloud is members-only. $100/year. Hard cap at MEMBERSHIP_CAP active
# seats. Trust-based monthly billing once active (no Stripe checkout — bills
# go out as part of the relationship). When the cap is hit, new applications
# become `waitlisted` and surface their queue position.
# ──────────────────────────────────────────────────────────────────────────────


# MembershipStatus — closed taxonomy of an org's membership state.
#   pending     · applied to join OR never applied; not yet a seat-holder
#   active      · holds a seat in the cap · gets dataset + compute access
#   waitlisted  · applied while the cap was full · will roll into active when a seat opens
#   inactive    · was active, then lapsed (legacy/future state)
MembershipStatus = Literal["pending", "active", "waitlisted", "inactive"]


class MembershipApplicationView(BaseModel):
    """What the applicant told us when they applied. Stored as JSONB on the
    organization; surfaced read-only on `GET /membership` so the org can see
    what they submitted (and admins can review).
    """

    model_config = ConfigDict(extra="allow")
    company_name: Optional[str] = None
    intended_use: Optional[str] = None
    referral_source: Optional[str] = None


class Membership(BaseModel):
    """`GET /membership` — the org's membership state + community capacity.

    `cap` is the hard ceiling on active members; `active_count` is the current
    headcount. When `active_count >= cap`, new applications become
    `waitlisted` and `waitlist_position` is the order they joined the queue.
    """

    status: MembershipStatus
    applied_at: Optional[str] = None
    activated_at: Optional[str] = None
    seat_number: Optional[int] = Field(
        default=None,
        description="Filled when status='active'. The seat the org holds (1..cap).",
    )
    cap: int = Field(description="Hard cap on active seats. Defaults to 100.")
    active_count: int = Field(description="Current active member count across the platform.")
    waitlist_position: Optional[int] = Field(
        default=None,
        description="Filled when status='waitlisted'. 1 = next in line.",
    )
    application: Optional[MembershipApplicationView] = None


class MembershipApplicationIn(BaseModel):
    """`POST /membership/apply` body. All fields optional except company_name —
    intended_use is the one we read most carefully; referral_source helps us
    understand how the community is growing.
    """

    company_name: str = Field(min_length=1, max_length=200)
    intended_use: Optional[str] = Field(default=None, max_length=1000)
    referral_source: Optional[str] = Field(default=None, max_length=200)


class AdminApplicationRow(BaseModel):
    """One row in the Admin Approval UI queue."""

    model_config = ConfigDict(extra="allow")
    org_id: str
    org_slug: str
    org_name: str
    applicant_email: Optional[str] = None
    status: str = Field(description="`pending` or `waitlisted`.")
    applied_at: Optional[str] = None
    waitlist_position: Optional[int] = None
    company_name: Optional[str] = None
    intended_use: Optional[str] = None
    referral_source: Optional[str] = None


class AdminApplicationList(BaseModel):
    """`GET /admin/applications` response."""

    applications: List[AdminApplicationRow]
    count: int


class MembershipApproveIn(BaseModel):
    """`POST /membership/approve` body · admin endpoint, internal-key gated.

    Identifies the org by its slug (same identifier the application email
    surfaces in the operator inbox).
    """

    org_slug: str = Field(min_length=1, max_length=80)


class MembershipCheckoutIn(BaseModel):
    """`POST /membership/checkout` body. Optional · the only field is the
    return origin (defaults to app_base_url), useful for preview deploys
    that want Stripe to redirect back to a non-prod URL.
    """

    model_config = ConfigDict(extra="ignore")
    return_to_origin: Optional[str] = Field(
        default=None,
        description="Override the success/cancel redirect origin. Defaults to APP_BASE_URL.",
    )


class MembershipCheckoutOut(BaseModel):
    """`POST /membership/checkout` response · the Stripe-hosted URL the
    frontend redirects the member to. The session expires after ~24h."""

    url: str = Field(description="Stripe Checkout hosted URL · redirect the browser here.")
    session_id: str = Field(description="Stripe checkout session id · useful for client-side logging.")
    expires_at: int = Field(description="Unix epoch seconds when the Stripe session expires.")


class TrainingDataPolicy(BaseModel):
    """`GET /policy/training-data` — frozen doctrine on what enters and never
    enters the training corpus. Hash-anchored: the `sha256` field is computed
    over the canonical body and any drift shifts the hash. Public, no auth.

    > We learn from how agents fail. We never learn from what your business is doing.
    """

    version: str = Field(description="Policy version. Updates bump this and last_updated.")
    statement: str
    we_learn_from: List[str]
    we_dont_learn_from: List[str]
    enforcement: List[str]
    effective_at: str
    last_updated: str
    sha256: str = Field(
        description="SHA-256 over the canonical policy body (excluding this field). Anyone can recompute."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Dataset catalog schemas — the members-only library surface.
#
# The catalog mirrors /mnt/swarm/CATALOG.md (the books-and-records inventory).
# 99 packages across 12 verticals · 3.35M training pairs · hash-anchored.
# Datasets are FREE with membership; we surface package identity + pair counts
# + deed status, never the internal NAS path or our internal $ valuation.
# ──────────────────────────────────────────────────────────────────────────────


class DatasetPackage(BaseModel):
    """A single dataset package in the library. Identity + counts + provenance,
    never the on-disk path or our internal valuation.
    """

    model_config = ConfigDict(extra="allow")
    slug: str = Field(description="Stable identifier · `<vertical>_<name-slug>` form.")
    name: str
    vertical: str = Field(description="One of: cre · medical · grants · jelly · signal · capital-markets · bee-hive · legal · finance · aviation · openalex · failure")
    tier: str = Field(description="Maturity tier · e.g. honey · canonical · master · royal_jelly · train · mixed · propolis · eval")
    pkg_class: str = Field(description="Package class · e.g. Premium · Expert · Specialist · Taste")
    pairs: int = Field(description="Count of training pairs in the package.")
    deed_anchored: bool = Field(description="True when the package has a local Merkle deed-anchor on the NAS.")
    deed: str = Field(description="Raw deed status · `none` or `anchored_local` or other.")


class DatasetCatalogScorecard(BaseModel):
    """Top-level totals from the catalog header — Total packages · Total pairs ·
    Deed-anchored count. Mirrors what's in CATALOG.md's `Sale-Ready Scorecard`.
    """

    model_config = ConfigDict(extra="allow")
    total_packages: int
    total_pairs: int
    priced_packages: Optional[int] = None
    deed_anchored: int
    total_usd: Optional[float] = Field(
        default=None,
        description=(
            "Internal valuation only — surfaced for books-and-records transparency. "
            "Datasets are FREE with membership; this isn't a customer-facing price."
        ),
    )


class DatasetCatalogVertical(BaseModel):
    """Per-vertical roll-up — packages + pairs + (internal) $ rollup."""

    model_config = ConfigDict(extra="allow")
    packages: int
    pairs: int
    usd: Optional[float] = None


class DatasetCatalogAnchor(BaseModel):
    """The catalog's anchor stamp — `grand_root_v2` label + hash from CATALOG.md."""

    label: Optional[str] = None
    hash: Optional[str] = None


class DatasetDownloadRequest(BaseModel):
    """`POST /datasets/catalog/{slug}/download` body — optional TTL override.

    Defaults to 24 hours; capped at 7 days to keep signed URLs short-lived.
    The receipt itself is permanent; only the operational signed URL TTL is
    bounded.
    """

    model_config = ConfigDict(extra="ignore")
    expires_in_hours: int = Field(default=24, ge=1, le=168)


class DatasetDownloadPackage(BaseModel):
    """The package identity sealed into the download receipt."""

    model_config = ConfigDict(extra="allow")
    slug: str
    name: str
    vertical: str
    tier: str
    pkg_class: str
    pairs: int
    deed_anchored: bool


class DatasetDownloadGrant(BaseModel):
    """`POST /datasets/catalog/{slug}/download` response.

    The receipt is the books-and-records artifact (per-org hash chain, JSON +
    PDF, shareable). The download_url is operational — it's an indirection
    through `GET /share/{token}/download` which 302s to a fresh Tigris signed
    URL each access. When `ready=False` the file isn't yet staged in our
    download bucket; the receipt still mints and the member can re-request a
    fresh URL anytime via the same share token.
    """

    receipt_id: str
    org_seq: int
    receipt_sha256: str
    share_url: str = Field(
        description="Public proof page for the grant — the receipt anyone can verify."
    )
    download_url: str = Field(
        description=(
            "Operational handle. GET this URL → 302 to a fresh Tigris signed URL when "
            "ready, or 425 with Retry-After when still staging."
        )
    )
    ready: bool = Field(
        description="True when the file is staged in Tigris. False = preparing; retry later."
    )
    expires_at: str = Field(
        description="ISO timestamp · the signed-URL TTL end. Receipts themselves never expire."
    )
    package: DatasetDownloadPackage


class DatasetCatalog(BaseModel):
    """`GET /datasets/catalog` — the members-only library view of the corpus.

    Carries the catalog's own SHA-256 (from the NAS source) plus the packages'
    canonical-list SHA-256 (computed over the sorted package list). A member can
    fetch this, recompute the packages hash from the response, and confirm the
    API mirror matches the books-and-records source.
    """

    model_config = ConfigDict(extra="allow")
    version: str = Field(description="Catalog snapshot version. Updates ship a new deploy.")
    generated_at: Optional[str] = None
    filter_version: Optional[str] = None
    catalog_sha256: Optional[str] = Field(
        default=None,
        description="SHA-256 of the catalog as published on /mnt/swarm/CATALOG.md (source-of-truth header).",
    )
    packages_sha256: Optional[str] = Field(
        default=None,
        description="SHA-256 over the canonical sorted packages list. Recompute to verify.",
    )
    anchor: Optional[DatasetCatalogAnchor] = None
    scorecard: DatasetCatalogScorecard
    verticals: Dict[str, DatasetCatalogVertical]
    packages: List[DatasetPackage]


# ──────────────────────────────────────────────────────────────────────────────
# § 12 · Model card library (Sprint 10)
# In-house model cards · compute is the meter. Members can PIN a model card
# on the per-org chain to seal client-deliverable provenance ("we used this
# model for this work, declared on this date, here's the verifiable card hash").
# ──────────────────────────────────────────────────────────────────────────────


class ModelCard(BaseModel):
    """A public, member-facing model card. Hides operator-only fields
    (weights_location, default_rate_usd_per_hour). Includes `card_sha256`
    computed at load time over the canonical card body."""

    model_config = ConfigDict(extra="allow")
    slug: str = Field(description="Stable identifier · `<name>-<base>` form.")
    name: str
    family: str = Field(description="`in-house` for sovereign cooks; other tags reserved.")
    base: str = Field(description="Underlying open base model · e.g. Qwen2-27B, Qwen3.5-9B, Gemma-2-2B.")
    base_license: str
    params_b: float = Field(description="Approximate parameter count, in billions.")
    context_window: int
    purpose: str = Field(description="Short statement of what this model is for.")
    trained_on: List[str] = Field(description="Dataset slug references (catalog vocabulary).")
    eval_notes: Optional[str] = None
    compute_class: str = Field(description="Hardware tier expected · informs ops planning.")
    status: str = Field(description="`active` · `experimental` · `archived`.")
    deed: Optional[str] = None
    card_sha256: str = Field(description="SHA-256 of the canonical card body. Verifiable, stable.")


class ModelCatalogScorecard(BaseModel):
    """Top-level totals for the model catalog."""

    model_config = ConfigDict(extra="allow")
    total_models: int
    in_house_models: int
    active_models: int


class ModelCatalog(BaseModel):
    """`GET /models/catalog` — members-only model card library.

    Carries `models_sha256` (computed over the sorted card list). A member can
    fetch the catalog, recompute the hash from the response, and confirm the
    API mirror matches the books-and-records source.
    """

    model_config = ConfigDict(extra="allow")
    version: str
    generated_at: Optional[str] = None
    scope: Optional[str] = None
    doctrine_note: Optional[str] = None
    models_sha256: str = Field(
        description="SHA-256 over the canonical sorted card list. Recompute to verify."
    )
    scorecard: ModelCatalogScorecard
    models: List[ModelCard]


class ModelPinRequest(BaseModel):
    """`POST /models/catalog/{slug}/pin` body. Both fields optional.

    `declaration` is a short member-supplied note describing what the model
    is being pinned FOR (e.g. "agent A on deal X"). Sealed into the receipt
    payload as-is. `client_ref` is an optional opaque tag the member can use
    to link the receipt to their own bookkeeping.
    """

    model_config = ConfigDict(extra="ignore")
    declaration: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Free-text note · what is this model being pinned for?",
    )
    client_ref: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Opaque member-side identifier (deal/agent/project tag).",
    )


class ModelPinModel(BaseModel):
    """The card identity sealed into a pin receipt. Smaller than the full
    card — just the fields that make the model identifiable to a third party
    reading the receipt later."""

    model_config = ConfigDict(extra="allow")
    slug: str
    name: str
    base: str
    params_b: float
    card_sha256: str = Field(
        description="The exact card hash at pin time. Stable forever even if the card later changes."
    )


class ReceiptRollup(BaseModel):
    """One row in the per-org recent-receipts rollup.

    Identity + share URL + a compact `summary` projected from the receipt
    payload. The summary fields vary by schema; the OpenAPI surface declares
    it as `Dict[str, Any]` so callers can dispatch on schema and read the
    headline fields without re-fetching the receipt.
    """

    model_config = ConfigDict(extra="allow")
    receipt_id: str
    org_seq: int
    payload_schema: str = Field(
        description="The receipt payload's `schema` field · e.g. defendablecloud.cook-receipt/v1"
    )
    receipt_sha256: str
    share_url: str = Field(description="Public proof page · /share/{token} on the API host")
    created_at: Optional[str] = None
    summary: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Schema-aware compact projection from the payload. Carries headline "
            "fields for tile rendering (run_title, outcome, lift, model_slug, etc.)."
        ),
    )


class ReceiptRollupList(BaseModel):
    """`GET /receipts/recent` response · sorted desc by created_at."""

    rollups: List[ReceiptRollup]
    count: int


class ModelPinReceiptOut(BaseModel):
    """`POST /models/catalog/{slug}/pin` response."""

    receipt_id: str
    org_seq: int
    receipt_sha256: str
    share_url: str = Field(
        description="Public proof page for the pin — anyone with the URL can verify."
    )
    pinned_at: str = Field(description="ISO timestamp · when the pin was minted.")
    model: ModelPinModel
    declaration: Optional[str] = None
    client_ref: Optional[str] = None
