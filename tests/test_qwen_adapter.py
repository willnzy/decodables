"""
Qwen/Wanx Adapter Tests
阿里云 DashScope AI 适配器测试

Coverage target: 90%+
Business logic tested:
- QwenTextAdapter: 通义千问文本模型
- WanxImageAdapter: 通义万相图像生成模型
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import aiohttp


# ==========================================
# Configuration Tests
# ==========================================

class TestQwenAdapterConfiguration:
    """Test adapter configuration constants"""
    
    def test_text_models_defined(self):
        """Qwen text models are properly defined"""
        from services.ai.adapters.qwen_adapter import QWEN_TEXT_MODELS
        
        assert "qwen-turbo" in QWEN_TEXT_MODELS
        assert "qwen-plus" in QWEN_TEXT_MODELS
        assert "qwen-max" in QWEN_TEXT_MODELS
        assert "qwen-max-longcontext" in QWEN_TEXT_MODELS
    
    def test_image_models_defined(self):
        """Wanx image models are properly defined"""
        from services.ai.adapters.qwen_adapter import WANX_IMAGE_MODELS
        
        assert "wanx-v1" in WANX_IMAGE_MODELS
        assert "wan2.6-t2i" in WANX_IMAGE_MODELS
        assert "wan2.6-image" in WANX_IMAGE_MODELS
    
    def test_size_mapping(self):
        """Size mapping covers common formats"""
        from services.ai.adapters.qwen_adapter import SIZE_MAPPING
        
        assert SIZE_MAPPING["square"] == "1024*1024"
        assert SIZE_MAPPING["1:1"] == "1024*1024"
        assert SIZE_MAPPING["landscape_4_3"] == "1280*960"
        assert SIZE_MAPPING["portrait_4_3"] == "960*1280"
        assert SIZE_MAPPING["16:9"] == "1280*720"
        assert SIZE_MAPPING["9:16"] == "720*1280"


# ==========================================
# QwenTextAdapter Tests
# ==========================================

class TestQwenTextAdapterInit:
    """Test QwenTextAdapter initialization"""
    
    def test_init_with_api_key(self):
        """Initialize with API key from environment"""
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}):
            # Need to reload the module to pick up new env
            import importlib
            from services.ai.adapters import qwen_adapter
            importlib.reload(qwen_adapter)
            
            adapter = qwen_adapter.QwenTextAdapter()
            assert adapter._api_key == 'test-key'
    
    def test_init_without_api_key(self):
        """Initialize without API key"""
        with patch.dict('os.environ', {}, clear=True):
            import importlib
            from services.ai.adapters import qwen_adapter
            # Clear the module level variable
            original_key = qwen_adapter.DASHSCOPE_API_KEY
            qwen_adapter.DASHSCOPE_API_KEY = None
            
            adapter = qwen_adapter.QwenTextAdapter()
            assert adapter._api_key is None
            
            # Restore
            qwen_adapter.DASHSCOPE_API_KEY = original_key
    
    def test_provider_name(self):
        """Provider name is correct"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        
        adapter = QwenTextAdapter()
        assert adapter.provider_name == "qwen"


class TestQwenTextAdapterAvailability:
    """Test QwenTextAdapter availability checks"""
    
    def test_is_available_with_key(self):
        """Available when API key is set"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        
        adapter = QwenTextAdapter()
        adapter._api_key = "test-key"
        
        assert adapter.is_available() is True
    
    def test_is_available_without_key(self):
        """Not available when API key is missing"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        
        adapter = QwenTextAdapter()
        adapter._api_key = None
        
        assert adapter.is_available() is False
    
    def test_get_available_models(self):
        """Returns copy of available models"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter, QWEN_TEXT_MODELS
        
        adapter = QwenTextAdapter()
        models = adapter.get_available_models()
        
        assert models == QWEN_TEXT_MODELS
        # Verify it's a copy (modifying doesn't affect original)
        models.append("test-model")
        assert "test-model" not in QWEN_TEXT_MODELS


class TestQwenTextAdapterChatCompletion:
    """Test QwenTextAdapter chat completion"""
    
    @pytest.mark.asyncio
    async def test_chat_completion_without_api_key(self):
        """Returns error when API key not configured"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        from services.ai.base import AIErrorType
        
        adapter = QwenTextAdapter()
        adapter._api_key = None
        
        result = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="qwen-turbo"
        )
        
        assert result.success is False
        assert result.error_type == AIErrorType.AUTH_ERROR
        assert "not configured" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        """Successful chat completion"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        
        adapter = QwenTextAdapter()
        adapter._api_key = "test-key"
        
        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {
                "choices": [
                    {"message": {"content": "Hello! How can I help you?"}}
                ]
            },
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30
            }
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="qwen-turbo",
                temperature=0.7
            )
        
        assert result.success is True
        assert result.content == "Hello! How can I help you?"
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 20
        assert result.provider == "qwen"
        assert result.model == "qwen-turbo"
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_max_tokens(self):
        """Chat completion with max_tokens parameter"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        
        adapter = QwenTextAdapter()
        adapter._api_key = "test-key"
        
        # Mock response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {"choices": [{"message": {"content": "Short response"}}]},
            "usage": {"input_tokens": 5, "output_tokens": 5, "total_tokens": 10}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                model="qwen-turbo",
                max_tokens=100
            )
        
        assert result.success is True
        # Verify max_tokens was passed in the payload
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs['json']['parameters']['max_tokens'] == 100
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_json_response_format(self):
        """Chat completion with JSON response format"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        
        adapter = QwenTextAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {"choices": [{"message": {"content": '{"key": "value"}'}}]},
            "usage": {"input_tokens": 5, "output_tokens": 10, "total_tokens": 15}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Return JSON"}],
                model="qwen-turbo",
                response_format={"type": "json_object"}
            )
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_chat_completion_api_error(self):
        """Handles API error response"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        from services.ai.base import AIErrorType
        
        adapter = QwenTextAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "code": "InvalidParameter",
            "message": "Invalid model specified"
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="invalid-model"
            )
        
        assert result.success is False
        assert result.error_type == AIErrorType.API_ERROR
        assert "Invalid model" in result.error
    
    @pytest.mark.asyncio
    async def test_chat_completion_network_error(self):
        """Handles network exception"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        
        adapter = QwenTextAdapter()
        adapter._api_key = "test-key"
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Network error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="qwen-turbo"
            )
        
        assert result.success is False
        assert result.latency_ms >= 0
    
    @pytest.mark.asyncio
    async def test_chat_completion_empty_choices(self):
        """Handles empty choices in response"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        
        adapter = QwenTextAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {"choices": []},
            "usage": {"input_tokens": 5, "output_tokens": 0, "total_tokens": 5}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="qwen-turbo"
            )
        
        assert result.success is True
        assert result.content == ""  # Empty content when no choices


# ==========================================
# WanxImageAdapter Tests
# ==========================================

class TestWanxImageAdapterInit:
    """Test WanxImageAdapter initialization"""
    
    def test_init_with_api_key(self):
        """Initialize with API key"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        # Provider name should be 'wanx' not 'qwen'
        assert adapter.provider_name == "wanx"
    
    def test_is_available_with_key(self):
        """Available when API key is set"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        assert adapter.is_available() is True
    
    def test_is_available_without_key(self):
        """Not available when API key is missing"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = None
        
        assert adapter.is_available() is False
    
    def test_get_available_models(self):
        """Returns Wanx image models"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter, WANX_IMAGE_MODELS
        
        adapter = WanxImageAdapter()
        models = adapter.get_available_models()
        
        assert models == WANX_IMAGE_MODELS


class TestWanxImageGeneration:
    """Test WanxImageAdapter image generation"""
    
    @pytest.mark.asyncio
    async def test_generate_image_without_api_key(self):
        """Returns error when API key not configured"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        from services.ai.base import AIErrorType
        
        adapter = WanxImageAdapter()
        adapter._api_key = None
        
        result = await adapter.generate_image(
            prompt="A cute cat",
            model="wan2.6-t2i"
        )
        
        assert result.success is False
        assert result.error_type == AIErrorType.AUTH_ERROR
        assert "not configured" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        """Successful image generation"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {
                "choices": [
                    {"message": {"content": [{"image": "https://example.com/image1.png"}]}}
                ]
            },
            "usage": {"image_count": 1}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.generate_image(
                prompt="A cute cat",
                model="wan2.6-t2i",
                size="1024*1024"
            )
        
        assert result.success is True
        assert result.content == ["https://example.com/image1.png"]
        assert result.usage.images_generated == 1
        assert result.provider == "wanx"
    
    @pytest.mark.asyncio
    async def test_generate_image_with_size_mapping(self):
        """Size mapping converts formats correctly"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {"choices": [{"message": {"content": [{"image": "https://example.com/img.png"}]}}]},
            "usage": {"image_count": 1}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.generate_image(
                prompt="A landscape",
                model="wan2.6-t2i",
                size="landscape_16_9"  # Should map to 1280*720
            )
        
        assert result.success is True
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs['json']['parameters']['size'] == "1280*720"
    
    @pytest.mark.asyncio
    async def test_generate_image_with_x_size_format(self):
        """Handles 'x' size format (e.g., 1024x1024)"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {"choices": [{"message": {"content": [{"image": "https://example.com/img.png"}]}}]},
            "usage": {}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.generate_image(
                prompt="Test",
                model="wan2.6-t2i",
                size="1024x1024"  # Should be converted to 1024*1024
            )
        
        assert result.success is True
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs['json']['parameters']['size'] == "1024*1024"
    
    @pytest.mark.asyncio
    async def test_generate_image_with_negative_prompt(self):
        """Image generation with negative prompt"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {"choices": [{"message": {"content": [{"image": "https://example.com/img.png"}]}}]},
            "usage": {}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.generate_image(
                prompt="A beautiful landscape",
                model="wan2.6-t2i",
                negative_prompt="blurry, low quality"
            )
        
        assert result.success is True
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs['json']['parameters']['negative_prompt'] == "blurry, low quality"
    
    @pytest.mark.asyncio
    async def test_generate_image_with_seed(self):
        """Image generation with seed for reproducibility"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {"choices": [{"message": {"content": [{"image": "https://example.com/img.png"}]}}]},
            "usage": {}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.generate_image(
                prompt="A cat",
                model="wan2.6-t2i",
                seed=12345
            )
        
        assert result.success is True
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs['json']['parameters']['seed'] == 12345
    
    @pytest.mark.asyncio
    async def test_generate_image_num_images_clamped(self):
        """Number of images is clamped to 1-4 range"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {"choices": [{"message": {"content": [{"image": "https://example.com/img.png"}]}}]},
            "usage": {}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Test clamping to max 4
            result = await adapter.generate_image(
                prompt="Test",
                model="wan2.6-t2i",
                num_images=10
            )
            call_kwargs = mock_session.post.call_args[1]
            assert call_kwargs['json']['parameters']['n'] == 4
            
            # Test clamping to min 1
            result = await adapter.generate_image(
                prompt="Test",
                model="wan2.6-t2i",
                num_images=0
            )
            call_kwargs = mock_session.post.call_args[1]
            assert call_kwargs['json']['parameters']['n'] == 1
    
    @pytest.mark.asyncio
    async def test_generate_image_multiple_images(self):
        """Multiple image generation"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {
                "choices": [
                    {"message": {"content": [{"image": "https://example.com/img1.png"}]}},
                    {"message": {"content": [{"image": "https://example.com/img2.png"}]}},
                ]
            },
            "usage": {"image_count": 2}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.generate_image(
                prompt="Cats",
                model="wan2.6-t2i",
                num_images=2
            )
        
        assert result.success is True
        assert len(result.content) == 2
        assert result.usage.images_generated == 2
    
    @pytest.mark.asyncio
    async def test_generate_image_api_error(self):
        """Handles API error response"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        from services.ai.base import AIErrorType
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "code": "ContentFiltered",
            "message": "Content was filtered"
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.generate_image(
                prompt="Inappropriate content",
                model="wan2.6-t2i"
            )
        
        assert result.success is False
        assert result.error_type == AIErrorType.API_ERROR
        assert result.content == []
    
    @pytest.mark.asyncio
    async def test_generate_image_network_error(self):
        """Handles network exception"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.generate_image(
                prompt="Test",
                model="wan2.6-t2i"
            )
        
        assert result.success is False
        assert result.content == []


class TestWanxImageToImage:
    """Test WanxImageAdapter image-to-image editing"""
    
    @pytest.mark.asyncio
    async def test_image_to_image_without_api_key(self):
        """Returns error when API key not configured"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        from services.ai.base import AIErrorType
        
        adapter = WanxImageAdapter()
        adapter._api_key = None
        
        result = await adapter.image_to_image(
            prompt="Make it blue",
            image_url="https://example.com/original.png"
        )
        
        assert result.success is False
        assert result.error_type == AIErrorType.AUTH_ERROR
    
    @pytest.mark.asyncio
    async def test_image_to_image_success(self):
        """Successful image-to-image editing"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "output": {
                "choices": [
                    {"message": {"content": [{"image": "https://example.com/edited.png"}]}}
                ]
            },
            "usage": {}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.image_to_image(
                prompt="Add a hat",
                image_url="https://example.com/original.png",
                model="wan2.6-image"
            )
        
        assert result.success is True
        assert result.content == ["https://example.com/edited.png"]
        
        # Verify payload contains both text and image
        call_kwargs = mock_session.post.call_args[1]
        content = call_kwargs['json']['input']['messages'][0]['content']
        assert any('text' in item for item in content)
        assert any('image' in item for item in content)
    
    @pytest.mark.asyncio
    async def test_image_to_image_api_error(self):
        """Handles API error in image-to-image"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        from services.ai.base import AIErrorType
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "code": "InvalidImage",
            "message": "Image format not supported"
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.image_to_image(
                prompt="Edit this",
                image_url="https://example.com/invalid.gif"
            )
        
        assert result.success is False
        assert result.error_type == AIErrorType.API_ERROR
        assert result.content == []
    
    @pytest.mark.asyncio
    async def test_image_to_image_network_error(self):
        """Handles network error in image-to-image"""
        from services.ai.adapters.qwen_adapter import WanxImageAdapter
        
        adapter = WanxImageAdapter()
        adapter._api_key = "test-key"
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=Exception("Timeout"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await adapter.image_to_image(
                prompt="Edit",
                image_url="https://example.com/img.png"
            )
        
        assert result.success is False
        assert result.content == []
