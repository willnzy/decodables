"""
OpenAI Adapter Tests
OpenAI 适配器测试
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os


class TestOpenAITextAdapter:
    @patch.dict(os.environ, {'OPENAI_API_KEY': ''}, clear=True)
    @patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', '')
    def test_not_available_without_key(self):
        from shared.ai.adapters.openai_adapter import OpenAITextAdapter
        adapter = OpenAITextAdapter()
        assert adapter.is_available() is False

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', 'test-key')
    @patch('services.ai.adapters.openai_adapter.openai.AsyncOpenAI')
    def test_available_with_key(self, mock_client_class):
        from shared.ai.adapters.openai_adapter import OpenAITextAdapter
        adapter = OpenAITextAdapter()
        assert adapter.is_available() is True

    def test_get_available_models(self):
        from shared.ai.adapters.openai_adapter import OpenAITextAdapter
        adapter = OpenAITextAdapter()
        models = adapter.get_available_models()
        assert 'gpt-4o-mini' in models
        assert 'gpt-4o' in models

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', 'test-key')
    @patch('services.ai.adapters.openai_adapter.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, mock_client_class):
        from shared.ai.adapters.openai_adapter import OpenAITextAdapter
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello!"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        mock_response.model_dump.return_value = {}
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        adapter = OpenAITextAdapter()
        response = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini"
        )
        
        assert response.success is True
        assert response.content == "Hello!"

    @pytest.mark.asyncio
    async def test_chat_completion_no_client(self):
        from shared.ai.adapters.openai_adapter import OpenAITextAdapter
        
        adapter = OpenAITextAdapter()
        adapter._client = None
        
        response = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini"
        )
        
        assert response.success is False
        assert "not configured" in response.error

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', 'test-key')
    @patch('services.ai.adapters.openai_adapter.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_completion_o1_model(self, mock_client_class):
        from shared.ai.adapters.openai_adapter import OpenAITextAdapter
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Reasoning result"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        mock_response.model_dump.return_value = {}
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        adapter = OpenAITextAdapter()
        response = await adapter.chat_completion(
            messages=[
                {"role": "system", "content": "You are a helper"},
                {"role": "user", "content": "Think about this"}
            ],
            model="o1-mini",
            max_tokens=1000
        )
        
        assert response.success is True

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', 'test-key')
    @patch('services.ai.adapters.openai_adapter.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_completion_error(self, mock_client_class):
        from shared.ai.adapters.openai_adapter import OpenAITextAdapter
        
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_client_class.return_value = mock_client
        
        adapter = OpenAITextAdapter()
        response = await adapter.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini"
        )
        
        assert response.success is False


class TestOpenAITextAdapterConvertSystem:
    def test_convert_system_to_user(self):
        from shared.ai.adapters.openai_adapter import OpenAITextAdapter
        
        adapter = OpenAITextAdapter()
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"}
        ]
        
        result = adapter._convert_system_to_user(messages)
        
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "Be helpful" in result[0]["content"]
        assert "Hello" in result[0]["content"]

    def test_convert_no_system(self):
        from shared.ai.adapters.openai_adapter import OpenAITextAdapter
        
        adapter = OpenAITextAdapter()
        messages = [{"role": "user", "content": "Hello"}]
        
        result = adapter._convert_system_to_user(messages)
        
        assert result == messages


class TestOpenAIImageAdapter:
    @patch.dict(os.environ, {'OPENAI_API_KEY': ''})
    @patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', '')
    def test_not_available_without_key(self):
        from shared.ai.adapters.openai_adapter import OpenAIImageAdapter
        adapter = OpenAIImageAdapter()
        assert adapter.is_available() is False

    def test_get_available_models(self):
        from shared.ai.adapters.openai_adapter import OpenAIImageAdapter
        adapter = OpenAIImageAdapter()
        models = adapter.get_available_models()
        assert 'dall-e-3' in models

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', 'test-key')
    @patch('services.ai.adapters.openai_adapter.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_generate_image_success(self, mock_client_class):
        from shared.ai.adapters.openai_adapter import OpenAIImageAdapter
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(url="https://example.com/image.png")]
        
        mock_client.images.generate = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        adapter = OpenAIImageAdapter()
        response = await adapter.generate_image(
            prompt="A cat",
            model="dall-e-3"
        )
        
        assert response.success is True
        assert len(response.content) == 1

    @pytest.mark.asyncio
    async def test_generate_image_no_client(self):
        from shared.ai.adapters.openai_adapter import OpenAIImageAdapter
        
        adapter = OpenAIImageAdapter()
        adapter._client = None
        
        response = await adapter.generate_image(
            prompt="A cat",
            model="dall-e-3"
        )
        
        assert response.success is False

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('services.ai.adapters.openai_adapter.OPENAI_API_KEY', 'test-key')
    @patch('services.ai.adapters.openai_adapter.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_generate_image_with_negative_prompt(self, mock_client_class):
        from shared.ai.adapters.openai_adapter import OpenAIImageAdapter
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(url="https://example.com/image.png")]
        
        mock_client.images.generate = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        adapter = OpenAIImageAdapter()
        response = await adapter.generate_image(
            prompt="A cat",
            model="dall-e-3",
            negative_prompt="dogs"
        )
        
        assert response.success is True
        # Check negative prompt was included
        call_args = mock_client.images.generate.call_args
        assert "Avoid:" in call_args[1]["prompt"]

    @pytest.mark.asyncio
    async def test_image_to_image_not_supported(self):
        from shared.ai.adapters.openai_adapter import OpenAIImageAdapter
        
        adapter = OpenAIImageAdapter()
        
        response = await adapter.image_to_image(
            prompt="Make it blue",
            image_url="http://example.com/img.png",
            model="dall-e-3"
        )
        
        assert response.success is False
        assert "not support" in response.error
