"""
AI Cache Tests
AI 缓存测试

核心业务规则:
1. 文本结果缓存 24 小时
2. 图像不缓存
3. 基于内容哈希的缓存键
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestAICacheTTL:
    def test_text_ttl_is_24_hours(self):
        from shared.ai.ai_cache import AI_CACHE_TTL
        assert AI_CACHE_TTL["text"] == 86400  # 24 hours

    def test_image_ttl_is_zero(self):
        from shared.ai.ai_cache import AI_CACHE_TTL
        assert AI_CACHE_TTL["image"] == 0


class TestGenerateCacheKey:
    def test_generates_hash(self):
        from shared.ai.ai_cache import generate_cache_key
        key = generate_cache_key("openai", "gpt-4o", "Hello", "text")
        assert len(key) == 16
        assert all(c in '0123456789abcdef' for c in key)

    def test_deterministic_same_input(self):
        from shared.ai.ai_cache import generate_cache_key
        key1 = generate_cache_key("openai", "gpt-4o", "Hello", "text")
        key2 = generate_cache_key("openai", "gpt-4o", "Hello", "text")
        assert key1 == key2

    def test_different_inputs_different_keys(self):
        from shared.ai.ai_cache import generate_cache_key
        key1 = generate_cache_key("openai", "gpt-4o", "Hello", "text")
        key2 = generate_cache_key("openai", "gpt-4o", "World", "text")
        assert key1 != key2

    def test_includes_relevant_kwargs(self):
        from shared.ai.ai_cache import generate_cache_key
        key1 = generate_cache_key("openai", "gpt-4o", "Hello", "text", temperature=0.3)
        key2 = generate_cache_key("openai", "gpt-4o", "Hello", "text", temperature=0.7)
        assert key1 != key2

    def test_ignores_irrelevant_kwargs(self):
        from shared.ai.ai_cache import generate_cache_key
        key1 = generate_cache_key("openai", "gpt-4o", "Hello", "text", user_id="123")
        key2 = generate_cache_key("openai", "gpt-4o", "Hello", "text", user_id="456")
        assert key1 == key2


class TestGetCachedResult:
    @patch('services.ai.ai_cache.cache_service')
    def test_returns_none_for_image(self, mock_cache):
        from shared.ai.ai_cache import get_cached_result
        result = get_cached_result("openai", "dall-e-3", "A cat", "image")
        assert result is None
        mock_cache.get_ai_result.assert_not_called()

    @patch('services.ai.ai_cache.AI_CACHE_TTL', {"text": 0, "image": 0})
    @patch('services.ai.ai_cache.cache_service')
    def test_returns_none_when_ttl_zero(self, mock_cache):
        from shared.ai.ai_cache import get_cached_result
        result = get_cached_result("openai", "gpt-4o", "Hello", "text")
        assert result is None

    @patch('services.ai.ai_cache.cache_service')
    def test_returns_cached_value_on_hit(self, mock_cache):
        from shared.ai.ai_cache import get_cached_result
        mock_cache.get_ai_result.return_value = "Cached response"
        result = get_cached_result("openai", "gpt-4o", "Hello", "text")
        assert result == "Cached response"

    @patch('services.ai.ai_cache.cache_service')
    def test_returns_none_on_miss(self, mock_cache):
        from shared.ai.ai_cache import get_cached_result
        mock_cache.get_ai_result.return_value = None
        result = get_cached_result("openai", "gpt-4o", "Hello", "text")
        assert result is None

    @patch('services.ai.ai_cache.cache_service')
    def test_handles_exception(self, mock_cache):
        from shared.ai.ai_cache import get_cached_result
        mock_cache.get_ai_result.side_effect = Exception("Cache error")
        result = get_cached_result("openai", "gpt-4o", "Hello", "text")
        assert result is None


class TestSetCachedResult:
    @patch('services.ai.ai_cache.cache_service')
    def test_returns_false_for_image(self, mock_cache):
        from shared.ai.ai_cache import set_cached_result
        result = set_cached_result("openai", "dall-e-3", "A cat", "image_url", "image")
        assert result is False
        mock_cache.set_ai_result.assert_not_called()

    @patch('services.ai.ai_cache.AI_CACHE_TTL', {"text": 0, "image": 0})
    @patch('services.ai.ai_cache.cache_service')
    def test_returns_false_when_ttl_zero(self, mock_cache):
        from shared.ai.ai_cache import set_cached_result
        result = set_cached_result("openai", "gpt-4o", "Hello", "Response", "text")
        assert result is False

    @patch('services.ai.ai_cache.cache_service')
    def test_sets_cache_successfully(self, mock_cache):
        from shared.ai.ai_cache import set_cached_result
        mock_cache.set_ai_result.return_value = True
        result = set_cached_result("openai", "gpt-4o", "Hello", "Response", "text")
        assert result is True
        mock_cache.set_ai_result.assert_called_once()

    @patch('services.ai.ai_cache.cache_service')
    def test_handles_exception(self, mock_cache):
        from shared.ai.ai_cache import set_cached_result
        mock_cache.set_ai_result.side_effect = Exception("Cache error")
        result = set_cached_result("openai", "gpt-4o", "Hello", "Response", "text")
        assert result is False


class TestInvalidateAICache:
    @patch('services.ai.ai_cache.cache_service')
    def test_invalidate_calls_delete_pattern(self, mock_cache):
        from shared.ai.ai_cache import invalidate_ai_cache
        invalidate_ai_cache()
        mock_cache.delete_pattern.assert_called_once()

    @patch('services.ai.ai_cache.cache_service')
    def test_handles_exception(self, mock_cache):
        from shared.ai.ai_cache import invalidate_ai_cache
        mock_cache.delete_pattern.side_effect = Exception("Error")
        # Should not raise
        invalidate_ai_cache()


class TestWithCache:
    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.set_cached_result')
    @patch('services.ai.ai_cache.get_cached_result')
    async def test_returns_cached_value_on_hit(self, mock_get, mock_set):
        from shared.ai.ai_cache import with_cache
        mock_get.return_value = "Cached response"
        mock_fetch = AsyncMock(return_value="Fresh response")
        
        result = await with_cache("openai", "gpt-4o", "Hello", "text", mock_fetch, use_cache=True)
        
        assert result == "Cached response"
        mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.set_cached_result')
    @patch('services.ai.ai_cache.get_cached_result')
    async def test_fetches_and_caches_on_miss(self, mock_get, mock_set):
        from shared.ai.ai_cache import with_cache
        mock_get.return_value = None
        mock_fetch = AsyncMock(return_value="Fresh response")
        
        result = await with_cache("openai", "gpt-4o", "Hello", "text", mock_fetch, use_cache=True)
        
        assert result == "Fresh response"
        mock_fetch.assert_called_once()
        mock_set.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.set_cached_result')
    @patch('services.ai.ai_cache.get_cached_result')
    async def test_skips_cache_when_disabled(self, mock_get, mock_set):
        from shared.ai.ai_cache import with_cache
        mock_fetch = AsyncMock(return_value="Fresh response")
        
        result = await with_cache("openai", "gpt-4o", "Hello", "text", mock_fetch, use_cache=False)
        
        assert result == "Fresh response"
        mock_get.assert_not_called()
        mock_set.assert_not_called()

    @pytest.mark.asyncio
    @patch('services.ai.ai_cache.set_cached_result')
    @patch('services.ai.ai_cache.get_cached_result')
    async def test_does_not_cache_empty_result(self, mock_get, mock_set):
        from shared.ai.ai_cache import with_cache
        mock_get.return_value = None
        mock_fetch = AsyncMock(return_value=None)
        
        result = await with_cache("openai", "gpt-4o", "Hello", "text", mock_fetch, use_cache=True)
        
        assert result is None
        mock_set.assert_not_called()
