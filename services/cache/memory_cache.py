"""
Memory Fallback Cache - In-memory cache when Redis unavailable

@module services.cache.memory_cache
@version 3.24
"""

import threading
import time
from typing import Optional, Any, Dict


class MemoryFallbackCache:
    """
    In-memory cache fallback when Redis is unavailable.
    Thread-safe implementation with TTL support.
    """
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._max_size = max_size
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                return None
            
            expiry_time = self._expiry.get(key, 0)
            if expiry_time and time.time() > expiry_time:
                del self._cache[key]
                del self._expiry[key]
                return None
            
            return self._cache[key]
    
    def set(self, key: str, value: str, ttl: int = 0):
        """Set value in cache with optional TTL."""
        with self._lock:
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = value
            if ttl > 0:
                self._expiry[key] = time.time() + ttl
            else:
                self._expiry.pop(key, None)
    
    def delete(self, key: str):
        """Delete key from cache."""
        with self._lock:
            self._cache.pop(key, None)
            self._expiry.pop(key, None)
    
    def delete_pattern(self, pattern: str):
        """Delete keys matching pattern (simple prefix match)."""
        prefix = pattern.replace("*", "")
        
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
                self._expiry.pop(key, None)
    
    def clear(self):
        """Clear all cache."""
        with self._lock:
            self._cache.clear()
            self._expiry.clear()
    
    def _evict_oldest(self):
        """Evict oldest entry (simple FIFO)."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._expiry.pop(oldest_key, None)
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
