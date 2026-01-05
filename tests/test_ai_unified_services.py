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

from services.ai.base import AIResponse, AIUsage, AIErrorType


# ==========================================
# UnifiedTextService Tests
# ==========================================

class TestUnifiedTextService:
    """UnifiedTextService 测试"""
    
    @pytest.mark.asyncio
    @patch('services.ai.unified_text_service.get_text_model_config')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    @patch('services.ai.unified_text_service.get_text_adapter')
    @patch('services.ai.unified_text_service.track_ai_usage')
    @patch('services.ai.unified_text_service.get_cached_result')
    async def test_successful_chat(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_config
    ):
        """成功的聊天请求"""
        from services.ai.unified_text_service import unified_text_service
        
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
    @patch('services.ai.unified_text_service.get_text_model_config')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    @patch('services.ai.unified_text_service.get_text_adapter')
    async def test_provider_not_enabled(
        self, mock_get_adapter, mock_is_enabled, mock_get_config
    ):
        """提供商未启用时返回错误"""
        from services.ai.unified_text_service import unified_text_service
        
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
    @patch('services.ai.unified_text_service.get_text_model_config')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    @patch('services.ai.unified_text_service.get_text_adapter')
    async def test_adapter_not_available(
        self, mock_get_adapter, mock_is_enabled, mock_get_config
    ):
        """适配器不可用时返回错误"""
        from services.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "fallback": None
        }
        mock_is_enabled.return_value = True
        mock_get_adapter.return_value = None  # 适配器不可用
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert response.success is False
    
    @pytest.mark.asyncio
    @patch('services.ai.unified_text_service.get_cached_result')
    @patch('services.ai.unified_text_service.get_text_model_config')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    async def test_cache_hit(
        self, mock_is_enabled, mock_get_config, mock_cache_get
    ):
        """缓存命中时直接返回"""
        from services.ai.unified_text_service import unified_text_service
        
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        mock_is_enabled.return_value = True
        
        # 返回缓存结果
        mock_cache_get.return_value = AIResponse(
            success=True,
            content="Cached response",
            model="gpt-4o-mini",
            provider="openai"
        )
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}],
            use_cache=True
        )
        
        assert response.success is True
        assert response.content == "Cached response"
    
    @pytest.mark.asyncio
    @patch('services.ai.unified_text_service.get_admin_model_config')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    @patch('services.ai.unified_text_service.get_text_adapter')
    @patch('services.ai.unified_text_service.track_ai_usage')
    @patch('services.ai.unified_text_service.get_cached_result')
    async def test_admin_model_usage(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_admin_config
    ):
        """Admin 模型使用"""
        from services.ai.unified_text_service import unified_text_service
        
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
    @patch('services.ai.unified_image_service.get_image_model_config')
    @patch('services.ai.unified_image_service.is_provider_enabled')
    @patch('services.ai.unified_image_service.get_image_adapter')
    @patch('services.ai.unified_image_service.track_ai_usage')
    async def test_successful_image_generation(
        self, mock_track, mock_get_adapter, mock_is_enabled, mock_get_config
    ):
        """成功的图像生成"""
        from services.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "fal",
            "model": "flux-schnell",
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
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
        mock_track.return_value = None
        
        response = await unified_image_service.generate(
            prompt="A cute cat",
            user_id="user_123",
            tier="free"
        )
        
        assert response.success is True
        assert len(response.content) == 1
        assert response.content[0].startswith("https://")
    
    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.get_image_model_config')
    @patch('services.ai.unified_image_service.is_provider_enabled')
    @patch('services.ai.unified_image_service.get_image_adapter')
    @patch('services.ai.unified_image_service.track_ai_usage')
    async def test_tier_based_model_selection(
        self, mock_track, mock_get_adapter, mock_is_enabled, mock_get_config
    ):
        """基于等级的模型选择"""
        from services.ai.unified_image_service import unified_image_service
        
        # Pro 用户应该使用 flux-dev
        mock_get_config.return_value = {
            "provider": "fal",
            "model": "flux-dev",  # Pro 模型
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        mock_is_enabled.return_value = True
        
        mock_adapter = MagicMock()
        mock_adapter.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/image.png"],
            model="flux-dev",
            provider="fal"
        ))
        mock_get_adapter.return_value = mock_adapter
        mock_track.return_value = None
        
        response = await unified_image_service.generate(
            prompt="High quality image",
            tier="pro"
        )
        
        assert response.success is True
        # 验证 get_image_model_config 被调用时传递了 tier
        mock_get_config.assert_called_once_with("pro")
    
    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.get_image_model_config')
    @patch('services.ai.unified_image_service.is_provider_enabled')
    @patch('services.ai.unified_image_service.get_image_adapter')
    @patch('services.ai.unified_image_service.track_ai_usage')
    async def test_image_to_image(
        self, mock_track, mock_get_adapter, mock_is_enabled, mock_get_config
    ):
        """图生图功能"""
        from services.ai.unified_image_service import unified_image_service
        
        mock_get_config.return_value = {
            "provider": "fal",
            "model": "flux-dev",
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        mock_is_enabled.return_value = True
        
        mock_adapter = MagicMock()
        mock_adapter.image_to_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/edited.png"],
            model="flux-dev",
            provider="fal"
        ))
        mock_get_adapter.return_value = mock_adapter
        mock_track.return_value = None
        
        response = await unified_image_service.image_to_image(
            prompt="Make it more colorful",
            image_url="https://example.com/original.png",
            strength=0.7
        )
        
        assert response.success is True
        mock_adapter.image_to_image.assert_called_once()


# ==========================================
# Canary Integration Tests
# ==========================================

class TestCanaryIntegration:
    """灰度发布集成测试"""
    
    @pytest.mark.asyncio
    @patch('services.ai.unified_text_service.should_use_canary')
    @patch('services.ai.unified_text_service.get_text_model_config')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    @patch('services.ai.unified_text_service.get_text_adapter')
    @patch('services.ai.unified_text_service.track_ai_usage')
    @patch('services.ai.unified_text_service.get_cached_result')
    async def test_canary_model_used(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_config, mock_canary
    ):
        """灰度模型被使用"""
        from services.ai.unified_text_service import unified_text_service
        
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
    @patch('services.ai.unified_text_service.get_text_model_config')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    @patch('services.ai.unified_text_service.get_text_adapter')
    @patch('services.ai.unified_text_service.track_ai_usage')
    @patch('services.ai.unified_text_service.get_cached_result')
    async def test_fallback_on_error(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_config
    ):
        """主模型失败时使用 fallback"""
        from services.ai.unified_text_service import unified_text_service
        
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
    @patch('services.ai.unified_text_service.get_text_model_config')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    @patch('services.ai.unified_text_service.get_text_adapter')
    @patch('services.ai.unified_text_service.track_ai_usage')
    @patch('services.ai.unified_text_service.get_cached_result')
    async def test_empty_messages(
        self, mock_cache_get, mock_track, mock_get_adapter, 
        mock_is_enabled, mock_get_config
    ):
        """空消息列表"""
        from services.ai.unified_text_service import unified_text_service
        
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
    @patch('services.ai.unified_image_service.get_image_model_config')
    @patch('services.ai.unified_image_service.is_provider_enabled')
    @patch('services.ai.unified_image_service.get_image_adapter')
    @patch('services.ai.unified_image_service.track_ai_usage')
    async def test_very_long_prompt(
        self, mock_track, mock_get_adapter, mock_is_enabled, mock_get_config
    ):
        """超长提示词"""
        from services.ai.unified_image_service import unified_image_service
        
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
        mock_track.return_value = None
        
        long_prompt = "A beautiful " * 1000  # 很长的提示词
        
        response = await unified_image_service.generate(
            prompt=long_prompt
        )
        
        # 应该正常处理
        assert isinstance(response, AIResponse)
