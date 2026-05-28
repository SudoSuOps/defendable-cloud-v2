"""/receipts — per-org rollup views over the chain.

Sprint 14 surface. Members and the Vault frontend hit this for the "what did I
just do" rollups on the dashboard and the model card page.

The single endpoint is intentionally narrow:

  GET /receipts/recent?schema=<schema>&limit=N

Returns the N most recent receipts on the calling member's org chain,
optionally filtered to a single schema. Each row carries the receipt's
verifiable identity (id, sha256, share_url) plus a compact `summary`
derived from the payload, schema-aware so the tile renders without a
second fetch.

The summary derivation is conservative — it picks a handful of headline
fields per schema; the full payload still lives behind the share URL.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.config import settings
from app.db import session_scope
from app.deps import Principal, require_member
from app.models import Receipt
from app.schemas import ReceiptRollup, ReceiptRollupList

router = APIRouter(prefix="/receipts", tags=["receipts"])


# Known schema → summary projector. Each fn takes the receipt payload and
# returns a small JSON-friendly dict suitable for tile rendering. Unknown
# schemas get a permissive fallback (the rollup still surfaces; the tile
# just shows the schema id + created_at).
def _summary_eval(p: dict) -> dict:
    v = p.get("verdict") or {}
    return {
        "lane": "eval",
        "run_title": (p.get("run") or {}).get("title"),
        "outcome": v.get("outcome"),
        "severity": v.get("severity"),
        "score_100": v.get("score_100"),
    }


def _summary_cook(p: dict) -> dict:
    c = p.get("cook") or {}
    pin = p.get("pinned_model") or {}
    return {
        "lane": "cook",
        "run_title": (p.get("run") or {}).get("title"),
        "base_model": c.get("base_model"),
        "eval_before": c.get("eval_before"),
        "eval_after": c.get("eval_after"),
        "lift": c.get("lift"),
        # Surface that a pin was sealed in so the tile can show a small badge
        # without having to refetch the receipt.
        "pinned_model_slug": pin.get("slug"),
    }


def _summary_incident(p: dict) -> dict:
    return {
        "lane": "incident",
        "kind": p.get("kind"),
        "title": p.get("title"),
        "severity": p.get("severity"),
        "status": p.get("status"),
    }


def _summary_dataset_download(p: dict) -> dict:
    pkg = p.get("package") or {}
    return {
        "lane": "dataset-download",
        "package_slug": pkg.get("slug"),
        "package_name": pkg.get("name"),
        "vertical": pkg.get("vertical"),
        "ready_at_grant": p.get("ready_at_grant"),
        "expires_at": p.get("expires_at"),
    }


def _summary_model_pin(p: dict) -> dict:
    m = p.get("model") or {}
    return {
        "lane": "model-pin",
        "model_slug": m.get("slug"),
        "model_name": m.get("name"),
        "base": m.get("base"),
        "params_b": m.get("params_b"),
        "declaration": p.get("declaration"),
        "client_ref": p.get("client_ref"),
    }


_SUMMARY_BY_PREFIX: list[tuple[str, Any]] = [
    ("defendablecloud.eval", _summary_eval),
    ("defendablecloud.cook", _summary_cook),
    ("defendablecloud.incident", _summary_incident),
    ("defendablecloud.dataset-download", _summary_dataset_download),
    ("defendablecloud.model-pin", _summary_model_pin),
]


def _summarize(payload: dict) -> dict:
    schema = str(payload.get("schema", ""))
    for prefix, fn in _SUMMARY_BY_PREFIX:
        if schema.startswith(prefix):
            return fn(payload)
    # Unknown schema · empty summary keeps the tile renderable.
    return {"lane": "unknown"}


@router.get("/recent", response_model=ReceiptRollupList)
async def recent(
    schema: Optional[str] = Query(
        default=None,
        description="Optional exact-match schema filter, e.g. defendablecloud.model-pin-receipt/v1.",
    ),
    limit: int = Query(default=10, ge=1, le=50),
    current: Principal = Depends(require_member),
):
    """Return the N most recent receipts on the calling org's chain.

    `schema` is an optional exact-match filter. We index `created_at` per
    receipt so this query is cheap even at the high end of the lane (50).
    Each row is a compact rollup: identity + share URL + schema-aware
    summary projected from the payload.
    """
    api_base = settings().api_base_url.rstrip("/")
    async with session_scope() as db:
        stmt = (
            select(Receipt)
            .where(Receipt.org_id == current.org_id)
            .order_by(Receipt.created_at.desc())
            .limit(limit)
        )
        if schema:
            stmt = stmt.where(Receipt.payload["schema"].astext == schema)
        rows = (await db.execute(stmt)).scalars().all()

    rollups: list[dict] = []
    for r in rows:
        payload = r.payload or {}
        rollups.append(
            {
                "receipt_id": r.receipt_id,
                "org_seq": r.org_seq,
                "payload_schema": str(payload.get("schema") or ""),
                "receipt_sha256": r.receipt_sha256,
                "share_url": f"{api_base}/share/{r.share_token}",
                "created_at": (
                    r.created_at.isoformat() if r.created_at is not None else None
                ),
                "summary": _summarize(payload),
            }
        )
    return {"rollups": rollups, "count": len(rollups)}
