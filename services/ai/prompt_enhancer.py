"""
Prompt Enhancement Service for AI Image Generation

Uses GPT-4o-mini to expand user's simple descriptions into detailed,
high-quality image generation prompts.

This is a standard technique used by:
- DALL-E 3 (uses GPT-4 to rewrite prompts)
- Midjourney (automatic prompt expansion)
- Adobe Firefly (built-in prompt optimization)

Cost: ~$0.0003 per call (100-200 input + 150 output tokens)

Supports two enhancement modes:
1. AI Design Page mode (theme-based): For page-level illustrations
2. Asset Generation mode (5W1H-based): For standalone assets with Who/What/Where/Style/Mood
"""

import json
import os
from openai import OpenAI
from typing import Optional, List

client = OpenAI()

# System prompt for the enhancer - designed for children's book illustrations
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


# System prompt for 5W1H asset generation enhancement
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


# Style descriptions to augment the prompt
STYLE_DESCRIPTIONS = {
    'cartoon': 'cartoon style, bold outlines, vibrant saturated colors, expressive characters, playful proportions',
    'watercolor': 'watercolor painting style, soft color bleeding, artistic texture, gentle gradients, delicate brushstrokes',
    'sketch': 'pencil sketch style, hand-drawn linework, artistic hatching, charming imperfections',
    'fantasy': 'fantasy art style, magical atmosphere, enchanting lighting, sparkles and glow effects, dreamy',
    'realistic': 'realistic illustration, detailed textures, natural lighting, accurate proportions, depth and dimension',
    'flat': 'flat design style, minimalist shapes, clean vectors, limited color palette, modern aesthetic',
    'scifi': 'science fiction style, futuristic elements, neon accents, sleek technology, space or cyber aesthetic'
}

# Mood descriptions for 5W1H enhancement
MOOD_DESCRIPTIONS = {
    'warm': 'warm, heartwarming atmosphere, golden hour lighting, cozy feeling',
    'adventurous': 'adventurous, exciting, dynamic energy, sense of movement',
    'mysterious': 'mysterious, magical ambiance, dramatic lighting, intriguing',
    'joyful': 'joyful, cheerful mood, bright and happy, playful energy',
    'peaceful': 'peaceful, serene scene, calm and tranquil, soft atmosphere',
    'funny': 'funny, humorous style, playful and silly, exaggerated expressions'
}


def enhance_prompt(
    theme: str,
    character: Optional[str] = None,
    style: str = 'cartoon',
    mode: str = 'guided',
    creativity_level: float = 0.3
) -> dict:
    """
    Enhance a simple user description into a detailed image prompt.
    
    Args:
        theme: What the page is about (e.g., "Counting fun", "A day at the zoo")
        character: Main character description (optional)
        style: Art style ID (cartoon, watercolor, sketch, fantasy, realistic, flat)
        mode: "guided" (more accurate) or "flexible" (more creative)
        creativity_level: 0.0-1.0 slider value (0=precise, 1=very creative)
    
    Returns:
        dict with enhanced_prompt, key_elements, and composition
        
    Cost: ~$0.0003 per call
    """
    # Build user message
    user_input = f"""Theme: {theme}
Character: {character or 'Not specified - use appropriate characters for the theme'}
Art Style: {style} ({STYLE_DESCRIPTIONS.get(style, 'colorful illustration')})
Mode: {mode}"""

    # Calculate temperature based on mode and creativity_level
    # Guided mode: 0.2-0.5 range (lower for accuracy)
    # Flexible mode: uses creativity_level to interpolate 0.3-0.9
    if mode == 'guided':
        temperature = 0.3  # Fixed low temperature for guided mode
    else:
        # Map creativity_level (0-1) to temperature (0.3-0.9)
        temperature = 0.3 + (creativity_level * 0.6)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": PROMPT_ENHANCER_SYSTEM},
                {"role": "user", "content": user_input}
            ],
            temperature=temperature,
            max_tokens=300
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Ensure required fields exist
        if 'enhanced_prompt' not in result:
            raise ValueError("Missing enhanced_prompt in response")
            
        # Add style suffix if not present
        enhanced = result['enhanced_prompt']
        style_desc = STYLE_DESCRIPTIONS.get(style, '')
        if style_desc and style not in enhanced.lower():
            enhanced = f"{enhanced}, {style_desc}"
        
        result['enhanced_prompt'] = enhanced
        result['original_theme'] = theme
        result['original_character'] = character
        result['mode'] = mode
        
        print(f"✨ Prompt enhanced ({mode} mode): {len(enhanced)} chars")
        return result
        
    except Exception as e:
        print(f"❌ Prompt enhancement failed: {e}")
        # Fallback: return a basic enhanced prompt without LLM
        return fallback_enhance(theme, character, style, mode)


def fallback_enhance(
    theme: str,
    character: Optional[str] = None,
    style: str = 'cartoon',
    mode: str = 'guided'
) -> dict:
    """
    Fallback prompt enhancement without LLM call.
    Used when the API call fails.
    """
    parts = []
    
    # Subject
    if character:
        parts.append(f"{character}")
    
    # Theme/action
    if theme:
        if character:
            parts.append(f"in a scene about {theme}")
        else:
            parts.append(f"Scene depicting {theme}")
    
    # Style
    style_desc = STYLE_DESCRIPTIONS.get(style, 'colorful illustration')
    parts.append(style_desc)
    
    # Standard suffixes
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
        'fallback': True  # Flag to indicate fallback was used
    }


def enhance_asset_prompt(
    who: str,
    what: Optional[str] = None,
    where: Optional[str] = None,
    style: str = 'cartoon',
    moods: Optional[List[str]] = None,
    mode: str = 'guided',
    creativity_level: float = 0.3
) -> dict:
    """
    Enhance a 5W1H-structured input into a detailed image prompt.
    
    This is optimized for the "Generate Assets with AI" modal which uses
    structured form inputs (Who/What/Where/Style/Mood).
    
    Args:
        who: Main character description (required)
        what: Action or activity (optional)
        where: Setting/scene (optional)
        style: Art style ID (cartoon, watercolor, sketch, fantasy, realistic, scifi, flat)
        moods: List of mood tags (warm, adventurous, mysterious, joyful, peaceful, funny)
        mode: "guided" (more accurate) or "flexible" (more creative)
        creativity_level: 0.0-1.0 slider value (0=precise, 1=very creative)
    
    Returns:
        dict with enhanced_prompt, key_elements, composition, color_palette
        
    Cost: ~$0.0003 per call
    """
    # Build structured input
    mood_list = moods or ['warm']
    mood_descriptions = [MOOD_DESCRIPTIONS.get(m, m) for m in mood_list if m]
    
    user_input = f"""Who: {who}
What: {what or 'in a natural pose'}
Where: {where or 'in a simple background'}
Art Style: {style} ({STYLE_DESCRIPTIONS.get(style, 'colorful illustration')})
Moods: {', '.join(mood_list)} ({'; '.join(mood_descriptions[:3])})
Mode: {mode}"""

    # Calculate temperature based on mode and creativity_level
    if mode == 'guided':
        temperature = 0.3  # Fixed low temperature for guided mode
    else:
        # Map creativity_level (0-1) to temperature (0.3-0.9)
        temperature = 0.3 + (creativity_level * 0.6)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ASSET_ENHANCER_SYSTEM},
                {"role": "user", "content": user_input}
            ],
            temperature=temperature,
            max_tokens=400
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Ensure required fields exist
        if 'enhanced_prompt' not in result:
            raise ValueError("Missing enhanced_prompt in response")
            
        # Add style suffix if not present
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
        
        print(f"✨ Asset prompt enhanced ({mode} mode): {len(enhanced)} chars")
        return result
        
    except Exception as e:
        print(f"❌ Asset prompt enhancement failed: {e}")
        # Fallback: return a basic enhanced prompt without LLM
        return fallback_asset_enhance(who, what, where, style, moods, mode)


def fallback_asset_enhance(
    who: str,
    what: Optional[str] = None,
    where: Optional[str] = None,
    style: str = 'cartoon',
    moods: Optional[List[str]] = None,
    mode: str = 'guided'
) -> dict:
    """
    Fallback 5W1H prompt enhancement without LLM call.
    Used when the API call fails.
    """
    parts = []
    
    # Who (required)
    parts.append(who)
    
    # What (action)
    if what:
        parts.append(what)
    
    # Where (setting)
    if where:
        parts.append(where)
    
    # Style
    style_desc = STYLE_DESCRIPTIONS.get(style, 'colorful illustration')
    parts.append(style_desc)
    
    # Moods
    if moods:
        mood_prompts = [MOOD_DESCRIPTIONS.get(m, m) for m in moods[:3]]
        parts.extend(mood_prompts)
    
    # Standard suffixes
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


# Test the module
if __name__ == "__main__":
    # Test guided mode (theme-based)
    print("\n=== THEME-BASED: GUIDED MODE TEST ===")
    result = enhance_prompt(
        theme="Counting fun with numbers 1-5",
        character="A friendly orange cat",
        style="cartoon",
        mode="guided"
    )
    print(json.dumps(result, indent=2))
    
    # Test flexible mode (theme-based)
    print("\n=== THEME-BASED: FLEXIBLE MODE TEST ===")
    result = enhance_prompt(
        theme="Learning to share",
        character=None,
        style="watercolor",
        mode="flexible"
    )
    print(json.dumps(result, indent=2))
    
    # Test 5W1H asset enhancement - guided
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
    
    # Test 5W1H asset enhancement - flexible
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