"""
Unit Tests for AI Base Classes
AI 基础类单元测试

Tests:
- AIResponse
- AIUsage
- AIMessage
- AIErrorType
- classify_error
"""

import pytest
from unittest.mock import MagicMock, patch
import asyncio
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接从 base 模块导入，避免 services.ai 的完整导入链
from services.ai.base import (
    AIResponse,
    AIUsage,
    AIMessage,
    AICallType,
    AIErrorType,
    classify_error,
    BaseTextAdapter,
    BaseImageAdapter,
)


# ==========================================
# AIUsage Tests
# ==========================================

class TestAIUsage:
    """AIUsage 数据类测试"""
    
    def test_default_values(self):
        """默认值测试"""
        usage = AIUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0
        assert usage.images_generated == 0
    
    def test_total_property_with_total_tokens(self):
        """total 属性 - 使用 total_tokens"""
        usage = AIUsage(input_tokens=100, output_tokens=50, total_tokens=150)
        assert usage.total == 150
    
    def test_total_property_calculated(self):
        """total 属性 - 计算值"""
        usage = AIUsage(input_tokens=100, output_tokens=50)
        assert usage.total == 150
    
    def test_with_images(self):
        """图像生成统计"""
        usage = AIUsage(images_generated=4)
        assert usage.images_generated == 4


# ==========================================
# AIMessage Tests
# ==========================================

class TestAIMessage:
    """AIMessage 数据类测试"""
    
    def test_to_dict(self):
        """转换为字典"""
        msg = AIMessage(role="user", content="Hello")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "Hello"}
    
    def test_system_message(self):
        """系统消息"""
        msg = AIMessage(role="system", content="You are helpful")
        assert msg.role == "system"
        assert msg.content == "You are helpful"
    
    def test_assistant_message(self):
        """助手消息"""
        msg = AIMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"


# ==========================================
# AIResponse Tests
# ==========================================

class TestAIResponse:
    """AIResponse 数据类测试"""
    
    def test_successful_text_response(self):
        """成功的文本响应"""
        response = AIResponse(
            success=True,
            content="Hello, world!",
            usage=AIUsage(input_tokens=10, output_tokens=5),
            model="gpt-4o-mini",
            provider="openai",
            latency_ms=150
        )
        assert response.success is True
        assert response.content == "Hello, world!"
        assert response.error is None
    
    def test_successful_image_response(self):
        """成功的图像响应 (URL 列表)"""
        response = AIResponse(
            success=True,
            content=["https://example.com/img1.png", "https://example.com/img2.png"],
            usage=AIUsage(images_generated=2),
            model="flux-schnell",
            provider="fal",
            latency_ms=2500
        )
        assert response.success is True
        assert len(response.content) == 2
        assert response.usage.images_generated == 2
    
    def test_from_error_factory(self):
        """from_error 工厂方法"""
        response = AIResponse.from_error(
            error="API key invalid",
            error_type=AIErrorType.AUTH_ERROR,
            provider="openai",
            model="gpt-4o"
        )
        assert response.success is False
        assert response.error == "API key invalid"
        assert response.error_type == AIErrorType.AUTH_ERROR
        assert response.provider == "openai"
    
    def test_default_values(self):
        """默认值"""
        response = AIResponse(success=True)
        assert response.content == ""
        assert response.model == ""
        assert response.provider == ""
        assert response.latency_ms == 0
        assert response.raw_response is None


# ==========================================
# AIErrorType Tests
# ==========================================

class TestAIErrorType:
    """AIErrorType 常量测试"""
    
    def test_error_types_exist(self):
        """错误类型常量存在"""
        assert AIErrorType.RATE_LIMIT == "rate_limit"
        assert AIErrorType.TIMEOUT == "timeout"
        assert AIErrorType.API_ERROR == "api_error"
        assert AIErrorType.AUTH_ERROR == "auth_error"
        assert AIErrorType.INVALID_REQUEST == "invalid_request"
        assert AIErrorType.MODEL_NOT_FOUND == "model_not_found"
        assert AIErrorType.CONTENT_FILTER == "content_filter"
        assert AIErrorType.QUOTA_EXCEEDED == "quota_exceeded"
        assert AIErrorType.NETWORK_ERROR == "network_error"


# ==========================================
# classify_error Tests
# ==========================================

class TestClassifyError:
    """classify_error 函数测试"""
    
    def test_timeout_error(self):
        """超时错误分类"""
        import asyncio
        error = asyncio.TimeoutError()
        assert classify_error(error) == AIErrorType.TIMEOUT
    
    def test_connection_error(self):
        """连接错误分类"""
        error = ConnectionError("Connection refused")
        assert classify_error(error) == AIErrorType.NETWORK_ERROR
    
    def test_rate_limit_from_message(self):
        """从消息识别限流"""
        error = Exception("Rate limit exceeded")
        assert classify_error(error) == AIErrorType.RATE_LIMIT
    
    def test_rate_limit_429(self):
        """429 状态码识别"""
        error = Exception("HTTP 429 Too Many Requests")
        assert classify_error(error) == AIErrorType.RATE_LIMIT
    
    def test_auth_error_401(self):
        """401 状态码识别"""
        error = Exception("HTTP 401 Unauthorized")
        assert classify_error(error) == AIErrorType.AUTH_ERROR
    
    def test_auth_error_api_key(self):
        """API key 错误识别"""
        error = Exception("Invalid API key provided")
        assert classify_error(error) == AIErrorType.AUTH_ERROR
    
    def test_quota_exceeded(self):
        """配额超限识别"""
        error = Exception("You have exceeded your quota")
        assert classify_error(error) == AIErrorType.QUOTA_EXCEEDED
    
    def test_content_filter(self):
        """内容过滤识别"""
        error = Exception("Content was filtered due to safety concerns")
        assert classify_error(error) == AIErrorType.CONTENT_FILTER
    
    def test_unknown_error(self):
        """未知错误默认分类"""
        error = Exception("Something unexpected happened")
        # 未知错误返回 'unknown' 或 'api_error' 都是合理的
        assert classify_error(error) in [AIErrorType.API_ERROR, "unknown"]


# ==========================================
# AICallType Tests
# ==========================================

class TestAICallType:
    """AICallType 枚举测试"""
    
    def test_call_types(self):
        """调用类型"""
        assert AICallType.TEXT == "text"
        assert AICallType.IMAGE == "image"


# ==========================================
# Base Adapter Abstract Methods Tests
# ==========================================

class TestBaseTextAdapter:
    """BaseTextAdapter 抽象类测试"""
    
    def test_cannot_instantiate_abstract(self):
        """不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            BaseTextAdapter()
    
    def test_concrete_implementation(self):
        """具体实现测试"""
        class ConcreteTextAdapter(BaseTextAdapter):
            provider_name = "test"
            
            def is_available(self) -> bool:
                return True
            
            def get_available_models(self):
                return ["model-1"]
            
            async def chat_completion(self, messages, model, **kwargs):
                return AIResponse(success=True, content="test")
        
        adapter = ConcreteTextAdapter()
        assert adapter.is_available() is True
        assert adapter.provider_name == "test"


class TestBaseImageAdapter:
    """BaseImageAdapter 抽象类测试"""
    
    def test_cannot_instantiate_abstract(self):
        """不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            BaseImageAdapter()
    
    def test_concrete_implementation(self):
        """具体实现测试"""
        class ConcreteImageAdapter(BaseImageAdapter):
            provider_name = "test_image"
            
            def is_available(self) -> bool:
                return True
            
            def get_available_models(self):
                return ["image-model-1"]
            
            async def generate_image(self, prompt, model, **kwargs):
                return AIResponse(success=True, content=["url1"])
            
            async def image_to_image(self, prompt, image_url, model, **kwargs):
                return AIResponse(success=True, content=["url1"])
        
        adapter = ConcreteImageAdapter()
        assert adapter.is_available() is True


# ==========================================
# Edge Cases
# ==========================================

class TestEdgeCases:
    """边界情况测试"""
    
    def test_empty_content(self):
        """空内容响应"""
        response = AIResponse(success=True, content="")
        assert response.success is True
        assert response.content == ""
    
    def test_empty_image_list(self):
        """空图像列表"""
        response = AIResponse(success=True, content=[])
        assert response.success is True
        assert response.content == []
    
    def test_large_token_count(self):
        """大 token 数"""
        usage = AIUsage(
            input_tokens=1_000_000,
            output_tokens=500_000,
            total_tokens=1_500_000
        )
        assert usage.total == 1_500_000
    
    def test_unicode_content(self):
        """Unicode 内容"""
        response = AIResponse(
            success=True,
            content="你好世界! 🎉 مرحبا"
        )
        assert "你好" in response.content
        assert "🎉" in response.content
    
    def test_very_long_error_message(self):
        """超长错误消息"""
        long_error = "Error: " + "x" * 10000
        response = AIResponse.from_error(long_error, AIErrorType.API_ERROR)
        assert len(response.error) == len(long_error)
