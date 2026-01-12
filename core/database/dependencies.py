"""
Database Dependencies - FastAPI dependency injection for async database client.

@module core.database.dependencies
@version 1.0.0

This module provides FastAPI dependencies for injecting async database clients
into route handlers. This is the recommended way to use Supabase in FastAPI.

Usage in API routes:
    from core.database.dependencies import get_async_db

    @router.get("/users/{user_id}")
    async def get_user(
        user_id: str,
        db: AsyncClient = Depends(get_async_db)
    ):
        result = await db.table("profiles").select("*").eq("id", user_id).execute()
        return result.data

Design Principles:
- FastAPI best practice: Use dependency injection for database clients
- Each request gets the same singleton AsyncClient instance
- No need for run_in_threadpool - native async/await
- Reference: https://fastapi.tiangolo.com/tutorial/dependencies/
"""

import logging
from typing import AsyncGenerator, Any

from .client import get_async_db_client

logger = logging.getLogger(__name__)


async def get_async_db() -> AsyncGenerator[Any, None]:
    """
    FastAPI dependency for async database client.

    This is a generator-style dependency that provides the AsyncClient
    to route handlers. The client is a singleton, so all requests share
    the same instance.

    Yields:
        AsyncClient instance for database operations

    Example:
        @router.get("/users/{user_id}")
        async def get_user(
            user_id: str,
            db: AsyncClient = Depends(get_async_db)
        ):
            result = await db.table("profiles").select("*").eq("id", user_id).single().execute()
            return result.data

    Note:
        - The client is initialized on first request (lazy initialization)
        - Returns None if database is not configured (check in route if needed)
        - No cleanup needed - client is managed by application lifespan
    """
    client = await get_async_db_client()

    if client is None:
        logger.warning("[DB Dependency] AsyncClient not available - database not configured")
        # Still yield None to let route handler decide how to handle
        # (some routes may want to return 503, others may have fallback logic)
        yield None
        return

    # Provide client to route handler
    yield client

    # No cleanup needed here - client lifecycle managed by app lifespan
    # (see main.py lifespan context manager)


async def require_async_db() -> AsyncGenerator[Any, None]:
    """
    FastAPI dependency for async database client (required version).

    This is a stricter version of get_async_db() that raises an error
    if the database is not configured. Use this for routes that MUST
    have database access to function.

    Yields:
        AsyncClient instance (guaranteed non-None)

    Raises:
        RuntimeError: If database is not configured

    Example:
        @router.post("/users")
        async def create_user(
            user_data: UserCreate,
            db: AsyncClient = Depends(require_async_db)
        ):
            # db is guaranteed to be non-None here
            result = await db.table("profiles").insert(user_data.dict()).execute()
            return result.data
    """
    client = await get_async_db_client()

    if client is None:
        logger.error("[DB Dependency] AsyncClient required but not available")
        raise RuntimeError(
            "Database not configured. Please set SUPABASE_URL and SUPABASE_KEY environment variables."
        )

    yield client


# Backward compatibility aliases (for gradual migration)
get_db = get_async_db  # Alias for legacy code
require_db = require_async_db  # Alias for legacy code
