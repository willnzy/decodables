"""
Cache Service Module
统一缓存服务

Provides:
- Unified caching interface
- Redis primary with memory fallback
- Automatic serialization/deserialization
- TTL management
"""

import json
import hashlib
import threading
import time
import logging
from typing import Optional, Any, Dict, List
from datetime import datetime

from .redis_client import get_redis_client, is_redis_available
from .cache_keys import (
    config_key,
    config_all_key,
    experiment_key,
    experiment_list_key,
    ai_result_key,
    stats_key,
    CacheTTL,
    CacheNamespace,
)

logger = logging.getLogger(__name__)


class MemoryFallbackCache:
    """
    In-memory cache fallback when Redis is unavailable.
    
    Thread-safe implementation with TTL support.
    Only used when Redis is down or not configured.
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
            
            # Check expiry
            expiry_time = self._expiry.get(key, 0)
            if expiry_time and time.time() > expiry_time:
                del self._cache[key]
                del self._expiry[key]
                return None
            
            return self._cache[key]
    
    def set(self, key: str, value: str, ttl: int = 0):
        """Set value in cache with optional TTL."""
        with self._lock:
            # Evict oldest if at capacity
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
        # Convert Redis pattern to simple prefix
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


class CacheService:
    """
    Unified cache service.
    
    Uses Redis when available, falls back to in-memory cache.
    Provides type-safe methods for different cache domains.
    """
    
    def __init__(self):
        self._fallback = MemoryFallbackCache()
        self._using_redis = False
        self._last_redis_check = 0
        self._redis_check_interval = 30  # Check Redis availability every 30s
    
    def _get_client(self):
        """
        Get Redis client with automatic fallback detection.
        
        Returns:
            Redis client or None (use fallback)
        """
        now = time.time()
        
        # Periodically recheck Redis availability
        if now - self._last_redis_check > self._redis_check_interval:
            self._using_redis = is_redis_available()
            self._last_redis_check = now
            
            if self._using_redis:
                logger.debug("[CacheService] Using Redis")
            else:
                logger.debug("[CacheService] Using memory fallback")
        
        if self._using_redis:
            client = get_redis_client()
            if client:
                return client
            # Redis became unavailable
            self._using_redis = False
            logger.warning("[CacheService] Redis unavailable, switching to memory fallback")
        
        return None
    
    # ==========================================
    # Generic Operations
    # ==========================================
    
    def get(self, key: str) -> Optional[str]:
        """
        Get string value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        client = self._get_client()
        
        try:
            if client:
                return client.get(key)
            return self._fallback.get(key)
        except Exception as e:
            logger.error(f"[CacheService] Get error: {e}")
            return self._fallback.get(key)
    
    def set(self, key: str, value: str, ttl: int = 0) -> bool:
        """
        Set string value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (0 = no expiry)
            
        Returns:
            True if successful
        """
        client = self._get_client()
        
        try:
            if client:
                if ttl > 0:
                    client.setex(key, ttl, value)
                else:
                    client.set(key, value)
                return True
            
            self._fallback.set(key, value, ttl)
            return True
        except Exception as e:
            logger.error(f"[CacheService] Set error: {e}")
            self._fallback.set(key, value, ttl)
            return True
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
        """
        client = self._get_client()
        
        try:
            if client:
                client.delete(key)
            self._fallback.delete(key)
            return True
        except Exception as e:
            logger.error(f"[CacheService] Delete error: {e}")
            self._fallback.delete(key)
            return True
    
    def delete_pattern(self, pattern: str) -> bool:
        """
        Delete keys matching pattern.
        
        Args:
            pattern: Redis glob pattern (e.g., "md:config:*")
            
        Returns:
            True if successful
        """
        client = self._get_client()
        
        try:
            if client:
                # Use SCAN to avoid blocking
                cursor = 0
                while True:
                    cursor, keys = client.scan(cursor, match=pattern, count=100)
                    if keys:
                        client.delete(*keys)
                    if cursor == 0:
                        break
            
            self._fallback.delete_pattern(pattern)
            return True
        except Exception as e:
            logger.error(f"[CacheService] Delete pattern error: {e}")
            self._fallback.delete_pattern(pattern)
            return True
    
    # ==========================================
    # JSON Operations
    # ==========================================
    
    def get_json(self, key: str) -> Optional[Any]:
        """
        Get JSON value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized value or None
        """
        value = self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.warning(f"[CacheService] JSON decode error for {key}: {e}")
            return None
    
    def set_json(self, key: str, value: Any, ttl: int = 0) -> bool:
        """
        Set JSON value in cache.
        
        Args:
            key: Cache key
            value: Value to serialize and cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value, default=str)
            return self.set(key, serialized, ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"[CacheService] JSON encode error: {e}")
            return False
    
    # ==========================================
    # System Config Cache
    # ==========================================
    
    def get_config(self, key: str) -> Optional[Any]:
        """Get cached config value."""
        cache_key = config_key(key)
        return self.get_json(cache_key)
    
    def set_config(self, key: str, value: Any) -> bool:
        """Set config in cache."""
        cache_key = config_key(key)
        return self.set_json(cache_key, value, CacheTTL.CONFIG)
    
    def delete_config(self, key: str) -> bool:
        """Delete specific config from cache."""
        cache_key = config_key(key)
        return self.delete(cache_key)
    
    def get_all_configs(self, group: str = None) -> Optional[Dict]:
        """Get all cached configs."""
        cache_key = config_all_key(group)
        return self.get_json(cache_key)
    
    def set_all_configs(self, configs: Dict, group: str = None) -> bool:
        """Set all configs in cache."""
        cache_key = config_all_key(group)
        return self.set_json(cache_key, configs, CacheTTL.CONFIG)
    
    def invalidate_config_cache(self, key: str = None):
        """
        Invalidate config cache.
        
        Args:
            key: Specific key to invalidate, or None for all
        """
        if key:
            self.delete_config(key)
            # Also invalidate the "all" cache
            self.delete_pattern(f"{CacheNamespace.CONFIG}__all__*")
        else:
            self.delete_pattern(f"{CacheNamespace.CONFIG}*")
    
    # ==========================================
    # Experiment Cache
    # ==========================================
    
    def get_experiment(self, exp_key: str) -> Optional[Dict]:
        """Get cached experiment."""
        cache_key = experiment_key(exp_key)
        return self.get_json(cache_key)
    
    def set_experiment(self, exp_key: str, experiment: Dict) -> bool:
        """Set experiment in cache."""
        cache_key = experiment_key(exp_key)
        return self.set_json(cache_key, experiment, CacheTTL.EXPERIMENT)
    
    def delete_experiment(self, exp_key: str) -> bool:
        """Delete experiment from cache."""
        cache_key = experiment_key(exp_key)
        return self.delete(cache_key)
    
    def invalidate_experiment_cache(self, exp_key: str = None):
        """
        Invalidate experiment cache.
        
        Args:
            exp_key: Specific experiment to invalidate, or None for all
        """
        if exp_key:
            self.delete_experiment(exp_key)
            # Also invalidate list cache
            self.delete_pattern(f"{CacheNamespace.EXPERIMENT}__list__*")
        else:
            self.delete_pattern(f"{CacheNamespace.EXPERIMENT}*")
    
    # ==========================================
    # Stats Cache
    # ==========================================
    
    def get_stats(self, stat_type: str, date: str = None) -> Optional[Any]:
        """Get cached stats."""
        cache_key = stats_key(stat_type, date)
        return self.get_json(cache_key)
    
    def set_stats(self, stat_type: str, stats: Any, date: str = None) -> bool:
        """Set stats in cache."""
        cache_key = stats_key(stat_type, date)
        return self.set_json(cache_key, stats, CacheTTL.STATS)
    
    def invalidate_stats_cache(self, stat_type: str = None):
        """Invalidate stats cache."""
        if stat_type:
            self.delete_pattern(f"{CacheNamespace.STATS}{stat_type}*")
        else:
            self.delete_pattern(f"{CacheNamespace.STATS}*")
    
    # ==========================================
    # AI Result Cache
    # ==========================================
    
    def get_ai_hash(self, prompt: str, model: str, params: Dict = None) -> str:
        """
        Generate hash key for AI result caching.
        
        Args:
            prompt: The input prompt
            model: Model name
            params: Additional parameters
            
        Returns:
            Hash string
        """
        content = f"{prompt}:{model}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_ai_result(self, hash_key: str) -> Optional[Any]:
        """Get cached AI result."""
        cache_key = ai_result_key(hash_key)
        return self.get_json(cache_key)
    
    def set_ai_result(self, hash_key: str, result: Any, ttl: int = None) -> bool:
        """Set AI result in cache."""
        cache_key = ai_result_key(hash_key)
        actual_ttl = ttl if ttl is not None else CacheTTL.AI_TEXT
        if actual_ttl <= 0:
            return False  # Don't cache if TTL is 0
        return self.set_json(cache_key, result, actual_ttl)
    
    # ==========================================
    # Health & Utility
    # ==========================================
    
    def is_redis_active(self) -> bool:
        """Check if currently using Redis."""
        return self._using_redis and is_redis_available()
    
    def get_backend_info(self) -> Dict:
        """Get current backend info."""
        return {
            "backend": "redis" if self._using_redis else "memory",
            "redis_available": is_redis_available(),
        }
    
    def clear_all(self):
        """
        Clear all cache (use with caution).
        
        Note: This only clears keys with our prefix.
        """
        from .cache_keys import PREFIX
        self.delete_pattern(f"{PREFIX}*")
        self._fallback.clear()
        logger.warning("[CacheService] All cache cleared")


# Module-level singleton
cache_service = CacheService()
