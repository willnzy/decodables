"""
Story Generator Tests
故事生成测试
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock


class TestGetOpenAIClient:
    @patch('shared.ai.story_generator.OpenAI')
    def test_lazy_loads_client(self, mock_openai):
        import services.ai.story_generator as sg
        sg._client = None  # Reset
        
        mock_openai.return_value = MagicMock()
        
        client = sg.get_openai_client()
        
        assert client is not None
        mock_openai.assert_called_once()

    @patch('shared.ai.story_generator.OpenAI')
    def test_returns_cached_client(self, mock_openai):
        import services.ai.story_generator as sg
        
        mock_client = MagicMock()
        sg._client = mock_client
        
        client = sg.get_openai_client()
        
        assert client is mock_client
        mock_openai.assert_not_called()
        
        # Cleanup
        sg._client = None


class TestOpenAIClientProxy:
    @patch('shared.ai.story_generator.get_openai_client')
    def test_proxies_attribute_access(self, mock_get_client):
        from shared.ai.story_generator import _OpenAIClientProxy
        
        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_get_client.return_value = mock_client
        
        proxy = _OpenAIClientProxy()
        _ = proxy.chat
        
        mock_get_client.assert_called_once()


class TestGenerateStoryJson:
    @patch('shared.ai.story_generator.unified_text_service')
    def test_successful_generation(self, mock_service):
        from shared.ai.story_generator import generate_story_json
        from shared.ai.base import AIResponse
        
        story_json = json.dumps({
            "title": "Test Story",
            "visual_style": "cartoon",
            "main_character": "A cat",
            "pages": [{"page_number": i, "story_text": f"Page {i}", "image_prompt": f"Prompt {i}"} for i in range(1, 9)]
        })
        
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=True,
            content=story_json,
            model="gpt-4o-mini",
            provider="openai"
        ))
        
        result = generate_story_json("A cat story", user_id="user_123", tier="pro")
        
        assert result is not None
        assert result["title"] == "Test Story"

    @patch('shared.ai.story_generator.unified_text_service')
    def test_failed_response(self, mock_service):
        from shared.ai.story_generator import generate_story_json
        from shared.ai.base import AIResponse
        
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=False,
            error="API Error"
        ))
        
        result = generate_story_json("A cat story")
        
        assert result is None

    @patch('shared.ai.story_generator.unified_text_service')
    def test_invalid_json_response(self, mock_service):
        from shared.ai.story_generator import generate_story_json
        from shared.ai.base import AIResponse
        
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=True,
            content="Not valid JSON {"
        ))
        
        result = generate_story_json("A cat story")
        
        assert result is None

    @patch('shared.ai.story_generator.unified_text_service')
    def test_exception_handling(self, mock_service):
        from shared.ai.story_generator import generate_story_json
        
        mock_service.chat = AsyncMock(side_effect=Exception("Unexpected error"))
        
        result = generate_story_json("A cat story")
        
        assert result is None


class TestGenerateStoryJsonAsync:
    @pytest.mark.asyncio
    @patch('shared.ai.story_generator.unified_text_service')
    async def test_successful_async_generation(self, mock_service):
        from shared.ai.story_generator import generate_story_json_async
        from shared.ai.base import AIResponse
        
        story_json = json.dumps({
            "title": "Async Story",
            "visual_style": "watercolor",
            "main_character": "A dog",
            "pages": [{"page_number": i, "story_text": f"Page {i}", "image_prompt": f"Prompt {i}"} for i in range(1, 9)]
        })
        
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=True,
            content=story_json,
            model="gpt-4o-mini",
            provider="openai"
        ))
        
        result = await generate_story_json_async("A dog story", user_id="user_456")
        
        assert result is not None
        assert result["title"] == "Async Story"

    @pytest.mark.asyncio
    @patch('shared.ai.story_generator.unified_text_service')
    async def test_failed_async_response(self, mock_service):
        from shared.ai.story_generator import generate_story_json_async
        from shared.ai.base import AIResponse
        
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=False,
            error="Rate limit"
        ))
        
        result = await generate_story_json_async("A story")
        
        assert result is None

    @pytest.mark.asyncio
    @patch('shared.ai.story_generator.unified_text_service')
    async def test_invalid_json_async(self, mock_service):
        from shared.ai.story_generator import generate_story_json_async
        from shared.ai.base import AIResponse
        
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=True,
            content="invalid json"
        ))
        
        result = await generate_story_json_async("A story")
        
        assert result is None

    @pytest.mark.asyncio
    @patch('shared.ai.story_generator.unified_text_service')
    async def test_exception_async(self, mock_service):
        from shared.ai.story_generator import generate_story_json_async
        
        mock_service.chat = AsyncMock(side_effect=Exception("Error"))
        
        result = await generate_story_json_async("A story")
        
        assert result is None


class TestStorySystemPrompt:
    def test_prompt_exists(self):
        from shared.ai.story_generator import STORY_SYSTEM_PROMPT
        
        assert "8-page" in STORY_SYSTEM_PROMPT
        assert "JSON" in STORY_SYSTEM_PROMPT
        assert "children's book" in STORY_SYSTEM_PROMPT
