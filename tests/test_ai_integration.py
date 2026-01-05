"""
Integration Tests for AI Model Configuration System
AI 模型配置系统集成测试

Tests end-to-end flows:
- Story generation with unified service
- Prompt enhancement with unified service
- Image generation with unified service
- Canary release flow
- Usage tracking flow
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, Mock
import asyncio

from services.ai.base import AIResponse, AIUsage, AIErrorType


# ==========================================
# Story Generator Integration Tests
# ==========================================

class TestStoryGeneratorIntegration:
    """故事生成器集成测试"""
    
    @patch('services.ai.story_generator.unified_text_service')
    def test_generate_story_json_success(self, mock_service):
        """成功生成故事 JSON"""
        from services.ai.story_generator import generate_story_json
        
        # Mock unified service response
        mock_response = AIResponse(
            success=True,
            content='{"title": "Test Story", "pages": []}',
            model="gpt-4o-mini",
            provider="openai"
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = generate_story_json(
            topic="A cat's adventure",
            user_id="user_123",
            tier="free"
        )
        
        assert result is not None
        assert 'title' in result
        assert result['title'] == "Test Story"
    
    @patch('services.ai.story_generator.unified_text_service')
    def test_generate_story_json_failure(self, mock_service):
        """故事生成失败返回 None"""
        from services.ai.story_generator import generate_story_json
        
        mock_response = AIResponse(
            success=False,
            error="API Error",
            error_type=AIErrorType.API_ERROR
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = generate_story_json(topic="Test topic")
        
        assert result is None
    
    @patch('services.ai.story_generator.unified_text_service')
    def test_generate_story_json_invalid_json(self, mock_service):
        """无效 JSON 响应返回 None"""
        from services.ai.story_generator import generate_story_json
        
        mock_response = AIResponse(
            success=True,
            content="Not a valid JSON",
            model="gpt-4o-mini",
            provider="openai"
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = generate_story_json(topic="Test topic")
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('services.ai.story_generator.unified_text_service')
    async def test_generate_story_json_async(self, mock_service):
        """异步版本故事生成"""
        from services.ai.story_generator import generate_story_json_async
        
        mock_response = AIResponse(
            success=True,
            content='{"title": "Async Story", "pages": []}',
            model="gpt-4o-mini",
            provider="openai"
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = await generate_story_json_async(
            topic="Async test",
            user_id="user_123",
            tier="pro"
        )
        
        assert result is not None
        assert result['title'] == "Async Story"


# ==========================================
# Prompt Enhancer Integration Tests
# ==========================================

class TestPromptEnhancerIntegration:
    """提示词增强器集成测试"""
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_prompt_success(self, mock_service):
        """成功增强提示词"""
        from services.ai.prompt_enhancer import enhance_prompt
        
        mock_response = AIResponse(
            success=True,
            content='{"enhanced_prompt": "A beautiful orange cat sitting in a sunny garden...", "key_elements": ["cat", "garden"], "composition": "centered"}',
            model="gpt-4o-mini",
            provider="openai"
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_prompt(
            theme="A cat in a garden",
            character="orange tabby cat",
            style="cartoon",
            mode="guided",
            user_id="user_123",
            tier="free"
        )
        
        assert result is not None
        assert 'enhanced_prompt' in result
        assert 'key_elements' in result
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_prompt_fallback_on_failure(self, mock_service):
        """失败时使用本地 fallback"""
        from services.ai.prompt_enhancer import enhance_prompt
        
        mock_response = AIResponse(
            success=False,
            error="Service unavailable"
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_prompt(
            theme="A cat",
            style="cartoon"
        )
        
        # 应该返回 fallback 结果
        assert result is not None
        assert 'enhanced_prompt' in result
        assert result.get('fallback') is True
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_asset_prompt_success(self, mock_service):
        """5W1H 模式增强成功"""
        from services.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = AIResponse(
            success=True,
            content='{"enhanced_prompt": "A curious orange cat exploring a magical garden...", "key_elements": ["cat", "garden"], "composition": "rule-of-thirds", "color_palette": "warm"}',
            model="gpt-4o-mini",
            provider="openai"
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_asset_prompt(
            who="A curious orange cat",
            what="exploring",
            where="in a magical garden",
            style="fantasy",
            moods=["warm", "adventurous"],
            mode="flexible",
            creativity_level=0.7,
            user_id="user_123",
            tier="pro"
        )
        
        assert result is not None
        assert 'enhanced_prompt' in result
        assert 'color_palette' in result


# ==========================================
# Image Generator Integration Tests
# ==========================================

class TestImageGeneratorIntegration:
    """图像生成器集成测试"""
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.unified_image_service')
    @patch('services.ai.image_generator.download_and_upload_image')
    @patch('services.ai.image_generator.upload_reference_image')
    async def test_generate_8_images_success(
        self, mock_upload_ref, mock_download_upload, mock_service
    ):
        """成功生成多张图像"""
        from services.ai.image_generator import generate_8_images
        
        mock_service.generate = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://fal.ai/generated1.png"],
            model="flux-schnell",
            provider="fal"
        ))
        mock_download_upload.return_value = "https://supabase.co/stored1.png"
        
        urls, task_id = await generate_8_images(
            prompts=["A cute cat"],
            user_id="user_123",
            tier="free"
        )
        
        assert task_id is not None
        assert len(urls) == 1
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.unified_image_service')
    @patch('services.ai.image_generator.download_and_upload_image')
    @patch('services.ai.image_generator.upload_reference_image')
    async def test_generate_with_reference_image(
        self, mock_upload_ref, mock_download_upload, mock_service
    ):
        """使用参考图生成"""
        from services.ai.image_generator import generate_8_images
        
        mock_upload_ref.return_value = "https://supabase.co/ref.png"
        mock_service.image_to_image = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://fal.ai/generated.png"],
            model="flux-dev",
            provider="fal"
        ))
        mock_download_upload.return_value = "https://supabase.co/stored.png"
        
        urls, task_id = await generate_8_images(
            prompts=["Similar style"],
            reference_image="base64encodedimage...",
            reference_strength=0.7,
            user_id="user_123",
            tier="pro"
        )
        
        assert task_id is not None
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.unified_image_service')
    @patch('services.ai.image_generator.download_and_upload_image')
    async def test_generate_batch_images(self, mock_download_upload, mock_service):
        """批量生成多个变体"""
        from services.ai.image_generator import generate_8_images
        
        mock_service.generate = AsyncMock(return_value=AIResponse(
            success=True,
            content=["https://fal.ai/img.png"],
            model="flux-schnell",
            provider="fal"
        ))
        mock_download_upload.return_value = "https://supabase.co/img.png"
        
        urls, task_id = await generate_8_images(
            prompts=["A cat"],
            num_images=4,  # 4 个变体
            user_id="user_123",
            tier="free"
        )
        
        # 应该调用 4 次生成
        assert mock_service.generate.call_count == 4


# ==========================================
# Canary Release Integration Tests
# ==========================================

class TestCanaryReleaseIntegration:
    """灰度发布集成测试"""
    
    @patch('services.ai.unified_text_service.get_text_model_config')
    @patch('services.ai.unified_text_service.should_use_canary')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    @patch('services.ai.unified_text_service.get_text_adapter')
    @patch('services.ai.unified_text_service.track_ai_usage')
    @patch('services.ai.unified_text_service.get_cached_result')
    @pytest.mark.asyncio
    async def test_canary_user_gets_canary_model(
        self, mock_cache, mock_track, mock_adapter, mock_enabled,
        mock_canary, mock_config
    ):
        """灰度用户使用灰度模型"""
        from services.ai.unified_text_service import unified_text_service
        
        mock_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        # 灰度命中
        mock_canary.return_value = (True, {"provider": "qwen", "model": "qwen-plus"})
        mock_enabled.return_value = True
        mock_cache.return_value = None
        
        qwen_adapter = MagicMock()
        qwen_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="Qwen response",
            model="qwen-plus",
            provider="qwen"
        ))
        mock_adapter.return_value = qwen_adapter
        mock_track.return_value = None
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}],
            user_id="canary_user_123",
            tier="pro"
        )
        
        assert response.success is True
        assert response.provider == "qwen"
        assert response.model == "qwen-plus"
    
    @patch('services.ai.unified_text_service.get_text_model_config')
    @patch('services.ai.unified_text_service.should_use_canary')
    @patch('services.ai.unified_text_service.is_provider_enabled')
    @patch('services.ai.unified_text_service.get_text_adapter')
    @patch('services.ai.unified_text_service.track_ai_usage')
    @patch('services.ai.unified_text_service.get_cached_result')
    @pytest.mark.asyncio
    async def test_non_canary_user_gets_default_model(
        self, mock_cache, mock_track, mock_adapter, mock_enabled,
        mock_canary, mock_config
    ):
        """非灰度用户使用默认模型"""
        from services.ai.unified_text_service import unified_text_service
        
        mock_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini"
        }
        # 灰度未命中
        mock_canary.return_value = (False, None)
        mock_enabled.return_value = True
        mock_cache.return_value = None
        
        openai_adapter = MagicMock()
        openai_adapter.chat_completion = AsyncMock(return_value=AIResponse(
            success=True,
            content="OpenAI response",
            model="gpt-4o-mini",
            provider="openai"
        ))
        mock_adapter.return_value = openai_adapter
        mock_track.return_value = None
        
        response = await unified_text_service.chat(
            messages=[{"role": "user", "content": "Hello"}],
            user_id="normal_user_123",
            tier="free"
        )
        
        assert response.success is True
        assert response.provider == "openai"


# ==========================================
# Usage Tracking Integration Tests
# ==========================================

class TestUsageTrackingIntegration:
    """使用量追踪集成测试"""
    
    @pytest.mark.asyncio
    @patch('services.ai.usage_tracker.supabase')
    async def test_track_ai_usage_success(self, mock_supabase):
        """成功记录使用量"""
        from services.ai.usage_tracker import track_ai_usage
        
        mock_supabase.rpc.return_value.execute.return_value = Mock(data=None)
        
        await track_ai_usage(
            provider="openai",
            model="gpt-4o-mini",
            call_type="text",
            success=True,
            input_tokens=100,
            output_tokens=50,
            latency_ms=150
        )
        
        # 应该调用 RPC
        mock_supabase.rpc.assert_called()
    
    @pytest.mark.asyncio
    @patch('services.ai.usage_tracker.supabase')
    async def test_track_ai_usage_failure(self, mock_supabase):
        """记录失败的调用"""
        from services.ai.usage_tracker import track_ai_usage
        
        mock_supabase.rpc.return_value.execute.return_value = Mock(data=None)
        
        await track_ai_usage(
            provider="qwen",
            model="qwen-plus",
            call_type="text",
            success=False,
            latency_ms=5000,
            error_type="timeout"
        )
        
        # 应该记录错误类型
        mock_supabase.rpc.assert_called()
    
    @patch('services.ai.usage_tracker.supabase')
    def test_get_usage_summary(self, mock_supabase):
        """获取使用量汇总"""
        from services.ai.usage_tracker import get_usage_summary
        
        mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=[
                {"provider": "openai", "total_calls": 100, "estimated_cost_usd": 0.50},
                {"provider": "fal", "total_calls": 50, "estimated_cost_usd": 0.15}
            ]
        )
        
        summary = get_usage_summary(days=30)
        
        assert summary is not None


# ==========================================
# Cache Integration Tests
# ==========================================

class TestCacheIntegration:
    """缓存集成测试"""
    
    @patch('services.ai.ai_cache.cache_service')
    def test_cache_hit(self, mock_cache):
        """缓存命中"""
        from services.ai.ai_cache import get_cached_result, set_cached_result
        
        # 设置缓存
        mock_cache.get_json.return_value = {
            "success": True,
            "content": "Cached content",
            "model": "gpt-4o-mini",
            "provider": "openai"
        }
        
        result = get_cached_result("test prompt", "gpt-4o-mini")
        
        assert result is not None
        assert result.content == "Cached content"
    
    @patch('services.ai.ai_cache.cache_service')
    def test_cache_miss(self, mock_cache):
        """缓存未命中"""
        from services.ai.ai_cache import get_cached_result
        
        mock_cache.get_json.return_value = None
        
        result = get_cached_result("uncached prompt", "gpt-4o-mini")
        
        assert result is None
    
    @patch('services.ai.ai_cache.cache_service')
    def test_set_cache(self, mock_cache):
        """设置缓存"""
        from services.ai.ai_cache import set_cached_result
        
        mock_cache.set_json.return_value = True
        
        response = AIResponse(
            success=True,
            content="Content to cache",
            model="gpt-4o-mini",
            provider="openai"
        )
        
        set_cached_result("prompt", "gpt-4o-mini", response)
        
        mock_cache.set_json.assert_called_once()
    
    @patch('services.ai.ai_cache.cache_service')
    def test_invalidate_cache(self, mock_cache):
        """清除缓存"""
        from services.ai.ai_cache import invalidate_ai_cache
        
        mock_cache.delete_pattern.return_value = 10
        
        invalidate_ai_cache()
        
        mock_cache.delete_pattern.assert_called()


# ==========================================
# Edge Cases Integration Tests
# ==========================================

class TestIntegrationEdgeCases:
    """集成边界情况测试"""
    
    @patch('services.ai.story_generator.unified_text_service')
    def test_story_generation_with_special_characters(self, mock_service):
        """包含特殊字符的主题"""
        from services.ai.story_generator import generate_story_json
        
        mock_response = AIResponse(
            success=True,
            content='{"title": "中文标题 🎉", "pages": []}',
            model="gpt-4o-mini",
            provider="openai"
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = generate_story_json(
            topic="中文主题 with emoji 🐱"
        )
        
        assert result is not None
        assert "中文" in result.get('title', '')
    
    @pytest.mark.asyncio
    @patch('services.ai.image_generator.unified_image_service')
    @patch('services.ai.image_generator.download_and_upload_image')
    async def test_image_generation_partial_failure(
        self, mock_download, mock_service
    ):
        """部分图像生成失败"""
        from services.ai.image_generator import generate_8_images
        
        # 第一次成功，第二次失败
        mock_service.generate = AsyncMock(side_effect=[
            AIResponse(success=True, content=["url1.png"]),
            AIResponse(success=False, error="Rate limited"),
        ])
        mock_download.return_value = "https://supabase.co/img.png"
        
        urls, task_id = await generate_8_images(
            prompts=["Prompt 1", "Prompt 2"],
            num_images=1
        )
        
        # 应该有一个成功，一个失败 (None)
        assert len(urls) == 2
        # 第一个应该有 URL，第二个可能是 None
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_prompt_enhancement_with_all_styles(self, mock_service):
        """测试所有风格"""
        from services.ai.prompt_enhancer import enhance_prompt, STYLE_DESCRIPTIONS
        
        mock_response = AIResponse(
            success=True,
            content='{"enhanced_prompt": "Enhanced", "key_elements": [], "composition": "centered"}',
            model="gpt-4o-mini",
            provider="openai"
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        for style in STYLE_DESCRIPTIONS.keys():
            result = enhance_prompt(
                theme="Test",
                style=style,
                mode="guided"
            )
            assert result is not None
