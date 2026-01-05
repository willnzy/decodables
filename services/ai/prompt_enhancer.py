"""
Prompt Enhancement Service for AI Image Generation
提示词增强服务

Uses unified AI service to expand user's simple descriptions into detailed,
high-quality image generation prompts.
使用统一 AI 服务将用户的简单描述扩展为详细、高质量的图像生成提示词。

This is a standard technique used by:
- DALL-E 3 (uses GPT-4 to rewrite prompts)
- Midjourney (automatic prompt expansion)
- Adobe Firefly (built-in prompt optimization)

Features:
- Automatic model selection from admin configuration
- Canary release support
- Usage tracking
- Caching (same input produces same output)
- Automatic fallback on errors

Supports two enhancement modes:
1. AI Design Page mode (theme-based): For page-level illustrations
2. Asset Generation mode (5W1H-based): For standalone assets with Who/What/Where/Style/Mood
"""

import json
import asyncio
import logging
from typing import Optional, List

from .unified_text_service import unified_text_service

logger = logging.getLogger(__name__)


# ==========================================
# System Prompts
# ==========================================

PROMPT_ENHANCER_SYSTEM = """You are an expert prompt engineer specializing in children's book illustrations.

Your task: Transform a user's simple idea into a detailed, high-quality image generation prompt.

INPUT:
- theme: What the page is about
- character: Main character description (optional)
- style: Art style (cartoon, watercolor, sketch, fantasy, realistic, flat)
- mode: "guided" or "flexible"

OUTPUT (JSON only):
{
  "enhanced_prompt": "Full detailed prompt for image generation",
  "key_elements": ["element1", "element2", "element3"],
  "composition": "centered | rule-of-thirds | dynamic | symmetrical"
}

=== MODE RULES ===

**GUIDED MODE** (more accurate):
- Be LITERAL and faithful to the user's description
- Add specific visual details (lighting, colors, composition)
- Keep the EXACT subject/character the user described
- DO NOT add elements the user didn't mention
- Focus on clarity and precision
- Use simple, direct compositions

**FLEXIBLE MODE** (more creative):
- Creative interpretation is encouraged
- Add whimsical, imaginative details
- Suggest unexpected but relevant elements
- Artistic flourishes welcome
- Can embellish the scene with complementary elements

=== ALWAYS INCLUDE ===

1. Subject/Character description (who/what is in the scene)
2. Action or pose (what they're doing)
3. Setting/Background (where it's happening)
4. Art style details (matching the selected style)
5. Lighting and color palette
6. Composition guidance

=== STYLE-SPECIFIC GUIDANCE ===

- cartoon: Bold outlines, vibrant colors, expressive features, playful proportions
- watercolor: Soft edges, color bleeding, artistic texture, gentle gradients
- sketch: Pencil/ink lines, hatching, hand-drawn feel, artistic imperfection
- fantasy: Magical elements, enchanting lighting, sparkles, dreamy atmosphere
- realistic: Detailed textures, natural lighting, accurate proportions, depth
- flat: Minimalist, clean shapes, limited palette, modern design aesthetic

=== OUTPUT REQUIREMENTS ===

- enhanced_prompt: 50-100 words, rich but focused
- Always include "children's book illustration" context
- Keep content safe and appropriate for young children
- Use positive, engaging imagery

Return ONLY valid JSON, no markdown or explanation."""


ASSET_ENHANCER_SYSTEM = """You are an expert prompt engineer specializing in children's book illustrations.

Your task: Transform structured 5W1H inputs into a detailed, high-quality image generation prompt.

INPUT FORMAT (5W1H):
- who: The main character/subject (e.g., "a curious cat", "a friendly robot")
- what: The action or activity (e.g., "exploring", "playing", "learning")
- where: The scene/setting (e.g., "in a magical garden", "underwater world")
- style: Art style (cartoon, watercolor, sketch, fantasy, realistic, scifi, flat)
- moods: Array of mood/atmosphere tags (e.g., ["warm", "joyful", "peaceful"])
- mode: "guided" or "flexible"

OUTPUT (JSON only):
{
  "enhanced_prompt": "Full detailed prompt for image generation",
  "key_elements": ["element1", "element2", "element3"],
  "composition": "centered | rule-of-thirds | dynamic | symmetrical",
  "color_palette": "description of recommended colors"
}

=== MODE RULES ===

**GUIDED MODE** (more accurate):
- Stay VERY faithful to the user's 5W1H inputs
- Add specific visual details (lighting, textures, poses)
- Keep the EXACT character/action/setting described
- DO NOT add new characters or change the scene
- Focus on bringing their exact vision to life

**FLEXIBLE MODE** (more creative):
- Use 5W1H as inspiration, not strict requirements
- Add complementary elements that enhance the scene
- Creative character poses and expressions
- Environmental details that tell a story
- Whimsical, unexpected but delightful additions

=== STYLE-SPECIFIC PROMPTING ===

- cartoon: "bold black outlines, vibrant saturated colors, expressive exaggerated features, playful proportions, disney-pixar inspired"
- watercolor: "soft watercolor washes, gentle color bleeding, artistic brush textures, translucent layers, dreamy atmospheric"
- sketch: "hand-drawn pencil sketch, artistic hatching and cross-hatching, charming imperfections, storybook linework"
- fantasy: "magical sparkles and glow effects, ethereal lighting, enchanted atmosphere, mystical colors, fairy tale quality"
- realistic: "detailed realistic rendering, natural lighting, accurate proportions, depth and dimension, lifelike textures"
- scifi: "futuristic technology, neon accents, sleek surfaces, space or cyber elements, sci-fi lighting"
- flat: "minimalist flat design, clean geometric shapes, limited color palette, modern vector aesthetic"

=== MOOD INTEGRATION ===

- warm: golden hour lighting, cozy atmosphere, soft shadows
- adventurous: dynamic composition, exciting poses, sense of movement
- mysterious: dramatic lighting, shadows, intriguing elements
- joyful: bright colors, happy expressions, playful energy
- peaceful: soft colors, calm composition, serene atmosphere
- funny: exaggerated expressions, humorous situations, playful details

=== OUTPUT REQUIREMENTS ===

- enhanced_prompt: 60-120 words, detailed but coherent
- Always end with "children's book illustration, high quality, detailed"
- Keep content safe and appropriate for young children
- Create vivid, engaging imagery that captures the mood

Return ONLY valid JSON, no markdown or explanation."""


# ==========================================
# Style and Mood Descriptions
# ==========================================

STYLE_DESCRIPTIONS = {
    'cartoon': 'cartoon style, bold outlines, vibrant saturated colors, expressive characters, playful proportions',
    'watercolor': 'watercolor painting style, soft color bleeding, artistic texture, gentle gradients, delicate brushstrokes',
    'sketch': 'pencil sketch style, hand-drawn linework, artistic hatching, charming imperfections',
    'fantasy': 'fantasy art style, magical atmosphere, enchanting lighting, sparkles and glow effects, dreamy',
    'realistic': 'realistic illustration, detailed textures, natural lighting, accurate proportions, depth and dimension',
    'flat': 'flat design style, minimalist shapes, clean vectors, limited color palette, modern aesthetic',
    'scifi': 'science fiction style, futuristic elements, neon accents, sleek technology, space or cyber aesthetic'
}

MOOD_DESCRIPTIONS = {
    'warm': 'warm, heartwarming atmosphere, golden hour lighting, cozy feeling',
    'adventurous': 'adventurous, exciting, dynamic energy, sense of movement',
    'mysterious': 'mysterious, magical ambiance, dramatic lighting, intriguing',
    'joyful': 'joyful, cheerful mood, bright and happy, playful energy',
    'peaceful': 'peaceful, serene scene, calm and tranquil, soft atmosphere',
    'funny': 'funny, humorous style, playful and silly, exaggerated expressions'
}


# ==========================================
# Helper: Run async in sync context
# ==========================================

def _run_async(coro):
    """在同步上下文中运行异步协程"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop and loop.is_running():
        # 已在异步上下文中，使用线程池
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        # 不在异步上下文中，直接运行
        return asyncio.run(coro)


# ==========================================
# Main Functions
# ==========================================

def enhance_prompt(
    theme: str,
    character: Optional[str] = None,
    style: str = 'cartoon',
    mode: str = 'guided',
    creativity_level: float = 0.3,
    user_id: Optional[str] = None,
    tier: str = "free"
) -> dict:
    """
    增强简单描述为详细的图像生成提示词 (主题模式)
    
    Args:
        theme: 页面主题 (e.g., "Counting fun", "A day at the zoo")
        character: 主角描述 (可选)
        style: 艺术风格 ID (cartoon, watercolor, sketch, fantasy, realistic, flat)
        mode: "guided" (准确) 或 "flexible" (创意)
        creativity_level: 0.0-1.0 创意程度 (0=精确, 1=非常创意)
        user_id: 用户 ID (用于灰度和追踪)
        tier: 用户等级 (free, starter, pro)
    
    Returns:
        包含 enhanced_prompt, key_elements, composition 的字典
        
    Note:
        - 模型选择由 Admin 配置管理
        - 支持灰度发布测试新模型
        - 自动追踪使用量
        - 相同输入会使用缓存
        - 失败时使用本地 fallback
    """
    # 构建用户输入
    user_input = f"""Theme: {theme}
Character: {character or 'Not specified - use appropriate characters for the theme'}
Art Style: {style} ({STYLE_DESCRIPTIONS.get(style, 'colorful illustration')})
Mode: {mode}"""

    # 计算温度
    if mode == 'guided':
        temperature = 0.3
    else:
        temperature = 0.3 + (creativity_level * 0.6)

    async def _enhance_async():
        response = await unified_text_service.chat(
            messages=[
                {"role": "system", "content": PROMPT_ENHANCER_SYSTEM},
                {"role": "user", "content": user_input}
            ],
            user_id=user_id,
            tier=tier,
            temperature=temperature,
            max_tokens=300,
            response_format={"type": "json_object"},
            use_cache=True,  # 相同输入可以缓存
        )
        return response

    try:
        response = _run_async(_enhance_async())
        
        if not response.success:
            logger.warning(f"[PromptEnhancer] AI call failed: {response.error}, using fallback")
            print(f"❌ Prompt enhancement failed: {response.error}")
            return fallback_enhance(theme, character, style, mode)
        
        result = json.loads(response.content)
        
        # 确保必需字段存在
        if 'enhanced_prompt' not in result:
            raise ValueError("Missing enhanced_prompt in response")
        
        # 添加风格后缀（如果不存在）
        enhanced = result['enhanced_prompt']
        style_desc = STYLE_DESCRIPTIONS.get(style, '')
        if style_desc and style not in enhanced.lower():
            enhanced = f"{enhanced}, {style_desc}"
        
        result['enhanced_prompt'] = enhanced
        result['original_theme'] = theme
        result['original_character'] = character
        result['mode'] = mode
        
        model_info = f"{response.provider}/{response.model}" if response.provider else "unknown"
        print(f"✨ Prompt enhanced ({mode} mode, {model_info}): {len(enhanced)} chars")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.warning(f"[PromptEnhancer] JSON parse error: {e}, using fallback")
        print(f"❌ Prompt enhancement failed: Invalid JSON")
        return fallback_enhance(theme, character, style, mode)
    except Exception as e:
        logger.warning(f"[PromptEnhancer] Error: {e}, using fallback")
        print(f"❌ Prompt enhancement failed: {e}")
        return fallback_enhance(theme, character, style, mode)


def enhance_asset_prompt(
    who: str,
    what: Optional[str] = None,
    where: Optional[str] = None,
    style: str = 'cartoon',
    moods: Optional[List[str]] = None,
    mode: str = 'guided',
    creativity_level: float = 0.3,
    user_id: Optional[str] = None,
    tier: str = "free"
) -> dict:
    """
    增强 5W1H 结构化输入为详细的图像生成提示词
    
    用于 "Generate Assets with AI" 模态框的结构化表单输入。
    
    Args:
        who: 主角描述 (必需)
        what: 动作或活动 (可选)
        where: 场景/设置 (可选)
        style: 艺术风格 ID (cartoon, watercolor, sketch, fantasy, realistic, scifi, flat)
        moods: 情绪标签列表 (warm, adventurous, mysterious, joyful, peaceful, funny)
        mode: "guided" (准确) 或 "flexible" (创意)
        creativity_level: 0.0-1.0 创意程度 (0=精确, 1=非常创意)
        user_id: 用户 ID (用于灰度和追踪)
        tier: 用户等级 (free, starter, pro)
    
    Returns:
        包含 enhanced_prompt, key_elements, composition, color_palette 的字典
    """
    # 构建结构化输入
    mood_list = moods or ['warm']
    mood_descriptions = [MOOD_DESCRIPTIONS.get(m, m) for m in mood_list if m]
    
    user_input = f"""Who: {who}
What: {what or 'in a natural pose'}
Where: {where or 'in a simple background'}
Art Style: {style} ({STYLE_DESCRIPTIONS.get(style, 'colorful illustration')})
Moods: {', '.join(mood_list)} ({'; '.join(mood_descriptions[:3])})
Mode: {mode}"""

    # 计算温度
    if mode == 'guided':
        temperature = 0.3
    else:
        temperature = 0.3 + (creativity_level * 0.6)

    async def _enhance_async():
        response = await unified_text_service.chat(
            messages=[
                {"role": "system", "content": ASSET_ENHANCER_SYSTEM},
                {"role": "user", "content": user_input}
            ],
            user_id=user_id,
            tier=tier,
            temperature=temperature,
            max_tokens=400,
            response_format={"type": "json_object"},
            use_cache=True,
        )
        return response

    try:
        response = _run_async(_enhance_async())
        
        if not response.success:
            logger.warning(f"[AssetEnhancer] AI call failed: {response.error}, using fallback")
            print(f"❌ Asset prompt enhancement failed: {response.error}")
            return fallback_asset_enhance(who, what, where, style, moods, mode)
        
        result = json.loads(response.content)
        
        # 确保必需字段存在
        if 'enhanced_prompt' not in result:
            raise ValueError("Missing enhanced_prompt in response")
        
        # 添加风格后缀
        enhanced = result['enhanced_prompt']
        style_desc = STYLE_DESCRIPTIONS.get(style, '')
        if style_desc and style not in enhanced.lower():
            enhanced = f"{enhanced}, {style_desc}"
        
        result['enhanced_prompt'] = enhanced
        result['original_who'] = who
        result['original_what'] = what
        result['original_where'] = where
        result['original_moods'] = moods
        result['mode'] = mode
        
        model_info = f"{response.provider}/{response.model}" if response.provider else "unknown"
        print(f"✨ Asset prompt enhanced ({mode} mode, {model_info}): {len(enhanced)} chars")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.warning(f"[AssetEnhancer] JSON parse error: {e}, using fallback")
        print(f"❌ Asset prompt enhancement failed: Invalid JSON")
        return fallback_asset_enhance(who, what, where, style, moods, mode)
    except Exception as e:
        logger.warning(f"[AssetEnhancer] Error: {e}, using fallback")
        print(f"❌ Asset prompt enhancement failed: {e}")
        return fallback_asset_enhance(who, what, where, style, moods, mode)


# ==========================================
# Async Versions (for direct async usage)
# ==========================================

async def enhance_prompt_async(
    theme: str,
    character: Optional[str] = None,
    style: str = 'cartoon',
    mode: str = 'guided',
    creativity_level: float = 0.3,
    user_id: Optional[str] = None,
    tier: str = "free"
) -> dict:
    """异步版本的 enhance_prompt"""
    user_input = f"""Theme: {theme}
Character: {character or 'Not specified - use appropriate characters for the theme'}
Art Style: {style} ({STYLE_DESCRIPTIONS.get(style, 'colorful illustration')})
Mode: {mode}"""

    temperature = 0.3 if mode == 'guided' else 0.3 + (creativity_level * 0.6)

    try:
        response = await unified_text_service.chat(
            messages=[
                {"role": "system", "content": PROMPT_ENHANCER_SYSTEM},
                {"role": "user", "content": user_input}
            ],
            user_id=user_id,
            tier=tier,
            temperature=temperature,
            max_tokens=300,
            response_format={"type": "json_object"},
            use_cache=True,
        )
        
        if not response.success:
            return fallback_enhance(theme, character, style, mode)
        
        result = json.loads(response.content)
        
        if 'enhanced_prompt' not in result:
            raise ValueError("Missing enhanced_prompt")
        
        enhanced = result['enhanced_prompt']
        style_desc = STYLE_DESCRIPTIONS.get(style, '')
        if style_desc and style not in enhanced.lower():
            enhanced = f"{enhanced}, {style_desc}"
        
        result['enhanced_prompt'] = enhanced
        result['original_theme'] = theme
        result['original_character'] = character
        result['mode'] = mode
        
        return result
        
    except Exception as e:
        logger.warning(f"[PromptEnhancer] Error: {e}, using fallback")
        return fallback_enhance(theme, character, style, mode)


async def enhance_asset_prompt_async(
    who: str,
    what: Optional[str] = None,
    where: Optional[str] = None,
    style: str = 'cartoon',
    moods: Optional[List[str]] = None,
    mode: str = 'guided',
    creativity_level: float = 0.3,
    user_id: Optional[str] = None,
    tier: str = "free"
) -> dict:
    """异步版本的 enhance_asset_prompt"""
    mood_list = moods or ['warm']
    mood_descriptions = [MOOD_DESCRIPTIONS.get(m, m) for m in mood_list if m]
    
    user_input = f"""Who: {who}
What: {what or 'in a natural pose'}
Where: {where or 'in a simple background'}
Art Style: {style} ({STYLE_DESCRIPTIONS.get(style, 'colorful illustration')})
Moods: {', '.join(mood_list)} ({'; '.join(mood_descriptions[:3])})
Mode: {mode}"""

    temperature = 0.3 if mode == 'guided' else 0.3 + (creativity_level * 0.6)

    try:
        response = await unified_text_service.chat(
            messages=[
                {"role": "system", "content": ASSET_ENHANCER_SYSTEM},
                {"role": "user", "content": user_input}
            ],
            user_id=user_id,
            tier=tier,
            temperature=temperature,
            max_tokens=400,
            response_format={"type": "json_object"},
            use_cache=True,
        )
        
        if not response.success:
            return fallback_asset_enhance(who, what, where, style, moods, mode)
        
        result = json.loads(response.content)
        
        if 'enhanced_prompt' not in result:
            raise ValueError("Missing enhanced_prompt")
        
        enhanced = result['enhanced_prompt']
        style_desc = STYLE_DESCRIPTIONS.get(style, '')
        if style_desc and style not in enhanced.lower():
            enhanced = f"{enhanced}, {style_desc}"
        
        result['enhanced_prompt'] = enhanced
        result['original_who'] = who
        result['original_what'] = what
        result['original_where'] = where
        result['original_moods'] = moods
        result['mode'] = mode
        
        return result
        
    except Exception as e:
        logger.warning(f"[AssetEnhancer] Error: {e}, using fallback")
        return fallback_asset_enhance(who, what, where, style, moods, mode)


# ==========================================
# Fallback Functions
# ==========================================

def fallback_enhance(
    theme: str,
    character: Optional[str] = None,
    style: str = 'cartoon',
    mode: str = 'guided'
) -> dict:
    """
    本地 fallback 提示词增强（不调用 AI）
    当 AI 服务不可用时使用。
    """
    parts = []
    
    if character:
        parts.append(f"{character}")
    
    if theme:
        if character:
            parts.append(f"in a scene about {theme}")
        else:
            parts.append(f"Scene depicting {theme}")
    
    style_desc = STYLE_DESCRIPTIONS.get(style, 'colorful illustration')
    parts.append(style_desc)
    parts.append("children's book illustration")
    parts.append("high quality, detailed, safe for children")
    
    enhanced_prompt = ", ".join(parts)
    
    return {
        'enhanced_prompt': enhanced_prompt,
        'key_elements': [theme, character or 'characters', style],
        'composition': 'centered',
        'original_theme': theme,
        'original_character': character,
        'mode': mode,
        'fallback': True
    }


def fallback_asset_enhance(
    who: str,
    what: Optional[str] = None,
    where: Optional[str] = None,
    style: str = 'cartoon',
    moods: Optional[List[str]] = None,
    mode: str = 'guided'
) -> dict:
    """
    本地 fallback 5W1H 提示词增强（不调用 AI）
    """
    parts = []
    
    parts.append(who)
    
    if what:
        parts.append(what)
    
    if where:
        parts.append(where)
    
    style_desc = STYLE_DESCRIPTIONS.get(style, 'colorful illustration')
    parts.append(style_desc)
    
    if moods:
        mood_prompts = [MOOD_DESCRIPTIONS.get(m, m) for m in moods[:3]]
        parts.extend(mood_prompts)
    
    parts.append("children's book illustration")
    parts.append("high quality, detailed, vibrant colors")
    
    enhanced_prompt = ", ".join(parts)
    
    return {
        'enhanced_prompt': enhanced_prompt,
        'key_elements': [who, what or 'pose', where or 'background'],
        'composition': 'centered',
        'color_palette': 'vibrant and warm',
        'original_who': who,
        'original_what': what,
        'original_where': where,
        'original_moods': moods,
        'mode': mode,
        'fallback': True
    }


# ==========================================
# Test
# ==========================================

if __name__ == "__main__":
    print("\n=== THEME-BASED: GUIDED MODE TEST ===")
    result = enhance_prompt(
        theme="Counting fun with numbers 1-5",
        character="A friendly orange cat",
        style="cartoon",
        mode="guided"
    )
    print(json.dumps(result, indent=2))
    
    print("\n=== THEME-BASED: FLEXIBLE MODE TEST ===")
    result = enhance_prompt(
        theme="Learning to share",
        character=None,
        style="watercolor",
        mode="flexible"
    )
    print(json.dumps(result, indent=2))
    
    print("\n=== 5W1H ASSET: GUIDED MODE TEST ===")
    result = enhance_asset_prompt(
        who="A curious orange tabby cat with big green eyes",
        what="exploring and discovering new things",
        where="in a beautiful garden full of flowers",
        style="cartoon",
        moods=["warm", "joyful"],
        mode="guided"
    )
    print(json.dumps(result, indent=2))
    
    print("\n=== 5W1H ASSET: FLEXIBLE MODE TEST ===")
    result = enhance_asset_prompt(
        who="A friendly robot helper",
        what="learning something new",
        where="in a cozy indoor room",
        style="scifi",
        moods=["adventurous", "funny"],
        mode="flexible",
        creativity_level=0.7
    )
    print(json.dumps(result, indent=2))
