"""
Unified Image Service Tests
统一图像服务测试
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestUnifiedImageServiceGenerate:
    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('services.ai.unified_image_service.get_image_adapter')
    @patch('services.ai.unified_image_service.is_provider_enabled')
    @patch('services.ai.unified_image_service.should_use_canary')
    @patch('services.ai.unified_image_service.get_image_model_config')
    async def test_successful_generation(self, mock_config, mock_canary, mock_enabled, mock_adapter, mock_track):
        from services.ai.unified_image_service import unified_image_service
        from services.ai.base import AIResponse, AIUsage
        
        mock_config.return_value = {"provider": "fal", "model": "flux-schnell", "fallback": {}}
        mock_canary.return_value = (False, None)
        mock_enabled.return_value = True
        
        mock_adapter_instance = MagicMock()
        mock_adapter_instance.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/image.png"],
            model="flux-schnell",
            provider="fal",
            usage=AIUsage(images_generated=1)
        ))
        mock_adapter.return_value = mock_adapter_instance
        
        response = await unified_image_service.generate(
            prompt="A cute cat",
            user_id="user_123",
            tier="free"
        )
        
        assert response.success is True
        assert len(response.content) == 1

    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('services.ai.unified_image_service.get_image_adapter')
    @patch('services.ai.unified_image_service.is_provider_enabled')
    @patch('services.ai.unified_image_service.should_use_canary')
    @patch('services.ai.unified_image_service.get_image_model_config')
    async def test_canary_model(self, mock_config, mock_canary, mock_enabled, mock_adapter, mock_track):
        from services.ai.unified_image_service import unified_image_service
        from services.ai.base import AIResponse, AIUsage
        
        mock_config.return_value = {"provider": "fal", "model": "flux-schnell", "fallback": {}}
        mock_canary.return_value = (True, {"provider": "jimeng", "model": "jimeng-2.1"})
        mock_enabled.return_value = True
        
        mock_adapter_instance = MagicMock()
        mock_adapter_instance.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/canary.png"],
            model="jimeng-2.1",
            provider="jimeng",
            usage=AIUsage(images_generated=1)
        ))
        mock_adapter.return_value = mock_adapter_instance
        
        response = await unified_image_service.generate(
            prompt="A dog",
            user_id="user_123",
            tier="pro"
        )
        
        assert response.success is True
        mock_adapter.assert_called_with("jimeng")

    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.get_fallback_config')
    @patch('services.ai.unified_image_service.is_provider_enabled')
    @patch('services.ai.unified_image_service.should_use_canary')
    @patch('services.ai.unified_image_service.get_image_model_config')
    async def test_provider_disabled(self, mock_config, mock_canary, mock_enabled, mock_fallback):
        from services.ai.unified_image_service import unified_image_service
        
        mock_config.return_value = {"provider": "disabled", "model": "model", "fallback": None}
        mock_canary.return_value = (False, None)
        mock_enabled.return_value = False
        mock_fallback.return_value = None
        
        response = await unified_image_service.generate(
            prompt="A cat",
            user_id="user_123"
        )
        
        assert response.success is False

    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.get_image_adapter')
    @patch('services.ai.unified_image_service.is_provider_enabled')
    @patch('services.ai.unified_image_service.should_use_canary')
    @patch('services.ai.unified_image_service.get_image_model_config')
    async def test_adapter_not_available(self, mock_config, mock_canary, mock_enabled, mock_adapter):
        from services.ai.unified_image_service import unified_image_service
        
        mock_config.return_value = {"provider": "fal", "model": "flux-schnell", "fallback": None}
        mock_canary.return_value = (False, None)
        mock_enabled.return_value = True
        mock_adapter.return_value = None
        
        response = await unified_image_service.generate(
            prompt="A cat",
            user_id="user_123"
        )
        
        assert response.success is False


class TestUnifiedImageServiceImageToImage:
    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('services.ai.unified_image_service.get_image_adapter')
    @patch('services.ai.unified_image_service.is_provider_enabled')
    @patch('services.ai.unified_image_service.should_use_canary')
    @patch('services.ai.unified_image_service.get_image_model_config')
    async def test_image_to_image_success(self, mock_config, mock_canary, mock_enabled, mock_adapter, mock_track):
        from services.ai.unified_image_service import unified_image_service
        from services.ai.base import AIResponse, AIUsage
        
        mock_config.return_value = {"provider": "fal", "model": "flux-schnell", "fallback": {}}
        mock_canary.return_value = (False, None)
        mock_enabled.return_value = True
        
        mock_adapter_instance = MagicMock()
        mock_adapter_instance.image_to_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/modified.png"],
            model="flux-schnell",
            provider="fal",
            usage=AIUsage(images_generated=1)
        ))
        mock_adapter.return_value = mock_adapter_instance
        
        response = await unified_image_service.image_to_image(
            prompt="Make it blue",
            image_url="https://example.com/original.png",
            user_id="user_123"
        )
        
        assert response.success is True


class TestTryFallback:
    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.get_fallback_config')
    async def test_no_fallback_configured(self, mock_fallback):
        from services.ai.unified_image_service import unified_image_service
        
        mock_fallback.return_value = None
        
        response = await unified_image_service._try_fallback(
            {"provider": "fal", "model": "flux"},
            "A cat", "1024x1024", 1, None, None, None, None
        )
        
        assert response.success is False
        assert "No fallback" in response.error

    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.track_ai_usage', new_callable=AsyncMock)
    @patch('services.ai.unified_image_service.get_image_adapter')
    @patch('services.ai.unified_image_service.get_fallback_config')
    async def test_fallback_success(self, mock_fallback, mock_adapter, mock_track):
        from services.ai.unified_image_service import unified_image_service
        from services.ai.base import AIResponse, AIUsage
        
        mock_fallback.return_value = {"provider": "openai", "model": "dall-e-3"}
        
        mock_adapter_instance = MagicMock()
        mock_adapter_instance.generate_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://example.com/fallback.png"],
            model="dall-e-3",
            provider="openai",
            usage=AIUsage(images_generated=1)
        ))
        mock_adapter.return_value = mock_adapter_instance
        
        response = await unified_image_service._try_fallback(
            {"provider": "fal", "model": "flux"},
            "A cat", "1024x1024", 1, None, None, None, None
        )
        
        assert response.success is True


class TestConvenienceFunctions:
    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.unified_image_service.generate')
    async def test_generate_image_function(self, mock_generate):
        from services.ai.unified_image_service import generate_image
        from services.ai.base import AIResponse
        
        mock_generate.return_value = AIResponse(success=True, content=["url"])
        
        response = await generate_image(
            prompt="A cat",
            user_id="user_123"
        )
        
        mock_generate.assert_called_once()
        assert response.success is True

    @pytest.mark.asyncio
    @patch('services.ai.unified_image_service.unified_image_service.image_to_image')
    async def test_image_to_image_function(self, mock_i2i):
        from services.ai.unified_image_service import image_to_image
        from services.ai.base import AIResponse
        
        mock_i2i.return_value = AIResponse(success=True, content=["url"])
        
        response = await image_to_image(
            prompt="Make blue",
            image_url="https://example.com/img.png"
        )
        
        mock_i2i.assert_called_once()
        assert response.success is True


class TestSingleton:
    def test_singleton_exists(self):
        from services.ai.unified_image_service import unified_image_service
        assert unified_image_service is not None
