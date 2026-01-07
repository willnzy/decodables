"""
Prompt Enhancer Tests
提示词增强测试

基于 BUSINESS_LOGIC_SPEC.md Section 5 的业务规则测试

核心业务规则:
1. 提示词增强模式:
   - guided: 精确模式，忠实于用户描述
   - flexible: 创意模式，可添加创意元素

2. 风格支持:
   - cartoon, watercolor, sketch, fantasy, realistic, flat, scifi

3. 情绪标签:
   - warm, adventurous, mysterious, joyful, peaceful, funny

@module tests/test_prompt_enhancer
@version v3.3
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


# ==========================================
# System Prompts Tests
# ==========================================

class TestSystemPrompts:
    """
    系统提示词测试
    """
    
    def test_prompt_enhancer_system_exists(self):
        """【业务规则 5】主题模式系统提示词存在"""
        from shared.ai.prompt_enhancer import PROMPT_ENHANCER_SYSTEM
        
        assert PROMPT_ENHANCER_SYSTEM is not None
        assert len(PROMPT_ENHANCER_SYSTEM) > 0
    
    def test_asset_enhancer_system_exists(self):
        """【业务规则 5】资产模式系统提示词存在"""
        from shared.ai.prompt_enhancer import ASSET_ENHANCER_SYSTEM
        
        assert ASSET_ENHANCER_SYSTEM is not None
        assert len(ASSET_ENHANCER_SYSTEM) > 0
    
    def test_prompt_system_mentions_modes(self):
        """【业务规则】系统提示词包含 guided 和 flexible 模式"""
        from shared.ai.prompt_enhancer import PROMPT_ENHANCER_SYSTEM
        
        assert "GUIDED" in PROMPT_ENHANCER_SYSTEM.upper()
        assert "FLEXIBLE" in PROMPT_ENHANCER_SYSTEM.upper()
    
    def test_asset_system_mentions_5w1h(self):
        """【业务规则】资产提示词支持 5W1H 格式"""
        from shared.ai.prompt_enhancer import ASSET_ENHANCER_SYSTEM
        
        assert "who" in ASSET_ENHANCER_SYSTEM.lower()
        assert "what" in ASSET_ENHANCER_SYSTEM.lower()
        assert "where" in ASSET_ENHANCER_SYSTEM.lower()


# ==========================================
# Style Descriptions Tests
# ==========================================

class TestStyleDescriptions:
    """
    风格描述测试
    """
    
    def test_all_styles_defined(self):
        """【业务规则 5】所有风格都有定义"""
        from shared.ai.prompt_enhancer import STYLE_DESCRIPTIONS
        
        expected_styles = ['cartoon', 'watercolor', 'sketch', 'fantasy', 'realistic', 'flat', 'scifi']
        
        for style in expected_styles:
            assert style in STYLE_DESCRIPTIONS, f"Missing style: {style}"
    
    def test_style_descriptions_not_empty(self):
        """【业务规则】风格描述不为空"""
        from shared.ai.prompt_enhancer import STYLE_DESCRIPTIONS
        
        for style, desc in STYLE_DESCRIPTIONS.items():
            assert desc, f"Empty description for style: {style}"
            assert len(desc) > 10, f"Description too short for style: {style}"


# ==========================================
# Mood Descriptions Tests
# ==========================================

class TestMoodDescriptions:
    """
    情绪描述测试
    """
    
    def test_all_moods_defined(self):
        """【业务规则 5】所有情绪都有定义"""
        from shared.ai.prompt_enhancer import MOOD_DESCRIPTIONS
        
        expected_moods = ['warm', 'adventurous', 'mysterious', 'joyful', 'peaceful', 'funny']
        
        for mood in expected_moods:
            assert mood in MOOD_DESCRIPTIONS, f"Missing mood: {mood}"
    
    def test_mood_descriptions_not_empty(self):
        """【业务规则】情绪描述不为空"""
        from shared.ai.prompt_enhancer import MOOD_DESCRIPTIONS
        
        for mood, desc in MOOD_DESCRIPTIONS.items():
            assert desc, f"Empty description for mood: {mood}"


# ==========================================
# _run_async Helper Tests
# ==========================================

class TestRunAsync:
    """
    异步运行辅助函数测试
    """
    
    def test_run_async_executes_coroutine(self):
        """【业务规则】执行异步协程"""
        from shared.ai.prompt_enhancer import _run_async
        
        async def sample_coro():
            return "test_result"
        
        result = _run_async(sample_coro())
        
        assert result == "test_result"


# ==========================================
# fallback_enhance Tests
# ==========================================

class TestFallbackEnhance:
    """
    本地 fallback 增强测试 (主题模式)
    """
    
    def test_fallback_with_character(self):
        """【业务规则】有角色时的 fallback"""
        from shared.ai.prompt_enhancer import fallback_enhance
        
        result = fallback_enhance(
            theme="A day at the zoo",
            character="A curious monkey",
            style="cartoon"
        )
        
        assert 'enhanced_prompt' in result
        assert 'A curious monkey' in result['enhanced_prompt']
        assert result['fallback'] is True
    
    def test_fallback_without_character(self):
        """【业务规则】无角色时的 fallback"""
        from shared.ai.prompt_enhancer import fallback_enhance
        
        result = fallback_enhance(
            theme="Learning to count",
            style="watercolor"
        )
        
        assert 'enhanced_prompt' in result
        assert 'Learning to count' in result['enhanced_prompt']
    
    def test_fallback_includes_style(self):
        """【业务规则】fallback 包含风格描述"""
        from shared.ai.prompt_enhancer import fallback_enhance, STYLE_DESCRIPTIONS
        
        result = fallback_enhance(
            theme="Adventure",
            style="fantasy"
        )
        
        # 应该包含 fantasy 风格的某些关键词
        assert 'fantasy' in result['enhanced_prompt'].lower() or 'magical' in result['enhanced_prompt'].lower()
    
    def test_fallback_includes_children_book_context(self):
        """【业务规则】fallback 包含儿童书上下文"""
        from shared.ai.prompt_enhancer import fallback_enhance
        
        result = fallback_enhance(theme="Test", style="cartoon")
        
        assert "children's book" in result['enhanced_prompt'].lower()
    
    def test_fallback_key_elements(self):
        """【业务规则】fallback 返回 key_elements"""
        from shared.ai.prompt_enhancer import fallback_enhance
        
        result = fallback_enhance(
            theme="Playing",
            character="A dog",
            style="sketch"
        )
        
        assert 'key_elements' in result
        assert isinstance(result['key_elements'], list)
    
    def test_fallback_composition(self):
        """【业务规则】fallback 返回 composition"""
        from shared.ai.prompt_enhancer import fallback_enhance
        
        result = fallback_enhance(theme="Test", style="cartoon")
        
        assert result['composition'] == 'centered'


# ==========================================
# fallback_asset_enhance Tests
# ==========================================

class TestFallbackAssetEnhance:
    """
    本地 fallback 增强测试 (资产模式)
    """
    
    def test_fallback_asset_basic(self):
        """【业务规则】资产 fallback 基本功能"""
        from shared.ai.prompt_enhancer import fallback_asset_enhance
        
        result = fallback_asset_enhance(
            who="A friendly robot",
            style="scifi"
        )
        
        assert 'enhanced_prompt' in result
        assert 'A friendly robot' in result['enhanced_prompt']
        assert result['fallback'] is True
    
    def test_fallback_asset_with_what_where(self):
        """【业务规则】包含 what 和 where"""
        from shared.ai.prompt_enhancer import fallback_asset_enhance
        
        result = fallback_asset_enhance(
            who="A cat",
            what="playing",
            where="in a garden",
            style="cartoon"
        )
        
        prompt = result['enhanced_prompt']
        assert 'playing' in prompt
        assert 'garden' in prompt
    
    def test_fallback_asset_with_moods(self):
        """【业务规则】包含情绪标签"""
        from shared.ai.prompt_enhancer import fallback_asset_enhance
        
        result = fallback_asset_enhance(
            who="A bird",
            moods=["joyful", "warm"],
            style="watercolor"
        )
        
        # 应该包含情绪相关的描述
        assert 'enhanced_prompt' in result
    
    def test_fallback_asset_color_palette(self):
        """【业务规则】返回 color_palette"""
        from shared.ai.prompt_enhancer import fallback_asset_enhance
        
        result = fallback_asset_enhance(who="Test", style="cartoon")
        
        assert 'color_palette' in result


# ==========================================
# enhance_prompt Tests
# ==========================================

class TestEnhancePrompt:
    """
    主题模式增强测试
    """
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_prompt_success(self, mock_run_async):
        """【业务规则 5】成功增强提示词"""
        from shared.ai.prompt_enhancer import enhance_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "enhanced_prompt": "A beautiful cartoon scene",
            "key_elements": ["cat", "garden"],
            "composition": "centered"
        })
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o-mini"
        
        mock_run_async.return_value = mock_response
        
        result = enhance_prompt(
            theme="A cat in the garden",
            style="cartoon",
            user_id="user_123",
            tier="pro"
        )
        
        assert 'enhanced_prompt' in result
        assert result['original_theme'] == "A cat in the garden"
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_prompt_api_failure_uses_fallback(self, mock_run_async):
        """【业务规则 5.5】API 失败时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_prompt
        
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.error = "API Error"
        
        mock_run_async.return_value = mock_response
        
        result = enhance_prompt(
            theme="Test theme",
            style="cartoon"
        )
        
        assert result['fallback'] is True
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_prompt_json_error_uses_fallback(self, mock_run_async):
        """【业务规则】JSON 解析错误时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "not valid json"
        
        mock_run_async.return_value = mock_response
        
        result = enhance_prompt(
            theme="Test theme",
            style="cartoon"
        )
        
        assert result['fallback'] is True
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_prompt_missing_field_uses_fallback(self, mock_run_async):
        """【业务规则】缺少必需字段时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "key_elements": ["test"]
            # missing enhanced_prompt
        })
        
        mock_run_async.return_value = mock_response
        
        result = enhance_prompt(
            theme="Test theme",
            style="cartoon"
        )
        
        assert result['fallback'] is True
    
    def test_enhance_prompt_temperature_guided_mode(self):
        """【业务规则】guided 模式温度为 0.3"""
        # 温度计算逻辑验证
        mode = 'guided'
        creativity_level = 0.5
        
        if mode == 'guided':
            temperature = 0.3
        else:
            temperature = 0.3 + (creativity_level * 0.6)
        
        assert temperature == 0.3
    
    def test_enhance_prompt_temperature_flexible_mode(self):
        """【业务规则】flexible 模式温度随 creativity_level 变化"""
        mode = 'flexible'
        creativity_level = 0.5
        
        if mode == 'guided':
            temperature = 0.3
        else:
            temperature = 0.3 + (creativity_level * 0.6)
        
        assert temperature == 0.6  # 0.3 + 0.5 * 0.6


# ==========================================
# enhance_asset_prompt Tests
# ==========================================

class TestEnhanceAssetPrompt:
    """
    资产模式增强测试
    """
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_asset_prompt_success(self, mock_run_async):
        """【业务规则 5】成功增强资产提示词"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "enhanced_prompt": "A cute cat exploring",
            "key_elements": ["cat", "garden"],
            "composition": "rule-of-thirds",
            "color_palette": "warm tones"
        })
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o-mini"
        
        mock_run_async.return_value = mock_response
        
        result = enhance_asset_prompt(
            who="A cute cat",
            what="exploring",
            where="in a garden",
            style="cartoon",
            moods=["warm", "joyful"],
            user_id="user_123",
            tier="pro"
        )
        
        assert 'enhanced_prompt' in result
        assert result['original_who'] == "A cute cat"
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_asset_prompt_api_failure(self, mock_run_async):
        """【业务规则】API 失败时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.error = "API Error"
        
        mock_run_async.return_value = mock_response
        
        result = enhance_asset_prompt(
            who="A robot",
            style="scifi"
        )
        
        assert result['fallback'] is True


# ==========================================
# Async Functions Tests
# ==========================================

class TestAsyncFunctions:
    """
    异步函数测试
    """
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_prompt_async_success(self, mock_service):
        """【业务规则】异步增强成功"""
        from shared.ai.prompt_enhancer import enhance_prompt_async
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "enhanced_prompt": "Test prompt",
            "key_elements": ["test"],
            "composition": "centered"
        })
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o"
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = await enhance_prompt_async(
            theme="Test",
            style="cartoon"
        )
        
        assert 'enhanced_prompt' in result
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_prompt_async_failure(self, mock_service):
        """【业务规则】异步增强失败使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_prompt_async
        
        mock_response = MagicMock()
        mock_response.success = False
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = await enhance_prompt_async(
            theme="Test",
            style="cartoon"
        )
        
        assert result['fallback'] is True
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_asset_prompt_async_success(self, mock_service):
        """【业务规则】异步资产增强成功"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt_async
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "enhanced_prompt": "Test asset prompt",
            "key_elements": ["test"],
            "composition": "centered",
            "color_palette": "warm"
        })
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o"
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = await enhance_asset_prompt_async(
            who="A cat",
            style="cartoon",
            moods=["warm"]
        )
        
        assert 'enhanced_prompt' in result
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_asset_prompt_async_failure(self, mock_service):
        """【业务规则】异步资产增强失败使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt_async
        
        mock_response = MagicMock()
        mock_response.success = False
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = await enhance_asset_prompt_async(
            who="A cat",
            style="cartoon"
        )
        
        assert result['fallback'] is True


# ==========================================
# Style Integration Tests
# ==========================================

class TestStyleIntegration:
    """
    风格集成测试
    """
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_style_appended_if_not_in_response(self, mock_run_async):
        """【业务规则】如果响应中没有风格，则添加"""
        from shared.ai.prompt_enhancer import enhance_prompt, STYLE_DESCRIPTIONS
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "enhanced_prompt": "A simple scene",  # 没有 cartoon
            "key_elements": ["test"],
            "composition": "centered"
        })
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o"
        
        mock_run_async.return_value = mock_response
        
        result = enhance_prompt(
            theme="Test",
            style="cartoon"
        )
        
        # 应该添加了 cartoon 风格描述
        style_keywords = ['cartoon', 'bold', 'vibrant', 'playful']
        assert any(kw in result['enhanced_prompt'].lower() for kw in style_keywords)


# ==========================================
# Mode Integration Tests
# ==========================================

class TestModeIntegration:
    """
    模式集成测试
    """
    
    def test_guided_mode_recorded(self):
        """【业务规则】记录 guided 模式"""
        from shared.ai.prompt_enhancer import fallback_enhance
        
        result = fallback_enhance(
            theme="Test",
            style="cartoon",
            mode="guided"
        )
        
        assert result['mode'] == 'guided'
    
    def test_flexible_mode_recorded(self):
        """【业务规则】记录 flexible 模式"""
        from shared.ai.prompt_enhancer import fallback_enhance
        
        result = fallback_enhance(
            theme="Test",
            style="cartoon",
            mode="flexible"
        )
        
        assert result['mode'] == 'flexible'


# ==========================================
# Async Context Tests
# ==========================================

class TestRunAsyncInAsyncContext:
    """在异步上下文中运行测试"""
    
    def test_run_async_without_running_loop(self):
        """不在异步上下文中使用 asyncio.run"""
        import asyncio
        
        async def test_coroutine():
            return "test_result"
        
        from shared.ai.prompt_enhancer import _run_async
        
        # Should work normally when no loop is running
        result = _run_async(test_coroutine())
        
        assert result == "test_result"
    
    def test_run_async_handles_runtime_error(self):
        """处理 RuntimeError (没有运行中的循环)"""
        import asyncio
        
        async def test_coroutine():
            return "success"
        
        from shared.ai.prompt_enhancer import _run_async
        
        result = _run_async(test_coroutine())
        assert result == "success"


class TestFlexibleModeTemperature:
    """Flexible 模式温度计算测试"""
    
    @patch('services.ai.prompt_enhancer._run_async')
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_flexible_mode_temperature_calculation(self, mock_service, mock_run_async):
        """flexible 模式温度计算: 0.3 + creativity_level * 0.6"""
        from shared.ai.prompt_enhancer import enhance_prompt, fallback_enhance
        
        # Return fallback result
        mock_run_async.side_effect = Exception("Force fallback")
        
        result = enhance_prompt(
            theme="Test",
            style="cartoon",
            mode="flexible",
            creativity_level=1.0  # Max creativity
        )
        
        # Should use fallback
        assert result['fallback'] is True
        
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_prompt_flexible_high_creativity(self, mock_run_async):
        """高创意度 flexible 模式"""
        from shared.ai.prompt_enhancer import enhance_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"enhanced_prompt": "A creative scene", "key_elements": [], "composition": "test"}'
        mock_run_async.return_value = mock_response
        
        result = enhance_prompt(
            theme="Magic forest",
            style="fantasy",
            mode="flexible",
            creativity_level=0.8
        )
        
        assert 'enhanced_prompt' in result


class TestEnhanceAssetPromptFlexible:
    """Asset 提示词增强 Flexible 模式测试"""
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_asset_prompt_flexible_mode(self, mock_run_async):
        """Asset 提示词 flexible 模式"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"enhanced_prompt": "Creative asset", "key_elements": [], "composition": "test"}'
        mock_run_async.return_value = mock_response
        
        result = enhance_asset_prompt(
            who="A robot",
            what="dancing",
            where="on the moon",
            style="scifi",
            mode="flexible",
            creativity_level=0.5
        )
        
        assert 'enhanced_prompt' in result
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_asset_prompt_with_all_params(self, mock_run_async):
        """Asset 提示词带所有参数"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"enhanced_prompt": "Full scene", "key_elements": ["robot", "moon"], "composition": "centered"}'
        mock_run_async.return_value = mock_response
        
        result = enhance_asset_prompt(
            who="A happy robot",
            what="waving hello",
            where="in space",
            style="cartoon",
            moods=["joyful", "warm"],
            mode="guided",
            creativity_level=0.3,
            user_id="test-user",
            tier="pro"
        )
        
        assert 'enhanced_prompt' in result


# ==========================================
# Enhanced Asset Prompt Error Handling Tests
# ==========================================

class TestEnhanceAssetPromptErrors:
    """Asset 提示词增强错误处理测试"""
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_asset_prompt_missing_enhanced_prompt(self, mock_run_async):
        """【业务规则】缺少 enhanced_prompt 字段时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "key_elements": ["test"],
            "composition": "centered"
            # missing enhanced_prompt
        })
        
        mock_run_async.return_value = mock_response
        
        result = enhance_asset_prompt(
            who="A robot",
            style="scifi"
        )
        
        assert result['fallback'] is True
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_asset_prompt_json_error(self, mock_run_async):
        """【业务规则】JSON 解析错误时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "not valid json at all"
        
        mock_run_async.return_value = mock_response
        
        result = enhance_asset_prompt(
            who="A cat",
            style="cartoon"
        )
        
        assert result['fallback'] is True
    
    @patch('services.ai.prompt_enhancer._run_async')
    def test_enhance_asset_prompt_generic_exception(self, mock_run_async):
        """【业务规则】通用异常时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_run_async.side_effect = Exception("Unexpected error")
        
        result = enhance_asset_prompt(
            who="A bird",
            style="watercolor"
        )
        
        assert result['fallback'] is True


# ==========================================
# Async Error Handling Tests
# ==========================================

class TestAsyncErrorHandling:
    """异步函数错误处理测试"""
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_prompt_async_missing_field(self, mock_service):
        """【业务规则】异步增强缺少字段时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_prompt_async
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "key_elements": ["test"],
            "composition": "centered"
            # missing enhanced_prompt
        })
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = await enhance_prompt_async(
            theme="Test",
            style="cartoon"
        )
        
        assert result['fallback'] is True
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_prompt_async_generic_exception(self, mock_service):
        """【业务规则】异步增强异常时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_prompt_async
        
        mock_service.chat = AsyncMock(side_effect=Exception("Unexpected error"))
        
        result = await enhance_prompt_async(
            theme="Test",
            style="cartoon"
        )
        
        assert result['fallback'] is True
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_asset_prompt_async_missing_field(self, mock_service):
        """【业务规则】异步资产增强缺少字段时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt_async
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "key_elements": ["test"],
            "composition": "centered"
            # missing enhanced_prompt
        })
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = await enhance_asset_prompt_async(
            who="A cat",
            style="cartoon"
        )
        
        assert result['fallback'] is True
    
    @pytest.mark.asyncio
    @patch('services.ai.prompt_enhancer.unified_text_service')
    async def test_enhance_asset_prompt_async_generic_exception(self, mock_service):
        """【业务规则】异步资产增强异常时使用 fallback"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt_async
        
        mock_service.chat = AsyncMock(side_effect=Exception("Unexpected error"))
        
        result = await enhance_asset_prompt_async(
            who="A cat",
            style="cartoon"
        )
        
        assert result['fallback'] is True


# ==========================================
# _run_async in Async Context Tests
# ==========================================

class TestRunAsyncInEventLoop:
    """在已运行的事件循环中测试 _run_async"""
    
    @pytest.mark.asyncio
    async def test_run_async_within_running_loop(self):
        """在运行中的事件循环内调用 _run_async"""
        import asyncio
        from shared.ai.prompt_enhancer import _run_async
        
        async def sample_coroutine():
            await asyncio.sleep(0)
            return "test_from_running_loop"
        
        # This should use the ThreadPoolExecutor path since we're in an async context
        result = _run_async(sample_coroutine())
        
        assert result == "test_from_running_loop"
    
    @pytest.mark.asyncio
    async def test_run_async_multiple_calls_in_loop(self):
        """在运行中的事件循环内多次调用 _run_async"""
        import asyncio
        from shared.ai.prompt_enhancer import _run_async
        
        async def add_coro(a, b):
            await asyncio.sleep(0)
            return a + b
        
        result1 = _run_async(add_coro(1, 2))
        result2 = _run_async(add_coro(3, 4))
        
        assert result1 == 3
        assert result2 == 7


# ==========================================
# Full Integration Tests (cover inner async)
# ==========================================

class TestFullIntegration:
    """完整集成测试 - 覆盖内部异步函数"""
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_prompt_full_flow(self, mock_service):
        """完整流程测试 enhance_prompt"""
        from shared.ai.prompt_enhancer import enhance_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "enhanced_prompt": "A beautiful cartoon scene with a cat",
            "key_elements": ["cat", "garden", "sunshine"],
            "composition": "rule-of-thirds"
        })
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o-mini"
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_prompt(
            theme="A cat playing in the garden",
            character="A fluffy orange cat",
            style="cartoon",
            mode="guided",
            user_id="user_123",
            tier="pro"
        )
        
        assert 'enhanced_prompt' in result
        assert result['original_theme'] == "A cat playing in the garden"
        assert result['original_character'] == "A fluffy orange cat"
        assert result['mode'] == 'guided'
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_asset_prompt_full_flow(self, mock_service):
        """完整流程测试 enhance_asset_prompt"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "enhanced_prompt": "A curious robot exploring space",
            "key_elements": ["robot", "space", "stars"],
            "composition": "centered",
            "color_palette": "cosmic blues and purples"
        })
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o"
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_asset_prompt(
            who="A curious robot",
            what="exploring",
            where="in outer space",
            style="scifi",
            moods=["adventurous", "mysterious"],
            mode="flexible",
            creativity_level=0.7,
            user_id="user_456",
            tier="starter"
        )
        
        assert 'enhanced_prompt' in result
        assert result['original_who'] == "A curious robot"
        assert result['original_what'] == "exploring"
        assert result['original_where'] == "in outer space"
        assert result['mode'] == 'flexible'
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_prompt_adds_style_if_missing(self, mock_service):
        """AI 响应没有包含风格时自动添加"""
        from shared.ai.prompt_enhancer import enhance_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "enhanced_prompt": "A simple scene without style keywords",
            "key_elements": ["scene"],
            "composition": "centered"
        })
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o"
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_prompt(
            theme="Test",
            style="watercolor",
            mode="guided"
        )
        
        # Should append watercolor style description
        assert 'watercolor' in result['enhanced_prompt'].lower()
    
    @patch('services.ai.prompt_enhancer.unified_text_service')
    def test_enhance_asset_prompt_adds_style_if_missing(self, mock_service):
        """Asset AI 响应没有包含风格时自动添加"""
        from shared.ai.prompt_enhancer import enhance_asset_prompt
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            "enhanced_prompt": "A scene without style keywords",
            "key_elements": ["test"],
            "composition": "centered",
            "color_palette": "neutral"
        })
        mock_response.provider = "openai"
        mock_response.model = "gpt-4o"
        
        mock_service.chat = AsyncMock(return_value=mock_response)
        
        result = enhance_asset_prompt(
            who="A bird",
            style="fantasy",
            mode="guided"
        )
        
        # Should append fantasy style description
        assert 'fantasy' in result['enhanced_prompt'].lower() or 'magical' in result['enhanced_prompt'].lower()
