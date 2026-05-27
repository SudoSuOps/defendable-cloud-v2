from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def make_magic_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_share_token() -> str:
    return secrets.token_urlsafe(24)


def issue_jwt(user_id: str, org_id: str, email: str) -> str:
    s = settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "org": org_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=s.jwt_ttl_hours)).timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, settings().jwt_secret, algorithms=["HS256"])
