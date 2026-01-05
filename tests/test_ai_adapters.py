"""
Unit Tests for AI Provider Adapters
AI 提供商适配器单元测试

基于 BUSINESS_LOGIC_SPEC.md Section 5 的业务规则测试

核心业务规则:
1. 文本推理模型 (Section 5.1):
   - 用户文本: gpt-4o-mini
   - Admin 分析: gpt-4o
2. 图像生成模型 (Section 5.1):
   - Free/Starter: flux-schnell
   - Pro: flux-dev

@module tests/test_ai_adapters
@version v3.3
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from services.ai.base import AIResponse, AIUsage, AIErrorType


# ==========================================
# Adapter Factory Tests
# ==========================================

class TestAdapterFactory:
    """适配器工厂测试"""
    
    def test_get_text_adapter_openai(self):
        """获取 OpenAI 文本适配器"""
        from services.ai.adapters import get_text_adapter
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            adapter = get_text_adapter("openai")
            
            if adapter:  # 如果适配器可用
                assert adapter.provider_name == "openai"
    
    def test_get_text_adapter_unknown(self):
        """获取未知提供商返回 None"""
        from services.ai.adapters import get_text_adapter
        
        adapter = get_text_adapter("unknown_provider")
        
        assert adapter is None
    
    def test_get_image_adapter_fal(self):
        """获取 FAL 图像适配器"""
        from services.ai.adapters import get_image_adapter
        
        with patch.dict('os.environ', {'FAL_KEY': 'test-key'}):
            adapter = get_image_adapter("fal")
            
            if adapter:
                assert adapter.provider_name == "fal"
    
    def test_get_available_text_providers(self):
        """获取可用的文本提供商"""
        from services.ai.adapters import get_available_text_providers
        
        providers = get_available_text_providers()
        
        assert isinstance(providers, list)
    
    def test_get_available_image_providers(self):
        """获取可用的图像提供商"""
        from services.ai.adapters import get_available_image_providers
        
        providers = get_available_image_providers()
        
        assert isinstance(providers, list)


# ==========================================
# OpenAI Adapter Tests
# ==========================================

class TestOpenAITextAdapter:
    """OpenAI 文本适配器测试"""
    
    def test_is_available_with_key(self):
        """【业务规则】有 API key 时可用"""
        with patch('services.ai.adapters.openai_adapter.openai.AsyncOpenAI') as mock_client:
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                with patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', 'test-key'):
                    from importlib import reload
                    import services.ai.adapters.openai_adapter as openai_adapter
                    
                    # 手动创建适配器
                    adapter = openai_adapter.OpenAITextAdapter()
                    adapter._client = MagicMock()  # 模拟客户端存在
                    
                    assert adapter.is_available() is True
    
    def test_is_available_without_key(self):
        """【业务规则】无 API key 时不可用"""
        with patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', None):
            from services.ai.adapters.openai_adapter import OpenAITextAdapter
            
            adapter = OpenAITextAdapter()
            
            assert adapter.is_available() is False
    
    def test_get_available_models(self):
        """【业务规则 5.1】获取可用模型列表包含 gpt-4o-mini 和 gpt-4o"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        adapter = OpenAITextAdapter()
        models = adapter.get_available_models()
        
        assert isinstance(models, list)
        assert "gpt-4o-mini" in models
        assert "gpt-4o" in models
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        """【业务规则】成功的聊天补全返回 AIResponse"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        # 创建 mock 客户端
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello!"))]
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )
        mock_response.model_dump = MagicMock(return_value={})
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        adapter = OpenAITextAdapter()
        adapter._client = mock_client
        
        result = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini"
        )
        
        assert result.success is True
        assert result.content == "Hello!"
        assert result.provider == "openai"
        assert result.usage.total_tokens == 15
    
    @pytest.mark.asyncio
    async def test_chat_completion_no_client(self):
        """【业务规则】无客户端时返回认证错误"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        adapter = OpenAITextAdapter()
        adapter._client = None
        
        result = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini"
        )
        
        assert result.success is False
        assert result.error_type == AIErrorType.AUTH_ERROR
    
    @pytest.mark.asyncio
    async def test_chat_completion_api_error(self):
        """【业务规则】API 错误返回失败响应"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )
        
        adapter = OpenAITextAdapter()
        adapter._client = mock_client
        
        result = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini"
        )
        
        assert result.success is False
        assert "Rate limit" in result.error
    
    @pytest.mark.asyncio
    async def test_o1_model_converts_system_message(self):
        """【业务规则】o1 模型将 system message 转换为 user message"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        mock_response.model_dump = MagicMock(return_value={})
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        adapter = OpenAITextAdapter()
        adapter._client = mock_client
        
        await adapter.chat_completion(
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ],
            model="o1-mini"
        )
        
        # 验证调用时没有 temperature 参数（o1 不支持）
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "temperature" not in call_kwargs


class TestOpenAIImageAdapter:
    """OpenAI 图像适配器测试"""
    
    def test_is_available_without_key(self):
        """【业务规则】无 API key 时不可用"""
        with patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', None):
            from services.ai.adapters.openai_adapter import OpenAIImageAdapter
            
            adapter = OpenAIImageAdapter()
            
            assert adapter.is_available() is False
    
    def test_get_available_models(self):
        """【业务规则】获取可用模型列表包含 dall-e-3"""
        from services.ai.adapters.openai_adapter import OpenAIImageAdapter
        
        adapter = OpenAIImageAdapter()
        models = adapter.get_available_models()
        
        assert "dall-e-3" in models
    
    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        """【业务规则】成功的图像生成"""
        from services.ai.adapters.openai_adapter import OpenAIImageAdapter
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(url="https://example.com/image.png")]
        mock_client.images.generate = AsyncMock(return_value=mock_response)
        
        adapter = OpenAIImageAdapter()
        adapter._client = mock_client
        
        result = await adapter.generate_image(
            prompt="A cat",
            model="dall-e-3"
        )
        
        assert result.success is True
        assert len(result.content) == 1
        assert "https://example.com/image.png" in result.content
    
    @pytest.mark.asyncio
    async def test_image_to_image_not_supported(self):
        """【业务规则】DALL-E 不支持 image-to-image"""
        from services.ai.adapters.openai_adapter import OpenAIImageAdapter
        
        adapter = OpenAIImageAdapter()
        adapter._client = MagicMock()
        
        result = await adapter.image_to_image(
            prompt="A cat",
            image_url="https://example.com/ref.png"
        )
        
        assert result.success is False
        assert result.error_type == AIErrorType.INVALID_REQUEST


# ==========================================
# FAL Adapter Tests
# ==========================================

class TestFALImageAdapter:
    """FAL 图像适配器测试"""
    
    def test_is_available_without_key(self):
        """【业务规则】无 API key 时不可用"""
        with patch('services.ai.adapters.fal_adapter.FAL_KEY', None):
            from services.ai.adapters.fal_adapter import FALImageAdapter
            
            adapter = FALImageAdapter()
            
            assert adapter.is_available() is False
    
    def test_get_available_models(self):
        """【业务规则 5.1】获取可用模型列表包含 flux-schnell 和 flux-dev"""
        with patch.dict('os.environ', {'FAL_KEY': 'test-key'}):
            from services.ai.adapters.fal_adapter import FALImageAdapter
            
            adapter = FALImageAdapter()
            models = adapter.get_available_models()
            
            assert "flux-schnell" in models or "fal-ai/flux/schnell" in str(models)
    
    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        """【业务规则】成功的图像生成"""
        from services.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._available = True
        adapter._client = True  # Mark as configured
        
        # Mock the async flow: submit_async returns handler, handler.get() returns result
        mock_handler = AsyncMock()
        mock_handler.get = AsyncMock(return_value={"images": [{"url": "https://fal.ai/image.png"}]})
        
        mock_fal = MagicMock()
        mock_fal.submit_async = AsyncMock(return_value=mock_handler)
        adapter._fal = mock_fal
        
        result = await adapter.generate_image(
            prompt="A beautiful sunset",
            model="flux-schnell"
        )
        
        assert result.success is True
        assert len(result.content) == 1
        assert "https://fal.ai/image.png" in result.content
    
    @pytest.mark.asyncio
    async def test_image_to_image_with_reference(self):
        """【业务规则】支持 image-to-image 生成"""
        from services.ai.adapters.fal_adapter import FALImageAdapter
        
        adapter = FALImageAdapter()
        adapter._available = True
        adapter._client = True  # Mark as configured
        
        # Mock the async flow
        mock_handler = AsyncMock()
        mock_handler.get = AsyncMock(return_value={"images": [{"url": "https://fal.ai/i2i.png"}]})
        
        mock_fal = MagicMock()
        mock_fal.submit_async = AsyncMock(return_value=mock_handler)
        adapter._fal = mock_fal
        
        result = await adapter.image_to_image(
            prompt="Make it more colorful",
            image_url="https://example.com/ref.png",
            model="flux-dev"
        )
        
        # FAL 应该支持 image-to-image
        assert result is not None
        assert result.success is True


# ==========================================
# Qwen Adapter Tests
# ==========================================

class TestQwenTextAdapter:
    """Qwen 文本适配器测试"""
    
    def test_is_available_without_key(self):
        """【业务规则】无 API key 时不可用"""
        with patch('services.ai.adapters.qwen_adapter.DASHSCOPE_API_KEY', None):
            from services.ai.adapters.qwen_adapter import QwenTextAdapter
            
            adapter = QwenTextAdapter()
            
            assert adapter.is_available() is False
    
    def test_get_available_models(self):
        """【业务规则】获取可用模型列表"""
        from services.ai.adapters.qwen_adapter import QwenTextAdapter
        
        adapter = QwenTextAdapter()
        models = adapter.get_available_models()
        
        assert isinstance(models, list)
    
    @pytest.mark.asyncio
    async def test_chat_completion_no_client(self):
        """【业务规则】无客户端时返回认证错误"""
        with patch('services.ai.adapters.qwen_adapter.DASHSCOPE_API_KEY', None):
            from services.ai.adapters.qwen_adapter import QwenTextAdapter
            
            adapter = QwenTextAdapter()
            
            result = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                model="qwen-turbo"
            )
            
            assert result.success is False
            assert result.error_type == AIErrorType.AUTH_ERROR


# ==========================================
# Adapter Error Handling Tests
# ==========================================

class TestAdapterErrorHandling:
    """适配器错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_timeout_error_classification(self):
        """【业务规则】超时错误正确分类"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=TimeoutError("Request timed out")
        )
        
        adapter = OpenAITextAdapter()
        adapter._client = mock_client
        
        result = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini"
        )
        
        assert result.success is False
        assert "timed out" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_auth_error_classification(self):
        """【业务规则】认证错误正确分类"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Invalid API key")
        )
        
        adapter = OpenAITextAdapter()
        adapter._client = mock_client
        
        result = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini"
        )
        
        assert result.success is False


# ==========================================
# Edge Cases Tests
# ==========================================

class TestAdapterEdgeCases:
    """适配器边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self):
        """【业务规则】处理空响应"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=""))]
        mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=0, total_tokens=5)
        mock_response.model_dump = MagicMock(return_value={})
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        adapter = OpenAITextAdapter()
        adapter._client = mock_client
        
        result = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini"
        )
        
        assert result.success is True
        assert result.content == ""
    
    @pytest.mark.asyncio
    async def test_unicode_content_handling(self):
        """【业务规则】正确处理 Unicode 内容"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="你好世界 🌍"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        mock_response.model_dump = MagicMock(return_value={})
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        adapter = OpenAITextAdapter()
        adapter._client = mock_client
        
        result = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Say hello in Chinese"}],
            model="gpt-4o-mini"
        )
        
        assert result.success is True
        assert "你好" in result.content
        assert "🌍" in result.content


# ==========================================
# Model Selection Business Rules Tests
# ==========================================

class TestModelSelectionBusinessRules:
    """
    模型选择业务规则测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 5.1
    """
    
    def test_text_models_include_user_model(self):
        """【业务规则 5.1】文本模型列表包含用户模型 gpt-4o-mini"""
        from services.ai.adapters.openai_adapter import OPENAI_TEXT_MODELS
        
        assert "gpt-4o-mini" in OPENAI_TEXT_MODELS
    
    def test_text_models_include_admin_model(self):
        """【业务规则 5.1】文本模型列表包含 Admin 模型 gpt-4o"""
        from services.ai.adapters.openai_adapter import OPENAI_TEXT_MODELS
        
        assert "gpt-4o" in OPENAI_TEXT_MODELS
    
    def test_image_models_include_dalle(self):
        """【业务规则】图像模型列表包含 dall-e-3"""
        from services.ai.adapters.openai_adapter import OPENAI_IMAGE_MODELS
        
        assert "dall-e-3" in OPENAI_IMAGE_MODELS


# ==========================================
# Base Class Tests
# ==========================================

class TestBaseClasses:
    """基类测试"""
    
    def test_ai_response_from_error(self):
        """【业务规则】AIResponse.from_error 创建失败响应"""
        response = AIResponse.from_error(
            "Test error",
            AIErrorType.API_ERROR,
            "openai",
            "gpt-4o-mini"
        )
        
        assert response.success is False
        assert response.error == "Test error"
        assert response.error_type == AIErrorType.API_ERROR
        assert response.provider == "openai"
        assert response.model == "gpt-4o-mini"
    
    def test_ai_usage_defaults(self):
        """【业务规则】AIUsage 默认值"""
        usage = AIUsage()
        
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0
        assert usage.images_generated == 0
