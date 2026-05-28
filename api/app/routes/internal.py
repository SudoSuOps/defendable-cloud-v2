"""/internal — operator-side endpoints, fail-closed.

This surface is for the rails-side dataset stager only. It's gated by a
shared `INTERNAL_API_KEY` header (`X-Internal-Key`), and returns 503 if the
key isn't configured. Customers never see this surface.

Flow (Sprint 9):

  rails worker every 2 min:
    GET  /internal/staging-tasks      ← list of pending tigris_keys + source paths
       (for each, rails checks Tigris; if absent, aws s3 cp from /mnt/swarm;
        if present, treat as already-uploaded and proceed)
    POST /internal/stage-complete     ← sweep receipts → Resend notify members

Idempotency: every member email is recorded in `download_notifications`
(receipt_id PK). Re-running stage-complete is a no-op for already-notified
receipts. Receipts themselves are NEVER mutated.

Why a separate route file: the auth dependency, the rate of churn (this code
will change as we tune the stager), and the operator-only nature all argue
for a clean seam from the customer surface.
"""
from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app import email
from app.catalog import raw_package_by_slug
from app.config import settings
from app.db import session_scope
from app.deps import require_internal
from app.models import ApiKey, DownloadNotification, Organization, Receipt, User
from app.storage import head_object

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal)])


DATASET_DOWNLOAD_SCHEMA = "defendablecloud.dataset-download-receipt/v1"


# ─── schemas ────────────────────────────────────────────────────────────────


class StagingTask(BaseModel):
    """One file the rails worker should ensure is in Tigris."""

    tigris_key: str = Field(description="Destination key in the Tigris bucket.")
    slug: str = Field(description="Package slug — used by rails for logging.")
    source_path: str = Field(
        description="NAS path the rails worker rsyncs from (e.g. /mnt/swarm/...)."
    )
    pending_receipts: int = Field(
        description="How many ready-at-grant=false receipts point at this key."
    )


class StagingTaskList(BaseModel):
    tasks: List[StagingTask]
    count: int


class StageCompleteRequest(BaseModel):
    tigris_key: str
    bytes_uploaded: int | None = None


class StageCompleteResult(BaseModel):
    tigris_key: str
    receipts_matched: int
    notified: int
    already_notified: int
    no_email_available: int


# ─── helpers ────────────────────────────────────────────────────────────────


def _slug_from_key(tigris_key: str) -> str | None:
    """`datasets/{slug}/{basename}` → `{slug}`. Returns None for malformed keys."""
    parts = tigris_key.split("/", 2)
    if len(parts) >= 2 and parts[0] == "datasets":
        return parts[1]
    return None


async def _resolve_email_for_grant(db, granted_to: str) -> str | None:
    """Resolve the recipient email from a `granted_to_user_id` payload value.

    The download endpoint stores `current.id` which is either a raw user id
    (JWT sign-in) or `apikey:<id>` (API-key principal). We walk back to the
    underlying user either way. Returns None if we can't find one.
    """
    if not granted_to:
        return None
    if granted_to.startswith("apikey:"):
        api_key_id = granted_to[len("apikey:") :]
        ak = await db.get(ApiKey, api_key_id)
        if ak is None or ak.created_by is None:
            return None
        u = await db.get(User, ak.created_by)
        return u.email if u else None
    u = await db.get(User, granted_to)
    return u.email if u else None


# ─── endpoints ──────────────────────────────────────────────────────────────


@router.get("/staging-tasks", response_model=StagingTaskList)
async def staging_tasks():
    """Return the unique pending `tigris_key` set across all members.

    A key is "pending" if at least one receipt with that key was minted with
    `ready_at_grant=false`. The rails worker is the only consumer; it
    deduplicates across members so we only rsync each file once.
    """
    async with session_scope() as db:
        # All download receipts that were minted before the file landed in
        # Tigris. We use the JSONB ->> operator (text extract) so the same
        # query plan works on both `false` (JSON bool) and `"false"` payloads
        # (the build helper emits booleans, but defense-in-depth).
        result = await db.execute(
            select(Receipt).where(
                Receipt.payload["schema"].astext == DATASET_DOWNLOAD_SCHEMA,
                Receipt.payload["ready_at_grant"].astext == "false",
            )
        )
        receipts = list(result.scalars())

    by_key: dict[str, int] = {}
    for r in receipts:
        key = r.payload.get("tigris_key")
        if not key:
            continue
        by_key[key] = by_key.get(key, 0) + 1

    tasks: list[StagingTask] = []
    for key, count in sorted(by_key.items()):
        slug = _slug_from_key(key)
        if slug is None:
            continue
        raw = raw_package_by_slug(slug)
        if raw is None:
            # Receipt points at a slug that no longer exists in the catalog.
            # Surface it anyway with empty source_path so the operator sees it
            # in the rails log and can decide.
            tasks.append(
                StagingTask(
                    tigris_key=key, slug=slug, source_path="", pending_receipts=count
                )
            )
            continue
        tasks.append(
            StagingTask(
                tigris_key=key,
                slug=slug,
                source_path=raw.get("path", "") or "",
                pending_receipts=count,
            )
        )

    return {"tasks": tasks, "count": len(tasks)}


@router.post("/stage-complete", response_model=StageCompleteResult)
async def stage_complete(body: StageCompleteRequest):
    """Confirm a file is staged in Tigris and notify every pending member.

    Idempotent. Calling twice for the same key:
      first call  → emails sent · download_notifications rows inserted
      second call → already_notified == receipts_matched · notified == 0
    """
    if not head_object(body.tigris_key):
        # The rails worker should not have called us; refuse so we don't
        # produce a "ready" email for a not-yet-staged object.
        raise HTTPException(
            status_code=425,
            detail=f"object not present in Tigris: {body.tigris_key}",
        )

    notified = 0
    already_notified = 0
    no_email = 0
    matched = 0

    api_base = settings().api_base_url.rstrip("/")

    async with session_scope() as db:
        rows = await db.execute(
            select(Receipt).where(
                Receipt.payload["schema"].astext == DATASET_DOWNLOAD_SCHEMA,
                Receipt.payload["tigris_key"].astext == body.tigris_key,
                Receipt.payload["ready_at_grant"].astext == "false",
            )
        )
        receipts = list(rows.scalars())
        matched = len(receipts)

        for r in receipts:
            # Idempotency check.
            existing = await db.get(DownloadNotification, r.id)
            if existing is not None:
                already_notified += 1
                continue

            payload = r.payload or {}
            pkg = payload.get("package") or {}
            granted_to = payload.get("granted_to_user_id") or ""
            recipient = await _resolve_email_for_grant(db, granted_to)
            if recipient is None:
                no_email += 1
                continue

            share_url = f"{api_base}/share/{r.share_token}"
            download_url = f"{share_url}/download"

            ok = await email.send_dataset_ready(
                to_email=recipient,
                package_name=pkg.get("name") or pkg.get("slug") or "your dataset",
                package_slug=pkg.get("slug") or "—",
                pairs=int(pkg.get("pairs") or 0),
                share_url=share_url,
                download_url=download_url,
                expires_at=payload.get("expires_at") or "—",
            )

            # We insert the notification row whether or not Resend accepted.
            # The receipt is books-and-records · we don't want to spam if
            # Resend was just temporarily down. Operator can re-trigger by
            # deleting the row if a re-send is intentional.
            db.add(
                DownloadNotification(
                    receipt_id=r.id,
                    notified_email=recipient,
                    tigris_key=body.tigris_key,
                )
            )
            if ok:
                notified += 1
            else:
                # Email send failed but row inserted to avoid retry loop.
                # Surface in the count of attempts that didn't actually email.
                no_email += 1

    return {
        "tigris_key": body.tigris_key,
        "receipts_matched": matched,
        "notified": notified,
        "already_notified": already_notified,
        "no_email_available": no_email,
    }
