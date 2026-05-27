from __future__ import annotations

import hashlib
from typing import Any, Iterable

import orjson

ZERO_HASH = "0" * 64


def canonical(obj: Any) -> bytes:
    """Deterministic JSON bytes (sorted keys) for stable hashing."""
    return orjson.dumps(obj, option=orjson.OPT_SORT_KEYS)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_canonical(obj: dict, exclude: Iterable[str] = ()) -> str:
    """SHA-256 over canonical JSON, with self-referential fields excluded."""
    skip = set(exclude)
    body = {k: v for k, v in obj.items() if k not in skip}
    return sha256_hex(canonical(body))
