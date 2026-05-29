#!/usr/bin/env python3
"""DefendableCloud dataset stager — runs on the private operator staging host.

Where the private dataset mount lives. Polls the API for pending download
grants, copies the matching dataset file into the Tigris bucket, then tells
the API the file is staged so it can email the member.

  rails worker every 2 min (systemd timer):
    GET  /internal/staging-tasks      ← unique tigris_keys waiting on staging
    for each task:
        if not already in Tigris:     boto3 upload_file from private dataset storage
    POST /internal/stage-complete     ← API sweeps + Resend-notifies members

Uses urllib (stdlib) for the API surface + boto3 for Tigris. Rails already
has boto3 — keeps us off `apt install awscli` on a production box and aligns
with the API side which uses boto3 too.

Env:
  STAGER_API_BASE        default https://api.defendablecloud.com
  INTERNAL_API_KEY       shared secret matching the API's INTERNAL_API_KEY  [required]
  STAGER_SOURCE_ROOT     private dataset mount root                         [required]
  TIGRIS_BUCKET          default defendable-cloud-v2
  TIGRIS_ENDPOINT_URL    default https://fly.storage.tigris.dev
  AWS_ACCESS_KEY_ID      Tigris access key id                                [required]
  AWS_SECRET_ACCESS_KEY  Tigris secret access key                            [required]
  AWS_REGION             default auto
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
import sys
import urllib.error
import urllib.request

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError


API = os.environ.get("STAGER_API_BASE", "https://api.defendablecloud.com").rstrip("/")
INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")
BUCKET = os.environ.get("TIGRIS_BUCKET", "defendable-cloud-v2")
ENDPOINT = os.environ.get("TIGRIS_ENDPOINT_URL", "https://fly.storage.tigris.dev")
REGION = os.environ.get("AWS_REGION", "auto")
DRY_RUN = os.environ.get("STAGER_DRY_RUN") == "1"
SOURCE_ROOT = os.environ.get("STAGER_SOURCE_ROOT", "")


_S3 = None


def s3():
    """Lazily build the Tigris boto3 client. signature_version=s3v4 is what
    Tigris expects; addressing_style=path matches our other code paths."""
    global _S3
    if _S3 is None:
        _S3 = boto3.client(
            "s3",
            endpoint_url=ENDPOINT,
            region_name=REGION,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
    return _S3


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


def head_object(tigris_key: str) -> bool:
    """True if the object exists in the bucket."""
    try:
        s3().head_object(Bucket=BUCKET, Key=tigris_key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        # Some other error (auth, network) — log + treat as "not staged" so
        # we re-attempt upload, which will then surface the real error.
        print(f"[head_object] {tigris_key}: {code or e}", file=sys.stderr)
        return False
    except BotoCoreError as e:
        print(f"[head_object] {tigris_key}: {e}", file=sys.stderr)
        return False


def resolve_source_path(source_path: str) -> str:
    if source_path and not os.path.isabs(source_path):
        return os.path.join(SOURCE_ROOT, source_path)
    return source_path


def upload(source_path: str, tigris_key: str) -> tuple[bool, str]:
    """rsync the file. Returns (ok, message)."""
    if not source_path:
        return False, "no source_path (slug not in catalog?)"
    source_path = resolve_source_path(source_path)
    if not os.path.exists(source_path):
        return False, f"source missing: {source_path}"
    if DRY_RUN:
        return True, f"DRY_RUN: would upload {source_path} → s3://{BUCKET}/{tigris_key}"
    try:
        s3().upload_file(Filename=source_path, Bucket=BUCKET, Key=tigris_key)
    except (ClientError, BotoCoreError) as e:
        return False, f"upload_file: {e}"
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
    if not SOURCE_ROOT:
        print("ERR: set STAGER_SOURCE_ROOT", file=sys.stderr)
        return 1
    if not (os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")):
        print("ERR: set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY", file=sys.stderr)
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
        resolved_src = resolve_source_path(src)
        if resolved_src and os.path.exists(resolved_src):
            try:
                size = os.path.getsize(resolved_src)
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
