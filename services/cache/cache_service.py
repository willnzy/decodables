"""
Cache Service Module - Unified caching interface

@module services.cache.cache_service
@version 3.24
"""

import json
import hashlib
import time
import logging
from typing import Optional, Any, Dict, Callable

from .redis_client import get_redis_client, is_redis_available
from .memory_cache import MemoryFallbackCache
from .cache_keys import (
    config_key, config_all_key, experiment_key, experiment_list_key,
    ai_result_key, stats_key, CacheTTL, CacheNamespace,
)

logger = logging.getLogger(__name__)


class CacheService:
    """
    Unified cache service with Redis primary and memory fallback.
    Provides cache penetration protection and domain-specific methods.
    """
    
    NULL_MARKER = "__CACHE_NULL__"
    NULL_TTL = 60
    
    def __init__(self):
        self._fallback = MemoryFallbackCache()
        self._using_redis = False
        self._last_redis_check = 0
        self._redis_check_interval = 30
    
    def _get_client(self):
        """Get Redis client with automatic fallback detection."""
        now = time.time()
        
        if now - self._last_redis_check > self._redis_check_interval:
            self._using_redis = is_redis_available()
            self._last_redis_check = now
        
        if self._using_redis:
            client = get_redis_client()
            if client:
                return client
            self._using_redis = False
        
        return None
    
    # ==========================================
    # Generic Operations
    # ==========================================
    
    def get(self, key: str) -> Optional[str]:
        """Get string value from cache."""
        client = self._get_client()
        try:
            if client:
                return client.get(key)
            return self._fallback.get(key)
        except Exception as e:
            logger.error(f"[Cache] Get error: {e}")
            return self._fallback.get(key)
    
    def set(self, key: str, value: str, ttl: int = 0) -> bool:
        """Set string value in cache."""
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
            logger.error(f"[Cache] Set error: {e}")
            self._fallback.set(key, value, ttl)
            return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        client = self._get_client()
        try:
            if client:
                client.delete(key)
            self._fallback.delete(key)
            return True
        except Exception as e:
            logger.error(f"[Cache] Delete error: {e}")
            self._fallback.delete(key)
            return True
    
    def delete_pattern(self, pattern: str) -> bool:
        """Delete keys matching pattern."""
        client = self._get_client()
        try:
            if client:
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
            logger.error(f"[Cache] Delete pattern error: {e}")
            self._fallback.delete_pattern(pattern)
            return True
    
    # ==========================================
    # Cache Penetration Protection
    # ==========================================
    
    def get_with_null_protection(self, key: str) -> tuple:
        """Get value with null value protection."""
        value = self.get(key)
        if value is None:
            return (False, None)
        if value == self.NULL_MARKER:
            return (True, None)
        try:
            return (True, json.loads(value))
        except json.JSONDecodeError:
            return (True, value)
    
    def set_null(self, key: str, ttl: int = None) -> bool:
        """Cache null value to prevent penetration."""
        return self.set(key, self.NULL_MARKER, ttl or self.NULL_TTL)
    
    def get_or_fetch(self, key: str, fetch_func: Callable, ttl: int = 300, null_ttl: int = None) -> Optional[Any]:
        """Get from cache or fetch from source."""
        is_cached, value = self.get_with_null_protection(key)
        if is_cached:
            return value
        
        try:
            result = fetch_func()
        except Exception as e:
            logger.error(f"[Cache] Fetch error for {key}: {e}")
            return None
        
        if result is None:
            self.set_null(key, null_ttl)
        else:
            self.set_json(key, result, ttl)
        
        return result
    
    async def get_or_fetch_async(self, key: str, fetch_func, ttl: int = 300, null_ttl: int = None) -> Optional[Any]:
        """Async version of get_or_fetch."""
        is_cached, value = self.get_with_null_protection(key)
        if is_cached:
            return value
        
        try:
            result = await fetch_func()
        except Exception as e:
            logger.error(f"[Cache] Async fetch error for {key}: {e}")
            return None
        
        if result is None:
            self.set_null(key, null_ttl)
        else:
            self.set_json(key, result, ttl)
        
        return result
    
    # ==========================================
    # JSON Operations
    # ==========================================
    
    def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache."""
        value = self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"[Cache] Invalid JSON for key: {key}")
            return None
    
    def set_json(self, key: str, value: Any, ttl: int = 0) -> bool:
        """Set JSON value in cache."""
        try:
            return self.set(key, json.dumps(value), ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"[Cache] JSON serialize error: {e}")
            return False
    
    # ==========================================
    # Domain-specific Methods
    # ==========================================
    
    def get_config(self, key: str) -> Optional[Any]:
        return self.get_json(config_key(key))
    
    def set_config(self, key: str, value: Any) -> bool:
        return self.set_json(config_key(key), value, CacheTTL.CONFIG)
    
    def delete_config(self, key: str) -> bool:
        return self.delete(config_key(key))
    
    def get_all_configs(self, group: str = None) -> Optional[Dict]:
        return self.get_json(config_all_key(group))
    
    def set_all_configs(self, configs: Dict, group: str = None) -> bool:
        return self.set_json(config_all_key(group), configs, CacheTTL.CONFIG)
    
    def invalidate_config_cache(self, key: str = None):
        """Invalidate config cache."""
        if key:
            self.delete(config_key(key))
        else:
            self.delete_pattern(f"{CacheNamespace.CONFIG}:*")
    
    def get_experiment(self, exp_key: str) -> Optional[Dict]:
        return self.get_json(experiment_key(exp_key))
    
    def set_experiment(self, exp_key: str, experiment: Dict) -> bool:
        return self.set_json(experiment_key(exp_key), experiment, CacheTTL.EXPERIMENT)
    
    def delete_experiment(self, exp_key: str) -> bool:
        return self.delete(experiment_key(exp_key))
    
    def invalidate_experiment_cache(self, exp_key: str = None):
        """Invalidate experiment cache."""
        if exp_key:
            self.delete(experiment_key(exp_key))
        else:
            self.delete_pattern(f"{CacheNamespace.EXPERIMENT}:*")
    
    def get_stats(self, stat_type: str, date: str = None) -> Optional[Any]:
        return self.get_json(stats_key(stat_type, date))
    
    def set_stats(self, stat_type: str, stats: Any, date: str = None) -> bool:
        return self.set_json(stats_key(stat_type, date), stats, CacheTTL.STATS)
    
    def invalidate_stats_cache(self, stat_type: str = None):
        """Invalidate stats cache."""
        if stat_type:
            self.delete_pattern(f"{CacheNamespace.STATS}:{stat_type}:*")
        else:
            self.delete_pattern(f"{CacheNamespace.STATS}:*")
    
    # ==========================================
    # AI Cache
    # ==========================================
    
    def get_ai_hash(self, prompt: str, model: str, params: Dict = None) -> str:
        """Generate hash for AI cache key."""
        content = f"{prompt}|{model}|{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_ai_result(self, hash_key: str) -> Optional[Any]:
        return self.get_json(ai_result_key(hash_key))
    
    def set_ai_result(self, hash_key: str, result: Any, ttl: int = None) -> bool:
        return self.set_json(ai_result_key(hash_key), result, ttl or CacheTTL.AI_RESULT)
    
    # ==========================================
    # Utility Methods
    # ==========================================
    
    def is_redis_active(self) -> bool:
        return self._using_redis and get_redis_client() is not None
    
    def get_backend_info(self) -> Dict:
        return {
            "backend": "redis" if self.is_redis_active() else "memory",
            "redis_available": self._using_redis,
            "fallback_size": self._fallback.size(),
        }


# Singleton instance
cache_service = CacheService()
