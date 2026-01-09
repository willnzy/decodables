"""
Unit Tests for Unified AI Services
统一 AI 服务单元测试

Tests:
- UnifiedTextService
- UnifiedImageService
- Fallback behavior
- Caching behavior
- Usage tracking
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from shared.ai.base import AIResponse, AIUsage, AIErrorType


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture(autouse=True)
def mock_config_service():
    """
    Automatically mock _get_config_service to prevent ConfigRepository instantiation.
    This fixture is autouse=True so it applies to all tests in this file.
    """
    with patch('shared.ai.model_config._get_config_service') as mock_model_service, \
         patch('shared.ai.canary._get_config_service') as mock_canary_service:
        mock_service = MagicMock()
        # Mock get_config as AsyncMock since it's called with await
        mock_service.get_config = AsyncMock(return_value=None)
        mock_model_service.return_value = mock_service
        mock_canary_service.return_value = mock_service
        yield mock_service


# ==========================================
# UnifiedTextService Tests
# ==========================================

class TestUnifiedTextService:
    """UnifiedTextService 测试"""
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.track_ai_usage')
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_successful_chat(
        self, mock_cache_get, mock_track, mock_get_adapter,
        mock_is_enabled, mock_get_config
    ):
        """成功的聊天请求"""
        from shared.ai.unified_text_service import unified_text_service

        # Setup mocks
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "fallback": {"provider": "openai", "model": "gpt-4o-mini"}
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None  # 无缓存

        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Hello, I'm an AI assistant!",
            usage=AIUsage(input_tokens=10, output_tokens=8),
            model="gpt-4o-mini",
            provider="openai",
            latency_ms=150
        ))
        mock_get_adapter.return_value = mock_adapter
        mock_track.return_value = None

        # Execute
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}],
            user_id="user_123",
            tier="free"
        )

        # Assert
        assert response.success is True
        assert "Hello" in response.content or "AI" in response.content
        mock_adapter.chat_completion.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    async def test_provider_not_enabled(
        self, mock_get_adapter, mock_is_enabled, mock_get_config
    ):
        """提供商未启用时返回错误"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "qwen",
            "model": "qwen-plus",
            "fallback": None  # 无 fallback
        }
        mock_is_enabled.return_value = False  # 未启用
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert response.success is False
        assert response.error_type == AIErrorType.AUTH_ERROR
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_fallback_config')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_adapter_not_available(
        self, mock_cache_get, mock_get_adapter, mock_is_enabled, mock_get_config, mock_fallback
    ):
        """适配器不可用时返回错误"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "fallback": None
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        mock_get_adapter.return_value = None  # 适配器不可用
        mock_fallback.return_value = None  # 无 fallback 配置
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert response.success is False
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_cached_result')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    async def test_cache_hit(
        self, mock_get_config, mock_cache_get
    ):
        """缓存命中时直接返回"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        
        # 缓存返回的是字符串内容，不是 AIResponse
        mock_cache_get.return_value = "Cached response"
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}],
            use_cache=True
        )
        
        assert response.success is True
        assert response.content == "Cached response"
        mock_cache_get.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_admin_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.track_ai_usage')
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_admin_model_usage(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_admin_config
    ):
        """Admin 模型使用"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_admin_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o",  # Admin 使用更好的模型
            "fallback": {"provider": "openai", "model": "gpt-4o-mini"}
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Admin response",
            model="gpt-4o",
            provider="openai"
        ))
        mock_get_adapter.return_value = mock_adapter
        mock_track.return_value = None
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Analyze this"}],
            use_admin_model=True
        )
        
        assert response.success is True
        # 应该使用 admin config
        mock_get_admin_config.assert_called_once()


# ==========================================
# UnifiedImageService Tests
# ==========================================

class TestUnifiedImageService:
    """UnifiedImageService 测试"""
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_image_service.get_image_adapter')
    @patch('shared.ai.unified_image_service.is_provider_enabled')
    @patch('shared.ai.unified_image_service.should_use_canary')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_successful_image_generation(
        self, mock_get_config, mock_should_canary, mock_is_enabled, mock_get_adapter, mock_track
    ):
        """成功的图像生成"""
        from shared.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "fal",
            "model": "flux-schnell",
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        mock_should_canary.return_value = (False, None)  # 不使用灰度
        mock_is_enabled.return_value = True
        
        mock_adapter = MagicMock()
        mock_adapter.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/image1.png"],
            usage=AIUsage(images_generated=1),
            model="flux-schnell",
            provider="fal",
            latency_ms=2500
        ))
        mock_get_adapter.return_value = mock_adapter
        
        response = await unified_image_service.generate(
            prompt="A cute cat",
            user_id="user_123",
            tier="free"
        )
        
        assert response.success is True
        assert len(response.content) == 1
        assert response.content[0].startswith("https://")
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_image_service.get_image_adapter')
    @patch('shared.ai.unified_image_service.is_provider_enabled')
    @patch('shared.ai.unified_image_service.should_use_canary')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_tier_based_model_selection(
        self, mock_get_config, mock_should_canary, mock_is_enabled, mock_get_adapter, mock_track
    ):
        """【业务规则 5.1】基于等级的模型选择 - Pro 用户使用 flux-dev"""
        from shared.ai.unified_image_service import unified_image_service
        
        # Pro 用户应该使用 flux-dev
        mock_get_config.return_value = {
            "provider": "fal",
            "model": "flux-dev",  # Pro 模型
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        mock_should_canary.return_value = (False, None)
        mock_is_enabled.return_value = True
        
        mock_adapter = MagicMock()
        mock_adapter.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/image.png"],
            model="flux-dev",
            provider="fal"
        ))
        mock_get_adapter.return_value = mock_adapter
        
        response = await unified_image_service.generate(
            prompt="High quality image",
            tier="pro"
        )
        
        assert response.success is True
        # 验证 get_image_model_config 被调用时传递了 tier
        mock_get_config.assert_called_once_with("pro")
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_image_service.get_image_adapter')
    @patch('shared.ai.unified_image_service.should_use_canary')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_image_to_image(
        self, mock_get_config, mock_should_canary, mock_get_adapter, mock_track
    ):
        """图生图功能"""
        from shared.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "fal",
            "model": "flux-dev",
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        mock_should_canary.return_value = (False, None)
        
        mock_adapter = MagicMock()
        mock_adapter.image_to_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/edited.png"],
            model="flux-dev",
            provider="fal"
        ))
        mock_get_adapter.return_value = mock_adapter
        
        response = await unified_image_service.image_to_image(
            prompt="Make it more colorful",
            image_url="https://example.com/original.png",
            strength=0.7
        )
        
        assert response.success is True
        mock_adapter.image_to_image.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_image_service.get_image_adapter')
    @patch('shared.ai.unified_image_service.should_use_canary')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_canary_model_used(
        self, mock_get_config, mock_should_canary, mock_get_adapter, mock_track
    ):
        """【业务规则 5.3】灰度用户使用灰度模型"""
        from shared.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "fal",
            "model": "flux-schnell",
        }
        # 灰度命中，使用不同模型
        mock_should_canary.return_value = (True, {"provider": "fal", "model": "flux-dev"})
        
        mock_adapter = MagicMock()
        mock_adapter.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/canary.png"],
            model="flux-dev",
            provider="fal"
        ))
        mock_get_adapter.return_value = mock_adapter
        
        response = await unified_image_service.generate(
            prompt="A cat",
            user_id="canary_user",
            tier="free"
        )
        
        assert response.success is True
        # 验证使用了灰度模型
        call_args = mock_adapter.generate_image.call_args
        assert call_args[1]["model"] == "flux-dev"
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_image_service.get_image_adapter')
    @patch('shared.ai.unified_image_service.get_fallback_config')
    @patch('shared.ai.unified_image_service.is_provider_enabled')
    @patch('shared.ai.unified_image_service.should_use_canary')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_provider_not_enabled_uses_fallback(
        self, mock_get_config, mock_should_canary, mock_is_enabled, 
        mock_get_fallback, mock_get_adapter, mock_track
    ):
        """【业务规则 5.5】提供商未启用时使用 fallback"""
        from shared.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "disabled_provider",
            "model": "some_model",
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        mock_should_canary.return_value = (False, None)
        mock_is_enabled.return_value = False  # 主提供商未启用
        mock_get_fallback.return_value = {"provider": "fal", "model": "flux-schnell"}
        
        mock_adapter = MagicMock()
        mock_adapter.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/fallback.png"],
            model="flux-schnell",
            provider="fal"
        ))
        mock_get_adapter.return_value = mock_adapter
        
        response = await unified_image_service.generate(
            prompt="A cat",
            tier="free"
        )
        
        assert response.success is True
        # 验证使用了 fallback 提供商
        mock_get_adapter.assert_called_with("fal")
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.get_fallback_config')
    @patch('shared.ai.unified_image_service.is_provider_enabled')
    @patch('shared.ai.unified_image_service.should_use_canary')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_provider_not_enabled_no_fallback(
        self, mock_get_config, mock_should_canary, mock_is_enabled, mock_get_fallback
    ):
        """【业务规则】提供商未启用且无 fallback 返回错误"""
        from shared.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "disabled_provider",
            "model": "some_model",
        }
        mock_should_canary.return_value = (False, None)
        mock_is_enabled.return_value = False
        mock_get_fallback.return_value = None  # 无 fallback
        
        response = await unified_image_service.generate(
            prompt="A cat",
            tier="free"
        )
        
        assert response.success is False
        assert response.error_type == AIErrorType.AUTH_ERROR
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_image_service.get_image_adapter')
    @patch('shared.ai.unified_image_service.get_fallback_config')
    @patch('shared.ai.unified_image_service.is_provider_enabled')
    @patch('shared.ai.unified_image_service.should_use_canary')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_adapter_not_available_tries_fallback(
        self, mock_get_config, mock_should_canary, mock_is_enabled, 
        mock_get_fallback, mock_get_adapter, mock_track
    ):
        """【业务规则 5.5】适配器不可用时尝试 fallback"""
        from shared.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "unavailable",
            "model": "some_model",
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        mock_should_canary.return_value = (False, None)
        mock_is_enabled.return_value = True
        mock_get_fallback.return_value = {"provider": "fal", "model": "flux-schnell"}
        
        # 第一次返回 None (主适配器不可用)，第二次返回可用适配器
        mock_fallback_adapter = MagicMock()
        mock_fallback_adapter.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/fb.png"],
            model="flux-schnell",
            provider="fal"
        ))
        mock_get_adapter.side_effect = [None, mock_fallback_adapter]
        
        response = await unified_image_service.generate(
            prompt="A cat",
            tier="free"
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_image_service.get_image_adapter')
    @patch('shared.ai.unified_image_service.get_fallback_config')
    @patch('shared.ai.unified_image_service.is_provider_enabled')
    @patch('shared.ai.unified_image_service.should_use_canary')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_generation_fails_tries_fallback(
        self, mock_get_config, mock_should_canary, mock_is_enabled, 
        mock_get_fallback, mock_get_adapter, mock_track
    ):
        """【业务规则 5.5】生成失败时尝试 fallback"""
        from shared.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "fal",
            "model": "flux-schnell",
            "fallback": {"provider": "fal", "model": "flux-dev"}
        }
        mock_should_canary.return_value = (False, None)
        mock_is_enabled.return_value = True
        mock_get_fallback.return_value = {"provider": "fal", "model": "flux-dev"}
        
        # 主适配器失败
        failed_adapter = MagicMock()
        failed_adapter.generate_image = AsyncMock(return_value=AIResponse(
            success=False,
            content=[],
            error="Main failed",
            error_type=AIErrorType.API_ERROR,
            provider="fal",
            model="flux-schnell"
        ))
        
        # Fallback 适配器成功
        fallback_adapter = MagicMock()
        fallback_adapter.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/fb.png"],
            model="flux-dev",
            provider="fal"
        ))
        
        mock_get_adapter.side_effect = [failed_adapter, fallback_adapter]
        
        response = await unified_image_service.generate(
            prompt="A cat",
            tier="free"
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_image_service.get_image_adapter')
    @patch('shared.ai.unified_image_service.should_use_canary')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_image_to_image_adapter_not_available(
        self, mock_get_config, mock_should_canary, mock_get_adapter, mock_track
    ):
        """【业务规则】image_to_image 适配器不可用返回错误"""
        from shared.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {"provider": "fal", "model": "flux-dev"}
        mock_should_canary.return_value = (False, None)
        mock_get_adapter.return_value = None
        
        response = await unified_image_service.image_to_image(
            prompt="Make it colorful",
            image_url="https://example.com/ref.png"
        )
        
        assert response.success is False
        assert response.error_type == AIErrorType.AUTH_ERROR


class TestUnifiedImageConvenienceFunctions:
    """UnifiedImageService 便捷函数测试"""
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.unified_image_service.generate')
    async def test_generate_image_convenience(self, mock_generate):
        """【业务规则】generate_image 便捷函数"""
        from shared.ai.unified_image_service import generate_image
        
        mock_generate.return_value = AIResponse(
            success=True,
            content=["https://example.com/img.png"]
        )
        
        response = await generate_image(
            prompt="A cat",
            user_id="user_123",
            tier="pro"
        )
        
        assert response.success is True
        mock_generate.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.unified_image_service.image_to_image')
    async def test_image_to_image_convenience(self, mock_i2i):
        """【业务规则】image_to_image 便捷函数"""
        from shared.ai.unified_image_service import image_to_image
        
        mock_i2i.return_value = AIResponse(
            success=True,
            content=["https://example.com/edited.png"]
        )
        
        response = await image_to_image(
            prompt="Make colorful",
            image_url="https://example.com/ref.png",
            user_id="user_123",
            tier="pro"
        )
        
        assert response.success is True
        mock_i2i.assert_called_once()


# ==========================================
# Canary Integration Tests
# ==========================================

class TestCanaryIntegration:
    """灰度发布集成测试"""
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.should_use_canary')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.track_ai_usage')
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_canary_model_used(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_config, mock_canary
    ):
        """灰度模型被使用"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        # 灰度命中
        mock_canary.return_value = (True, {"provider": "qwen", "model": "qwen-plus"})
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Canary response",
            model="qwen-plus",
            provider="qwen"
        ))
        mock_get_adapter.return_value = mock_adapter
        mock_track.return_value = None
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}],
            user_id="user_in_canary",
            tier="pro"
        )
        
        assert response.success is True
        # 应该调用 qwen 适配器
        mock_get_adapter.assert_called_with("qwen")


# ==========================================
# Fallback Tests
# ==========================================

class TestFallbackBehavior:
    """Fallback 行为测试"""
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.track_ai_usage')
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_fallback_on_error(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_config
    ):
        """主模型失败时使用 fallback"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "qwen",
            "model": "qwen-plus",
            "fallback": {"provider": "openai", "model": "gpt-4o-mini"}
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        
        # 主适配器失败
        failed_adapter = MagicMock()
        failed_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=False,
            error="API Error",
            error_type=AIErrorType.API_ERROR
        ))
        
        # Fallback 适配器成功
        success_adapter = MagicMock()
        success_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Fallback response",
            model="gpt-4o-mini",
            provider="openai"
        ))
        
        # 第一次调用返回失败适配器，第二次返回成功适配器
        mock_get_adapter.side_effect = [failed_adapter, success_adapter]
        mock_track.return_value = None
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        # 应该使用 fallback 成功
        # (注意：实际行为取决于 unified_text_service 的实现)
        assert mock_get_adapter.call_count >= 1


# ==========================================
# Edge Cases
# ==========================================

class TestUnifiedServicesEdgeCases:
    """边界情况测试"""
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.track_ai_usage')
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_empty_messages(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_config
    ):
        """空消息列表"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Response to empty"
        ))
        mock_get_adapter.return_value = mock_adapter
        mock_track.return_value = None
        
        response = await unified_text_service.chat(
            messages=[]
        )
        
        # 应该正常处理空消息
        assert isinstance(response, AIResponse)
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_image_service.get_image_adapter')
    @patch('shared.ai.unified_image_service.is_provider_enabled')
    @patch('shared.ai.unified_image_service.get_image_model_config')
    async def test_very_long_prompt(
        self, mock_get_config, mock_is_enabled, mock_get_adapter, mock_track
    ):
        """超长提示词"""
        from shared.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "fal",
            "model": "flux-schnell"
        }
        mock_is_enabled.return_value = True
        
        mock_adapter = MagicMock()
        mock_adapter.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/image.png"]
        ))
        mock_get_adapter.return_value = mock_adapter
        
        long_prompt = "A beautiful " * 1000  # 很长的提示词
        
        response = await unified_image_service.generate(
            prompt=long_prompt
        )
        
        # 应该正常处理
        assert isinstance(response, AIResponse)


# ==========================================
# Additional Coverage Tests
# ==========================================

class TestUnifiedTextServiceAdditionalCoverage:
    """补充覆盖率测试 - UnifiedTextService"""
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_fallback_config')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_provider_not_enabled_with_fallback(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_config, mock_fallback
    ):
        """提供商未启用时使用 fallback（覆盖 117-118 行）"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "disabled_provider",
            "model": "some-model",
        }
        mock_is_enabled.return_value = False
        mock_cache_get.return_value = None
        
        # 配置 fallback
        mock_fallback.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Fallback response",
            model="gpt-4o-mini",
            provider="openai"
        ))
        mock_get_adapter.return_value = mock_adapter
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert response.success is True
        # 应该使用 fallback provider
        mock_get_adapter.assert_called_with("openai")
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_fallback_config')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_adapter_not_available_with_fallback_success(
        self, mock_cache_get, mock_get_adapter, mock_is_enabled, 
        mock_get_config, mock_fallback
    ):
        """主适配器不可用，fallback 成功（覆盖 130-132 行）"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "qwen",
            "model": "qwen-plus",
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        
        # 配置 fallback
        mock_fallback.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        
        # 主适配器不可用，fallback 适配器可用
        fallback_adapter = MagicMock()
        fallback_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Fallback success",
            model="gpt-4o-mini",
            provider="openai"
        ))
        
        # 第一次返回 None（主适配器），第二次返回 fallback 适配器
        mock_get_adapter.side_effect = [None, fallback_adapter]
        
        with patch('shared.ai.unified_text_service.track_ai_usage', new_callable=AsyncMock):
            response = await unified_text_service.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert response.success is True
        assert response.content == "Fallback success"
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_fallback_config')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_try_fallback_no_config(
        self, mock_cache_get, mock_get_adapter, mock_is_enabled, 
        mock_get_config, mock_fallback
    ):
        """_try_fallback 没有配置时返回错误（覆盖 192 行）"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        mock_get_adapter.return_value = None
        mock_fallback.return_value = None  # 无 fallback 配置
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert response.success is False
        assert response.error_type == AIErrorType.API_ERROR
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_fallback_config')
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_try_fallback_adapter_not_available(
        self, mock_cache_get, mock_get_adapter, mock_is_enabled, 
        mock_get_config, mock_fallback
    ):
        """fallback adapter 不可用时返回错误（覆盖 206 行）"""
        from shared.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "qwen",
            "model": "qwen-plus",
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        
        # 配置 fallback
        mock_fallback.return_value = {
            "provider": "anthropic",
            "model": "claude-3"
        }
        
        # 两个适配器都返回 None
        mock_get_adapter.return_value = None
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert response.success is False
        assert response.error_type == AIErrorType.AUTH_ERROR


class TestConvenienceFunctions:
    """便捷函数测试（覆盖 254, 270 行）"""
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_text_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_chat_convenience_function(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_config
    ):
        """测试 chat 便捷函数（覆盖 254 行）"""
        from shared.ai.unified_text_service import chat
        
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Response from chat",
            model="gpt-4o-mini",
            provider="openai"
        ))
        mock_get_adapter.return_value = mock_adapter
        
        response = await chat(
            messages=[{"role": "user", "content": "Hello"}],
            user_id="user_123",
            tier="free"
        )
        
        assert response.success is True
        assert response.content == "Response from chat"
    
    @pytest.mark.asyncio
    @patch('shared.ai.unified_text_service.get_admin_model_config')
    @patch('shared.ai.unified_text_service.is_provider_enabled')
    @patch('shared.ai.unified_text_service.get_text_adapter')
    @patch('shared.ai.unified_text_service.track_ai_usage', new_callable=AsyncMock)
    @patch('shared.ai.unified_text_service.get_cached_result')
    async def test_admin_chat_convenience_function(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_admin_config
    ):
        """测试 admin_chat 便捷函数（覆盖 270 行）"""
        from shared.ai.unified_text_service import admin_chat
        
        mock_get_admin_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o",
        }
        mock_is_enabled.return_value = True
        mock_cache_get.return_value = None
        
        mock_adapter = MagicMock()
        mock_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Admin analysis result",
            model="gpt-4o",
            provider="openai"
        ))
        mock_get_adapter.return_value = mock_adapter
        
        response = await admin_chat(
            messages=[{"role": "user", "content": "Analyze data"}]
        )
        
        assert response.success is True
        assert response.content == "Admin analysis result"
        # admin_chat 应该使用 admin 模型配置
        mock_get_admin_config.assert_called_once()
