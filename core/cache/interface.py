"""
Cache Provider Interface - Abstract base for cache implementations.

@module core.cache.interface
@version 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class ICacheProvider(ABC):
    """
    Abstract interface for cache providers.

    All cache implementations (Redis, Memory, etc.) must implement this interface.
    This enables easy swapping of cache backends and testing with mocks.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """
        Get string value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    def set(self, key: str, value: str, ttl: int = 0) -> bool:
        """
        Set string value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (0 = no expiration)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def delete_pattern(self, pattern: str) -> bool:
        """
        Delete keys matching pattern.

        Args:
            pattern: Glob-style pattern (e.g., "prefix:*")

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        pass

    @abstractmethod
    def clear(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def size(self) -> int:
        """
        Get current number of cached items.

        Returns:
            Number of items in cache
        """
        pass
