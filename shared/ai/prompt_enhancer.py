"""
Prompt Enhancement Service for AI Image Generation

Uses unified AI service to expand user's descriptions into detailed prompts.

@module services.ai.prompt_enhancer
@version 3.24
"""

import json
import asyncio
import logging
from typing import Optional, List

from .unified_text_service import unified_text_service
from .prompt_templates import (
    PROMPT_ENHANCER_SYSTEM,
    ASSET_ENHANCER_SYSTEM,
    STYLE_DESCRIPTIONS,
    MOOD_DESCRIPTIONS,
    FALLBACK_PROMPT_TEMPLATE,
    FALLBACK_ASSET_TEMPLATE,
)

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


def enhance_prompt(
    theme: str,
    character: Optional[str] = None,
    style: str = 'cartoon',
    mode: str = 'guided',
    creativity_level: float = 0.3,
    user_id: Optional[str] = None,
    tier: str = "free"
) -> dict:
    """Enhance simple theme description into detailed prompt."""
    user_input = f"""Theme: {theme}
Character: {character or 'Not specified - use appropriate characters for the theme'}
Art Style: {style} ({STYLE_DESCRIPTIONS.get(style, 'colorful illustration')})
Mode: {mode}"""

    temperature = 0.3 if mode == 'guided' else 0.3 + (creativity_level * 0.6)

    async def _enhance_async():
        return await unified_text_service.chat(
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

    try:
        response = _run_async(_enhance_async())
        
        if not response.success:
            logger.warning(f"[PromptEnhancer] AI call failed: {response.error}")
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
        
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"[PromptEnhancer] Error: {e}, using fallback")
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
    """Enhance 5W1H structured input into detailed prompt."""
    mood_list = moods or ['warm']
    mood_descriptions = [MOOD_DESCRIPTIONS.get(m, m) for m in mood_list if m]
    
    user_input = f"""Who: {who}
What: {what or 'in a natural pose'}
Where: {where or 'in a simple background'}
Art Style: {style} ({STYLE_DESCRIPTIONS.get(style, 'colorful illustration')})
Moods: {', '.join(mood_list)} ({'; '.join(mood_descriptions[:3])})
Mode: {mode}"""

    temperature = 0.3 if mode == 'guided' else 0.3 + (creativity_level * 0.6)

    async def _enhance_async():
        return await unified_text_service.chat(
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

    try:
        response = _run_async(_enhance_async())
        
        if not response.success:
            logger.warning(f"[AssetEnhancer] AI call failed: {response.error}")
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
        
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"[AssetEnhancer] Error: {e}, using fallback")
        return fallback_asset_enhance(who, what, where, style, moods, mode)


# ==========================================
# Async Versions
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
    """Async version of enhance_prompt."""
    user_input = f"""Theme: {theme}
Character: {character or 'Not specified'}
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
            return fallback_enhance(theme, character, style, mode)
        
        enhanced = result['enhanced_prompt']
        style_desc = STYLE_DESCRIPTIONS.get(style, '')
        if style_desc and style not in enhanced.lower():
            enhanced = f"{enhanced}, {style_desc}"
        
        result['enhanced_prompt'] = enhanced
        result['original_theme'] = theme
        result['mode'] = mode
        
        return result
        
    except Exception as e:
        logger.warning(f"[PromptEnhancer] Async error: {e}")
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
    """Async version of enhance_asset_prompt."""
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
            return fallback_asset_enhance(who, what, where, style, moods, mode)
        
        enhanced = result['enhanced_prompt']
        style_desc = STYLE_DESCRIPTIONS.get(style, '')
        if style_desc and style not in enhanced.lower():
            enhanced = f"{enhanced}, {style_desc}"
        
        result['enhanced_prompt'] = enhanced
        result['original_who'] = who
        result['mode'] = mode
        
        return result
        
    except Exception as e:
        logger.warning(f"[AssetEnhancer] Async error: {e}")
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
    """Fallback enhancement when AI fails."""
    style_desc = STYLE_DESCRIPTIONS.get(style, 'colorful illustration style')
    
    enhanced = FALLBACK_PROMPT_TEMPLATE.format(
        theme=theme,
        style_desc=style_desc
    )
    
    if character:
        enhanced = enhanced.replace("children's book illustration of",
                                     f"children's book illustration of {character},")
    
    return {
        'enhanced_prompt': enhanced,
        'key_elements': [theme, style, 'children\'s book'],
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
    """Fallback asset enhancement when AI fails."""
    style_desc = STYLE_DESCRIPTIONS.get(style, 'colorful illustration style')
    
    mood_list = moods or ['warm']
    mood_desc = ', '.join([MOOD_DESCRIPTIONS.get(m, m) for m in mood_list[:2]])
    
    enhanced = FALLBACK_ASSET_TEMPLATE.format(
        who=who,
        what=what or 'in a natural pose',
        where=where or 'in a beautiful setting',
        style_desc=style_desc,
        mood_desc=mood_desc
    )
    
    return {
        'enhanced_prompt': enhanced,
        'key_elements': [who, style] + mood_list[:2],
        'composition': 'centered',
        'color_palette': 'warm, inviting colors',
        'original_who': who,
        'original_what': what,
        'original_where': where,
        'original_moods': moods,
        'mode': mode,
        'fallback': True
    }
