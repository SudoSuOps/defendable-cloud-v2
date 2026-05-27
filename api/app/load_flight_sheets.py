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
    if not files:
        print(f"[flight-sheets] no library files in {LIBRARY} — skipping (keeping existing)")
        return
    library_slugs: set[str] = set()
    added = updated = 0
    async with session_scope() as db:
        for f in files:
            fs = json.loads(f.read_text())
            library_slugs.add(fs["slug"])
            row = (
                await db.execute(select(FlightSheet).where(FlightSheet.slug == fs["slug"]))
            ).scalar_one_or_none()
            if row is None:
                db.add(FlightSheet(id=new_id(), slug=fs["slug"], active=True,
                                   eval_spec=fs.get("eval_spec"), **{k: fs[k] for k in FIELDS}))
                added += 1
            else:
                for k in FIELDS:
                    setattr(row, k, fs[k])
                row.eval_spec = fs.get("eval_spec")
                row.active = True
                updated += 1

        # Source-of-truth: anything not in the library is retired from the picker
        # (deactivated, not deleted — historical runs keep their flight_sheet_id).
        existing = (await db.execute(select(FlightSheet))).scalars().all()
        deactivated = 0
        for row in existing:
            if row.slug not in library_slugs and row.active:
                row.active = False
                deactivated += 1
    print(
        f"[flight-sheets] synced {len(files)} file(s) from {LIBRARY} · "
        f"{added} added · {updated} updated · {deactivated} deactivated"
    )


def main() -> None:
    asyncio.run(sync())


if __name__ == "__main__":
    main()
