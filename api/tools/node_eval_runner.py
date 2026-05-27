#!/usr/bin/env python3
"""Node 001 eval-runner — repeatable, schema-enforced agentic-work evals.

Bakes format-schema enforcement into the eval lane: every submission is generated
under grammar-constrained decoding against the Flight Sheet's required shape, so
the referee measures the agent's CAPABILITY (math/policy), not its JSON brackets.

The model is reached over an OpenAI-compatible / Ollama-native endpoint, so the
SAME harness benchmarks any serving lane (Ollama now; vLLM / SGLang next) — only
--backend / --base changes. Submits to DefendableCloud and prints the verdict.

Usage (JWT in env):
  JWT=... python node_eval_runner.py --sheet cre_memo_dscr_ltv_v1 --model hermes3:8b \
       --tier small --backend ollama-ssh
  # add --no-constrain to reproduce the free-form 'before' (format-masking)
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, time
import httpx

API = os.environ.get("DC_API", "https://api.defendablecloud.com")
RIG_KEY = os.path.expanduser(os.environ.get("RIG_KEY", "~/.ssh/defendable_5090"))
RIG = os.environ.get("RIG", "swarm@192.168.0.99")

# Canonical structured-submission schema the executor checks. Used as the
# grammar constraint so the model cannot emit a shape the referee can't read.
SUBMISSION_SCHEMA = {
    "type": "object",
    "properties": {
        "assignment_id": {"type": "string"},
        "agent_summary": {"type": "string"},
        "inputs_used": {"type": "array", "items": {"type": "string"}},
        "missing_inputs": {"type": "array", "items": {"type": "string"}},
        "claims": {"type": "array", "items": {"type": "object", "properties": {
            "claim": {"type": "string"}, "evidence_reference": {"type": "string"}, "confidence": {"type": "string"}},
            "required": ["claim", "evidence_reference", "confidence"]}},
        "calculations": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "formula": {"type": "string"},
            "inputs": {"type": "object", "additionalProperties": {"type": "number"}},
            "result": {"type": "number"}, "units": {"type": "string"}},
            "required": ["name", "formula", "inputs", "result", "units"]}},
        "risks": {"type": "array", "items": {"type": "object"}},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "final_output": {"type": "string"},
        "self_check": {"type": "object", "additionalProperties": {"type": "boolean"}},
    },
    "required": ["assignment_id", "agent_summary", "inputs_used", "missing_inputs", "claims",
                 "calculations", "risks", "assumptions", "open_questions", "final_output", "self_check"],
}


def _extract_json(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).replace("```json", "").replace("```", "")
    i, j = text.find("{"), text.rfind("}")
    return text[i:j + 1] if i >= 0 and j > i else text


def generate(prompt: str, model: str, backend: str, base: str, constrain: bool) -> tuple[str, float]:
    """Return (raw_text, tok_per_s). Constrained decoding when constrain=True."""
    t0 = time.time()
    if backend == "ollama-ssh":
        payload = {"model": model, "prompt": prompt, "stream": False,
                   "options": {"temperature": 0.1, "num_predict": 1024}}
        if constrain:
            payload["format"] = SUBMISSION_SCHEMA
        out = subprocess.run(["ssh", "-i", RIG_KEY, RIG, "curl -s -m 240 http://localhost:11434/api/generate -d @-"],
                             input=json.dumps(payload).encode(), capture_output=True, timeout=280)
        d = json.loads(out.stdout.decode())
        ec, ed = d.get("eval_count", 0), d.get("eval_duration", 1) / 1e9
        return d["response"], (ec / ed if ed else 0.0)
    # openai-compatible (vLLM / SGLang / Ollama /v1) — used for the serving-lane benchmark
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 1024}
    if constrain:
        body["response_format"] = {"type": "json_schema",
                                   "json_schema": {"name": "submission", "schema": SUBMISSION_SCHEMA, "strict": True}}
    r = httpx.post(f"{base}/chat/completions", json=body, timeout=280,
                   headers={"Authorization": "Bearer sk-local"})
    j = r.json()
    txt = j["choices"][0]["message"]["content"]
    usage = j.get("usage", {})
    ct = usage.get("completion_tokens", 0)
    return txt, (ct / (time.time() - t0) if ct else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default="cre_memo_dscr_ltv_v1")
    ap.add_argument("--model", default="hermes3:8b")
    ap.add_argument("--tier", default="small")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--backend", default="ollama-ssh", choices=["ollama-ssh", "openai"])
    ap.add_argument("--base", default="http://localhost:11434/v1")
    ap.add_argument("--no-constrain", dest="constrain", action="store_false")
    args = ap.parse_args()

    c = httpx.Client(base_url=API, timeout=60, headers={"Authorization": f"Bearer {os.environ['JWT']}"})
    name = args.profile or f"{args.model.split(':')[0]} (5090)"
    prof = next((p for p in c.get("/agent-profiles").json()["agent_profiles"] if p["name"] == name), None)
    if not prof:
        prof = c.post("/agent-profiles", json={"name": name, "harness": args.backend, "model": args.model,
                      "model_provider": "ollama", "served_by": "ollama", "runtime_host": "mrd-defendable-eth",
                      "runtime_hardware": "RTX 5090 · 32GB", "capability_tier": args.tier, "context_window": 8192}).json()
    fs = next(f for f in c.get("/flight-sheets").json()["flight_sheets"] if f["slug"] == args.sheet)

    prompt = (
        "You are a CRE underwriting agent. DEAL: purchase price $2,000,000; loan $1,300,000; "
        "annual NOI $150,000; annual debt service $120,000. Produce the underwriting object with two "
        "calculations: Debt Service Coverage Ratio (noi/debt) and Loan to Value (loan/price). Compute the "
        "real results. assignment_id='cre_memo_dscr_ltv_v1', final_output='PASS'."
    )
    print(f"[runner] sheet={args.sheet} model={args.model} backend={args.backend} constrain={args.constrain}")
    raw, tps = generate(prompt, args.model, args.backend, args.base, args.constrain)
    body = _extract_json(raw)
    print(f"[runner] {tps:.1f} tok/s · output {len(body)} chars")

    pid = c.post("/projects", json={"name": "Node 001 · runner"}).json()["id"]
    rid = c.post("/runs", json={"project_id": pid, "flight_sheet_id": fs["id"], "agent_profile_id": prof["id"]}).json()["id"]
    c.post(f"/runs/{rid}/evidence", json={"kind": "file", "label": "deal", "content": "price 2.0M·loan 1.3M·NOI 150k·DS 120k"})
    c.post(f"/runs/{rid}/submission", json={"agent_name": name, "model_name": args.model, "provider": args.backend, "output_text": body})
    aud = c.post(f"/runs/{rid}/audit").json(); v = aud["verdict"]
    print(f"[runner] VERDICT {v['severity'].upper()} · {v['score_100']}/100 · {v['summary']}")
    for ch in aud["checks"]:
        if ch["status"] == "flag":
            print(f"         FLAG[{ch['severity']}] {ch['label']} — {ch['detail']}")


if __name__ == "__main__":
    main()
