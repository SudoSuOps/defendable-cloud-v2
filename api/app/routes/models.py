"""/models/catalog — the members-only model card library.

Sprint 10 surface. 4 in-house models in v1 (Atlas, Katnis, SwarmCurator,
SwarmMarketer). Hash-anchored on the per-org chain via the pin endpoint —
when a member declares "we used model X for this work", that mint flows
through the same `mint_receipt` rail as eval / cook / incident / dataset-
download receipts, with a distinct `schema` field.

Datasets are free with membership; models are reference cards. Compute is the
meter. The pin receipt is the books-and-records artifact the member can hand
a client to prove what model produced what.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app import receipts as receipt_builder
from app.config import settings
from app.db import session_scope
from app.deps import Principal, require_member
from app.ledger import mint_receipt
from app.models import Organization
from app.models_catalog import card_by_slug, catalog_view
from app.schemas import (
    ModelCard,
    ModelCatalog,
    ModelPinReceiptOut,
    ModelPinRequest,
)

router = APIRouter(prefix="/models/catalog", tags=["models"])


@router.get("", response_model=ModelCatalog)
async def get_catalog(_: Principal = Depends(require_member)):
    """The full members-only model card library — scorecard + cards.

    Carries `models_sha256` so members can recompute and confirm the API
    mirror matches the books-and-records source.
    """
    return catalog_view()


@router.get("/{slug}", response_model=ModelCard)
async def get_card(slug: str, _: Principal = Depends(require_member)):
    """Single model card by slug — identity + base + params + card hash."""
    card = card_by_slug(slug)
    if card is None:
        raise HTTPException(status_code=404, detail=f"model card not found: {slug}")
    return card


@router.post("/{slug}/pin", response_model=ModelPinReceiptOut, status_code=201)
async def pin_card(
    slug: str,
    body: ModelPinRequest | None = None,
    current: Principal = Depends(require_member),
):
    """Pin a model card on the per-org chain.

    Seals the model's slug + name + base + params + card hash at THIS instant.
    The card body in the catalog can evolve later; the receipt remembers the
    exact card_sha256 the member declared on this date.

    The member's optional declaration + client_ref are stored as-is in the
    receipt payload — useful for "agent A on deal X" annotation. The receipt
    is shareable via /share/{token} like all other receipts.
    """
    card = card_by_slug(slug)
    if card is None:
        raise HTTPException(status_code=404, detail=f"model card not found: {slug}")

    body = body or ModelPinRequest()

    async with session_scope() as db:
        org = await db.get(Organization, current.org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="org not found")

        def build(receipt_id, org_seq, parent_hash, created_at, share_url):
            return receipt_builder.build_model_pin_payload(
                receipt_id=receipt_id, org_seq=org_seq, parent_hash=parent_hash,
                created_at=created_at,
                org={"id": org.id, "name": org.name},
                card=card,
                pinned_by_user_id=current.id,
                declaration=body.declaration,
                client_ref=body.client_ref,
                share_url=share_url,
            )

        receipt = await mint_receipt(db, org_id=current.org_id, run_id=None, build=build)
        share_url = f"{settings().api_base_url.rstrip('/')}/share/{receipt.share_token}"
        pinned_at = receipt.payload.get("pinned_at") or datetime.now(timezone.utc).isoformat()

        return {
            "receipt_id": receipt.receipt_id,
            "org_seq": receipt.org_seq,
            "receipt_sha256": receipt.receipt_sha256,
            "share_url": share_url,
            "pinned_at": pinned_at,
            "model": {
                "slug": card["slug"],
                "name": card["name"],
                "base": card["base"],
                "params_b": card["params_b"],
                "card_sha256": card["card_sha256"],
            },
            "declaration": body.declaration,
            "client_ref": body.client_ref,
        }
