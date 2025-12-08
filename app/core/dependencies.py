"""FastAPI dependencies for database and other services"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.adapter.postgres import get_postgres_adapter


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get a database session.
    
    Yields:
        Async database session
    """
    adapter = get_postgres_adapter()
    async with adapter.get_session() as session:
        yield session
