"""Frozen dataset catalog loader.

The catalog body lives at `app/data/catalog_v1.json`, parsed from the canonical
`/mnt/swarm/CATALOG.md` on the rails NAS. Updates require a deploy that ships
a new JSON snapshot — same discipline as the training-data policy.

The customer-facing API hides the internal NAS path and the internal USD
valuation. Datasets are free with membership; the priced columns are internal
books-and-records.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).parent / "data" / "catalog_v1.json"


@lru_cache(maxsize=1)
def _raw_catalog() -> dict[str, Any]:
    with _CATALOG_PATH.open() as f:
        return json.load(f)


def _package_out(p: dict[str, Any]) -> dict[str, Any]:
    """Render a package for the API. Hides internal-only fields (NAS path,
    internal USD valuation). Members see the books-and-records identifiers
    (slug, name, vertical, tier, pkg_class, pairs, deed status, sha256 from
    the catalog) — never the on-disk path or our internal valuation.
    """
    deed = p.get("deed") or "none"
    return {
        "slug": p["slug"],
        "name": p["name"],
        "vertical": p["vertical"],
        "tier": p["tier"],
        "pkg_class": p["pkg_class"],
        "pairs": p["pairs"],
        "deed_anchored": deed != "none",
        "deed": deed,
    }


def catalog_view() -> dict[str, Any]:
    """The full member-facing catalog view — scorecard + verticals + packages.

    Includes the catalog's own SHA-256 (computed at parse time over the canonical
    packages list) so a member can verify the API mirror matches the NAS source.
    """
    raw = _raw_catalog()
    return {
        "version": "v1",
        "generated_at": raw["header"].get("generated_at"),
        "filter_version": raw["header"].get("filter_version"),
        "catalog_sha256": raw["header"].get("catalog_sha256"),
        "packages_sha256": raw.get("packages_sha256"),
        "anchor": {
            "label": raw["header"].get("anchor_label"),
            "hash": raw["header"].get("anchor_hash"),
        },
        "scorecard": raw["scorecard"],
        "verticals": raw["verticals"],
        "packages": [_package_out(p) for p in raw["packages"]],
    }


def package_by_slug(slug: str) -> dict[str, Any] | None:
    for p in _raw_catalog()["packages"]:
        if p["slug"] == slug:
            return _package_out(p)
    return None
