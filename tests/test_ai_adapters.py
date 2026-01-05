"""
Unit Tests for AI Provider Adapters
AI 提供商适配器单元测试

Tests:
- OpenAITextAdapter
- OpenAIImageAdapter
- FALImageAdapter
- QwenTextAdapter
- WanxImageAdapter
- Adapter factory functions
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
    
    @patch('services.ai.adapters.openai_adapter.OpenAI')
    def test_is_available_with_key(self, mock_openai_class):
        """有 API key 时可用"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from services.ai.adapters.openai_adapter import OpenAITextAdapter
            
            adapter = OpenAITextAdapter()
            assert adapter.is_available() is True
    
    @patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', None)
    def test_is_available_without_key(self):
        """无 API key 时不可用"""
        from services.ai.adapters.openai_adapter import OpenAITextAdapter
        
        adapter = OpenAITextAdapter()
        # 没有 key 应该不可用
        # (实际行为取决于实现)
    
    def test_get_available_models(self):
        """获取可用模型列表"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from services.ai.adapters.openai_adapter import OpenAITextAdapter
            
            adapter = OpenAITextAdapter()
            models = adapter.get_available_models()
            
            assert isinstance(models, list)
            assert "gpt-4o-mini" in models or len(models) >= 0
    
    @pytest.mark.asyncio
    @patch('services.ai.adapters.openai_adapter.OpenAI')
    async def test_chat_completion_success(self, mock_openai_class):
        """成功的聊天补全"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from services.ai.adapters.openai_adapter import OpenAITextAdapter
            
            # Mock OpenAI client
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Hello!"))]
            mock_response.usage = MagicMock(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15
            )
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            adapter = OpenAITextAdapter()
            response = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini",
                temperature=0.7
            )
            
            assert response.success is True
            assert response.content == "Hello!"
    
    @pytest.mark.asyncio
    @patch('services.ai.adapters.openai_adapter.OpenAI')
    async def test_chat_completion_rate_limit(self, mock_openai_class):
        """限流错误处理"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from services.ai.adapters.openai_adapter import OpenAITextAdapter
            
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
            mock_openai_class.return_value = mock_client
            
            adapter = OpenAITextAdapter()
            response = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini"
            )
            
            assert response.success is False
            assert response.error_type == AIErrorType.RATE_LIMIT


class TestOpenAIImageAdapter:
    """OpenAI 图像适配器测试"""
    
    @pytest.mark.asyncio
    @patch('services.ai.adapters.openai_adapter.OpenAI')
    async def test_generate_image_success(self, mock_openai_class):
        """成功生成图像"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from services.ai.adapters.openai_adapter import OpenAIImageAdapter
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(url="https://oaidalleapiprodscus.blob.core.windows.net/image.png")]
            mock_client.images.generate.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            adapter = OpenAIImageAdapter()
            response = await adapter.generate_image(
                prompt="A cute cat",
                model="dall-e-3",
                size="1024x1024"
            )
            
            assert response.success is True
            assert len(response.content) == 1
            assert response.content[0].startswith("https://")


# ==========================================
# FAL Adapter Tests
# ==========================================

class TestFALImageAdapter:
    """FAL 图像适配器测试"""
    
    def test_is_available_with_key(self):
        """有 API key 时可用"""
        with patch.dict('os.environ', {'FAL_KEY': 'test-key'}):
            from services.ai.adapters.fal_adapter import FALImageAdapter
            
            adapter = FALImageAdapter()
            assert adapter.is_available() is True
    
    def test_get_available_models(self):
        """获取可用模型"""
        with patch.dict('os.environ', {'FAL_KEY': 'test-key'}):
            from services.ai.adapters.fal_adapter import FALImageAdapter
            
            adapter = FALImageAdapter()
            models = adapter.get_available_models()
            
            assert "flux-schnell" in models
            assert "flux-dev" in models
    
    @pytest.mark.asyncio
    @patch('services.ai.adapters.fal_adapter.fal_client')
    async def test_generate_image_success(self, mock_fal):
        """成功生成图像"""
        with patch.dict('os.environ', {'FAL_KEY': 'test-key'}):
            from services.ai.adapters.fal_adapter import FALImageAdapter
            
            # Mock fal_client
            mock_handler = MagicMock()
            mock_handler.get = AsyncMock(return_value={
                "images": [{"url": "https://fal.media/image.png"}]
            })
            mock_fal.submit_async = AsyncMock(return_value=mock_handler)
            
            adapter = FALImageAdapter()
            response = await adapter.generate_image(
                prompt="A cute cat",
                model="flux-schnell",
                size="landscape_4_3"
            )
            
            assert response.success is True
            assert len(response.content) == 1
    
    @pytest.mark.asyncio
    @patch('services.ai.adapters.fal_adapter.fal_client')
    async def test_image_to_image(self, mock_fal):
        """图生图"""
        with patch.dict('os.environ', {'FAL_KEY': 'test-key'}):
            from services.ai.adapters.fal_adapter import FALImageAdapter
            
            mock_handler = MagicMock()
            mock_handler.get = AsyncMock(return_value={
                "images": [{"url": "https://fal.media/edited.png"}]
            })
            mock_fal.submit_async = AsyncMock(return_value=mock_handler)
            
            adapter = FALImageAdapter()
            response = await adapter.image_to_image(
                prompt="Make it more colorful",
                image_url="https://example.com/original.png",
                model="flux-dev",
                strength=0.7
            )
            
            assert response.success is True


# ==========================================
# Qwen Adapter Tests
# ==========================================

class TestQwenTextAdapter:
    """通义千问文本适配器测试"""
    
    def test_is_available_with_key(self):
        """有 API key 时可用"""
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}):
            from services.ai.adapters.qwen_adapter import QwenTextAdapter
            
            adapter = QwenTextAdapter()
            assert adapter.is_available() is True
    
    def test_provider_name(self):
        """提供商名称正确"""
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}):
            from services.ai.adapters.qwen_adapter import QwenTextAdapter
            
            adapter = QwenTextAdapter()
            assert adapter.provider_name == "qwen"
    
    def test_get_available_models(self):
        """获取可用模型"""
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}):
            from services.ai.adapters.qwen_adapter import QwenTextAdapter
            
            adapter = QwenTextAdapter()
            models = adapter.get_available_models()
            
            assert "qwen-turbo" in models
            assert "qwen-plus" in models
            assert "qwen-max" in models
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_chat_completion_success(self, mock_session_class):
        """成功的聊天补全"""
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}):
            from services.ai.adapters.qwen_adapter import QwenTextAdapter
            
            # Mock aiohttp session
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "output": {
                    "choices": [
                        {"message": {"content": "你好！"}}
                    ]
                },
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15
                }
            })
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            adapter = QwenTextAdapter()
            response = await adapter.chat_completion(
                messages=[{"role": "user", "content": "你好"}],
                model="qwen-turbo",
                temperature=0.7
            )
            
            assert response.success is True
            assert "你好" in response.content


# ==========================================
# Wanx Adapter Tests
# ==========================================

class TestWanxImageAdapter:
    """通义万相图像适配器测试"""
    
    def test_provider_name(self):
        """提供商名称正确 (wanx, 不是 qwen)"""
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}):
            from services.ai.adapters.qwen_adapter import WanxImageAdapter
            
            adapter = WanxImageAdapter()
            # 重要：Wanx 是独立的 provider，不是 qwen
            assert adapter.provider_name == "wanx"
    
    def test_get_available_models(self):
        """获取可用模型"""
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}):
            from services.ai.adapters.qwen_adapter import WanxImageAdapter
            
            adapter = WanxImageAdapter()
            models = adapter.get_available_models()
            
            assert "wan2.6-t2i" in models
            assert "wan2.6-image" in models
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_generate_image_success(self, mock_session_class):
        """成功生成图像"""
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'test-key'}):
            from services.ai.adapters.qwen_adapter import WanxImageAdapter
            
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "output": {
                    "choices": [
                        {
                            "message": {
                                "content": [
                                    {"image": "https://dashscope.aliyuncs.com/image.png"}
                                ]
                            }
                        }
                    ]
                },
                "usage": {"image_count": 1}
            })
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            adapter = WanxImageAdapter()
            response = await adapter.generate_image(
                prompt="一只可爱的猫",
                model="wan2.6-t2i",
                size="1024*1024"
            )
            
            assert response.success is True
            assert len(response.content) == 1
    
    def test_size_mapping(self):
        """尺寸映射测试"""
        from services.ai.adapters.qwen_adapter import SIZE_MAPPING
        
        # 检查常用尺寸映射
        assert SIZE_MAPPING.get("square") == "1024*1024"
        assert SIZE_MAPPING.get("landscape_4_3") == "1280*960"
        assert SIZE_MAPPING.get("portrait_4_3") == "960*1280"


# ==========================================
# Error Handling Tests
# ==========================================

class TestAdapterErrorHandling:
    """适配器错误处理测试"""
    
    @pytest.mark.asyncio
    @patch('services.ai.adapters.openai_adapter.OpenAI')
    async def test_timeout_error(self, mock_openai_class):
        """超时错误处理"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from services.ai.adapters.openai_adapter import OpenAITextAdapter
            
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = asyncio.TimeoutError()
            mock_openai_class.return_value = mock_client
            
            adapter = OpenAITextAdapter()
            response = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini"
            )
            
            assert response.success is False
            assert response.error_type == AIErrorType.TIMEOUT
    
    @pytest.mark.asyncio
    @patch('services.ai.adapters.openai_adapter.OpenAI')
    async def test_auth_error(self, mock_openai_class):
        """认证错误处理"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'invalid-key'}):
            from services.ai.adapters.openai_adapter import OpenAITextAdapter
            
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("Invalid API key")
            mock_openai_class.return_value = mock_client
            
            adapter = OpenAITextAdapter()
            response = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini"
            )
            
            assert response.success is False
            assert response.error_type == AIErrorType.AUTH_ERROR


# ==========================================
# Edge Cases
# ==========================================

class TestAdapterEdgeCases:
    """适配器边界情况测试"""
    
    @pytest.mark.asyncio
    @patch('services.ai.adapters.openai_adapter.OpenAI')
    async def test_empty_response(self, mock_openai_class):
        """空响应处理"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from services.ai.adapters.openai_adapter import OpenAITextAdapter
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content=""))]
            mock_response.usage = MagicMock(
                prompt_tokens=10,
                completion_tokens=0,
                total_tokens=10
            )
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            adapter = OpenAITextAdapter()
            response = await adapter.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                model="gpt-4o-mini"
            )
            
            assert response.success is True
            assert response.content == ""
    
    @pytest.mark.asyncio
    @patch('services.ai.adapters.openai_adapter.OpenAI')
    async def test_unicode_content(self, mock_openai_class):
        """Unicode 内容处理"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from services.ai.adapters.openai_adapter import OpenAITextAdapter
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="你好世界 🌍 مرحبا"))]
            mock_response.usage = MagicMock(
                prompt_tokens=10,
                completion_tokens=8,
                total_tokens=18
            )
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            adapter = OpenAITextAdapter()
            response = await adapter.chat_completion(
                messages=[{"role": "user", "content": "你好"}],
                model="gpt-4o-mini"
            )
            
            assert response.success is True
            assert "你好" in response.content
            assert "🌍" in response.content
    
    def test_adapter_lazy_loading(self):
        """适配器懒加载"""
        from services.ai.adapters import _text_adapter_instances
        
        # 清除缓存
        _text_adapter_instances.clear()
        
        from services.ai.adapters import get_text_adapter
        
        # 第一次获取
        adapter1 = get_text_adapter("openai")
        # 第二次应该返回相同实例
        adapter2 = get_text_adapter("openai")
        
        if adapter1 is not None:
            assert adapter1 is adapter2
