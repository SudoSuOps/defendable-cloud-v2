"""/datasets/catalog — the members-only dataset library surface.

99 packages across 12 verticals · 3.35M training pairs · hash-anchored. Free
with membership; we surface package identity + pair counts + deed status,
never the internal NAS path or our internal $ valuation.

Members can fetch the catalog and recompute `packages_sha256` from the canonical
sorted packages list to confirm the API mirror matches the books-and-records
source on the NAS.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.catalog import catalog_view, package_by_slug
from app.deps import Principal, require_member
from app.schemas import DatasetCatalog, DatasetPackage

router = APIRouter(prefix="/datasets/catalog", tags=["datasets"])


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
