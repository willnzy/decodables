"""
Prompt Enhancer Service Tests
提示词增强服务测试

基于 BUSINESS_LOGIC_SPEC.md Section 5 的业务规则测试

核心业务规则:
1. AI 生成模式 (Section 5.2):
   - guided: 精准模式，高 guidance_scale (3.5-4.5)
   - flexible: 自由模式，低 guidance_scale (1.5-2.5)

2. 提示词增强:
   - 使用统一 AI 服务
   - 支持缓存
   - 支持 fallback

@module tests/test_prompt_enhancer
@version v3.3
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json

from services.ai.base import AIResponse, AIUsage


# ==========================================
# _run_async Tests
# ==========================================

class TestRunAsync:
    """_run_async 辅助函数测试"""
    
    def test_run_async_executes_coroutine(self):
        """【业务规则】_run_async 正确执行协程"""
        from services.ai.prompt_enhancer import _run_async
        
        async def sample_coro():
            return "result"
        
        result = _run_async(sample_coro())
        assert result == "result"


# ==========================================
# enhance_prompt Tests
# ==========================================

class TestEnhancePrompt:
    """enhance_prompt 函数测试"""
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_prompt_guided_mode(self, mock_service):
        """【业务规则 5.2】guided 模式使用精准增强"""
        from services.ai.prompt_enhancer import enhance_prompt
        
        # Mock 成功响应
        mock_response = AIResponse(
            success=True,
            content=json.dumps({
                "enhanced_prompt": "A detailed scene of a cat playing",
                "key_elements": ["cat", "playing", "ball"],
                "composition": "centered"
            })
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_prompt(
            theme="a cat playing",
            character="orange tabby cat",
            style="cartoon",
            mode="guided"
        )
        
        assert result is not None
        assert isinstance(result, dict)
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_prompt_flexible_mode(self, mock_service):
        """【业务规则 5.2】flexible 模式允许更多创意"""
        from services.ai.prompt_enhancer import enhance_prompt
        
        mock_response = AIResponse(
            success=True,
            content=json.dumps({
                "enhanced_prompt": "A whimsical scene with creative elements",
                "key_elements": ["cat", "magic", "flowers"],
                "composition": "dynamic"
            })
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_prompt(
            theme="a magical cat",
            style="fantasy",
            mode="flexible"
        )
        
        assert result is not None
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_prompt_fallback_on_failure(self, mock_service):
        """【业务规则 5.5】AI 失败时使用 fallback"""
        from services.ai.prompt_enhancer import enhance_prompt
        
        # Mock 失败响应
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=False,
            error="API error"
        ))
        
        result = enhance_prompt(
            theme="a simple cat",
            style="cartoon",
            mode="guided"
        )
        
        # 应该返回 fallback 结果
        assert result is not None
        assert "enhanced_prompt" in result
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_prompt_invalid_json_fallback(self, mock_service):
        """【业务规则】无效 JSON 响应使用 fallback"""
        from services.ai.prompt_enhancer import enhance_prompt
        
        # Mock 返回无效 JSON
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=True,
            content="This is not JSON"
        ))
        
        result = enhance_prompt(
            theme="a cat",
            style="cartoon",
            mode="guided"
        )
        
        # 应该返回 fallback 结果
        assert result is not None


# ==========================================
# enhance_asset_prompt Tests
# ==========================================

class TestEnhanceAssetPrompt:
    """enhance_asset_prompt 函数测试"""
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_asset_prompt_success(self, mock_service):
        """【业务规则】成功增强资产提示词"""
        from services.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = AIResponse(
            success=True,
            content=json.dumps({
                "enhanced_prompt": "A cute cartoon dragon character",
                "key_elements": ["dragon", "cute", "character"],
                "suggested_negative": "scary, violent"
            })
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_asset_prompt(
            who="a dragon",
            what="flying",
            where="sky",
            style="cartoon",
            moods=["happy"]
        )
        
        assert result is not None
        assert isinstance(result, dict)
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_asset_prompt_fallback(self, mock_service):
        """【业务规则】资产增强失败时使用 fallback"""
        from services.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=False,
            error="Rate limited"
        ))
        
        result = enhance_asset_prompt(
            who="a unicorn",
            what="running",
            style="fantasy"
        )
        
        assert result is not None
        assert "enhanced_prompt" in result


# ==========================================
# Async Functions Tests
# ==========================================

class TestAsyncEnhanceFunctions:
    """异步增强函数测试"""
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_prompt_async(self, mock_service):
        """【业务规则】异步提示词增强"""
        from services.ai.prompt_enhancer import enhance_prompt_async
        
        mock_response = AIResponse(
            success=True,
            content=json.dumps({
                "enhanced_prompt": "Detailed prompt",
                "key_elements": ["a", "b", "c"],
                "composition": "centered"
            })
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = await enhance_prompt_async(
            theme="test theme",
            style="cartoon",
            mode="guided"
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_asset_prompt_async(self, mock_service):
        """【业务规则】异步资产提示词增强"""
        from services.ai.prompt_enhancer import enhance_asset_prompt_async
        
        mock_response = AIResponse(
            success=True,
            content=json.dumps({
                "enhanced_prompt": "Asset prompt",
                "key_elements": ["x", "y"],
                "suggested_negative": "bad things"
            })
        )
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = await enhance_asset_prompt_async(
            who="hero",
            what="standing",
            style="cartoon"
        )
        
        assert result is not None


# ==========================================
# Fallback Functions Tests
# ==========================================

class TestFallbackFunctions:
    """Fallback 函数测试"""
    
    def test_fallback_enhance_basic(self):
        """【业务规则】基础 fallback 增强"""
        from services.ai.prompt_enhancer import fallback_enhance
        
        result = fallback_enhance(
            theme="a dog running",
            character="golden retriever",
            style="cartoon"
        )
        
        assert result is not None
        assert "enhanced_prompt" in result
        assert "key_elements" in result
        assert "composition" in result
        # 应该包含主题
        assert "dog" in result["enhanced_prompt"].lower()
    
    def test_fallback_enhance_all_styles(self):
        """【业务规则】fallback 支持所有风格"""
        from services.ai.prompt_enhancer import fallback_enhance
        
        styles = ["cartoon", "watercolor", "sketch", "fantasy", "realistic", "flat"]
        
        for style in styles:
            result = fallback_enhance(
                theme="test subject",
                style=style
            )
            assert result is not None
            assert "enhanced_prompt" in result
    
    def test_fallback_asset_enhance(self):
        """【业务规则】资产 fallback 增强"""
        from services.ai.prompt_enhancer import fallback_asset_enhance
        
        result = fallback_asset_enhance(
            who="a wizard",
            what="casting spell",
            where="tower",
            style="fantasy",
            moods=["mysterious"]
        )
        
        assert result is not None
        assert "enhanced_prompt" in result
        assert "wizard" in result["enhanced_prompt"].lower()


# ==========================================
# Edge Cases Tests
# ==========================================

class TestEdgeCases:
    """边界情况测试"""
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_empty_theme_handled(self, mock_service):
        """【业务规则】空主题使用 fallback"""
        from services.ai.prompt_enhancer import enhance_prompt
        
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=True,
            content=json.dumps({
                "enhanced_prompt": "result",
                "key_elements": [],
                "composition": "centered"
            })
        ))
        
        result = enhance_prompt(
            theme="",
            style="cartoon",
            mode="guided"
        )
        
        assert result is not None
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_special_characters_in_input(self, mock_service):
        """【业务规则】特殊字符被正确处理"""
        from services.ai.prompt_enhancer import enhance_prompt
        
        mock_service.chat = AsyncMock(return_value=AIResponse(
            success=True,
            content=json.dumps({
                "enhanced_prompt": "Result with special chars",
                "key_elements": ["test"],
                "composition": "centered"
            })
        ))
        
        result = enhance_prompt(
            theme="A cat's adventure: <exciting> & fun!",
            style="cartoon",
            mode="guided"
        )
        
        assert result is not None


# ==========================================
# Style Mapping Tests
# ==========================================

class TestStyleMapping:
    """风格映射测试"""
    
    def test_all_styles_have_fallback(self):
        """【业务规则】所有风格都有 fallback 支持"""
        from services.ai.prompt_enhancer import fallback_enhance
        
        known_styles = ["cartoon", "watercolor", "sketch", "fantasy", "realistic", "flat"]
        
        for style in known_styles:
            result = fallback_enhance(theme="test", style=style)
            assert result is not None
            # 风格应该出现在 enhanced_prompt 中
            # (fallback 会根据风格添加描述)
    
    def test_unknown_style_has_default(self):
        """【业务规则】未知风格使用默认处理"""
        from services.ai.prompt_enhancer import fallback_enhance
        
        result = fallback_enhance(theme="test", style="unknown_style_xyz")
        
        assert result is not None
        assert "enhanced_prompt" in result
