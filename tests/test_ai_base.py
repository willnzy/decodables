"""
AI Base Classes Tests
AI 基础类测试
"""

import pytest
from unittest.mock import MagicMock


class TestAICallType:
    def test_text_value(self):
        from shared.ai.base import AICallType
        assert AICallType.TEXT == "text"

    def test_image_value(self):
        from shared.ai.base import AICallType
        assert AICallType.IMAGE == "image"


class TestAIMessage:
    def test_creation(self):
        from shared.ai.base import AIMessage
        msg = AIMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_to_dict(self):
        from shared.ai.base import AIMessage
        msg = AIMessage(role="assistant", content="Hi there")
        d = msg.to_dict()
        assert d == {"role": "assistant", "content": "Hi there"}


class TestAIUsage:
    def test_default_values(self):
        from shared.ai.base import AIUsage
        usage = AIUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0

    def test_total_property_uses_total_tokens(self):
        from shared.ai.base import AIUsage
        usage = AIUsage(total_tokens=100)
        assert usage.total == 100

    def test_total_property_calculates_sum(self):
        from shared.ai.base import AIUsage
        usage = AIUsage(input_tokens=50, output_tokens=30, total_tokens=0)
        assert usage.total == 80

    def test_images_generated(self):
        from shared.ai.base import AIUsage
        usage = AIUsage(images_generated=5)
        assert usage.images_generated == 5


class TestAIResponse:
    def test_success_response(self):
        from shared.ai.base import AIResponse
        response = AIResponse(
            success=True,
            content="Hello!",
            model="gpt-4o-mini",
            provider="openai"
        )
        assert response.success is True
        assert response.content == "Hello!"

    def test_default_values(self):
        from shared.ai.base import AIResponse, AIUsage
        response = AIResponse(success=True)
        assert response.content == ""
        assert response.model == ""
        assert response.error is None

    def test_from_error_classmethod(self):
        from shared.ai.base import AIResponse
        response = AIResponse.from_error(
            error="Something went wrong",
            error_type="api_error",
            provider="openai",
            model="gpt-4o"
        )
        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.error_type == "api_error"

    def test_image_content(self):
        from shared.ai.base import AIResponse
        response = AIResponse(
            success=True,
            content=["url1.png", "url2.png"]
        )
        assert len(response.content) == 2


class TestAIErrorType:
    def test_error_type_constants(self):
        from shared.ai.base import AIErrorType
        
        assert AIErrorType.RATE_LIMIT == "rate_limit"
        assert AIErrorType.TIMEOUT == "timeout"
        assert AIErrorType.API_ERROR == "api_error"
        assert AIErrorType.AUTH_ERROR == "auth_error"
        assert AIErrorType.INVALID_REQUEST == "invalid_request"
        assert AIErrorType.MODEL_NOT_FOUND == "model_not_found"
        assert AIErrorType.CONTENT_FILTER == "content_filter"
        assert AIErrorType.QUOTA_EXCEEDED == "quota_exceeded"
        assert AIErrorType.NETWORK_ERROR == "network_error"
        assert AIErrorType.UNKNOWN == "unknown"


class TestClassifyError:
    def test_rate_limit(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Rate limit exceeded")
        assert classify_error(error) == AIErrorType.RATE_LIMIT

    def test_rate_limit_429(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Error 429: Too many requests")
        assert classify_error(error) == AIErrorType.RATE_LIMIT

    def test_timeout(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Request timed out")
        assert classify_error(error) == AIErrorType.TIMEOUT

    def test_timeout_exception_type(self):
        from shared.ai.base import classify_error, AIErrorType
        class TimeoutException(Exception):
            pass
        error = TimeoutException("Operation failed")
        assert classify_error(error) == AIErrorType.TIMEOUT

    def test_auth_error(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Invalid API key")
        assert classify_error(error) == AIErrorType.AUTH_ERROR

    def test_auth_error_401(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Error 401: Unauthorized")
        assert classify_error(error) == AIErrorType.AUTH_ERROR

    def test_content_filter(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Content blocked by safety filter")
        assert classify_error(error) == AIErrorType.CONTENT_FILTER

    def test_quota_exceeded(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Quota exceeded for this month")
        assert classify_error(error) == AIErrorType.QUOTA_EXCEEDED

    def test_model_not_found(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Model not found: gpt-5")
        assert classify_error(error) == AIErrorType.MODEL_NOT_FOUND

    def test_invalid_request(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Bad request: invalid parameter")
        assert classify_error(error) == AIErrorType.INVALID_REQUEST

    def test_network_error(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Connection refused")
        assert classify_error(error) == AIErrorType.NETWORK_ERROR

    def test_api_error_500(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Internal server error 500")
        assert classify_error(error) == AIErrorType.API_ERROR

    def test_unknown_error(self):
        from shared.ai.base import classify_error, AIErrorType
        error = Exception("Something completely unknown happened")
        assert classify_error(error) == AIErrorType.UNKNOWN


class TestBaseTextAdapter:
    def test_is_abstract(self):
        from shared.ai.base import BaseTextAdapter
        
        with pytest.raises(TypeError):
            BaseTextAdapter()

    def test_default_is_available(self):
        from shared.ai.base import BaseTextAdapter
        
        class TestAdapter(BaseTextAdapter):
            async def chat_completion(self, messages, model, **kwargs):
                pass
            def get_available_models(self):
                return []
        
        adapter = TestAdapter()
        assert adapter.is_available() is True

    def test_provider_name(self):
        from shared.ai.base import BaseTextAdapter
        
        class TestAdapter(BaseTextAdapter):
            provider_name = "test_provider"
            async def chat_completion(self, messages, model, **kwargs):
                pass
            def get_available_models(self):
                return []
        
        adapter = TestAdapter()
        assert adapter.provider_name == "test_provider"


class TestBaseImageAdapter:
    def test_is_abstract(self):
        from shared.ai.base import BaseImageAdapter
        
        with pytest.raises(TypeError):
            BaseImageAdapter()

    def test_default_is_available(self):
        from shared.ai.base import BaseImageAdapter
        
        class TestAdapter(BaseImageAdapter):
            async def generate_image(self, prompt, model, **kwargs):
                pass
            async def image_to_image(self, prompt, image_url, model, **kwargs):
                pass
            def get_available_models(self):
                return []
        
        adapter = TestAdapter()
        assert adapter.is_available() is True

    def test_provider_name(self):
        from shared.ai.base import BaseImageAdapter
        
        class TestAdapter(BaseImageAdapter):
            provider_name = "test_img_provider"
            async def generate_image(self, prompt, model, **kwargs):
                pass
            async def image_to_image(self, prompt, image_url, model, **kwargs):
                pass
            def get_available_models(self):
                return []
        
        adapter = TestAdapter()
        assert adapter.provider_name == "test_img_provider"
