"""Phase 6 — the structured-submission executor.

The agent returns JSON conforming to the flight sheet's required_output_schema.
The executor RUNS the checkable rules against that JSON — deterministically, no
opinion, no operator grading on the machine-checkable rules:

  - required fields present
  - field type / value-in-set / required-keys on array items / expected value
  - evidence: declared evidence fields are non-empty on every item
  - MATH: re-derive each calculation's result from its own inputs + formula and
    compare within tolerance (the real math referee)

Rules whose condition is free-text English (not a structured primitive) are
marked `skip` (not machine-evaluable in v1) — honest, not faked. They stay in
eval_spec for a future condition DSL.
"""
from __future__ import annotations

import ast
import json
import re
from typing import Any

from app.eval import compute_verdict

_MISSING = object()

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd,
)


def _num(v: Any):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _get(obj: Any, path: str):
    cur = obj
    for part in path.split("."):
        part = part.strip()
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return _MISSING
    return cur


def _resolve(obj: Any, match_field: str):
    mf = (match_field or "").strip()
    m = re.fullmatch(r"len\((.+)\)", mf)
    if m:
        v = _get(obj, m.group(1).strip())
        return len(v) if isinstance(v, (list, str, dict)) else _MISSING
    return _get(obj, mf)


def safe_eval(expr: str, names: dict) -> float:
    """Evaluate a pure-arithmetic formula over `names`. Raises on anything else."""
    expr = expr.replace("^", "**")
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"disallowed: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in names:
            raise ValueError(f"unknown name: {node.id}")
    return float(eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, names))


_MISS_EXPR = object()


def _calc(sub: dict, name: str):
    for c in sub.get("calculations") or []:
        if isinstance(c, dict) and c.get("name") == name:
            return _num(c.get("result"))
    return _MISS_EXPR


def _operand(node: Any, sub: dict):
    """Resolve an operand: literal | {field} | {calc} | {len}."""
    if isinstance(node, dict):
        if "field" in node:
            v = _resolve(sub, node["field"])
            return _MISS_EXPR if v is _MISSING else v
        if "calc" in node:
            return _calc(sub, node["calc"])
        if "len" in node:
            v = _resolve(sub, node["len"])
            return len(v) if isinstance(v, (list, str, dict)) else _MISS_EXPR
    return node  # literal


_CMP = {
    "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
    ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b, "<": lambda a, b: a < b,
}


def eval_expr(expr: Any, sub: dict):
    """Evaluate a structured rule expression → True | False | None (unknown→skip)."""
    if not isinstance(expr, dict) or "op" not in expr:
        return None
    op = expr["op"]
    if op in _CMP:
        a, b = _operand(expr.get("left"), sub), _operand(expr.get("right"), sub)
        if a is _MISS_EXPR or b is _MISS_EXPR:
            return None
        try:
            return bool(_CMP[op](a, b))
        except TypeError:
            return None
    if op == "in":
        a = _operand(expr.get("left"), sub)
        return None if a is _MISS_EXPR else (a in (expr.get("right") or []))
    if op == "all_nonempty":
        arr = _resolve(sub, expr.get("array", ""))
        field = expr.get("field")
        if not isinstance(arr, list) or not field:
            return None
        return all(isinstance(it, dict) and str(it.get(field, "")).strip() for it in arr)
    if op in ("and", "or"):
        vals = [eval_expr(t, sub) for t in (expr.get("terms") or [])]
        if any(v is None for v in vals):
            return None
        return all(vals) if op == "and" else any(vals)
    if op == "not":
        v = eval_expr(expr.get("term"), sub)
        return None if v is None else (not v)
    if op == "if":
        cond = eval_expr(expr.get("cond"), sub)
        if cond is None:
            return None
        return True if not cond else eval_expr(expr.get("then"), sub)
    return None


def _r(key, label, category, status, severity, detail):
    return {"check_key": key, "label": label, "category": category, "kind": "auto",
            "source": "auto", "status": status, "severity": severity, "detail": detail}


def run_structured_audit(eval_spec: dict, submission_text: str) -> tuple[list[dict], dict | None]:
    # 0 · valid JSON
    try:
        sub = json.loads(submission_text)
        if not isinstance(sub, dict):
            raise ValueError("not an object")
    except Exception as e:  # noqa: BLE001
        results = [_r("json_valid", "Submission is valid JSON", "schema", "flag", "critical", f"Not valid JSON: {e}")]
        return results, compute_verdict({}, results)

    results: list[dict] = [_r("json_valid", "Submission is valid JSON", "schema", "pass", "critical", "Parsed.")]

    # 1 · required fields present
    required = (eval_spec.get("required_output_schema") or {}).get("required") or []
    missing = [k for k in required if _get(sub, k) is _MISSING]
    results.append(_r(
        "required_fields_present", "Required fields present", "schema",
        "pass" if not missing else "flag", "critical",
        "All required fields present." if not missing else f"Missing: {', '.join(missing)}.",
    ))

    # 2 · structured deterministic checks
    for i, dc in enumerate(eval_spec.get("deterministic_checks") or []):
        if not isinstance(dc, dict):
            continue
        label = str(dc.get("check") or f"check {i+1}")[:300]
        mf = dc.get("match_field")
        key = f"det_{i+1}"
        if mf is None:
            results.append(_r(key, label, "structure", "skip", "noncritical", "No match_field; not machine-evaluable in v1."))
            continue
        val = _resolve(sub, mf)
        if "expected_values" in dc:
            ok = val in dc["expected_values"]
            results.append(_r(key, label, "structure", "pass" if ok else "flag", "critical",
                              f"{mf} = {val!r}" + ("" if ok else f"; not in {dc['expected_values']}")))
        elif "type" in dc:
            tymap = {"array": list, "object": dict, "number": (int, float), "string": str, "boolean": bool}
            ty = tymap.get(dc["type"])
            ok = ty is not None and val is not _MISSING and isinstance(val, ty) and not (dc["type"] == "number" and isinstance(val, bool))
            results.append(_r(key, label, "schema", "pass" if ok else "flag", "critical",
                              f"{mf} is {type(val).__name__}" if val is not _MISSING else f"{mf} missing"))
        elif "required_keys" in dc:
            arr = val if isinstance(val, list) else None
            if arr is None:
                results.append(_r(key, label, "schema", "flag", "critical", f"{mf} is not an array."))
            else:
                bad = [j for j, it in enumerate(arr) if not (isinstance(it, dict) and all(k in it for k in dc["required_keys"]))]
                results.append(_r(key, label, "schema", "pass" if not bad else "flag", "critical",
                                  "All items have required keys." if not bad else f"Items missing keys at index {bad[:5]}."))
        elif "expected_value" in dc:
            ok = val == dc["expected_value"]
            results.append(_r(key, label, "structure", "pass" if ok else "flag", "critical",
                              f"{mf} = {val!r}" + ("" if ok else f"; expected {dc['expected_value']!r}")))
        else:
            results.append(_r(key, label, "structure", "skip", "noncritical", "Condition is free-text; not machine-evaluable in v1."))

    # 3 · evidence non-empty pattern (claims/action_items reference fields)
    for i, ec in enumerate(eval_spec.get("evidence_checks") or []):
        if not isinstance(ec, dict):
            continue
        cond = (str(ec.get("condition", "")) + " " + str(ec.get("check", ""))).lower()
        mf = ec.get("match_field")
        field = next((f for f in ("evidence_reference", "source_location", "source") if f in cond), None)
        label = str(ec.get("check") or f"evidence {i+1}")[:300]
        key = f"ev_{i+1}"
        if not field or not mf:
            results.append(_r(key, label, "evidence", "skip", "noncritical", "Not a machine-evaluable evidence pattern in v1."))
            continue
        arr = _resolve(sub, mf)
        if not isinstance(arr, list):
            results.append(_r(key, label, "evidence", "skip", "noncritical", f"{mf} not an array."))
            continue
        bad = [j for j, it in enumerate(arr) if not (isinstance(it, dict) and str(it.get(field, "")).strip())]
        results.append(_r(key, label, "evidence", "pass" if not bad else "flag", "critical",
                          f"All items carry {field}." if not bad else f"{len(bad)} item(s) missing {field}."))

    # 4 · MATH — re-derive each calculation from its own inputs + formula
    calcs = sub.get("calculations")
    if isinstance(calcs, list):
        for c in calcs:
            if not isinstance(c, dict):
                continue
            name = str(c.get("name") or "calc")
            formula = c.get("formula")
            inputs = c.get("inputs")
            result = _num(c.get("result"))
            if not (isinstance(formula, str) and isinstance(inputs, dict) and result is not None):
                continue
            names = {k: _num(v) for k, v in inputs.items()}
            if any(v is None for v in names.values()):
                results.append(_r(f"math_{name}", f"Math: {name}", "math", "skip", "noncritical", "Non-numeric inputs; skipped."))
                continue
            try:
                got = safe_eval(formula, names)
            except Exception:
                results.append(_r(f"math_{name}", f"Math: {name}", "math", "skip", "noncritical", "Formula not pure-arithmetic; not verifiable in v1."))
                continue
            tol = max(1e-6, abs(result) * 0.01)
            ok = abs(got - result) <= tol
            results.append(_r(f"math_{name}", f"Math: {name}", "math", "pass" if ok else "flag", "critical",
                              f"{name}: stated {result}, recomputed {round(got, 6)}" + ("" if ok else " — MISMATCH")))

    # 5 · structured rule DSL — machine-precise yes/no expressions (thresholds,
    # cross-field, conditionals). No English parsing: the rulebook declares the
    # expression, the executor evaluates it. Unknown operand → skip (honest).
    for i, rule in enumerate(eval_spec.get("rules") or []):
        if not isinstance(rule, dict):
            continue
        key = str(rule.get("id") or f"rule_{i+1}")
        label = str(rule.get("label") or key)[:300]
        sev = "critical" if str(rule.get("severity", "")).lower() in ("critical", "high", "propolis") else "noncritical"
        cat = rule.get("category", "policy")
        res = eval_expr(rule.get("expr"), sub)
        if res is None:
            results.append(_r(key, label, cat, "skip", sev, "Operand missing in submission; not evaluable."))
        else:
            results.append(_r(key, label, cat, "pass" if res else "flag", sev,
                              "Rule satisfied." if res else "Rule violated."))

    return results, compute_verdict({}, results)
