#!/usr/bin/env python3
"""DefendableCloud dataset stager — runs on swarmrails (192.168.0.100).

Where the NAS lives. Polls the API for pending download grants, rsyncs the
matching dataset file from `/mnt/swarm/...` to the Tigris bucket, then tells
the API the file is staged so it can email the member.

  rails worker every 2 min (systemd timer):
    GET  /internal/staging-tasks      ← unique tigris_keys waiting on staging
    for each task:
        if not already in Tigris:     aws s3 cp /mnt/swarm/... s3://...
    POST /internal/stage-complete     ← API sweeps + Resend-notifies members

This script is stdlib-only (urllib + subprocess + aws CLI). No pip install on
rails. Same shape as cook-runner/runner.py — single file, easy to read on a
production box.

Env:
  STAGER_API_BASE        default https://api.defendablecloud.com
  INTERNAL_API_KEY       shared secret matching the API's INTERNAL_API_KEY  [required]
  TIGRIS_BUCKET          default defendable-cloud-v2
  TIGRIS_ENDPOINT_URL    default https://fly.storage.tigris.dev
  AWS_ACCESS_KEY_ID      Tigris access key id                                [required]
  AWS_SECRET_ACCESS_KEY  Tigris secret access key                            [required]
  STAGER_DRY_RUN         "1" → don't upload or call stage-complete

Exit codes:
  0   one pass succeeded (including "no pending tasks")
  1   misconfiguration (missing env)
  2   API unreachable
  3   one or more upload failures (other tasks may have succeeded)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


API = os.environ.get("STAGER_API_BASE", "https://api.defendablecloud.com").rstrip("/")
INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")
BUCKET = os.environ.get("TIGRIS_BUCKET", "defendable-cloud-v2")
ENDPOINT = os.environ.get("TIGRIS_ENDPOINT_URL", "https://fly.storage.tigris.dev")
DRY_RUN = os.environ.get("STAGER_DRY_RUN") == "1"


def _http(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Internal-Key": INTERNAL_KEY,
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode() or "{}")


def _aws(args: list[str]) -> tuple[int, str]:
    """Run `aws s3 ...` with the Tigris endpoint. Returns (rc, combined_output)."""
    cmd = ["aws", "s3", *args, "--endpoint-url", ENDPOINT]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "aws cli not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, "aws cli timed out after 600s"


def head_object(tigris_key: str) -> bool:
    """True if the object exists in the bucket."""
    rc, _ = _aws(["ls", f"s3://{BUCKET}/{tigris_key}"])
    return rc == 0


def upload(source_path: str, tigris_key: str) -> tuple[bool, str]:
    """rsync the file. Returns (ok, message)."""
    if not source_path:
        return False, "no source_path (slug not in catalog?)"
    if not os.path.exists(source_path):
        return False, f"source missing: {source_path}"
    if DRY_RUN:
        return True, f"DRY_RUN: would cp {source_path} → s3://{BUCKET}/{tigris_key}"
    rc, out = _aws(["cp", source_path, f"s3://{BUCKET}/{tigris_key}"])
    if rc != 0:
        return False, f"aws cp rc={rc}: {out[:240]}"
    return True, "uploaded"


def stage_complete(tigris_key: str, bytes_uploaded: int | None = None) -> dict:
    if DRY_RUN:
        return {"dry_run": True}
    return _http(
        "POST",
        "/internal/stage-complete",
        {"tigris_key": tigris_key, "bytes_uploaded": bytes_uploaded},
    )


def main() -> int:
    if not INTERNAL_KEY:
        print("ERR: set INTERNAL_API_KEY", file=sys.stderr)
        return 1

    try:
        listing = _http("GET", "/internal/staging-tasks")
    except urllib.error.HTTPError as e:
        print(f"ERR: staging-tasks {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"ERR: staging-tasks unreachable: {e}", file=sys.stderr)
        return 2

    tasks = listing.get("tasks") or []
    if not tasks:
        print("no pending staging tasks · idle")
        return 0

    failures = 0
    for t in tasks:
        key = t.get("tigris_key")
        slug = t.get("slug")
        src = t.get("source_path") or ""
        pending = t.get("pending_receipts") or 0
        if not key:
            continue

        if head_object(key):
            tag = "already-staged"
        else:
            ok, msg = upload(src, key)
            if not ok:
                print(f"[{slug}] FAILED · {msg}", file=sys.stderr)
                failures += 1
                continue
            tag = "uploaded"

        size = None
        if src and os.path.exists(src):
            try:
                size = os.path.getsize(src)
            except OSError:
                size = None

        try:
            res = stage_complete(key, size)
        except urllib.error.HTTPError as e:
            print(
                f"[{slug}] stage-complete {e.code}: {e.read().decode()[:200]}",
                file=sys.stderr,
            )
            failures += 1
            continue
        except Exception as e:  # noqa: BLE001
            print(f"[{slug}] stage-complete unreachable: {e}", file=sys.stderr)
            failures += 1
            continue

        if DRY_RUN:
            print(f"[{slug}] {tag} · pending={pending} · DRY_RUN")
        else:
            print(
                f"[{slug}] {tag} · pending={pending} · "
                f"matched={res.get('receipts_matched', 0)} "
                f"notified={res.get('notified', 0)} "
                f"already={res.get('already_notified', 0)}"
            )

    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
