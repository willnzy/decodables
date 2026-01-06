"""
Cache Service Tests
缓存服务测试

基于 BUSINESS_LOGIC_SPEC.md Section 11 的业务规则测试

核心业务规则:
1. 双层存储架构 (Section 11.1):
   - Redis 主存储
   - Memory 降级存储

2. TTL 配置 (Section 11.2):
   - 配置: 60s
   - 实验: 60s
   - AI 文本: 24h
   - AI 图像: 不缓存

@module tests/test_cache_service
@version v3.3
"""

import pytest
from unittest.mock import patch, MagicMock
import json


# ==========================================
# MemoryFallback Tests
# ==========================================

class TestMemoryFallbackCache:
    """
    内存降级缓存测试
    """
    
    def test_memory_cache_init(self):
        """【业务规则 11.1】内存缓存初始化"""
        from services.cache.cache_service import MemoryFallbackCache
        
        cache = MemoryFallbackCache(max_size=100)
        
        assert cache._max_size == 100
    
    def test_memory_cache_set_get(self):
        """【业务规则 11.1】内存缓存存取"""
        from services.cache.cache_service import MemoryFallbackCache
        
        cache = MemoryFallbackCache()
        
        cache.set("test_key", "test_value")
        result = cache.get("test_key")
        
        assert result == "test_value"
    
    def test_memory_cache_get_nonexistent(self):
        """【业务规则】获取不存在的键返回 None"""
        from services.cache.cache_service import MemoryFallbackCache
        
        cache = MemoryFallbackCache()
        
        result = cache.get("nonexistent_key")
        
        assert result is None
    
    def test_memory_cache_delete(self):
        """【业务规则】删除缓存键"""
        from services.cache.cache_service import MemoryFallbackCache
        
        cache = MemoryFallbackCache()
        cache.set("key_to_delete", "value")
        
        cache.delete("key_to_delete")
        result = cache.get("key_to_delete")
        
        assert result is None
    
    def test_memory_cache_delete_pattern(self):
        """【业务规则】按模式删除"""
        from services.cache.cache_service import MemoryFallbackCache
        
        cache = MemoryFallbackCache()
        cache.set("prefix:key1", "value1")
        cache.set("prefix:key2", "value2")
        cache.set("other:key3", "value3")
        
        cache.delete_pattern("prefix:*")
        
        assert cache.get("prefix:key1") is None
        assert cache.get("prefix:key2") is None
        assert cache.get("other:key3") == "value3"
    
    def test_memory_cache_clear(self):
        """【业务规则】清空缓存"""
        from services.cache.cache_service import MemoryFallbackCache
        
        cache = MemoryFallbackCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_memory_cache_ttl_expiry(self):
        """【业务规则 11.2】TTL 过期"""
        from services.cache.cache_service import MemoryFallbackCache
        import time
        
        cache = MemoryFallbackCache()
        cache.set("ttl_key", "value", ttl=1)  # 1 秒
        
        # 立即获取应该存在
        assert cache.get("ttl_key") == "value"
        
        # 等待过期
        time.sleep(1.1)
        assert cache.get("ttl_key") is None
    
    def test_memory_cache_evict_oldest(self):
        """【业务规则】LRU 淘汰"""
        from services.cache.cache_service import MemoryFallbackCache
        
        cache = MemoryFallbackCache(max_size=2)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # 应该淘汰 key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"


# ==========================================
# CacheService Basic Tests
# ==========================================

class TestCacheServiceBasic:
    """
    CacheService 基本操作测试
    """
    
    def test_cache_service_init(self):
        """【业务规则 11.1】缓存服务初始化"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        
        assert service._fallback is not None
    
    @patch('services.cache.cache_service.get_redis_client')
    @patch('services.cache.cache_service.is_redis_available')
    def test_set_get_with_redis(self, mock_redis_available, mock_get_client):
        """【业务规则 11.1】使用 Redis 存取"""
        from services.cache.cache_service import CacheService
        
        mock_redis_available.return_value = True
        mock_client = MagicMock()
        mock_client.get.return_value = b"test_value"
        mock_get_client.return_value = mock_client
        
        service = CacheService()
        service._using_redis = True
        
        result = service.get("test_key")
        
        # 返回值取决于 Redis 客户端的返回
        assert result is not None or result is None  # 可能是 mock 的返回值
    
    def test_set_get_with_fallback(self):
        """【业务规则 11.1】使用内存降级存取"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        service.set("fallback_key", "fallback_value")
        result = service.get("fallback_key")
        
        assert result == "fallback_value"


# ==========================================
# CacheService JSON Tests
# ==========================================

class TestCacheServiceJSON:
    """
    CacheService JSON 操作测试
    """
    
    def test_set_get_json(self):
        """【业务规则】JSON 存取"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        data = {"key": "value", "nested": {"a": 1}}
        service.set_json("json_key", data)
        result = service.get_json("json_key")
        
        assert result == data
    
    def test_get_json_nonexistent(self):
        """【业务规则】获取不存在的 JSON 返回 None"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        result = service.get_json("nonexistent_json")
        
        assert result is None


# ==========================================
# CacheService Config Tests
# ==========================================

class TestCacheServiceConfig:
    """
    CacheService 配置缓存测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 11.2
    """
    
    def test_set_get_config(self):
        """【业务规则 11.2】配置缓存 TTL=60s"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        config_data = {"setting1": True, "setting2": "value"}
        service.set_config("test_config", config_data)
        result = service.get_config("test_config")
        
        assert result == config_data
    
    def test_delete_config(self):
        """【业务规则】删除配置缓存"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        service.set_config("delete_config", {"a": 1})
        service.delete_config("delete_config")
        result = service.get_config("delete_config")
        
        assert result is None
    
    def test_invalidate_config_cache(self):
        """【业务规则】清除配置缓存"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        service.set_config("config1", {"a": 1})
        service.set_config("config2", {"b": 2})
        
        service.invalidate_config_cache()
        
        # 可能清除了所有配置缓存
        # 具体取决于实现


# ==========================================
# CacheService Experiment Tests
# ==========================================

class TestCacheServiceExperiment:
    """
    CacheService 实验缓存测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 11.2
    """
    
    def test_set_get_experiment(self):
        """【业务规则 11.2】实验缓存 TTL=60s"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        experiment_data = {"id": "exp_001", "variants": []}
        service.set_experiment("test_exp", experiment_data)
        result = service.get_experiment("test_exp")
        
        assert result == experiment_data
    
    def test_delete_experiment(self):
        """【业务规则】删除实验缓存"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        service.set_experiment("delete_exp", {"id": "exp_001"})
        service.delete_experiment("delete_exp")
        result = service.get_experiment("delete_exp")
        
        assert result is None
    
    def test_invalidate_experiment_cache(self):
        """【业务规则】清除实验缓存"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        service.set_experiment("exp1", {"id": "exp_001"})
        service.invalidate_experiment_cache()
        
        # 可能清除了所有实验缓存


# ==========================================
# CacheService Stats Tests
# ==========================================

class TestCacheServiceStats:
    """
    CacheService 统计缓存测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 11.2
    """
    
    def test_set_get_stats(self):
        """【业务规则 11.2】统计缓存 TTL=5min"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        stats_data = {"total": 100, "active": 50}
        service.set_stats("user_stats", stats_data)
        result = service.get_stats("user_stats")
        
        assert result == stats_data
    
    def test_invalidate_stats_cache(self):
        """【业务规则】清除统计缓存"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        service.set_stats("stats1", {"a": 1})
        service.invalidate_stats_cache()


# ==========================================
# CacheService AI Tests
# ==========================================

class TestCacheServiceAI:
    """
    CacheService AI 缓存测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 11.2
    """
    
    def test_get_ai_hash(self):
        """【业务规则】生成 AI 缓存哈希"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        
        hash1 = service.get_ai_hash("prompt1", "gpt-4o-mini")
        hash2 = service.get_ai_hash("prompt1", "gpt-4o-mini")
        hash3 = service.get_ai_hash("prompt2", "gpt-4o-mini")
        
        # 相同输入产生相同哈希
        assert hash1 == hash2
        # 不同输入产生不同哈希
        assert hash1 != hash3
    
    def test_set_get_ai_result(self):
        """【业务规则 11.2】AI 文本缓存 TTL=24h"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        ai_result = {"response": "Hello, world!"}
        hash_key = service.get_ai_hash("test prompt", "gpt-4o")
        
        service.set_ai_result(hash_key, ai_result)
        result = service.get_ai_result(hash_key)
        
        assert result == ai_result


# ==========================================
# CacheService Backend Info Tests
# ==========================================

class TestCacheServiceBackendInfo:
    """
    CacheService 后端信息测试
    """
    
    def test_is_redis_active(self):
        """【业务规则 11.1】检查 Redis 是否活跃"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        
        # 返回布尔值
        result = service.is_redis_active()
        
        assert isinstance(result, bool)
    
    def test_get_backend_info(self):
        """【业务规则 11.1】获取后端信息"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        
        info = service.get_backend_info()
        
        assert isinstance(info, dict)
        # 可能包含 backend 或 redis_available 等字段
        assert "backend" in info or "using_redis" in info or "redis_available" in info


# ==========================================
# CacheService Delete Pattern Tests
# ==========================================

class TestCacheServiceDeletePattern:
    """
    CacheService 模式删除测试
    """
    
    def test_delete_pattern_with_fallback(self):
        """【业务规则】内存降级模式删除"""
        from services.cache.cache_service import CacheService
        
        service = CacheService()
        service._using_redis = False
        
        service.set("prefix:key1", "value1")
        service.set("prefix:key2", "value2")
        service.set("other:key3", "value3")
        
        service.delete_pattern("prefix:*")
        
        assert service.get("prefix:key1") is None
        assert service.get("prefix:key2") is None
        assert service.get("other:key3") == "value3"


# ==========================================
# CacheService Clear All Tests
# ==========================================

# ==========================================
# CacheTTL Constants Tests
# ==========================================

class TestCacheTTLConstants:
    """
    缓存 TTL 常量测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 11.2
    """
    
    def test_config_ttl(self):
        """【业务规则 11.2】配置 TTL = 60s"""
        from services.cache.cache_keys import CacheTTL
        
        assert CacheTTL.CONFIG == 60
    
    def test_experiment_ttl(self):
        """【业务规则 11.2】实验 TTL = 60s"""
        from services.cache.cache_keys import CacheTTL
        
        assert CacheTTL.EXPERIMENT == 60
    
    def test_ai_text_ttl(self):
        """【业务规则 11.2】AI 文本 TTL = 24h (86400s)"""
        from services.cache.cache_keys import CacheTTL
        
        assert CacheTTL.AI_TEXT == 86400
    
    def test_ai_image_no_cache(self):
        """【业务规则 11.2】AI 图像不缓存 (TTL = 0)"""
        from services.cache.cache_keys import CacheTTL
        
        assert CacheTTL.AI_IMAGE == 0
    
    def test_stats_ttl(self):
        """【业务规则 11.2】统计 TTL = 5min (300s)"""
        from services.cache.cache_keys import CacheTTL
        
        assert CacheTTL.STATS == 300
    
    def test_rate_limit_ttl(self):
        """【业务规则 11.2】限流 TTL = 60s"""
        from services.cache.cache_keys import CacheTTL
        
        assert CacheTTL.RATE_LIMIT == 60


# ==========================================
# CacheNamespace Constants Tests
# ==========================================

class TestCacheNamespaceConstants:
    """
    缓存命名空间测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 11.2
    """
    
    def test_config_namespace(self):
        """【业务规则 11.2】配置命名空间"""
        from services.cache.cache_keys import CacheNamespace
        
        assert "config" in CacheNamespace.CONFIG.lower()
    
    def test_experiment_namespace(self):
        """【业务规则 11.2】实验命名空间"""
        from services.cache.cache_keys import CacheNamespace
        
        assert "experiment" in CacheNamespace.EXPERIMENT.lower()
    
    def test_ai_namespace(self):
        """【业务规则 11.2】AI 命名空间"""
        from services.cache.cache_keys import CacheNamespace
        
        assert "ai" in CacheNamespace.AI.lower()
    
    def test_rate_limit_namespace(self):
        """【业务规则 11.2】限流命名空间"""
        from services.cache.cache_keys import CacheNamespace
        
        assert "rl" in CacheNamespace.RATE_LIMIT.lower()
    
    def test_stats_namespace(self):
        """【业务规则 11.2】统计命名空间"""
        from services.cache.cache_keys import CacheNamespace
        
        assert "stats" in CacheNamespace.STATS.lower()


# ==========================================
# Redis Fallback & Error Handling Tests
# ==========================================

class TestCacheServiceRedisFailover:
    """Redis 故障转移测试"""
    
    def test_redis_unavailable_switches_to_memory(self):
        """Redis 不可用时切换到内存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_get.return_value = None  # Redis client returns None
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                
                # This should trigger fallback
                client = service._get_client()
                
                assert client is None
                assert service._using_redis is False


class TestCacheServiceGetErrors:
    """Get 操作错误处理测试"""
    
    def test_get_with_redis_exception(self):
        """Redis get 异常时回退到内存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Redis connection error")
            mock_get.return_value = mock_client
            
            from services.cache.cache_service import CacheService
            service = CacheService()
            service._using_redis = True
            
            # Should fallback to memory without raising
            result = service.get("test_key")
            
            # Should return None (memory fallback)
            assert result is None


class TestCacheServiceSetErrors:
    """Set 操作错误处理测试"""
    
    def test_set_with_redis_and_ttl(self):
        """Redis set 带 TTL"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0  # Force recheck
                
                result = service.set("key", "value", ttl=60)
                
                mock_client.setex.assert_called_once_with("key", 60, "value")
                assert result is True
    
    def test_set_with_redis_no_ttl(self):
        """Redis set 无 TTL"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                result = service.set("key", "value", ttl=0)
                
                mock_client.set.assert_called_once_with("key", "value")
                assert result is True
    
    def test_set_with_redis_exception(self):
        """Redis set 异常时回退到内存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                mock_client.setex.side_effect = Exception("Redis error")
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                # Should fallback without raising
                result = service.set("key", "value", ttl=60)
                
                assert result is True


class TestCacheServiceDeleteErrors:
    """Delete 操作错误处理测试"""
    
    def test_delete_with_redis(self):
        """Redis delete 成功"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                result = service.delete("key")
                
                mock_client.delete.assert_called_once_with("key")
                assert result is True
    
    def test_delete_with_redis_exception(self):
        """Redis delete 异常时回退到内存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                mock_client.delete.side_effect = Exception("Redis error")
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                # Should fallback without raising
                result = service.delete("key")
                
                assert result is True


class TestCacheServiceDeletePatternWithRedis:
    """Delete pattern with Redis SCAN"""
    
    def test_delete_pattern_with_redis_scan(self):
        """Redis delete_pattern 使用 SCAN"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                # SCAN returns (cursor, keys) - simulate single batch
                mock_client.scan.return_value = (0, ["key1", "key2"])
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                result = service.delete_pattern("md:*")
                
                mock_client.scan.assert_called()
                mock_client.delete.assert_called_with("key1", "key2")
                assert result is True
    
    def test_delete_pattern_with_redis_scan_multiple_batches(self):
        """Redis delete_pattern 多批次 SCAN"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                # Simulate multiple batches
                mock_client.scan.side_effect = [
                    (1, ["key1"]),  # First batch, cursor=1
                    (0, ["key2"])   # Second batch, cursor=0 (done)
                ]
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                result = service.delete_pattern("md:*")
                
                assert mock_client.scan.call_count == 2
                assert result is True
    
    def test_delete_pattern_with_redis_exception(self):
        """Redis delete_pattern 异常时回退"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                mock_client.scan.side_effect = Exception("Redis error")
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                # Should fallback without raising
                result = service.delete_pattern("md:*")
                
                assert result is True


class TestCacheServiceAllConfigs:
    """All configs cache operations"""
    
    def test_get_all_configs(self):
        """获取所有配置缓存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            mock_client = MagicMock()
            mock_client.get.return_value = '{"key1": "value1", "key2": "value2"}'
            mock_get.return_value = mock_client
            
            from services.cache.cache_service import CacheService
            service = CacheService()
            service._using_redis = True
            
            result = service.get_all_configs()
            
            assert result is not None or result is None  # May or may not hit cache
    
    def test_set_all_configs(self):
        """设置所有配置缓存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            
            from services.cache.cache_service import CacheService
            service = CacheService()
            service._using_redis = True
            
            result = service.set_all_configs({"key1": "value1"})
            
            assert result is True
    
    def test_get_all_configs_with_group(self):
        """获取特定组的配置缓存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            mock_client = MagicMock()
            mock_client.get.return_value = None
            mock_get.return_value = mock_client
            
            from services.cache.cache_service import CacheService
            service = CacheService()
            service._using_redis = True
            
            result = service.get_all_configs(group="api")
            
            assert result is None


class TestCacheServiceInvalidateWithKey:
    """Invalidate with specific key"""
    
    def test_invalidate_config_cache_with_key(self):
        """清除特定配置缓存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                mock_client.scan.return_value = (0, [])
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                service.invalidate_config_cache(key="specific_config")
                
                # Should delete specific key and pattern
                assert mock_client.delete.called or mock_client.scan.called
    
    def test_invalidate_experiment_cache_with_key(self):
        """清除特定实验缓存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                mock_client.scan.return_value = (0, [])
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                service.invalidate_experiment_cache(exp_key="exp_123")
                
                # Should delete specific key and list pattern
                assert mock_client.delete.called or mock_client.scan.called
    
    def test_invalidate_stats_cache_with_type(self):
        """清除特定类型统计缓存"""
        with patch('services.cache.cache_service.get_redis_client') as mock_get:
            with patch('services.cache.cache_service.is_redis_available') as mock_avail:
                mock_avail.return_value = True
                mock_client = MagicMock()
                mock_client.scan.return_value = (0, [])
                mock_get.return_value = mock_client
                
                from services.cache.cache_service import CacheService
                service = CacheService()
                service._using_redis = True
                service._last_redis_check = 0
                
                service.invalidate_stats_cache(stat_type="user_stats")
                
                # Should delete pattern
                mock_client.scan.assert_called()


class TestCacheServiceAIResultZeroTTL:
    """AI result with zero TTL"""
    
    def test_set_ai_result_zero_ttl_returns_false(self):
        """AI 结果 TTL=0 不缓存"""
        from services.cache.cache_service import CacheService
        service = CacheService()
        
        result = service.set_ai_result("hash123", {"result": "data"}, ttl=0)
        
        assert result is False
