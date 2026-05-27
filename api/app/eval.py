"""Flight-sheet-driven audit + referee verdict.

Auto checks run deterministically on the agent's pasted output (structure,
schema, format, declared numbers). Judgment checks (evidence-use, math validity,
hallucination, client-readiness) are created as `review` for the operator to
grade — the referee is automated logic + a human, with a judge-model slot for
later. No model calls in v1.
"""
from __future__ import annotations

import re


def build_assignment(fs: dict) -> str:
    """Generate the assignment prompt the operator sends to the agent."""
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


def _auto_check(key: str, label: str, category: str, fs: dict, text: str, evidence: list[dict]) -> dict:
    out = {"check_key": key, "label": label, "category": category, "source": "auto"}

    if key == "sections_present":
        expected = fs.get("expected_outputs", [])
        missing = [o for o in expected if not _present(o, text)]
        present = len(expected) - len(missing)
        if not missing:
            return {**out, "status": "pass", "severity": "honey", "detail": f"All {len(expected)} sections present."}
        ratio = present / max(len(expected), 1)
        status = "risk" if ratio >= 0.5 else "fail"
        return {**out, "status": status, "severity": "jelly" if status == "risk" else "propolis",
                "detail": f"Missing: {', '.join(missing)}."}

    if key == "output_nonempty":
        n = len(text.strip())
        ok = n >= 200
        return {**out, "status": "pass" if ok else "fail", "severity": "honey" if ok else "propolis",
                "detail": f"{n} characters." + ("" if ok else " Output looks too thin.")}

    if key in ("numbers_present", "specs_present"):
        has = bool(re.search(r"\d", text))
        return {**out, "status": "pass" if has else "risk", "severity": "honey" if has else "jelly",
                "detail": "Quantified figures found." if has else "No numbers found where metrics were expected."}

    if key == "citations_present":
        markers = ["source", "per the", "according to", "exhibit", "rent roll", "t12", "page", "[", "cited", "provided"]
        has = any(m in text.lower() for m in markers)
        return {**out, "status": "pass" if has else "risk", "severity": "honey" if has else "jelly",
                "detail": "Evidence references found." if has else "No evidence citations detected."}

    # Unknown auto check — don't fabricate a pass.
    return {**out, "status": "review", "severity": None, "detail": "Needs review."}


def run_audit(fs: dict, submission_text: str, evidence: list[dict]) -> list[dict]:
    results: list[dict] = []
    for chk in fs.get("audit_checks", []):
        key, label, category, kind = chk["key"], chk["label"], chk["category"], chk.get("kind", "judgment")
        if kind == "auto":
            results.append(_auto_check(key, label, category, fs, submission_text, evidence))
        else:
            results.append({
                "check_key": key, "label": label, "category": category, "source": "operator",
                "status": "review", "severity": None,
                "detail": "Operator judgment required — grade this finding.",
            })
    return results


def compute_verdict(fs: dict, checks: list[dict]) -> dict:
    """checks: dicts/objects with .status (pass|fail|risk|skip|review)."""
    def st(c):
        return c["status"] if isinstance(c, dict) else c.status

    def lbl(c):
        return c["label"] if isinstance(c, dict) else c.label

    graded = [c for c in checks if st(c) in ("pass", "fail", "risk")]
    passed = sum(1 for c in graded if st(c) == "pass")
    failed = sum(1 for c in graded if st(c) == "fail")
    risky = sum(1 for c in graded if st(c) == "risk")
    total = max(len(graded), 1)
    score_100 = round(100 * (passed + 0.5 * risky) / total)

    pass_t = int(fs.get("pass_threshold", 80))
    fail_t = int(fs.get("fail_threshold", 60))

    if score_100 >= pass_t and failed == 0:
        outcome, severity, client_ready = "pass", "honey", "yes"
    elif score_100 < fail_t:
        outcome, severity, client_ready = "fail", "propolis", "no"
    else:
        outcome, severity, client_ready = "risk", "jelly", "after minor edits"

    problems = [lbl(c) for c in graded if st(c) in ("fail", "risk")]
    recommended = (
        "Correct or review: " + "; ".join(problems) + "." if problems
        else "Clean across all checks. Approve and issue the receipt."
    )
    summary = f"{passed} passed, {risky} flagged, {failed} failed of {total} graded checks. Score {score_100}/100."

    return {
        "outcome": outcome,
        "score": round(score_100 / 100, 4),
        "score_100": score_100,
        "severity": severity,
        "client_ready": client_ready,
        "recommended_action": recommended,
        "summary": summary,
        "checks_passed": passed,
        "checks_failed": failed,
    }
