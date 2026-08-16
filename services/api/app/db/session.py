import os
from collections.abc import AsyncGenerator
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def normalize_database_url(url: str) -> tuple[str, dict]:
    """asyncpg wants ssl=True (a bool/SSLContext, not the libpq 'sslmode' string),
    and its own driver prefix. Neon connection strings come as
    postgresql://...?sslmode=require — translate both."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    connect_args: dict = {}
    if query.pop("sslmode", None) is not None:
        connect_args["ssl"] = True
    query.pop("channel_binding", None)

    clean_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return clean_url, connect_args


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see services/api/.env.example)")
    return url


@lru_cache
def get_engine() -> AsyncEngine:
    url, connect_args = normalize_database_url(get_database_url())
    return create_async_engine(url, pool_pre_ping=True, connect_args=connect_args)


async def get_session() -> AsyncGenerator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        yield session
