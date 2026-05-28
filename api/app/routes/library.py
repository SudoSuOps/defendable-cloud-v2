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

from app import receipts as receipt_builder
from app.catalog import catalog_view, package_by_slug, raw_package_by_slug
from app.config import settings
from app.db import session_scope
from app.deps import Principal, require_member
from app.ledger import mint_receipt
from app.models import Organization
from app.schemas import (
    DatasetCatalog,
    DatasetDownloadGrant,
    DatasetDownloadRequest,
    DatasetPackage,
)
from app.storage import head_object

router = APIRouter(prefix="/datasets/catalog", tags=["datasets"])


def _tigris_key_for(slug: str, source_path: str) -> str:
    """Derive the Tigris staging key from the source NAS path. Keeps the
    on-disk basename so the file is recognisable on download, namespaced by
    slug so multiple packages don't collide.
    """
    basename = os.path.basename(source_path) or f"{slug}.jsonl"
    return f"datasets/{slug}/{basename}"


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
    tigris_key = _tigris_key_for(slug, raw_pkg.get("path", ""))
    ready = head_object(tigris_key)

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(hours=expires_in_hours)).isoformat()

    async with session_scope() as db:
        org = await db.get(Organization, current.org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="org not found")

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
