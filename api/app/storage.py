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
