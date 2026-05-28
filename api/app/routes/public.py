from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.db import session_scope
from app.deps import Principal, get_current_user
from app.hashing import ZERO_HASH, canonical, sha256_hex
from app.models import Receipt
from app import receipts as receipt_builder
from app.schemas import LedgerList, LedgerVerifyResult, PublicReceipt
from app.storage import head_object, presigned_get_url
from app.util import iso

router = APIRouter(tags=["public"])


@router.get("/share/{token}", response_model=PublicReceipt)
async def public_receipt(token: str):
    async with session_scope() as db:
        r = (
            await db.execute(select(Receipt).where(Receipt.share_token == token))
        ).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="receipt not found")
        recomputed = sha256_hex(canonical(r.payload))
        return {
            "receipt_id": r.receipt_id,
            "org_seq": r.org_seq,
            "parent_hash": r.parent_hash,
            "receipt_sha256": r.receipt_sha256,
            "verified": recomputed == r.receipt_sha256,
            "created_at": r.payload.get("created_at"),
            "payload": r.payload,
        }


@router.get("/share/{token}/download")
async def public_receipt_download(token: str):
    """Indirect through a dataset-download receipt to a fresh Tigris signed URL.

    Works only for receipts whose `schema` is `defendablecloud.dataset-download-receipt/v1`.
    For any other receipt, returns 404 (the share token isn't a download grant).

    Behavior:
      - receipt not found / wrong schema → 404
      - grant expired → 410 Gone
      - object not yet staged in Tigris → 425 Too Early (Retry-After hint)
      - all good → 302 to a fresh signed URL (TTL = 15 min)
    """
    async with session_scope() as db:
        r = (
            await db.execute(select(Receipt).where(Receipt.share_token == token))
        ).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="receipt not found")

        schema = str(r.payload.get("schema", ""))
        if not schema.startswith("defendablecloud.dataset-download"):
            raise HTTPException(status_code=404, detail="share token isn't a download grant")

        expires_at_str = r.payload.get("expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
            except ValueError:
                expires_at = None
            if expires_at is not None and datetime.now(timezone.utc) > expires_at:
                raise HTTPException(
                    status_code=410,
                    detail="download grant expired — re-request via POST /datasets/catalog/{slug}/download",
                )

        tigris_key = r.payload.get("tigris_key")
        if not tigris_key:
            raise HTTPException(status_code=500, detail="receipt missing tigris_key")
        if not head_object(tigris_key):
            return Response(
                status_code=425,
                content='{"detail":"download still preparing — retry shortly"}',
                media_type="application/json",
                headers={"Retry-After": "300"},
            )
        signed = presigned_get_url(tigris_key, expires_in_seconds=900)
        return RedirectResponse(url=signed, status_code=302)


@router.get("/share/{token}/pdf")
async def public_receipt_pdf(token: str):
    async with session_scope() as db:
        r = (
            await db.execute(select(Receipt).where(Receipt.share_token == token))
        ).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="receipt not found")
        pdf = receipt_builder.render_pdf(r.payload, r.receipt_sha256)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{r.receipt_id}.pdf"'},
        )


@router.get("/ledger", response_model=LedgerList)
async def list_ledger(current: Principal = Depends(get_current_user)):
    """List the per-org hash chain in `org_seq` order — chain coordinates only,
    no payload. The chain bytes for any single entry are at `/share/{token}`."""
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(Receipt).where(Receipt.org_id == current.org_id).order_by(Receipt.org_seq.asc())
            )
        ).scalars().all()
        return {
            "entries": [
                {
                    "receipt_id": r.receipt_id,
                    "org_seq": r.org_seq,
                    "parent_hash": r.parent_hash,
                    "receipt_sha256": r.receipt_sha256,
                    "created_at": iso(r.created_at) if r.created_at else None,
                }
                for r in rows
            ]
        }


@router.get("/ledger/verify", response_model=LedgerVerifyResult)
async def verify_ledger(current: Principal = Depends(get_current_user)):
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(Receipt).where(Receipt.org_id == current.org_id).order_by(Receipt.org_seq.asc())
            )
        ).scalars().all()
        errors: list[dict] = []
        prev = ZERO_HASH
        for i, r in enumerate(rows):
            recomputed = sha256_hex(canonical(r.payload))
            if recomputed != r.receipt_sha256:
                errors.append({"org_seq": r.org_seq, "error": "hash mismatch"})
            if r.org_seq != i:
                errors.append({"org_seq": r.org_seq, "error": f"sequence gap (expected {i})"})
            if r.payload.get("parent_hash") != prev:
                errors.append({"org_seq": r.org_seq, "error": "broken parent link"})
            prev = r.receipt_sha256
        return {
            "ok": len(errors) == 0,
            "receipts_checked": len(rows),
            "errors": errors[:20],
        }
