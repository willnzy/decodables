"""
Database Client - Supabase client initialization and management.

@module core.database.client
@version 1.0.0
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, Any, TYPE_CHECKING

# Type alias for Supabase client (for type hints in repositories)
if TYPE_CHECKING:
    from supabase import Client as SupabaseClient
    DatabaseClient = SupabaseClient
else:
    DatabaseClient = Any

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str
    key: str

    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create config from environment variables."""
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")

        # Ensure URL has trailing slash
        if url and not url.endswith('/'):
            url = url + '/'

        return cls(url=url, key=key)

    @property
    def is_valid(self) -> bool:
        """Check if config is valid."""
        return bool(self.url and self.key)


# Module-level singletons
_db_client: Optional[Any] = None  # Sync client
_async_db_client: Optional[Any] = None  # Async client
_config: Optional[DatabaseConfig] = None

# WS-20: Track outstanding task-specific clients for leak detection
_active_task_clients: int = 0
_TASK_CLIENT_WARN_THRESHOLD = 10  # Warn if more than 10 outstanding clients


def get_db_client(config: DatabaseConfig = None) -> Optional[Any]:
    """
    Get database client (singleton).

    Args:
        config: Optional configuration, uses environment if not provided

    Returns:
        Supabase client instance, or None if not configured
    """
    global _db_client, _config

    if _db_client is not None:
        return _db_client

    # Use provided config or load from environment
    cfg = config or DatabaseConfig.from_env()

    if not cfg.is_valid:
        logger.warning("[DB] Database not initialized - missing URL or KEY")
        return None

    try:
        from supabase import create_client
        _db_client = create_client(cfg.url, cfg.key)
        _config = cfg
        logger.info("[DB] Database client initialized")
        return _db_client
    except ImportError:
        logger.error("[DB] supabase package not installed")
        return None
    except Exception as e:
        logger.error(f"[DB] Failed to initialize client: {e}")
        return None


def is_db_available() -> bool:
    """
    Check if database is available.

    Returns:
        True if client is initialized and accessible
    """
    client = get_db_client()
    if not client:
        return False

    try:
        # Simple health check - try to select from a system table
        # This is a lightweight query that should always work
        client.table("system_configs").select("key").limit(1).execute()
        return True
    except Exception as e:
        logger.warning(f"[DB] Health check failed: {e}")
        return False


async def get_async_db_client(config: DatabaseConfig = None) -> Optional[Any]:
    """
    Get async database client (singleton).

    This is the new async-native client for FastAPI.
    Uses Supabase AsyncClient for native async/await operations.

    Args:
        config: Optional configuration, uses environment if not provided

    Returns:
        Supabase AsyncClient instance, or None if not configured

    Example:
        async_client = await get_async_db_client()
        result = await async_client.table("users").select("*").execute()
    """
    global _async_db_client, _config

    if _async_db_client is not None:
        return _async_db_client

    # Use provided config or load from environment
    cfg = config or DatabaseConfig.from_env()

    if not cfg.is_valid:
        logger.warning("[DB] Async database not initialized - missing URL or KEY")
        return None

    try:
        from supabase import acreate_client
        _async_db_client = await acreate_client(cfg.url, cfg.key)
        _config = cfg
        logger.info("[DB] Async database client initialized")
        return _async_db_client
    except ImportError:
        logger.error("[DB] supabase package not installed or AsyncClient not available")
        return None
    except Exception as e:
        logger.error(f"[DB] Failed to initialize async client: {e}")
        return None


def close_db_client():
    """
    Close database client (for graceful shutdown).
    """
    global _db_client, _config
    _db_client = None
    _config = None
    logger.info("[DB] Database client closed")


async def close_async_db_client():
    """
    Close async database client (for graceful shutdown).
    """
    global _async_db_client
    if _async_db_client is not None:
        # AsyncClient may have cleanup methods in the future
        _async_db_client = None
        logger.info("[DB] Async database client closed")


async def create_task_async_client(config: DatabaseConfig = None) -> Any:
    """
    Create a fresh async client for scheduled tasks.

    IMPORTANT: This is NOT a singleton. Each scheduled task should create
    its own client to avoid event loop conflicts.

    Background:
    - BackgroundScheduler runs tasks in separate threads
    - Each thread creates a new event loop via asyncio.run()
    - Singleton async clients are bound to the original event loop
    - Using a singleton across event loops causes "Event loop is closed" error

    The caller is responsible for closing the client after use.

    Args:
        config: Optional configuration, uses environment if not provided

    Returns:
        New Supabase AsyncClient instance

    Raises:
        ValueError: If database is not configured

    Usage in scheduled tasks:
        async def my_task():
            client = await create_task_async_client()
            try:
                # use client...
            finally:
                # Cleanup (if aclose is available)
                if hasattr(client, 'aclose'):
                    await client.aclose()
    """
    cfg = config or DatabaseConfig.from_env()

    if not cfg.is_valid:
        raise ValueError("Database not configured - missing URL or KEY")

    global _active_task_clients

    try:
        from supabase import acreate_client
        client = await acreate_client(cfg.url, cfg.key)
        _active_task_clients += 1

        # WS-20: Connection pool leak detection
        if _active_task_clients > _TASK_CLIENT_WARN_THRESHOLD:
            logger.warning(
                f"[DB] ⚠️ Connection pool leak suspected: {_active_task_clients} "
                f"active task clients (threshold: {_TASK_CLIENT_WARN_THRESHOLD}). "
                f"Ensure clients are closed after use."
            )
        else:
            logger.info(f"[DB] Task-specific async client created (active: {_active_task_clients})")

        return client
    except ImportError:
        logger.error("[DB] supabase package not installed or AsyncClient not available")
        raise
    except Exception as e:
        logger.error(f"[DB] Failed to create task async client: {e}")
        raise


def notify_task_client_closed():
    """
    WS-20: Track when a task-specific client is closed.

    Call this after closing a task client to maintain accurate count.
    """
    global _active_task_clients
    if _active_task_clients > 0:
        _active_task_clients -= 1


def get_db_info() -> dict:
    """
    Get database connection info (for monitoring/debugging).

    Returns:
        Dict with database info
    """
    cfg = _config or DatabaseConfig.from_env()

    if not cfg.is_valid:
        return {"status": "unavailable", "reason": "not configured"}

    client = get_db_client()
    if not client:
        return {"status": "unavailable", "reason": "client not initialized"}

    return {
        "status": "connected" if is_db_available() else "error",
        "url": cfg.url[:30] + "..." if len(cfg.url) > 30 else cfg.url,
    }
