"""Sync the flight-sheet library (api/flight_sheets/*.json) into the DB.

Idempotent upsert by slug. Flight sheets are CONTENT, not migrations — this runs
at deploy (after alembic) so the library is always in sync. Forged by the
flight-sheet-forge skill.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.db import session_scope
from app.models import FlightSheet
from app.util import new_id

LIBRARY = Path(__file__).resolve().parent.parent / "flight_sheets"

FIELDS = (
    "name", "version", "lane", "summary", "purpose", "assignment_instructions",
    "required_inputs", "expected_outputs", "audit_checks", "pass_threshold", "fail_threshold",
)


async def sync() -> None:
    files = sorted(LIBRARY.glob("*.json")) if LIBRARY.exists() else []
    added = updated = 0
    async with session_scope() as db:
        for f in files:
            fs = json.loads(f.read_text())
            row = (
                await db.execute(select(FlightSheet).where(FlightSheet.slug == fs["slug"]))
            ).scalar_one_or_none()
            if row is None:
                db.add(FlightSheet(id=new_id(), slug=fs["slug"], active=True, **{k: fs[k] for k in FIELDS}))
                added += 1
            else:
                for k in FIELDS:
                    setattr(row, k, fs[k])
                row.active = True
                updated += 1
    print(f"[flight-sheets] synced {len(files)} file(s) from {LIBRARY} · {added} added · {updated} updated")


def main() -> None:
    asyncio.run(sync())


if __name__ == "__main__":
    main()
