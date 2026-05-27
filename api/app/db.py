from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


_engine: Optional[AsyncEngine] = None
_SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def _coerce_async_url(url: str) -> str:
    """Use the asyncpg driver and drop libpq-only query params asyncpg rejects."""
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    parts = urlsplit(url)
    drop = {"sslmode", "channel_binding", "gssencmode"}
    q = [(k, v) for k, v in parse_qsl(parts.query) if k not in drop]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


def connect_args_for(raw_url: str) -> dict:
    """asyncpg doesn't read libpq's sslmode; translate sslmode=disable → ssl off.
    Internal Fly flycast Postgres speaks plaintext on the private network."""
    low = (raw_url or "").lower()
    if "sslmode=disable" in low or "ssl=false" in low:
        return {"ssl": False}
    return {}


def get_engine() -> AsyncEngine:
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine
    url = settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    _engine = create_async_engine(
        _coerce_async_url(url),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args=connect_args_for(url),
    )
    _SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


async def db_health() -> bool:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        return True
    except Exception:
        return False


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    sf = get_session_factory()
    async with sf() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise
