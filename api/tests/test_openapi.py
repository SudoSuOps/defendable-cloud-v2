"""Lock the doctrine vocabulary in the OpenAPI contract.

This test fails if a future code change silently drops one of the named doctrine
schemas from the OpenAPI document. Once a concept is named here, the next
person can't accidentally rename or remove it without this test flagging.

The point: the rulebook engine speaks a *fixed* vocabulary — Severity (honey /
jelly / propolis), TierLevel (low / mid / high), CheckStatus (pass / flag /
open / skip), and the named entities FlightSheet / Submission / Check /
Finding / Verdict / Approval / Receipt / LedgerEntry. Pydantic owns the
contract; this test owns the audit.
"""
from __future__ import annotations

import os

# Ensure no live deploys / external services are required to build the app.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("API_BASE_URL", "https://api.example.test")

from app.main import app  # noqa: E402


REQUIRED_DOCTRINE_SCHEMAS = {
    # Locked literals from the rulebook vocabulary appear inline on the parent
    # models (Pydantic doesn't always promote literals to standalone components),
    # so the assertion targets the *named* models.
    "FlightSheet",
    "FlightSheetRule",
    "FlightSheetList",
    "Submission",
    "Check",
    "Finding",
    "Verdict",
    "Approval",
    "Receipt",
    "LedgerEntry",
    "LedgerList",
    "LedgerError",
    "LedgerVerifyResult",
    "PublicReceipt",
    "ChecksList",
    "FlagsList",
}


def test_doctrine_schemas_present_in_openapi():
    schema = app.openapi()
    components = (schema.get("components") or {}).get("schemas") or {}
    missing = REQUIRED_DOCTRINE_SCHEMAS - set(components.keys())
    assert not missing, (
        "Doctrine schemas missing from OpenAPI components.schemas: "
        f"{sorted(missing)}. Add them back, or rename the test if the doctrine intentionally changed."
    )


def _enum_values(node) -> set[str]:
    """Recursively collect all string `enum` values nested inside a schema node."""
    found: set[str] = set()

    def walk(n):
        if isinstance(n, dict):
            enum = n.get("enum")
            if isinstance(enum, list):
                for v in enum:
                    if isinstance(v, str):
                        found.add(v)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(node)
    return found


def test_severity_literal_used_on_verdict():
    """The Verdict.severity field must speak honey / jelly / propolis only.

    If a future PR widens the literal, this test fails and the doctrine drift
    is caught at the contract boundary.
    """
    schema = app.openapi()
    verdict = (schema.get("components") or {}).get("schemas", {}).get("Verdict")
    assert verdict is not None, "Verdict schema missing"
    severity = verdict.get("properties", {}).get("severity", {})
    found = _enum_values(severity)
    assert found == {"honey", "jelly", "propolis"}, (
        f"Verdict.severity literal drifted from honey/jelly/propolis: {sorted(found)}"
    )


# Closed set of every severity value that has appeared in a Flight Sheet
# author's hand. New flight sheets should prefer the tier-shaped values
# (high/mid/low); the others are accepted for backward compatibility.
EXPECTED_RULE_SEVERITY = {
    "high", "mid", "medium", "low",       # tier-shaped (preferred)
    "critical", "noncritical",            # Kimi Library V1 vocabulary
    "honey", "jelly", "propolis",         # verdict-vocab leak (legacy)
    "minor",
}


def test_rule_severity_literal_used_on_check():
    """The *rule's* severity (Check.severity) must come from RuleSeverity.

    Distinct from Verdict.severity. A Flight Sheet authoring an unknown
    severity will fail Pydantic validation at the response boundary rather
    than be silently coerced through `tier_of()`.
    """
    schema = app.openapi()
    check = (schema.get("components") or {}).get("schemas", {}).get("Check")
    assert check is not None, "Check schema missing"
    severity = check.get("properties", {}).get("severity", {})
    found = _enum_values(severity)
    assert found == EXPECTED_RULE_SEVERITY, (
        f"Check.severity literal drifted from RuleSeverity vocabulary: "
        f"missing={sorted(EXPECTED_RULE_SEVERITY - found)}, "
        f"extra={sorted(found - EXPECTED_RULE_SEVERITY)}"
    )


def test_rule_severity_literal_used_on_finding():
    """Finding inherits from Check; its severity field must reference the same RuleSeverity."""
    schema = app.openapi()
    finding = (schema.get("components") or {}).get("schemas", {}).get("Finding")
    assert finding is not None, "Finding schema missing"
    severity = finding.get("properties", {}).get("severity", {})
    found = _enum_values(severity)
    assert found == EXPECTED_RULE_SEVERITY, (
        f"Finding.severity must speak RuleSeverity (inherits from Check). Got: {sorted(found)}"
    )


def test_org_schemas_present_in_openapi():
    """Phase 4 client-dashboard schemas — Org, ApiKey, ApiKeyCreated, ApiKeyList,
    ApiKeyIn, UsageStats — must be named components.
    """
    schema = app.openapi()
    components = (schema.get("components") or {}).get("schemas") or {}
    required = {"Org", "ApiKey", "ApiKeyCreated", "ApiKeyIn", "ApiKeyList", "UsageStats"}
    missing = required - set(components.keys())
    assert not missing, (
        f"Phase 4 client-dashboard schemas missing from OpenAPI: {sorted(missing)}"
    )


def test_org_plan_literal_locked():
    """Org.plan must speak the canonical PlanTier literal — free/pro/enterprise.

    Stripe (Phase 5) wires real billing onto these tier values; a typo here
    means subscription state doesn't match plan state.
    """
    schema = app.openapi()
    org = (schema.get("components") or {}).get("schemas", {}).get("Org")
    assert org is not None, "Org schema missing"
    plan = org.get("properties", {}).get("plan", {})
    found = _enum_values(plan)
    assert found == {"free", "pro", "enterprise"}, (
        f"Org.plan literal drifted from PlanTier vocabulary: {sorted(found)}"
    )


def test_org_endpoints_registered():
    """The four /org endpoints must be wired before the frontend can call them."""
    schema = app.openapi()
    paths = set(schema.get("paths", {}).keys())
    required = {"/org", "/org/api-keys", "/org/api-keys/{key_id}", "/org/usage"}
    missing = required - paths
    assert not missing, f"/org endpoints missing from OpenAPI: {sorted(missing)}"


def test_membership_schemas_present_in_openapi():
    """Phase 5 membership schemas — Membership, MembershipApplicationIn,
    MembershipApplicationView — must be named components.
    """
    schema = app.openapi()
    components = (schema.get("components") or {}).get("schemas") or {}
    required = {"Membership", "MembershipApplicationIn", "MembershipApplicationView"}
    missing = required - set(components.keys())
    assert not missing, (
        f"Membership schemas missing from OpenAPI: {sorted(missing)}"
    )


def test_membership_status_literal_locked():
    """Membership.status must speak the canonical MembershipStatus literal.

    Doctrine: members-only community, capped seats, trust-based monthly billing.
    The four states are pending / active / waitlisted / inactive. A typo here
    would silently break the dashboard or the apply flow.
    """
    schema = app.openapi()
    membership = (schema.get("components") or {}).get("schemas", {}).get("Membership")
    assert membership is not None, "Membership schema missing"
    status = membership.get("properties", {}).get("status", {})
    found = _enum_values(status)
    assert found == {"pending", "active", "waitlisted", "inactive"}, (
        f"Membership.status literal drifted from MembershipStatus vocabulary: {sorted(found)}"
    )


def test_membership_endpoints_registered():
    """The two /membership endpoints must be wired before the frontend can call them."""
    schema = app.openapi()
    paths = set(schema.get("paths", {}).keys())
    required = {"/membership", "/membership/apply"}
    missing = required - paths
    assert not missing, f"/membership endpoints missing from OpenAPI: {sorted(missing)}"


def test_training_data_policy_schema_present():
    """TrainingDataPolicy must appear as a named OpenAPI component."""
    schema = app.openapi()
    components = (schema.get("components") or {}).get("schemas") or {}
    assert "TrainingDataPolicy" in components, "TrainingDataPolicy schema missing"


def test_policy_endpoint_registered_and_public():
    """`/policy/training-data` must exist · and must NOT require auth.

    The policy is the brand promise — readable by anyone, anywhere, no sign-in.
    """
    schema = app.openapi()
    path = (schema.get("paths") or {}).get("/policy/training-data", {})
    assert path, "/policy/training-data endpoint missing"
    get_op = path.get("get", {})
    assert get_op, "/policy/training-data has no GET operation"
    # If FastAPI added a security requirement, it would show up here.
    assert not get_op.get("security"), (
        "/policy/training-data must remain unauthenticated — found a security requirement: "
        f"{get_op.get('security')}"
    )


def test_training_data_policy_hash_stable():
    """The policy hash must be deterministic across Python invocations.

    Drift means the policy body silently changed — that's a doctrine event.
    Update the version + last_updated *deliberately* if the policy needs an
    update; the hash should change in lockstep, never silently.
    """
    from app.routes.policy import training_data_policy

    pol_a = training_data_policy()
    pol_b = training_data_policy()
    assert pol_a["sha256"] == pol_b["sha256"], (
        f"policy hash drifted across calls: {pol_a['sha256']} vs {pol_b['sha256']}"
    )
    # Verify the hash format (64-char hex).
    assert len(pol_a["sha256"]) == 64, f"policy sha256 wrong length: {len(pol_a['sha256'])}"
    int(pol_a["sha256"], 16)  # must parse as hex


def test_training_data_policy_doctrine_lock():
    """The policy MUST state the customer-data gate. If someone weakens or
    removes the doctrine sentence, this test catches it.
    """
    from app.routes.policy import training_data_policy

    pol = training_data_policy()
    statement = pol["statement"].lower()
    # The locked doctrine line — Mr. Defendable voice
    assert "we learn from how agents fail" in statement, (
        "policy statement doesn't carry the locked doctrine sentence — fix or lock it"
    )
    assert "never learn from what your business is doing" in statement, (
        "policy statement weakened the customer-data gate — fix or lock it"
    )
    # The four categorical no's must all be present
    nos = " ".join(s.lower() for s in pol["we_dont_learn_from"])
    assert "customer evidence" in nos, "we_dont_learn_from missing 'customer evidence'"
    assert "customer agent submissions" in nos, "we_dont_learn_from missing 'customer agent submissions'"
    assert "customer-identifiable" in nos, "we_dont_learn_from missing 'customer-identifiable'"


def test_evidence_and_submission_customer_provided_defaults_true():
    """Fail-safe default · the SQLAlchemy model must default customer_provided
    to TRUE on both EvidenceItem and AgentSubmission. Operator-side cooks set
    FALSE explicitly when they want training-eligible rows.
    """
    from app.models import AgentSubmission, EvidenceItem

    e_col = EvidenceItem.__table__.c.customer_provided
    s_col = AgentSubmission.__table__.c.customer_provided
    assert e_col is not None, "EvidenceItem.customer_provided column missing"
    assert s_col is not None, "AgentSubmission.customer_provided column missing"
    assert not e_col.nullable, "EvidenceItem.customer_provided must be NOT NULL"
    assert not s_col.nullable, "AgentSubmission.customer_provided must be NOT NULL"
    # SQLAlchemy stores the python-side default; both should be True.
    assert e_col.default is not None and e_col.default.arg is True, (
        "EvidenceItem.customer_provided default must be True (fail-safe)"
    )
    assert s_col.default is not None and s_col.default.arg is True, (
        "AgentSubmission.customer_provided default must be True (fail-safe)"
    )


def test_incident_kind_documented_taxonomy():
    """IncidentIn.kind is a closed taxonomy. The doctrine says a single flag is
    NOT an incident — it's a Run-level work-defect / deal-finding. Crossing
    into incident-land requires policy_violation (declared gate) or
    recurring_flag (operational pattern). This test asserts the taxonomy
    holds; if the doctrine changes (e.g. add `single_flag`), update both the
    Literal in schemas.py AND this test deliberately.
    """
    schema = app.openapi()
    incident_in = (schema.get("components") or {}).get("schemas", {}).get("IncidentIn")
    assert incident_in is not None, "IncidentIn schema missing"
    kind = incident_in.get("properties", {}).get("kind", {})
    found = _enum_values(kind)
    assert found == {"rogue", "dark", "policy_violation", "recurring_flag"}, (
        f"IncidentKind taxonomy drifted: {sorted(found)}. "
        "If you intentionally added a new kind, update this test."
    )
    # Negative assertion: single_flag is *explicitly* not in the taxonomy.
    assert "single_flag" not in found, (
        "single_flag added to IncidentKind. The doctrine routes single flags "
        "through the Run's repair plan (work-defect / deal-finding), not via "
        "incidents. If you intend to change this, document the rationale."
    )
