"""Shared receipt minting — the per-org hash chain. Used by run + cook receipts."""
from __future__ import annotations

from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import receipts as receipt_builder
from app.config import settings
from app.hashing import ZERO_HASH, canonical, sha256_hex
from app.models import Artifact, Receipt
from app.security import make_share_token
from app.storage import put_object
from app.util import iso_now, new_id

# build(receipt_id, org_seq, parent_hash, created_at, share_url) -> payload dict
PayloadBuilder = Callable[[str, int, str, str, str], dict]


async def mint_receipt(db: AsyncSession, *, org_id: str, run_id: str, build: PayloadBuilder) -> Receipt:
    last = (
        await db.execute(
            select(Receipt).where(Receipt.org_id == org_id).order_by(Receipt.org_seq.desc()).limit(1)
        )
    ).scalar_one_or_none()
    org_seq = (last.org_seq + 1) if last else 0
    parent_hash = last.receipt_sha256 if last else ZERO_HASH

    receipt_id = f"DCR-{org_seq:06d}-{new_id()[:8]}"
    share_token = make_share_token()
    share_url = f"{settings().api_base_url.rstrip('/')}/share/{share_token}"
    created_at = iso_now()

    payload = build(receipt_id, org_seq, parent_hash, created_at, share_url)
    receipt_sha256 = sha256_hex(canonical(payload))

    rid = new_id()
    json_key = f"orgs/{org_id}/receipts/{receipt_id}.json"
    pdf_key = f"orgs/{org_id}/receipts/{receipt_id}.pdf"
    pdf_bytes = receipt_builder.render_pdf(payload, receipt_sha256)
    json_bytes = canonical({**payload, "receipt_sha256": receipt_sha256})
    sj = sp = None
    try:
        put_object(json_key, json_bytes, content_type="application/json")
        sj = json_key
        put_object(pdf_key, pdf_bytes, content_type="application/pdf")
        sp = pdf_key
    except Exception:
        pass

    r = Receipt(
        id=rid, org_id=org_id, run_id=run_id, receipt_id=receipt_id, org_seq=org_seq,
        parent_hash=parent_hash, receipt_sha256=receipt_sha256, share_token=share_token,
        payload=payload, json_key=sj, pdf_key=sp,
    )
    db.add(r)
    # Persist the receipt before its artifacts: the artifacts carry a FK to
    # receipts.id and are flushed via a batched executemany that would otherwise
    # race ahead of the parent insert (artifacts_receipt_id_fkey violation).
    await db.flush()
    if sj:
        db.add(Artifact(id=new_id(), run_id=run_id, receipt_id=rid, kind="receipt_json",
                        tigris_key=json_key, sha256=sha256_hex(json_bytes), byte_size=len(json_bytes),
                        content_type="application/json"))
    if sp:
        db.add(Artifact(id=new_id(), run_id=run_id, receipt_id=rid, kind="receipt_pdf",
                        tigris_key=pdf_key, sha256=sha256_hex(pdf_bytes), byte_size=len(pdf_bytes),
                        content_type="application/pdf"))
    await db.flush()
    return r
