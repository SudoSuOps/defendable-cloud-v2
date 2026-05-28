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


def test_severity_literal_used_on_verdict():
    """The Verdict.severity field must speak honey / jelly / propolis only.

    If a future PR widens the literal, this test fails and the doctrine drift
    is caught at the contract boundary.
    """
    schema = app.openapi()
    verdict = (schema.get("components") or {}).get("schemas", {}).get("Verdict")
    assert verdict is not None, "Verdict schema missing"
    severity = verdict.get("properties", {}).get("severity", {})
    # The field is Optional[Severity], so Pydantic emits anyOf with the enum + null.
    found_values: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            enum = node.get("enum")
            if isinstance(enum, list):
                for v in enum:
                    if isinstance(v, str):
                        found_values.add(v)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(severity)
    assert found_values == {"honey", "jelly", "propolis"}, (
        f"Verdict.severity literal drifted from honey/jelly/propolis: {sorted(found_values)}"
    )
