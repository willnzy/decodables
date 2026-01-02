"""
Prompt Enhancement Service for AI Design Page

Uses GPT-4o-mini to expand user's simple descriptions into detailed,
high-quality image generation prompts.

This is a standard technique used by:
- DALL-E 3 (uses GPT-4 to rewrite prompts)
- Midjourney (automatic prompt expansion)
- Adobe Firefly (built-in prompt optimization)

Cost: ~$0.0003 per call (100-200 input + 150 output tokens)
"""

import json
import os
from openai import OpenAI
from typing import Optional

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


# Style descriptions to augment the prompt
STYLE_DESCRIPTIONS = {
    'cartoon': 'cartoon style, bold outlines, vibrant saturated colors, expressive characters, playful proportions',
    'watercolor': 'watercolor painting style, soft color bleeding, artistic texture, gentle gradients, delicate brushstrokes',
    'sketch': 'pencil sketch style, hand-drawn linework, artistic hatching, charming imperfections',
    'fantasy': 'fantasy art style, magical atmosphere, enchanting lighting, sparkles and glow effects, dreamy',
    'realistic': 'realistic illustration, detailed textures, natural lighting, accurate proportions, depth and dimension',
    'flat': 'flat design style, minimalist shapes, clean vectors, limited color palette, modern aesthetic'
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


# Test the module
if __name__ == "__main__":
    # Test guided mode
    print("\n=== GUIDED MODE TEST ===")
    result = enhance_prompt(
        theme="Counting fun with numbers 1-5",
        character="A friendly orange cat",
        style="cartoon",
        mode="guided"
    )
    print(json.dumps(result, indent=2))
    
    # Test flexible mode
    print("\n=== FLEXIBLE MODE TEST ===")
    result = enhance_prompt(
        theme="Learning to share",
        character=None,
        style="watercolor",
        mode="flexible"
    )
    print(json.dumps(result, indent=2))
