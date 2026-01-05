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
    async def test_returns_url_if_http(self):
        from services.ai.image_generator import upload_reference_image
        
        session = MagicMock()
        result = await upload_reference_image(session, "http://example.com/image.png", "task123")
        
        assert result == "http://example.com/image.png"

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
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase')
    async def test_uploads_base64_with_data_uri_prefix(self, mock_supabase):
        """测试带 data URI 前缀的 base64 图片"""
        from services.ai.image_generator import upload_reference_image
        import base64
        
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        mock_storage.upload.return_value = MagicMock()
        mock_storage.get_public_url.return_value = "https://storage.supabase.co/image.png"
        
        # Base64 with data URI prefix
        base64_data = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100).decode()
        data_uri = f"data:image/png;base64,{base64_data}"
        
        session = MagicMock()
        result = await upload_reference_image(session, data_uri, "task123", "user_123")
        
        assert result == "https://storage.supabase.co/image.png"
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase')
    async def test_uploads_anonymous_user(self, mock_supabase):
        """测试匿名用户上传 (无 user_id)"""
        from services.ai.image_generator import upload_reference_image
        import base64
        
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        mock_storage.upload.return_value = MagicMock()
        mock_storage.get_public_url.return_value = "https://storage.supabase.co/anon.png"
        
        base64_data = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100).decode()
        
        session = MagicMock()
        result = await upload_reference_image(session, base64_data, "task123", None)
        
        assert result == "https://storage.supabase.co/anon.png"
        # Verify the path contains 'anonymous'
        upload_call_args = mock_storage.upload.call_args
        assert 'anonymous' in upload_call_args[1]['path']
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase')
    async def test_upload_exception_returns_none(self, mock_supabase):
        """测试上传异常时返回 None"""
        from services.ai.image_generator import upload_reference_image
        import base64
        
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        mock_storage.upload.side_effect = Exception("Upload failed")
        
        base64_data = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100).decode()
        
        session = MagicMock()
        result = await upload_reference_image(session, base64_data, "task123", "user_123")
        
        assert result is None


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
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase')
    async def test_downloads_and_uploads_anonymous_user(self, mock_supabase):
        """测试匿名用户下载上传"""
        from services.ai.image_generator import download_and_upload_image
        
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        mock_storage.upload.return_value = MagicMock()
        mock_storage.get_public_url.return_value = "https://storage.supabase.co/anon.png"
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b'image_bytes')
        
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
        
        result = await download_and_upload_image(mock_session, "http://example.com/img.png", "task123", 0, None)
        
        assert result == "https://storage.supabase.co/anon.png"
        # Verify the path contains 'anonymous'
        upload_call_args = mock_storage.upload.call_args
        assert 'anonymous' in upload_call_args[1]['path']
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase')
    async def test_returns_none_on_non_200_status(self, mock_supabase):
        """测试下载失败 (非 200 状态码)"""
        from services.ai.image_generator import download_and_upload_image
        
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
        
        result = await download_and_upload_image(mock_session, "http://example.com/notfound.png", "task123", 0, "user_123")
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.supabase')
    async def test_returns_none_on_exception(self, mock_supabase):
        """测试下载异常"""
        from services.ai.image_generator import download_and_upload_image
        
        mock_storage = MagicMock()
        mock_supabase.storage.from_.return_value = mock_storage
        
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=Exception("Network error"))
        
        result = await download_and_upload_image(mock_session, "http://example.com/img.png", "task123", 0, "user_123")
        
        assert result is None


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
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.download_and_upload_image')
    @patch('services.ai.image_generator.unified_image_service')
    async def test_with_custom_negative_prompt(self, mock_service, mock_download):
        """测试自定义 negative prompt"""
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
            negative_prompt="ugly, blurry, low quality",
            user_id="user_123", tier="pro"
        )
        
        assert result == "https://storage.supabase.co/final.png"
        # Verify negative_prompt was included in the call
        call_kwargs = mock_service.generate.call_args[1]
        assert "ugly" in call_kwargs['negative_prompt'] or "nsfw" in call_kwargs['negative_prompt']
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.unified_image_service')
    async def test_exception_during_generation(self, mock_service):
        """测试生成过程中的异常"""
        from services.ai.image_generator import generate_and_upload_single
        
        mock_service.generate = AsyncMock(side_effect=Exception("Unexpected error"))
        
        session = MagicMock()
        result = await generate_and_upload_single(
            session, "A cat", 0, "task123",
            user_id="user_123", tier="pro"
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
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.upload_reference_image')
    @patch('services.ai.image_generator.generate_and_upload_single')
    async def test_failed_reference_image_falls_back_to_text(self, mock_gen_single, mock_upload_ref):
        """测试 reference image 上传失败时降级为纯文本生成"""
        from services.ai.image_generator import generate_8_images
        
        mock_upload_ref.return_value = None  # Upload failed
        mock_gen_single.return_value = "https://storage.supabase.co/gen.png"
        
        urls, task_id = await generate_8_images(
            prompts=["Cat"],
            reference_image="base64data",
            user_id="user_123"
        )
        
        assert len(urls) == 1
        mock_upload_ref.assert_called_once()
        # Should still generate using text-only mode
        mock_gen_single.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.generate_and_upload_single')
    async def test_with_multiple_variations(self, mock_gen_single):
        """测试生成多个变体"""
        from services.ai.image_generator import generate_8_images
        
        mock_gen_single.return_value = "https://storage.supabase.co/image.png"
        
        urls, task_id = await generate_8_images(
            prompts=["Cat"],
            num_images=3,  # Generate 3 variations
            user_id="user_123"
        )
        
        assert len(urls) == 3
        assert mock_gen_single.call_count == 3
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.generate_and_upload_single')
    async def test_clamps_num_images(self, mock_gen_single):
        """测试 num_images 范围限制"""
        from services.ai.image_generator import generate_8_images
        
        mock_gen_single.return_value = "url"
        
        # num_images should be clamped to max 4
        urls, task_id = await generate_8_images(
            prompts=["Cat"],
            num_images=10  # Should be clamped to 4
        )
        
        assert len(urls) == 4
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.generate_and_upload_single')
    async def test_with_negative_prompt(self, mock_gen_single):
        """测试带 negative prompt 的生成"""
        from services.ai.image_generator import generate_8_images
        
        mock_gen_single.return_value = "https://storage.supabase.co/image.png"
        
        urls, task_id = await generate_8_images(
            prompts=["A happy cat"],
            negative_prompt="scary, dark, creepy",
            user_id="user_123"
        )
        
        assert len(urls) == 1
        # Verify negative_prompt was passed to generate_and_upload_single
        call_kwargs = mock_gen_single.call_args[1]
        assert call_kwargs.get('negative_prompt') == "scary, dark, creepy"


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
