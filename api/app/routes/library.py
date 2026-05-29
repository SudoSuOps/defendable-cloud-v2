"""/datasets/catalog — the members-only dataset library surface.

99 packages across 12 verticals · 3.35M training pairs · hash-anchored. Free
with membership; we surface package identity + pair counts + deed status,
never the internal NAS path or our internal $ valuation.

Members can fetch the catalog and recompute `packages_sha256` from the canonical
sorted packages list to confirm the API mirror matches the books-and-records
source on the NAS.

The download endpoint (`POST /datasets/catalog/{slug}/download`) mints a
download receipt on the per-org hash chain and returns a download URL that
indirects through `GET /share/{token}/download` (in routes/public.py) — that
indirection rotates the underlying Tigris signed URL on each access without
re-minting the receipt.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select, func

from app import receipts as receipt_builder
from app.catalog import catalog_view, package_by_slug, raw_package_by_slug
from app.config import settings
from app.db import session_scope
from app.deps import Principal, require_member
from app.ledger import mint_receipt
from app.models import Organization, Receipt
from app.schemas import (
    DatasetCatalog,
    DatasetDownloadGrant,
    DatasetDownloadRequest,
    DatasetPackage,
)
from app.storage import get_object_partial, head_object, head_object_meta

router = APIRouter(prefix="/datasets/catalog", tags=["datasets"])

DATASET_DOWNLOAD_SCHEMA = "defendablecloud.dataset-download-receipt/v1"


def _tigris_key_for(slug: str, source_path: str) -> str:
    """Derive the Tigris staging key from the catalog source basename.

    Older private snapshots used a full source path; public snapshots should
    only carry a basename. Namespacing by slug avoids collisions.
    """
    basename = os.path.basename(source_path) or f"{slug}.jsonl"
    return f"datasets/{slug}/{basename}"


async def _enforce_download_quota(db, *, current: Principal, limit: int) -> None:
    if limit < 1:
        raise HTTPException(status_code=503, detail="dataset download quota is not configured")
    window_start = datetime.now(timezone.utc) - timedelta(hours=24)
    identity_filters = [Receipt.payload["granted_to_user_id"].astext == current.id]
    if current.email:
        identity_filters.append(Receipt.payload["granted_to_email"].astext == current.email)
    used = (
        await db.execute(
            select(func.count(Receipt.id)).where(
                Receipt.org_id == current.org_id,
                Receipt.created_at >= window_start,
                Receipt.payload["schema"].astext == DATASET_DOWNLOAD_SCHEMA,
                or_(*identity_filters),
            )
        )
    ).scalar_one()
    if int(used) >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"dataset download limit reached ({limit} grants per rolling 24 hours). "
                "Contact build@defendableos.com for higher-volume access."
            ),
            headers={"Retry-After": "86400"},
        )


@router.get("", response_model=DatasetCatalog)
async def get_catalog(_: Principal = Depends(require_member)):
    """The full members-only catalog — scorecard, vertical roll-up, all packages.

    Carries the source `catalog_sha256` and our `packages_sha256` so members
    can recompute and confirm the mirror matches the NAS books-and-records.
    """
    return catalog_view()


@router.get("/{slug}", response_model=DatasetPackage)
async def get_package(slug: str, _: Principal = Depends(require_member)):
    """Single package by slug — identity + pair count + deed status."""
    pkg = package_by_slug(slug)
    if pkg is None:
        raise HTTPException(status_code=404, detail=f"package not found: {slug}")
    return pkg


@router.post("/{slug}/download", response_model=DatasetDownloadGrant, status_code=201)
async def request_download(
    slug: str,
    body: DatasetDownloadRequest | None = None,
    current: Principal = Depends(require_member),
):
    """Mint a download receipt and return a fresh download URL for a package.

    The receipt rides the per-org hash chain alongside eval/cook/incident
    receipts (same `Receipt` model, distinct `schema` field). If the file is
    not yet staged in Tigris, `ready=False` is sealed into the receipt; the
    member can re-request anytime to get a fresh download URL once the file
    is staged. Re-requests mint NEW receipts — every access leaves a trail.
    """
    raw_pkg = raw_package_by_slug(slug)
    customer_pkg = package_by_slug(slug)
    if raw_pkg is None or customer_pkg is None:
        raise HTTPException(status_code=404, detail=f"package not found: {slug}")

    expires_in_hours = (body or DatasetDownloadRequest()).expires_in_hours
    tigris_key = _tigris_key_for(slug, raw_pkg.get("source_basename") or raw_pkg.get("path", ""))
    ready = head_object(tigris_key)

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(hours=expires_in_hours)).isoformat()

    async with session_scope() as db:
        org = await db.get(Organization, current.org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="org not found")
        await _enforce_download_quota(
            db,
            current=current,
            limit=settings().dataset_download_daily_limit,
        )

        # Principal.id is the user id; if it's an api-key principal, it's
        # `apikey:<id>` — record it as-is for audit.
        granted_to = current.id

        def build(receipt_id, org_seq, parent_hash, created_at, share_url):
            return receipt_builder.build_dataset_download_payload(
                receipt_id=receipt_id, org_seq=org_seq, parent_hash=parent_hash,
                created_at=created_at,
                org={"id": org.id, "name": org.name},
                package=customer_pkg,
                tigris_key=tigris_key,
                ready_at_grant=ready,
                expires_at=expires_at,
                granted_to_user_id=granted_to,
                granted_to_email=current.email or None,
                share_url=share_url,
            )

        receipt = await mint_receipt(db, org_id=current.org_id, run_id=None, build=build)
        share_url = f"{settings().api_base_url.rstrip('/')}/share/{receipt.share_token}"
        download_url = f"{share_url}/download"

        return {
            "receipt_id": receipt.receipt_id,
            "org_seq": receipt.org_seq,
            "receipt_sha256": receipt.receipt_sha256,
            "share_url": share_url,
            "download_url": download_url,
            "ready": ready,
            "expires_at": expires_at,
            "package": customer_pkg,
        }


@router.get("/{slug}/samples")
async def get_samples(
    slug: str,
    limit: int = 10,
    _: Principal = Depends(require_member),
):
    """Cheap sample preview from the staged Tigris object · for the public
    share view's "crystal clear" rendering.

    Reads a small byte range from the dataset's staged Tigris object,
    parses the first N JSONL rows, and returns them with file metadata
    (size, etag, content-length). Capped at 50 rows to keep the payload
    tile-shaped.

    Behavior:
      - object not staged → 425 Too Early with Retry-After hint (member
        triggers staging via POST /datasets/catalog/{slug}/download)
      - object staged → 200 with {rows, count, file_bytes, sha256_or_etag}
    """
    import hashlib
    import json
    import os

    if limit < 1 or limit > 50:
        raise HTTPException(status_code=422, detail="limit must be 1..50")

    raw_pkg = raw_package_by_slug(slug)
    customer_pkg = package_by_slug(slug)
    if raw_pkg is None or customer_pkg is None:
        raise HTTPException(status_code=404, detail=f"package not found: {slug}")

    tigris_key = _tigris_key_for(slug, raw_pkg.get("source_basename") or raw_pkg.get("path", ""))
    meta = head_object_meta(tigris_key)
    if meta is None:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=425,
            content={
                "detail": "dataset not yet staged · request a download to trigger staging",
                "tigris_key": tigris_key,
            },
            headers={"Retry-After": "120"},
        )

    file_bytes = int(meta.get("ContentLength", 0))
    etag = (meta.get("ETag") or "").strip('"')

    # Read up to ~128KB · enough for ~10 rows of even verbose CRE memos
    # without burning bandwidth. Bound the range to actual file size.
    read_cap = min(128 * 1024, file_bytes - 1) if file_bytes else 128 * 1024
    body = get_object_partial(tigris_key, byte_range=(0, read_cap))
    if body is None:
        raise HTTPException(status_code=500, detail="failed to read tigris partial")

    # Parse JSONL · stop at limit or first malformed line. The last line may
    # be truncated (we stop early), so we ignore it deliberately.
    rows: list[dict] = []
    text = body.decode("utf-8", errors="replace")
    for raw_line in text.split("\n"):
        if len(rows) >= limit:
            break
        line = raw_line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # Truncated last line; stop here.
            break

    return {
        "package": customer_pkg,
        "tigris_key": tigris_key,
        "file_bytes": file_bytes,
        "file_etag": etag,
        # NOTE: ETag is the s3 standard hash for non-multipart uploads
        # (single-part = MD5 over content). For files >5GB it diverges from
        # a plain sha256, but our datasets are well under that ceiling.
        "rows": rows,
        "count": len(rows),
        "basename": os.path.basename(tigris_key),
    }
