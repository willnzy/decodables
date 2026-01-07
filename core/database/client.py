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


# Module-level singleton
_db_client: Optional[Any] = None
_config: Optional[DatabaseConfig] = None


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


def close_db_client():
    """
    Close database client (for graceful shutdown).
    """
    global _db_client, _config
    _db_client = None
    _config = None
    logger.info("[DB] Database client closed")


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
