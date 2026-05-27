#!/usr/bin/env python3
"""DefendableCloud cook runner — runs on the dedicated GPU rig.

Polls the cloud API for queued fine-tune cooks, tunes one of our base models on
the matched dataset, re-runs the eval, and posts the proven before->after lift
back (which mints a cook receipt).

Two modes (COOK_MODE):
  sim   — deterministic simulated lift. No GPU, no deps. Proves the whole
          pipeline end-to-end (request -> claim -> complete -> receipt) anywhere.
  real  — LoRA fine-tune via transformers/peft/trl, then re-eval. Runs on the
          rig. See real_cook() — wire your corpus + eval harness there.

Env:
  COOK_API_BASE   default https://api.defendablecloud.com
  RUNNER_TOKEN    shared secret (must match the API's RUNNER_TOKEN)   [required]
  COOK_MODE       sim | real            (default sim)
  RUNNER_NAME     label for receipts    (default rig)
  POLL_SECONDS    idle poll interval    (default 10)
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
import urllib.error

API = os.environ.get("COOK_API_BASE", "https://api.defendablecloud.com").rstrip("/")
TOKEN = os.environ.get("RUNNER_TOKEN", "")
MODE = os.environ.get("COOK_MODE", "sim")
RUNNER = os.environ.get("RUNNER_NAME", "rig")
POLL = float(os.environ.get("POLL_SECONDS", "10"))

TIER_FACTOR = {"royal_jelly": 0.62, "honey": 0.45, "jelly": 0.30}


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or "{}")


def sim_cook(cook: dict) -> dict:
    """Deterministic, plausible lift — no GPU. Same cook id => same result."""
    before = float(cook["eval_before"])
    pairs = int(cook.get("pairs") or 0)
    tier = (cook.get("dataset") or {}).get("tier", "honey")
    headroom = max(0.0, 1.0 - before)
    seed = int(hashlib.sha256(cook["id"].encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    factor = TIER_FACTOR.get(tier, 0.45) * min(1.0, pairs / 1000.0)
    frac = factor * (0.7 + 0.5 * seed)  # some run-to-run variance
    after = round(min(0.985, before + headroom * frac), 4)
    duration = round(45 + pairs * 0.35, 1)  # simulated wall time
    return {
        "eval_after": after,
        "adapter_ref": f"sim://lora/{cook['id'][:8]}",
        "metrics": {
            "mode": "sim",
            "duration_sec": duration,
            "pairs": pairs,
            "train_loss": round(0.9 - 0.4 * frac, 4),
            "note": "simulated cook — deterministic lift for pipeline verification",
        },
    }


def real_cook(cook: dict) -> dict:
    """LoRA fine-tune + re-eval on the rig.

    Wire this to your stack on the GPU box. The shape:
      1. Load base_model (cook['base_model']) — e.g. a Qwen/Llama checkpoint.
      2. Load the matched corpus for cook['dataset']['slug'] as instruction pairs.
      3. Train a LoRA adapter (peft + trl SFTTrainer) — ~1000 pairs, r=16-64.
      4. Re-run the SAME eval used to score eval_before, on the tuned model.
      5. Return {eval_after, adapter_ref, metrics{duration_sec, train_loss, ...}}.

    Kept as a guarded scaffold so the runner imports cleanly without torch.
    """
    import importlib.util

    for mod in ("torch", "transformers", "peft", "trl", "datasets"):
        if importlib.util.find_spec(mod) is None:
            raise RuntimeError(
                f"real mode needs '{mod}'. Install: pip install -r requirements.txt, "
                "and wire your corpus + eval harness in real_cook()."
            )
    raise NotImplementedError(
        "real_cook(): plug in corpus load + peft/trl SFT + re-eval for cook "
        f"{cook['id']} on {cook['base_model']} / dataset {cook.get('dataset', {}).get('slug')}."
    )


def process(cook: dict) -> None:
    cid = cook["id"]
    print(f"[cook {cid[:8]}] claimed · {cook['base_model']} · {cook.get('dataset', {}).get('slug')} · before={cook['eval_before']}")
    _post(f"/runner/cooks/{cid}/status", {"status": "running"})
    try:
        result = sim_cook(cook) if MODE == "sim" else real_cook(cook)
        out = _post(f"/runner/cooks/{cid}/complete", result)
        print(f"[cook {cid[:8]}] done · after={out.get('eval_after')} lift={out.get('lift')} receipt={out.get('share_token')}")
    except Exception as e:  # noqa: BLE001
        print(f"[cook {cid[:8]}] FAILED · {e}")
        try:
            _post(f"/runner/cooks/{cid}/fail", {"error": str(e)})
        except Exception:
            pass


def main() -> None:
    if not TOKEN:
        raise SystemExit("set RUNNER_TOKEN")
    print(f"DefendableCloud cook runner · {API} · mode={MODE} · runner={RUNNER}")
    while True:
        try:
            r = _post("/runner/cooks/next", {"runner": RUNNER})
            cook = r.get("cook")
            if cook:
                process(cook)
                continue
        except urllib.error.HTTPError as e:
            print(f"http {e.code}: {e.read().decode()[:200]}")
        except Exception as e:  # noqa: BLE001
            print(f"poll error: {e}")
        time.sleep(POLL)


if __name__ == "__main__":
    main()
