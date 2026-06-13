"""
Database setup — Async SQLAlchemy 2.0
"""
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base. All models inherit from this."""
    pass


def _make_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.app_debug,
        # NullPool: setiap request/task buka koneksi baru, tutup setelah selesai.
        # Penting untuk Celery workers — pool koneksi asyncpg yang dipakai
        # lintas event-loop (Celery task vs FastAPI request) akan error
        # "got Future attached to a different loop".
        # Tradeoff: latency naik ~5-10ms per query (handshake overhead).
        # Untuk v1 (solo dev, low traffic) ini trade-off yang bagus.
        # Production: consider a separate sync engine untuk Celery.
        poolclass=NullPool,
        pool_pre_ping=True,
    )


engine: AsyncEngine = _make_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async session, ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database (create all tables). Use Alembic in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database engine on shutdown."""
    await engine.dispose()


# Type alias for cleaner endpoint signatures
DB = Annotated[AsyncSession, Depends(get_db)]
