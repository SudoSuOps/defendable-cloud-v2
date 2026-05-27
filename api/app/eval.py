"""The referee is a rulebook engine — not a judge model.

It applies the Flight Sheet (the declared rulebook) to the agent submission and
throws FLAGS when a rule is violated. Every rule either PASSES or raises a flag.
There is no opinion, no "seems good", no quality grade.

- auto rules     — code/math/schema/structure/citations/thresholds. The engine
                   decides pass | flag deterministically.
- checklist rules — a declared binary rule the human operator applies
                   ("assumption labeled? satisfied / raise flag"). Not a 1-100
                   opinion — a rule, applied by the human authority.

Severity is declared per rule and flag-driven:
  propolis = a critical flag · jelly = non-critical flag(s) only · honey = no flags.

Any future model assistance is advisory only — never the referee, never proof.
"""
from __future__ import annotations

import re


def build_assignment(fs: dict) -> str:
    outs = "\n".join(f"  {i + 1}. {o}" for i, o in enumerate(fs.get("expected_outputs", [])))
    return (
        f"ASSIGNMENT — {fs['name']}\n\n"
        f"{fs['assignment_instructions']}\n\n"
        f"Deliver these sections:\n{outs}\n\n"
        "Rules: use only the provided evidence unless explicitly allowed to assume; "
        "label every assumption; if a required input is missing, say so; do not "
        "fabricate facts or cite evidence that was not provided."
    )


def _present(label: str, text: str) -> bool:
    t = text.lower()
    lab = label.lower()
    if lab in t:
        return True
    words = [w for w in re.split(r"[^a-z]+", lab) if len(w) > 3]
    return bool(words) and all(w in t for w in words)


def _auto_rule(rule: dict, fs: dict, text: str, evidence: list[dict]) -> tuple[str, str]:
    """Return (status, detail) for an auto rule. status in {pass, flag}."""
    key = rule["key"]

    if key == "sections_present":
        expected = fs.get("expected_outputs", [])
        missing = [o for o in expected if not _present(o, text)]
        if not missing:
            return "pass", f"All {len(expected)} required sections present."
        return "flag", f"Missing required section(s): {', '.join(missing)}."

    if key == "output_nonempty":
        n = len(text.strip())
        return ("pass", f"{n} characters.") if n >= 200 else ("flag", f"Output too thin ({n} chars).")

    if key in ("numbers_present", "specs_present"):
        return ("pass", "Quantified figures present.") if re.search(r"\d", text) else ("flag", "No numbers where metrics were required.")

    if key == "citations_present":
        markers = ["source", "per the", "according to", "exhibit", "rent roll", "t12", "page", "[", "cited", "provided"]
        return ("pass", "Evidence references present.") if any(m in text.lower() for m in markers) else ("flag", "No evidence citations detected.")

    if key == "evidence_attached":
        return ("pass", f"{len(evidence)} evidence item(s) attached.") if evidence else ("flag", "No evidence attached to the run.")

    # Unknown auto rule — fail closed: raise a flag rather than fake a pass.
    return "flag", "Auto rule has no implementation; flagged for review."


def run_audit(fs: dict, submission_text: str, evidence: list[dict]) -> list[dict]:
    results: list[dict] = []
    for rule in fs.get("audit_checks", []):
        kind = rule.get("kind", "checklist")
        severity = rule.get("severity", "noncritical")
        base = {
            "check_key": rule["key"], "label": rule["label"], "category": rule["category"],
            "kind": kind, "severity": severity,
        }
        if kind == "auto":
            status, detail = _auto_rule(rule, fs, submission_text, evidence)
            results.append({**base, "source": "auto", "status": status, "detail": detail})
        else:
            results.append({
                **base, "source": "operator", "status": "open",
                "detail": "Operator must apply this rule: confirm satisfied or raise a flag.",
            })
    return results


# Phase 9 — three risk tiers. Not all penalties are equal: a missing citation is a
# 5-yarder, a CRE deal penciled at a 10-cap when it's a 5-cap (or a $5k check that
# should be $100) is a game-changer. The flight sheet pre-weights each rule; the
# math/approx referee can escalate by the size of the miss (the spot of the foul).
TIER_WEIGHT = {"high": 5, "mid": 2, "low": 1}
TIER_ORDER = ("high", "mid", "low")


def tier_of(severity) -> str:
    """Normalize a check's severity to a risk tier (legacy values mapped in)."""
    s = (severity or "").strip().lower()
    if s in ("high", "critical", "propolis"):
        return "high"
    if s in ("low", "honey", "minor"):
        return "low"
    return "mid"  # mid | medium | noncritical | jelly | unknown


def compute_verdict(fs: dict, checks: list) -> dict:
    """checks: ORM CheckResult objects (or dicts) with status + severity + label.

    Outcome is risk-tier-driven, not a quality grade:
      any HIGH flag  → propolis (a game-changer — do not release)
      MID flag(s)    → jelly    (usable with limitations / after repair)
      LOW flag(s) only → honey  (small hits — safe to release, noted)
      no flags       → honey
    Score is weighted by tier (high=5, mid=2, low=1) so a high-risk miss drops it hard.
    """
    def g(c, k):
        return c[k] if isinstance(c, dict) else getattr(c, k)

    applied = [c for c in checks if g(c, "status") in ("pass", "flag")]
    passed = [c for c in applied if g(c, "status") == "pass"]
    flags = [c for c in applied if g(c, "status") == "flag"]

    def w(c):
        return TIER_WEIGHT[tier_of(g(c, "severity"))]

    total_w = sum(w(c) for c in applied) or 1
    passed_w = sum(w(c) for c in passed)
    score_100 = round(100 * passed_w / total_w)

    by_tier = {t: [c for c in flags if tier_of(g(c, "severity")) == t] for t in TIER_ORDER}
    high, mid, low = by_tier["high"], by_tier["mid"], by_tier["low"]

    if high:
        severity, outcome, client_ready = "propolis", "fail", "No — high-risk flag"
    elif mid:
        severity, outcome, client_ready = "jelly", "risk", "With limitations / after repair"
    elif low:
        severity, outcome, client_ready = "honey", "pass", "Yes — minor notes only"
    else:
        severity, outcome, client_ready = "honey", "pass", "Yes"

    def names(cs):
        return "; ".join(g(c, "label") for c in cs)

    if high:
        recommended = "HIGH-RISK — resolve before release: " + names(high) + "."
    elif mid:
        recommended = "Clear flags: " + names(mid) + "."
    elif low:
        recommended = "Minor notes (safe to release): " + names(low) + "."
    else:
        recommended = "No flags raised. Approve and issue the receipt."

    summary = (
        f"{len(passed)}/{len(applied)} rules passed · "
        f"{len(high)} high-risk, {len(mid)} mid, {len(low)} low flag(s) · "
        f"{score_100}/100 weighted."
    )

    return {
        "outcome": outcome,
        "score": round(score_100 / 100, 4),
        "score_100": score_100,
        "severity": severity,
        "client_ready": client_ready,
        "recommended_action": recommended,
        "summary": summary,
        "checks_passed": len(passed),
        "checks_failed": len(flags),
        "risk_breakdown": {t: [g(c, "label") for c in by_tier[t]] for t in TIER_ORDER},
    }
