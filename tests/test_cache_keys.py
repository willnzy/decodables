"""
Cache Keys Tests
缓存键命名测试

Coverage target: 90%+
"""

import pytest


class TestCacheNamespace:
    """Test CacheNamespace class"""
    
    def test_namespaces_have_prefix(self):
        """All namespaces start with md: prefix"""
        from services.cache.cache_keys import CacheNamespace, PREFIX
        
        assert CacheNamespace.CONFIG.startswith(PREFIX)
        assert CacheNamespace.EXPERIMENT.startswith(PREFIX)
        assert CacheNamespace.AI.startswith(PREFIX)
        assert CacheNamespace.RATE_LIMIT.startswith(PREFIX)
        assert CacheNamespace.STATS.startswith(PREFIX)
    
    def test_namespace_values(self):
        """Namespace values are correct"""
        from services.cache.cache_keys import CacheNamespace
        
        assert CacheNamespace.CONFIG == "md:config:"
        assert CacheNamespace.EXPERIMENT == "md:experiment:"
        assert CacheNamespace.AI == "md:ai:"
        assert CacheNamespace.RATE_LIMIT == "md:rl:"
        assert CacheNamespace.STATS == "md:stats:"


class TestCacheTTL:
    """Test CacheTTL class"""
    
    def test_ttl_values(self):
        """TTL values are defined"""
        from services.cache.cache_keys import CacheTTL
        
        assert CacheTTL.CONFIG == 60
        assert CacheTTL.EXPERIMENT == 60
        assert CacheTTL.AI_TEXT == 86400
        assert CacheTTL.AI_IMAGE == 0
        assert CacheTTL.STATS == 300
        assert CacheTTL.RATE_LIMIT == 60
    
    def test_ai_image_no_caching(self):
        """AI_IMAGE TTL is 0 (no caching)"""
        from services.cache.cache_keys import CacheTTL
        
        assert CacheTTL.AI_IMAGE == 0


class TestConfigKey:
    """Test config_key function"""
    
    def test_config_key_basic(self):
        """Basic config key generation"""
        from services.cache.cache_keys import config_key
        
        result = config_key("rate_limit.payment.checkout")
        
        assert result == "md:config:rate_limit.payment.checkout"
    
    def test_config_key_simple(self):
        """Simple config key"""
        from services.cache.cache_keys import config_key
        
        result = config_key("test")
        
        assert result == "md:config:test"


class TestConfigAllKey:
    """Test config_all_key function"""
    
    def test_config_all_key_no_group(self):
        """Config all key without group"""
        from services.cache.cache_keys import config_all_key
        
        result = config_all_key()
        
        assert result == "md:config:__all__"
    
    def test_config_all_key_with_group(self):
        """Config all key with group filter"""
        from services.cache.cache_keys import config_all_key
        
        result = config_all_key("rate_limit")
        
        assert result == "md:config:__all__:rate_limit"
    
    def test_config_all_key_with_none(self):
        """Config all key with None group"""
        from services.cache.cache_keys import config_all_key
        
        result = config_all_key(None)
        
        assert result == "md:config:__all__"


class TestExperimentKey:
    """Test experiment_key function"""
    
    def test_experiment_key_basic(self):
        """Basic experiment key"""
        from services.cache.cache_keys import experiment_key
        
        result = experiment_key("hero_button_test")
        
        assert result == "md:experiment:hero_button_test"
    
    def test_experiment_key_with_dashes(self):
        """Experiment key with dashes"""
        from services.cache.cache_keys import experiment_key
        
        result = experiment_key("pricing-page-v2")
        
        assert result == "md:experiment:pricing-page-v2"


class TestExperimentListKey:
    """Test experiment_list_key function"""
    
    def test_experiment_list_key_no_status(self):
        """Experiment list key without status"""
        from services.cache.cache_keys import experiment_list_key
        
        result = experiment_list_key()
        
        assert result == "md:experiment:__list__"
    
    def test_experiment_list_key_with_status(self):
        """Experiment list key with status filter"""
        from services.cache.cache_keys import experiment_list_key
        
        result = experiment_list_key("active")
        
        assert result == "md:experiment:__list__:active"
    
    def test_experiment_list_key_with_none(self):
        """Experiment list key with None status"""
        from services.cache.cache_keys import experiment_list_key
        
        result = experiment_list_key(None)
        
        assert result == "md:experiment:__list__"
    
    def test_experiment_list_key_completed(self):
        """Experiment list key with completed status"""
        from services.cache.cache_keys import experiment_list_key
        
        result = experiment_list_key("completed")
        
        assert result == "md:experiment:__list__:completed"


class TestAIResultKey:
    """Test ai_result_key function"""
    
    def test_ai_result_key(self):
        """AI result key generation"""
        from services.cache.cache_keys import ai_result_key
        
        result = ai_result_key("abc123def456")
        
        assert result == "md:ai:abc123def456"
    
    def test_ai_result_key_sha256(self):
        """AI result key with SHA256 hash"""
        from services.cache.cache_keys import ai_result_key
        
        hash_key = "a" * 64  # SHA256 length
        result = ai_result_key(hash_key)
        
        assert result == f"md:ai:{hash_key}"


class TestStatsKey:
    """Test stats_key function"""
    
    def test_stats_key_no_date(self):
        """Stats key without date"""
        from services.cache.cache_keys import stats_key
        
        result = stats_key("daily_users")
        
        assert result == "md:stats:daily_users"
    
    def test_stats_key_with_date(self):
        """Stats key with date"""
        from services.cache.cache_keys import stats_key
        
        result = stats_key("daily_users", "2024-01-06")
        
        assert result == "md:stats:daily_users:2024-01-06"
    
    def test_stats_key_with_none_date(self):
        """Stats key with None date"""
        from services.cache.cache_keys import stats_key
        
        result = stats_key("revenue", None)
        
        assert result == "md:stats:revenue"
    
    def test_stats_key_various_types(self):
        """Stats key with various stat types"""
        from services.cache.cache_keys import stats_key
        
        assert stats_key("active_users") == "md:stats:active_users"
        assert stats_key("revenue", "2024-01") == "md:stats:revenue:2024-01"
        assert stats_key("conversions", "2024-01-06") == "md:stats:conversions:2024-01-06"


class TestRateLimitKey:
    """Test rate_limit_key function"""
    
    def test_rate_limit_key_ip(self):
        """Rate limit key with IP"""
        from services.cache.cache_keys import rate_limit_key
        
        result = rate_limit_key("192.168.1.1", "generate.story")
        
        assert result == "md:rl:generate.story:192.168.1.1"
    
    def test_rate_limit_key_user_id(self):
        """Rate limit key with user ID"""
        from services.cache.cache_keys import rate_limit_key
        
        result = rate_limit_key("user_abc123", "payment.checkout")
        
        assert result == "md:rl:payment.checkout:user_abc123"
    
    def test_rate_limit_key_format(self):
        """Rate limit key format is endpoint:identifier"""
        from services.cache.cache_keys import rate_limit_key
        
        result = rate_limit_key("test-id", "api.endpoint")
        
        # Format should be namespace + endpoint + identifier
        assert result.startswith("md:rl:")
        assert "api.endpoint" in result
        assert "test-id" in result


class TestGlobalPrefix:
    """Test global PREFIX constant"""
    
    def test_prefix_value(self):
        """PREFIX is md:"""
        from services.cache.cache_keys import PREFIX
        
        assert PREFIX == "md:"
    
    def test_prefix_used_in_all_keys(self):
        """All key functions use the prefix"""
        from services.cache.cache_keys import (
            config_key, config_all_key, experiment_key, 
            experiment_list_key, ai_result_key, stats_key, 
            rate_limit_key, PREFIX
        )
        
        assert config_key("test").startswith(PREFIX)
        assert config_all_key().startswith(PREFIX)
        assert experiment_key("test").startswith(PREFIX)
        assert experiment_list_key().startswith(PREFIX)
        assert ai_result_key("test").startswith(PREFIX)
        assert stats_key("test").startswith(PREFIX)
        assert rate_limit_key("id", "endpoint").startswith(PREFIX)
