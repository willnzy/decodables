"""
Image Generator Tests
图像生成测试
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestGetGenerationParams:
    def test_guided_mode_flux_dev(self):
        from services.ai.image_generator import get_generation_params
        
        params = get_generation_params("flux-dev", "guided")
        
        assert params["num_inference_steps"] == 35
        assert params["guidance_scale"] == 4.5

    def test_guided_mode_flux_schnell(self):
        from services.ai.image_generator import get_generation_params
        
        params = get_generation_params("flux-schnell", "guided")
        
        assert params["num_inference_steps"] == 4
        assert params["guidance_scale"] == 3.5

    def test_guided_mode_unknown_model(self):
        from services.ai.image_generator import get_generation_params
        
        params = get_generation_params("unknown-model", "guided")
        
        assert params["num_inference_steps"] == 28
        assert params["guidance_scale"] == 4.0

    def test_flexible_mode_zero_creativity(self):
        from services.ai.image_generator import get_generation_params
        
        params = get_generation_params("flux-dev", "flexible", creativity_level=0.0)
        
        assert params["guidance_scale"] == 4.0

    def test_flexible_mode_max_creativity(self):
        from services.ai.image_generator import get_generation_params
        
        params = get_generation_params("flux-dev", "flexible", creativity_level=1.0)
        
        assert params["guidance_scale"] == 1.5

    def test_flexible_mode_mid_creativity(self):
        from services.ai.image_generator import get_generation_params
        
        params = get_generation_params("flux-dev", "flexible", creativity_level=0.5)
        
        assert 2.0 < params["guidance_scale"] < 3.5


class TestUploadReferenceImage:
    @pytest.mark.asyncio
    async def test_returns_url_if_already_url(self):
        from services.ai.image_generator import upload_reference_image
        
        session = MagicMock()
        result = await upload_reference_image(session, "https://example.com/image.png", "task123")
        
        assert result == "https://example.com/image.png"

    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase', None)
    async def test_returns_none_when_no_supabase(self):
        from services.ai.image_generator import upload_reference_image
        
        session = MagicMock()
        result = await upload_reference_image(session, "base64data", "task123")
        
        assert result is None

    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase')
    async def test_uploads_base64_image(self, mock_supabase):
        from services.ai.image_generator import upload_reference_image
        import base64
        
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        mock_storage.upload.return_value = MagicMock()
        mock_storage.get_public_url.return_value = "https://storage.supabase.co/image.png"
        
        # Valid base64 PNG header
        base64_data = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100).decode()
        
        session = MagicMock()
        result = await upload_reference_image(session, base64_data, "task123", "user_123")
        
        assert result == "https://storage.supabase.co/image.png"


class TestDownloadAndUploadImage:
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase', None)
    async def test_returns_none_when_no_supabase(self):
        from services.ai.image_generator import download_and_upload_image
        
        session = MagicMock()
        result = await download_and_upload_image(session, "http://example.com/img.png", "task123", 0)
        
        assert result is None

    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase')
    async def test_downloads_and_uploads(self, mock_supabase):
        from services.ai.image_generator import download_and_upload_image
        
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        mock_storage.upload.return_value = MagicMock()
        mock_storage.get_public_url.return_value = "https://storage.supabase.co/uploaded.png"
        
        # Mock aiohttp session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b'image_bytes')
        
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
        
        result = await download_and_upload_image(mock_session, "http://example.com/img.png", "task123", 0, "user_123")
        
        assert result == "https://storage.supabase.co/uploaded.png"


class TestGenerateAndUploadSingle:
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.download_and_upload_image')
    @patch('services.ai.image_generator.unified_image_service')
    async def test_text_to_image_generation(self, mock_service, mock_download):
        from services.ai.image_generator import generate_and_upload_single
        from services.ai.base import AIResponse
        
        mock_service.generate = AsyncMock(return_value=AIResponse(
            success=True,
            content=["http://generated.com/image.png"]
        ))
        mock_download.return_value = "https://storage.supabase.co/final.png"
        
        session = MagicMock()
        result = await generate_and_upload_single(
            session, "A cat", 0, "task123",
            user_id="user_123", tier="pro"
        )
        
        assert result == "https://storage.supabase.co/final.png"
        mock_service.generate.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.ai.image_generator.download_and_upload_image')
    @patch('services.ai.image_generator.unified_image_service')
    async def test_image_to_image_generation(self, mock_service, mock_download):
        from services.ai.image_generator import generate_and_upload_single
        from services.ai.base import AIResponse
        
        mock_service.image_to_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["http://generated.com/i2i.png"]
        ))
        mock_download.return_value = "https://storage.supabase.co/final_i2i.png"
        
        session = MagicMock()
        result = await generate_and_upload_single(
            session, "Make it blue", 0, "task123",
            reference_image_url="http://example.com/ref.png",
            user_id="user_123"
        )
        
        assert result == "https://storage.supabase.co/final_i2i.png"
        mock_service.image_to_image.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.ai.image_generator.unified_image_service')
    async def test_generation_failure(self, mock_service):
        from services.ai.image_generator import generate_and_upload_single
        from services.ai.base import AIResponse
        
        mock_service.generate = AsyncMock(return_value=AIResponse(
            success=False,
            error="Generation failed"
        ))
        
        session = MagicMock()
        result = await generate_and_upload_single(
            session, "A cat", 0, "task123"
        )
        
        assert result is None

    @pytest.mark.asyncio
    @patch('services.ai.image_generator.unified_image_service')
    async def test_empty_content_response(self, mock_service):
        from services.ai.image_generator import generate_and_upload_single
        from services.ai.base import AIResponse
        
        mock_service.generate = AsyncMock(return_value=AIResponse(
            success=True,
            content=[]
        ))
        
        session = MagicMock()
        result = await generate_and_upload_single(
            session, "A cat", 0, "task123"
        )
        
        assert result is None


class TestGenerate8Images:
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.generate_and_upload_single')
    async def test_generates_multiple_images(self, mock_gen_single):
        from services.ai.image_generator import generate_8_images
        
        mock_gen_single.return_value = "https://storage.supabase.co/image.png"
        
        prompts = ["Cat", "Dog"]
        urls, task_id = await generate_8_images(
            prompts=prompts,
            user_id="user_123",
            tier="pro"
        )
        
        assert len(urls) == 2
        assert all(url == "https://storage.supabase.co/image.png" for url in urls)

    @pytest.mark.asyncio
    @patch('services.ai.image_generator.generate_and_upload_single')
    async def test_validates_generation_mode(self, mock_gen_single):
        from services.ai.image_generator import generate_8_images
        
        mock_gen_single.return_value = "url"
        
        urls, task_id = await generate_8_images(
            prompts=["Cat"],
            generation_mode="invalid_mode"
        )
        
        # Should default to "guided"
        assert len(urls) == 1

    @pytest.mark.asyncio
    @patch('services.ai.image_generator.generate_and_upload_single')
    async def test_clamps_creativity_level(self, mock_gen_single):
        from services.ai.image_generator import generate_8_images
        
        mock_gen_single.return_value = "url"
        
        urls, task_id = await generate_8_images(
            prompts=["Cat"],
            creativity_level=2.0  # Should be clamped to 1.0
        )
        
        assert len(urls) == 1

    @pytest.mark.asyncio
    @patch('services.ai.image_generator.upload_reference_image')
    @patch('services.ai.image_generator.generate_and_upload_single')
    async def test_with_reference_image(self, mock_gen_single, mock_upload_ref):
        from services.ai.image_generator import generate_8_images
        
        mock_upload_ref.return_value = "https://storage.supabase.co/ref.png"
        mock_gen_single.return_value = "https://storage.supabase.co/gen.png"
        
        urls, task_id = await generate_8_images(
            prompts=["Cat"],
            reference_image="base64data",
            user_id="user_123"
        )
        
        assert len(urls) == 1
        mock_upload_ref.assert_called_once()


class TestGenerateImagesAsync:
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.generate_8_images')
    async def test_convenience_function(self, mock_gen_8):
        from services.ai.image_generator import generate_images_async
        
        mock_gen_8.return_value = (["url1", "url2"], "task123")
        
        urls, task_id = await generate_images_async(
            prompts=["Cat", "Dog"],
            user_id="user_123"
        )
        
        assert urls == ["url1", "url2"]
        assert task_id == "task123"
        mock_gen_8.assert_called_once()


class TestGenerationModeParams:
    def test_guided_params_exist(self):
        from services.ai.image_generator import GENERATION_MODE_PARAMS
        
        assert "guided" in GENERATION_MODE_PARAMS
        assert "flux-dev" in GENERATION_MODE_PARAMS["guided"]

    def test_flexible_params_exist(self):
        from services.ai.image_generator import GENERATION_MODE_PARAMS
        
        assert "flexible" in GENERATION_MODE_PARAMS
        assert "default" in GENERATION_MODE_PARAMS["flexible"]
