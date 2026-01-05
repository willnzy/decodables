"""
Tests for AI Cache Service
AI 缓存服务测试

Tests for:
- generate_cache_key: Cache key generation
- get_cached_result: Cache retrieval
- set_cached_result: Cache storage
- invalidate_ai_cache: Cache invalidation
- with_cache: Async cache wrapper
"""

import pytest
import hashlib
import json
from unittest.mock import MagicMock, patch, AsyncMock


class TestGenerateCacheKey:
    """Tests for generate_cache_key function."""
    
    def test_basic_key_generation(self):
        """Test basic cache key generation."""
        from services.ai.ai_cache import generate_cache_key
        
        key = generate_cache_key(
            provider="openai",
            model="gpt-4",
            prompt="Hello world",
            call_type="text"
        )
        
        assert isinstance(key, str)
        assert len(key) == 16  # SHA256 truncated to 16 chars
    
    def test_same_params_same_key(self):
        """Test that same parameters produce same key."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text")
        key2 = generate_cache_key("openai", "gpt-4", "Hello", "text")
        
        assert key1 == key2
    
    def test_different_provider_different_key(self):
        """Test that different providers produce different keys."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text")
        key2 = generate_cache_key("anthropic", "gpt-4", "Hello", "text")
        
        assert key1 != key2
    
    def test_different_model_different_key(self):
        """Test that different models produce different keys."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text")
        key2 = generate_cache_key("openai", "gpt-3.5-turbo", "Hello", "text")
        
        assert key1 != key2
    
    def test_different_prompt_different_key(self):
        """Test that different prompts produce different keys."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text")
        key2 = generate_cache_key("openai", "gpt-4", "Goodbye", "text")
        
        assert key1 != key2
    
    def test_different_call_type_different_key(self):
        """Test that different call types produce different keys."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text")
        key2 = generate_cache_key("openai", "gpt-4", "Hello", "image")
        
        assert key1 != key2
    
    def test_with_temperature(self):
        """Test that temperature affects the key."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text", temperature=0.7)
        key2 = generate_cache_key("openai", "gpt-4", "Hello", "text", temperature=0.9)
        key3 = generate_cache_key("openai", "gpt-4", "Hello", "text")
        
        assert key1 != key2
        assert key1 != key3
    
    def test_with_max_tokens(self):
        """Test that max_tokens affects the key."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text", max_tokens=100)
        key2 = generate_cache_key("openai", "gpt-4", "Hello", "text", max_tokens=200)
        
        assert key1 != key2
    
    def test_with_response_format(self):
        """Test that response_format affects the key."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text", response_format="json")
        key2 = generate_cache_key("openai", "gpt-4", "Hello", "text", response_format="text")
        
        assert key1 != key2
    
    def test_irrelevant_kwargs_ignored(self):
        """Test that irrelevant kwargs don't affect the key."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text")
        key2 = generate_cache_key("openai", "gpt-4", "Hello", "text", user_id="123")
        key3 = generate_cache_key("openai", "gpt-4", "Hello", "text", random_param="value")
        
        assert key1 == key2
        assert key1 == key3
    
    def test_none_kwargs_ignored(self):
        """Test that None kwargs don't affect the key."""
        from services.ai.ai_cache import generate_cache_key
        
        key1 = generate_cache_key("openai", "gpt-4", "Hello", "text")
        key2 = generate_cache_key("openai", "gpt-4", "Hello", "text", temperature=None)
        key3 = generate_cache_key("openai", "gpt-4", "Hello", "text", max_tokens=None)
        
        assert key1 == key2
        assert key1 == key3


class TestGetCachedResult:
    """Tests for get_cached_result function."""
    
    def test_image_type_returns_none(self):
        """Test that image call type always returns None (no caching)."""
        from services.ai.ai_cache import get_cached_result
        
        result = get_cached_result(
            provider="fal",
            model="flux",
            prompt="a cat",
            call_type="image"
        )
        
        assert result is None
    
    def test_unknown_call_type_returns_none(self):
        """Test that unknown call type with TTL 0 returns None."""
        from services.ai.ai_cache import get_cached_result
        
        result = get_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="unknown_type"
        )
        
        assert result is None
    
    @patch('services.ai.ai_cache.cache_service')
    def test_cache_hit(self, mock_cache):
        """Test cache hit returns cached value."""
        from services.ai.ai_cache import get_cached_result
        
        mock_cache.get_ai_result.return_value = "cached response"
        
        result = get_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text"
        )
        
        assert result == "cached response"
        mock_cache.get_ai_result.assert_called_once()
    
    @patch('services.ai.ai_cache.cache_service')
    def test_cache_miss(self, mock_cache):
        """Test cache miss returns None."""
        from services.ai.ai_cache import get_cached_result
        
        mock_cache.get_ai_result.return_value = None
        
        result = get_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text"
        )
        
        assert result is None
        mock_cache.get_ai_result.assert_called_once()
    
    @patch('services.ai.ai_cache.cache_service')
    def test_cache_exception_returns_none(self, mock_cache):
        """Test that cache exception returns None gracefully."""
        from services.ai.ai_cache import get_cached_result
        
        mock_cache.get_ai_result.side_effect = Exception("Redis connection error")
        
        result = get_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text"
        )
        
        assert result is None
    
    @patch('services.ai.ai_cache.cache_service')
    def test_with_kwargs(self, mock_cache):
        """Test that kwargs are passed through for key generation."""
        from services.ai.ai_cache import get_cached_result
        
        mock_cache.get_ai_result.return_value = "response"
        
        result = get_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text",
            temperature=0.7
        )
        
        assert result == "response"


class TestSetCachedResult:
    """Tests for set_cached_result function."""
    
    def test_image_type_returns_false(self):
        """Test that image call type returns False (no caching)."""
        from services.ai.ai_cache import set_cached_result
        
        result = set_cached_result(
            provider="fal",
            model="flux",
            prompt="a cat",
            result="image_url",
            call_type="image"
        )
        
        assert result is False
    
    def test_unknown_call_type_returns_false(self):
        """Test that unknown call type with TTL 0 returns False."""
        from services.ai.ai_cache import set_cached_result
        
        result = set_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            result="response",
            call_type="unknown_type"
        )
        
        assert result is False
    
    @patch('services.ai.ai_cache.cache_service')
    def test_successful_cache_set(self, mock_cache):
        """Test successful cache set returns True."""
        from services.ai.ai_cache import set_cached_result
        
        mock_cache.set_ai_result.return_value = True
        
        result = set_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            result="AI response",
            call_type="text"
        )
        
        assert result is True
        mock_cache.set_ai_result.assert_called_once()
    
    @patch('services.ai.ai_cache.cache_service')
    def test_failed_cache_set(self, mock_cache):
        """Test failed cache set returns False."""
        from services.ai.ai_cache import set_cached_result
        
        mock_cache.set_ai_result.return_value = False
        
        result = set_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            result="AI response",
            call_type="text"
        )
        
        assert result is False
    
    @patch('services.ai.ai_cache.cache_service')
    def test_cache_exception_returns_false(self, mock_cache):
        """Test that cache exception returns False gracefully."""
        from services.ai.ai_cache import set_cached_result
        
        mock_cache.set_ai_result.side_effect = Exception("Redis connection error")
        
        result = set_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            result="AI response",
            call_type="text"
        )
        
        assert result is False
    
    @patch('services.ai.ai_cache.cache_service')
    def test_with_kwargs(self, mock_cache):
        """Test that kwargs are passed through for key generation."""
        from services.ai.ai_cache import set_cached_result
        
        mock_cache.set_ai_result.return_value = True
        
        result = set_cached_result(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            result="AI response",
            call_type="text",
            temperature=0.7,
            max_tokens=100
        )
        
        assert result is True


class TestInvalidateAICache:
    """Tests for invalidate_ai_cache function."""
    
    @patch('services.ai.ai_cache.cache_service')
    def test_successful_invalidation(self, mock_cache):
        """Test successful cache invalidation."""
        from services.ai.ai_cache import invalidate_ai_cache
        
        mock_cache.delete_pattern.return_value = True
        
        # Should not raise
        invalidate_ai_cache()
        
        mock_cache.delete_pattern.assert_called_once()
        # Check that the pattern contains the AI namespace
        call_args = mock_cache.delete_pattern.call_args[0][0]
        assert "ai:" in call_args.lower() or "md:ai" in call_args.lower()
    
    @patch('services.ai.ai_cache.cache_service')
    def test_invalidation_with_exception(self, mock_cache):
        """Test that invalidation handles exceptions gracefully."""
        from services.ai.ai_cache import invalidate_ai_cache
        
        mock_cache.delete_pattern.side_effect = Exception("Redis error")
        
        # Should not raise
        invalidate_ai_cache()


class TestWithCache:
    """Tests for with_cache async wrapper function."""
    
    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.get_cached_result')
    @patch('services.ai.ai_cache.set_cached_result')
    async def test_cache_hit_returns_cached(self, mock_set, mock_get):
        """Test that cache hit returns cached value without calling fetch_func."""
        from services.ai.ai_cache import with_cache
        
        mock_get.return_value = "cached response"
        mock_fetch = AsyncMock(return_value="fresh response")
        
        result = await with_cache(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text",
            fetch_func=mock_fetch,
            use_cache=True
        )
        
        assert result == "cached response"
        mock_get.assert_called_once()
        mock_fetch.assert_not_called()  # Should not call fetch on cache hit
        mock_set.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.get_cached_result')
    @patch('services.ai.ai_cache.set_cached_result')
    async def test_cache_miss_fetches_and_caches(self, mock_set, mock_get):
        """Test that cache miss fetches result and caches it."""
        from services.ai.ai_cache import with_cache
        
        mock_get.return_value = None  # Cache miss
        mock_fetch = AsyncMock(return_value="fresh response")
        
        result = await with_cache(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text",
            fetch_func=mock_fetch,
            use_cache=True
        )
        
        assert result == "fresh response"
        mock_get.assert_called_once()
        mock_fetch.assert_called_once()
        mock_set.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.get_cached_result')
    @patch('services.ai.ai_cache.set_cached_result')
    async def test_use_cache_false_bypasses_cache(self, mock_set, mock_get):
        """Test that use_cache=False bypasses cache completely."""
        from services.ai.ai_cache import with_cache
        
        mock_fetch = AsyncMock(return_value="fresh response")
        
        result = await with_cache(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text",
            fetch_func=mock_fetch,
            use_cache=False
        )
        
        assert result == "fresh response"
        mock_get.assert_not_called()  # Should not check cache
        mock_fetch.assert_called_once()
        mock_set.assert_not_called()  # Should not set cache
    
    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.get_cached_result')
    @patch('services.ai.ai_cache.set_cached_result')
    async def test_empty_result_not_cached(self, mock_set, mock_get):
        """Test that empty/None result is not cached."""
        from services.ai.ai_cache import with_cache
        
        mock_get.return_value = None
        mock_fetch = AsyncMock(return_value=None)
        
        result = await with_cache(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text",
            fetch_func=mock_fetch,
            use_cache=True
        )
        
        assert result is None
        mock_fetch.assert_called_once()
        mock_set.assert_not_called()  # Should not cache None result
    
    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.get_cached_result')
    @patch('services.ai.ai_cache.set_cached_result')
    async def test_empty_string_not_cached(self, mock_set, mock_get):
        """Test that empty string result is not cached."""
        from services.ai.ai_cache import with_cache
        
        mock_get.return_value = None
        mock_fetch = AsyncMock(return_value="")
        
        result = await with_cache(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text",
            fetch_func=mock_fetch,
            use_cache=True
        )
        
        assert result == ""
        mock_fetch.assert_called_once()
        mock_set.assert_not_called()  # Empty string is falsy
    
    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.get_cached_result')
    @patch('services.ai.ai_cache.set_cached_result')
    async def test_kwargs_passed_to_fetch_func(self, mock_set, mock_get):
        """Test that kwargs are passed to fetch_func."""
        from services.ai.ai_cache import with_cache
        
        mock_get.return_value = None
        mock_fetch = AsyncMock(return_value="response")
        
        result = await with_cache(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text",
            fetch_func=mock_fetch,
            use_cache=True,
            temperature=0.7,
            max_tokens=100,
            custom_param="value"
        )
        
        mock_fetch.assert_called_once_with(
            temperature=0.7,
            max_tokens=100,
            custom_param="value"
        )
    
    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.get_cached_result')
    @patch('services.ai.ai_cache.set_cached_result')
    async def test_kwargs_used_for_cache_key(self, mock_set, mock_get):
        """Test that relevant kwargs are used for cache key generation."""
        from services.ai.ai_cache import with_cache
        
        mock_get.return_value = None
        mock_fetch = AsyncMock(return_value="response")
        
        await with_cache(
            provider="openai",
            model="gpt-4",
            prompt="Hello",
            call_type="text",
            fetch_func=mock_fetch,
            use_cache=True,
            temperature=0.7
        )
        
        # Verify get_cached_result was called with temperature
        mock_get.assert_called_once_with(
            "openai", "gpt-4", "Hello", "text",
            temperature=0.7
        )


class TestAICacheTTLConfiguration:
    """Tests for AI Cache TTL configuration."""
    
    def test_text_ttl_is_positive(self):
        """Test that text TTL is positive (caching enabled)."""
        from services.ai.ai_cache import AI_CACHE_TTL
        
        assert AI_CACHE_TTL["text"] > 0
    
    def test_image_ttl_is_zero(self):
        """Test that image TTL is zero (no caching)."""
        from services.ai.ai_cache import AI_CACHE_TTL
        
        assert AI_CACHE_TTL["image"] == 0


class TestCacheKeyDeterminism:
    """Tests for cache key determinism."""
    
    def test_key_is_deterministic(self):
        """Test that cache key generation is deterministic."""
        from services.ai.ai_cache import generate_cache_key
        
        params = {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": "Test prompt",
            "call_type": "text",
            "temperature": 0.7,
        }
        
        keys = [generate_cache_key(**params) for _ in range(10)]
        
        assert all(k == keys[0] for k in keys)
    
    def test_key_format_is_hex(self):
        """Test that cache key is a valid hex string."""
        from services.ai.ai_cache import generate_cache_key
        
        key = generate_cache_key("openai", "gpt-4", "test", "text")
        
        # Should be valid hex (only 0-9, a-f)
        assert all(c in '0123456789abcdef' for c in key)


class TestCacheIntegration:
    """Integration tests for cache functions working together."""
    
    @patch('services.ai.ai_cache.cache_service')
    def test_set_then_get_same_key(self, mock_cache):
        """Test that set and get use the same cache key."""
        from services.ai.ai_cache import set_cached_result, get_cached_result, generate_cache_key
        
        params = {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": "Hello",
            "call_type": "text",
        }
        
        # Expected key
        expected_key = generate_cache_key(**params)
        
        # Set
        mock_cache.set_ai_result.return_value = True
        set_cached_result(**params, result="response")
        set_key = mock_cache.set_ai_result.call_args[0][0]
        
        # Get
        mock_cache.get_ai_result.return_value = "response"
        get_cached_result(**params)
        get_key = mock_cache.get_ai_result.call_args[0][0]
        
        # Keys should match
        assert set_key == get_key == expected_key
