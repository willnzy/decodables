"""
FAL Adapter Tests
FAL AI 适配器测试
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os


class TestFALImageAdapter:
    @patch.dict(os.environ, {'FAL_KEY': ''}, clear=True)
    @patch('shared.ai.adapters.fal_adapter.FAL_KEY', '')
    def test_not_available_without_key(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        adapter = FALImageAdapter()
        assert adapter.is_available() is False

    def test_get_available_models(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        adapter = FALImageAdapter()
        models = adapter.get_available_models()
        assert 'flux-schnell' in models
        assert 'flux-dev' in models

    @pytest.mark.asyncio
    async def test_generate_image_no_client(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._client = None
        
        response = await adapter.generate_image(
            prompt="A cat",
            model="flux-schnell"
        )
        
        assert response.success is False
        assert "not configured" in response.error

    @pytest.mark.asyncio
    async def test_generate_image_unknown_model(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._client = True
        adapter._fal = MagicMock()
        
        response = await adapter.generate_image(
            prompt="A cat",
            model="unknown-model"
        )
        
        assert response.success is False
        assert "Unknown" in response.error

    @patch('shared.ai.adapters.fal_adapter.FAL_KEY', 'test-key')
    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._client = True
        
        mock_fal = MagicMock()
        mock_handler = MagicMock()
        mock_handler.get = AsyncMock(return_value={
            "images": [{"url": "https://fal.ai/image.png"}]
        })
        mock_fal.submit_async = AsyncMock(return_value=mock_handler)
        adapter._fal = mock_fal
        
        response = await adapter.generate_image(
            prompt="A cat",
            model="flux-schnell"
        )
        
        assert response.success is True
        assert len(response.content) == 1

    @patch('shared.ai.adapters.fal_adapter.FAL_KEY', 'test-key')
    @pytest.mark.asyncio
    async def test_generate_image_with_negative_prompt(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._client = True
        
        mock_fal = MagicMock()
        mock_handler = MagicMock()
        mock_handler.get = AsyncMock(return_value={
            "images": [{"url": "https://fal.ai/image.png"}]
        })
        mock_fal.submit_async = AsyncMock(return_value=mock_handler)
        adapter._fal = mock_fal
        
        response = await adapter.generate_image(
            prompt="A cat",
            model="flux-schnell",
            negative_prompt="dogs"
        )
        
        assert response.success is True
        call_args = mock_fal.submit_async.call_args
        assert "negative_prompt" in call_args[1]["arguments"]

    @patch('shared.ai.adapters.fal_adapter.FAL_KEY', 'test-key')
    @pytest.mark.asyncio
    async def test_generate_image_error(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._client = True
        
        mock_fal = MagicMock()
        mock_fal.submit_async = AsyncMock(side_effect=Exception("API Error"))
        adapter._fal = mock_fal
        
        response = await adapter.generate_image(
            prompt="A cat",
            model="flux-schnell"
        )
        
        assert response.success is False

    @pytest.mark.asyncio
    async def test_image_to_image_no_client(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._client = None
        
        response = await adapter.image_to_image(
            prompt="Make blue",
            image_url="http://example.com/img.png",
            model="flux-dev"
        )
        
        assert response.success is False

    @patch('shared.ai.adapters.fal_adapter.FAL_KEY', 'test-key')
    @pytest.mark.asyncio
    async def test_image_to_image_success(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._client = True
        
        mock_fal = MagicMock()
        mock_handler = MagicMock()
        mock_handler.get = AsyncMock(return_value={
            "images": [{"url": "https://fal.ai/modified.png"}]
        })
        mock_fal.submit_async = AsyncMock(return_value=mock_handler)
        adapter._fal = mock_fal
        
        response = await adapter.image_to_image(
            prompt="Make it blue",
            image_url="http://example.com/original.png",
            model="flux-dev",
            strength=0.7
        )
        
        assert response.success is True
        assert len(response.content) == 1

    @patch('shared.ai.adapters.fal_adapter.FAL_KEY', 'test-key')
    @pytest.mark.asyncio
    async def test_image_to_image_error(self):
        from shared.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._client = True
        
        mock_fal = MagicMock()
        mock_fal.submit_async = AsyncMock(side_effect=Exception("API Error"))
        adapter._fal = mock_fal
        
        response = await adapter.image_to_image(
            prompt="Make blue",
            image_url="http://example.com/img.png",
            model="flux-dev"
        )
        
        assert response.success is False


class TestFALModelConfig:
    def test_model_endpoints(self):
        from shared.ai.adapters.fal_adapter import FAL_MODEL_ENDPOINTS
        
        assert "flux-schnell" in FAL_MODEL_ENDPOINTS
        assert "flux-dev" in FAL_MODEL_ENDPOINTS
        assert "flux-pro" in FAL_MODEL_ENDPOINTS

    def test_model_defaults(self):
        from shared.ai.adapters.fal_adapter import FAL_MODEL_DEFAULTS
        
        assert FAL_MODEL_DEFAULTS["flux-schnell"]["num_inference_steps"] == 4
        assert FAL_MODEL_DEFAULTS["flux-dev"]["num_inference_steps"] == 28
