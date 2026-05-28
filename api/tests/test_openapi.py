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
