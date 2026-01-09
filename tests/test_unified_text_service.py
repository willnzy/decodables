"""
Unified Text Service Tests
统一文本服务测试
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestUnifiedTextServiceChat:
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    async def test_successful_chat(self, mock_config, mock_enabled, mock_adapter, mock_track):
        from shared.ai.unified_text_service import unified_text_service
        from shared.ai.base import AIResponse, AIUsage
        
        mock_config.return_value = {"provider": "openai", "model": "gpt-4o-mini"}
        mock_enabled.return_value = True
        
        mock_adapter_instance = MagicMock()
        mock_adapter_instance.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Hello!",
            model="gpt-4o-mini",
            provider="openai",
            usage=AIUsage(input_tokens=10, output_tokens=5)
        ))
        mock_adapter.return_value = mock_adapter_instance
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hi"}],
            user_id="user_123",
            use_cache=False
        )
        
        assert response.success is True
        assert response.content == "Hello!"

    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_cached_result')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    async def test_cache_hit(self, mock_config, mock_cache):
        from shared.ai.unified_text_service import unified_text_service
        
        mock_config.return_value = {"provider": "openai", "model": "gpt-4o-mini"}
        mock_cache.return_value = "Cached response"
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hi"}],
            use_cache=True
        )
        
        assert response.success is True
        assert response.content == "Cached response"

    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_admin_model_config')
    async def test_admin_model(self, mock_config, mock_enabled, mock_adapter, mock_track):
        from shared.ai.unified_text_service import unified_text_service
        from shared.ai.base import AIResponse, AIUsage
        
        mock_config.return_value = {"provider": "openai", "model": "gpt-4o"}
        mock_enabled.return_value = True
        
        mock_adapter_instance = MagicMock()
        mock_adapter_instance.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Admin response",
            model="gpt-4o",
            provider="openai",
            usage=AIUsage()
        ))
        mock_adapter.return_value = mock_adapter_instance
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Analyze"}],
            use_admin_model=True,
            use_cache=False
        )
        
        assert response.success is True
        mock_config.assert_called_once()

    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.should_use_canary')
    @patch('shared.ai.unified_text_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    async def test_canary_model(self, mock_config, mock_enabled, mock_adapter, mock_track, mock_canary):
        from shared.ai.unified_text_service import unified_text_service
        from shared.ai.base import AIResponse, AIUsage
        
        mock_config.return_value = {"provider": "openai", "model": "gpt-4o-mini"}
        mock_enabled.return_value = True
        mock_canary.return_value = (True, {"provider": "qwen", "model": "qwen-plus"})
        
        mock_adapter_instance = MagicMock()
        mock_adapter_instance.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Canary response",
            model="qwen-plus",
            provider="qwen",
            usage=AIUsage()
        ))
        mock_adapter.return_value = mock_adapter_instance
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hi"}],
            user_id="user_123",
            tier="pro",
            use_cache=False
        )
        
        assert response.success is True
        mock_adapter.assert_called_with("qwen")

    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_fallback_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    async def test_provider_disabled_uses_fallback(self, mock_config, mock_enabled, mock_fallback):
        from shared.ai.unified_text_service import unified_text_service
        
        mock_config.return_value = {"provider": "disabled_provider", "model": "model"}
        mock_enabled.return_value = False
        mock_fallback.return_value = None
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hi"}],
            use_cache=False
        )
        
        assert response.success is False
        assert "not enabled" in response.error

    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    async def test_adapter_not_available(self, mock_config, mock_enabled, mock_adapter):
        from shared.ai.unified_text_service import unified_text_service
        
        mock_config.return_value = {"provider": "openai", "model": "gpt-4o-mini"}
        mock_enabled.return_value = True
        mock_adapter.return_value = None
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hi"}],
            use_cache=False
        )
        
        assert response.success is False


class TestTryFallback:
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_fallback_config')
    async def test_no_fallback_configured(self, mock_fallback):
        from shared.ai.unified_text_service import unified_text_service
        
        mock_fallback.return_value = None
        
        response = await unified_text_service._try_fallback(
            {"provider": "openai", "model": "gpt-4o"},
            [{"role": "user", "content": "Hi"}],
            0.7, None, None, None
        )
        
        assert response.success is False
        assert "No fallback" in response.error

    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.get_fallback_config')
    async def test_fallback_success(self, mock_fallback, mock_adapter, mock_track):
        from shared.ai.unified_text_service import unified_text_service
        from shared.ai.base import AIResponse, AIUsage
        
        mock_fallback.return_value = {"provider": "qwen", "model": "qwen-plus"}
        
        mock_adapter_instance = MagicMock()
        mock_adapter_instance.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Fallback response",
            model="qwen-plus",
            provider="qwen",
            usage=AIUsage()
        ))
        mock_adapter.return_value = mock_adapter_instance
        
        response = await unified_text_service._try_fallback(
            {"provider": "openai", "model": "gpt-4o"},
            [{"role": "user", "content": "Hi"}],
            0.7, None, None, None
        )
        
        assert response.success is True
        assert response.content == "Fallback response"

    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.get_fallback_config')
    async def test_fallback_adapter_not_available(self, mock_fallback, mock_adapter):
        from shared.ai.unified_text_service import unified_text_service
        
        mock_fallback.return_value = {"provider": "qwen", "model": "qwen-plus"}
        mock_adapter.return_value = None
        
        response = await unified_text_service._try_fallback(
            {"provider": "openai", "model": "gpt-4o"},
            [{"role": "user", "content": "Hi"}],
            0.7, None, None, None
        )
        
        assert response.success is False
        assert "Fallback adapter not available" in response.error


class TestConvenienceFunctions:
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.unified_text_service.chat')
    async def test_chat_function(self, mock_chat):
        from shared.ai.unified_text_service import chat
        from shared.ai.base import AIResponse
        
        mock_chat.return_value = AIResponse(success=True, content="Response")
        
        response = await chat(
            messages=[{"role": "user", "content": "Hi"}],
            user_id="user_123",
            tier="pro"
        )
        
        mock_chat.assert_called_once()
        assert response.success is True

    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.unified_text_service.chat')
    async def test_admin_chat_function(self, mock_chat):
        from shared.ai.unified_text_service import admin_chat
        from shared.ai.base import AIResponse
        
        mock_chat.return_value = AIResponse(success=True, content="Admin response")
        
        response = await admin_chat(
            messages=[{"role": "user", "content": "Analyze"}]
        )
        
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["use_admin_model"] is True
        assert call_kwargs["use_cache"] is False


class TestSingleton:
    def test_singleton_exists(self):
        from shared.ai.unified_text_service import unified_text_service
        assert unified_text_service is not None

    def test_singleton_is_instance(self):
        from shared.ai.unified_text_service import unified_text_service, UnifiedTextService
        assert isinstance(unified_text_service, UnifiedTextService)
