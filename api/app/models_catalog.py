"""Frozen model card catalog loader.

The catalog body lives at `app/data/models_v1.json`. Updates require a deploy
that ships a new JSON snapshot — same discipline as the dataset catalog.

For each model:
  - The catalog returns the public card (purpose, base, params, eval notes,
    compute class, rate). Members can pin a card on their per-org chain;
    pin receipts seal the card's content hash so the deliverable is durable
    even if the card is later refreshed.
  - card_sha256 is computed at parse time over the canonical card body
    (everything except the hash itself). A future card update changes the
    hash; old pin receipts still verify their own sealed copy.

The customer-facing API hides the internal weights_location and the default
rate (which is operational, not customer-facing).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.hashing import canonical, sha256_canonical, sha256_hex

_CATALOG_PATH = Path(__file__).parent / "data" / "models_v1.json"

# Fields that are operator-only and never returned over the API.
_INTERNAL_FIELDS = ("weights_location", "default_rate_usd_per_hour")
# Fields excluded from the card_sha256 computation (self-referential or
# operator-only). The card hash is over the public, declared content.
_EXCLUDED_FROM_CARD_HASH = ("card_sha256",) + _INTERNAL_FIELDS


@lru_cache(maxsize=1)
def _raw_catalog() -> dict[str, Any]:
    with _CATALOG_PATH.open() as f:
        raw = json.load(f)
    # Compute card_sha256 once at load time over each model's public card body.
    for m in raw["models"]:
        m["card_sha256"] = sha256_canonical(m, exclude=_EXCLUDED_FROM_CARD_HASH)
    return raw


def _card_out(m: dict[str, Any]) -> dict[str, Any]:
    """Render a model card for the API. Hides operator-only fields."""
    return {k: v for k, v in m.items() if k not in _INTERNAL_FIELDS}


def _models_sha256(cards: list[dict[str, Any]]) -> str:
    """SHA-256 over the canonical sorted card list. Member-recomputable."""
    keyed = sorted(cards, key=lambda c: c["slug"])
    return sha256_hex(canonical(keyed))


def catalog_view() -> dict[str, Any]:
    """The full member-facing model card catalog · scorecard + cards.

    Includes `models_sha256` so a member can recompute and confirm the API
    mirror matches the books-and-records source.
    """
    raw = _raw_catalog()
    cards = [_card_out(m) for m in raw["models"]]
    return {
        "version": raw["header"]["version"],
        "generated_at": raw["header"].get("generated_at"),
        "scope": raw["header"].get("scope"),
        "doctrine_note": raw["header"].get("doctrine_note"),
        "models_sha256": _models_sha256(cards),
        "scorecard": {
            "total_models": len(cards),
            "in_house_models": sum(1 for c in cards if c.get("family") == "in-house"),
            "active_models": sum(1 for c in cards if c.get("status") == "active"),
        },
        "models": cards,
    }


def card_by_slug(slug: str) -> dict[str, Any] | None:
    """Customer-facing card — internal fields hidden."""
    for m in _raw_catalog()["models"]:
        if m["slug"] == slug:
            return _card_out(m)
    return None


def raw_card_by_slug(slug: str) -> dict[str, Any] | None:
    """Internal use only — returns the raw card WITH operator fields. Used by
    the pin endpoint to seal the public card identity (not the operator
    fields) into the receipt. Never returned over the API.
    """
    for m in _raw_catalog()["models"]:
        if m["slug"] == slug:
            return m
    return None


# ── pin → cook join helpers ────────────────────────────────────────────────


MODEL_PIN_SCHEMA = "defendablecloud.model-pin-receipt/v1"


async def find_latest_active_pin(db, *, org_id: str, model_slug: str) -> dict | None:
    """Return the most recent model-pin-receipt for `org_id` + `model_slug`.

    "Active" = most recent · later pins for the same (org, slug) supersede
    earlier ones. Old pins stay on-chain (immutable books-and-records) but
    they're not what we link to a fresh cook.

    Returns a dict shaped for sealing into a cook receipt:
        {
          "slug", "name", "base", "params_b", "card_sha256",  ← from pin payload
          "pinned_at", "declaration", "client_ref",
          "pin_receipt_id", "pin_receipt_sha256", "pin_share_url",
        }
    or None if no pin exists. Imports SQLAlchemy lazily to avoid a circular
    `models_catalog → models → db → models_catalog` cycle at startup.
    """
    from sqlalchemy import select

    from app.models import Receipt

    rows = await db.execute(
        select(Receipt)
        .where(
            Receipt.org_id == org_id,
            Receipt.payload["schema"].astext == MODEL_PIN_SCHEMA,
            Receipt.payload["model"]["slug"].astext == model_slug,
        )
        .order_by(Receipt.created_at.desc())
        .limit(1)
    )
    r = rows.scalar_one_or_none()
    if r is None:
        return None
    pin = r.payload or {}
    model = pin.get("model") or {}
    return {
        "slug": model.get("slug"),
        "name": model.get("name"),
        "base": model.get("base"),
        "params_b": model.get("params_b"),
        "card_sha256": model.get("card_sha256"),
        "pinned_at": pin.get("pinned_at") or pin.get("created_at"),
        "declaration": pin.get("declaration"),
        "client_ref": pin.get("client_ref"),
        "pin_receipt_id": r.receipt_id,
        "pin_receipt_sha256": r.receipt_sha256,
        "pin_share_url": pin.get("share_url"),
    }
