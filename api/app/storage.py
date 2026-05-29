from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import boto3
from botocore.client import Config

from app.config import settings


@dataclass
class PutResult:
    key: str
    etag: str
    size: int
    public_url: str


@lru_cache(maxsize=1)
def _client():
    s = settings()
    return boto3.client(
        "s3",
        endpoint_url=s.aws_endpoint_url_s3,
        aws_access_key_id=s.aws_access_key_id,
        aws_secret_access_key=s.aws_secret_access_key,
        region_name=s.aws_region,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def bucket() -> str:
    return settings().tigris_bucket


def storage_health() -> bool:
    try:
        _client().head_bucket(Bucket=bucket())
        return True
    except Exception:
        return False


def put_object(key: str, body: bytes, content_type: str = "application/json") -> PutResult:
    resp = _client().put_object(
        Bucket=bucket(),
        Key=key,
        Body=body,
        ContentType=content_type,
        CacheControl="public, max-age=300",
    )
    etag = (resp.get("ETag") or "").strip('"')
    return PutResult(
        key=key,
        etag=etag,
        size=len(body),
        public_url=f"{settings().aws_endpoint_url_s3.rstrip('/')}/{bucket()}/{key}",
    )


def get_object(key: str) -> Optional[bytes]:
    try:
        resp = _client().get_object(Bucket=bucket(), Key=key)
        return resp["Body"].read()
    except _client().exceptions.NoSuchKey:
        return None
    except Exception:
        return None


def head_object(key: str) -> bool:
    """Return True if the object exists in Tigris. Used by the dataset-download
    flow to surface a `ready` flag without streaming the file.
    """
    try:
        _client().head_object(Bucket=bucket(), Key=key)
        return True
    except Exception:
        return False


def get_object_partial(key: str, *, byte_range: tuple[int, int]) -> Optional[bytes]:
    """Read a byte range from a Tigris object · used for cheap sample previews
    of large JSONL datasets without streaming the full file.

    `byte_range` is (start, end) inclusive in HTTP Range header style.
    Returns None if the object doesn't exist or the read fails.
    """
    start, end = byte_range
    try:
        resp = _client().get_object(
            Bucket=bucket(), Key=key, Range=f"bytes={start}-{end}"
        )
        return resp["Body"].read()
    except _client().exceptions.NoSuchKey:
        return None
    except Exception:
        return None


def head_object_meta(key: str) -> Optional[dict]:
    """Return the head_object response (size, etag, etc.) or None."""
    try:
        return _client().head_object(Bucket=bucket(), Key=key)
    except Exception:
        return None


def presigned_get_url(key: str, *, expires_in_seconds: int = 86400) -> str:
    """Generate a time-limited signed URL for a GET against the bucket.
    Used by /share/{token}/download to redirect to fresh URLs on each access.
    """
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket(), "Key": key},
        ExpiresIn=expires_in_seconds,
        HttpMethod="GET",
    )
