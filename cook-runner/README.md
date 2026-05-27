# cook-runner

The agent that runs on the **dedicated GPU rig** and executes DefendableCloud
fine-tune cooks. It polls the cloud API for queued cooks, tunes one of our base
models on the matched dataset, re-runs the eval, and posts the proven
**before → after lift** back (which mints a cook receipt).

```
client eval (fail/risk) → request cook → [this runner on the rig] → re-eval → lift receipt
```

## Modes

- **`sim`** — deterministic simulated lift. No GPU, no dependencies (stdlib only).
  Use it to prove the whole pipeline end-to-end before wiring real training.
- **`real`** — LoRA fine-tune (transformers + peft + trl) then re-eval. Runs on
  the rig. Wire your corpus + eval harness into `real_cook()`.

## Run it

```bash
# sim — anywhere, no deps
RUNNER_TOKEN=<shared-secret> COOK_API_BASE=https://api.defendablecloud.com \
  COOK_MODE=sim RUNNER_NAME=rig-whale python3 runner.py

# real — on the rig
pip install -r requirements.txt
RUNNER_TOKEN=<shared-secret> COOK_MODE=real RUNNER_NAME=rig-whale python3 runner.py
```

`RUNNER_TOKEN` must match the API's `RUNNER_TOKEN` secret. Set it on the API with:

```
fly secrets set RUNNER_TOKEN=$(openssl rand -hex 24) -a defendable-cloud-api
```

## Wiring real training

`real_cook(cook)` receives `base_model`, `eval_before`, `pairs`, and the matched
`dataset` (slug/domain). Implement:

1. Load `base_model` (a Qwen/Llama checkpoint we own).
2. Load the corpus for `dataset.slug` as instruction pairs (~1,000).
3. LoRA SFT (peft + trl `SFTTrainer`, r=16–64).
4. Re-run **the same eval** that produced `eval_before` on the tuned model.
5. Return `{eval_after, adapter_ref, metrics: {duration_sec, train_loss, ...}}`.

Keep the canary-then-cook discipline: a cook that lowers the eval is a lobotomy —
the receipt will show it, and we don't ship (or charge for) a negative lift.
