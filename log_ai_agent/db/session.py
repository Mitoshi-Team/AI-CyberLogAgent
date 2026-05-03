import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Build sync and async DB URLs from environment variables
PG_USER = os.getenv("POSTGRES_USER", "cyberlog_user")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "cyberlog_password")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_DB = os.getenv("POSTGRES_DB", "cyberlog_db")

SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}",
)

ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL",
    f"postgresql+asyncpg://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}",
)

# Lazy-load engines to avoid connection errors during module import
_sync_engine = None
_async_engine = None
SyncSessionLocal = None
AsyncSessionLocal = None


def _get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(SYNC_DATABASE_URL, future=True)
    return _sync_engine


def _get_async_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(ASYNC_DATABASE_URL, future=True)
    return _async_engine


def _get_sync_sessionmaker():
    global SyncSessionLocal
    if SyncSessionLocal is None:
        SyncSessionLocal = sessionmaker(bind=_get_sync_engine(), autoflush=False, autocommit=False)
    return SyncSessionLocal


def _get_async_sessionmaker():
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = sessionmaker(bind=_get_async_engine(), class_=AsyncSession, expire_on_commit=False)
    return AsyncSessionLocal


def get_sync_engine():
    return _get_sync_engine()


def get_async_engine():
    return _get_async_engine()


def get_sync_session():
    return _get_sync_sessionmaker()()


def get_async_session():
    return _get_async_sessionmaker()()
