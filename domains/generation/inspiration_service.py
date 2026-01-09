"""
Inspiration Service - AI-powered creative suggestions.

@module domains.generation.inspiration_service
@version 1.0.0

This service provides FREE creative inspiration suggestions for
children's book illustrations using OpenAI GPT-4o-mini.

Changes:
- v1.0.0: Initial creation - Extracted from api/user/generation_story.py
          Implemented DDD architecture
          Fixed GS-CODE-3: Moved fallback data to Service layer
"""

import json
import logging
from typing import Dict, List, Any, Optional

from shared.ai.story_generator import client as openai_client

logger = logging.getLogger(__name__)


# ==========================================
# Fallback Data
# ==========================================

FALLBACK_SUGGESTIONS = [
    {
        "character": "A friendly robot with colorful lights",
        "action": "learning to dance",
        "setting": "in a cozy playroom",
        "style": "cartoon",
        "moods": ["joyful", "funny"]
    },
    {
        "character": "A brave little mouse with a tiny hat",
        "action": "exploring a magical library",
        "setting": "among giant books and floating lanterns",
        "style": "fantasy",
        "moods": ["adventurous", "mysterious"]
    },
    {
        "character": "A wise owl wearing spectacles",
        "action": "teaching baby animals",
        "setting": "in a sunlit forest clearing",
        "style": "watercolor",
        "moods": ["warm", "peaceful"]
    }
]


# ==========================================
# Category Prompts
# ==========================================

CATEGORY_PROMPTS = {
    "character": """Generate 3 creative character ideas for children's book illustrations.
Each character should be unique, imaginative, and child-friendly.

Return JSON:
{
  "suggestions": [
    {"character": "description", "personality": "trait"}
  ]
}""",
    "scene": """Generate 3 creative scene/setting ideas for children's book illustrations.
Each scene should be vivid, magical, and spark imagination.

Return JSON:
{
  "suggestions": [
    {"setting": "description", "atmosphere": "mood description"}
  ]
}""",
    "story": """Generate 3 creative mini-story ideas for children's book illustrations.
Each story should have a character, action, and setting that work together.

Return JSON:
{
  "suggestions": [
    {"character": "who", "action": "what they're doing", "setting": "where", "mood": "atmosphere"}
  ]
}""",
    "all": """Generate 3 complete creative ideas for children's book illustrations.
Each idea should include a character, what they're doing, where, and suggested art style.
Be creative, whimsical, and child-friendly!

Return JSON:
{
  "suggestions": [
    {
      "character": "A curious orange tabby cat with big sparkly eyes",
      "action": "discovering a hidden treasure chest",
      "setting": "in an enchanted forest clearing with glowing mushrooms",
      "style": "watercolor",
      "moods": ["adventurous", "mysterious"]
    }
  ]
}"""
}


# ==========================================
# Inspiration Service
# ==========================================

class InspirationService:
    """
    Service for AI-powered creative inspiration.

    Generates creative suggestions for children's book illustrations.
    This is a FREE service (no credits required).

    Features:
    - Category-based prompt selection (all/character/scene/story)
    - OpenAI GPT-4o-mini with JSON mode
    - Graceful fallback on errors (3 hardcoded suggestions)
    """

    def __init__(self):
        """Initialize InspirationService (stateless)."""
        pass

    async def generate_inspiration(
        self,
        user_id: str,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate creative inspiration suggestions.

        Args:
            user_id: User ID (for logging only)
            category: Category (all/character/scene/story, default: all)

        Returns:
            Dict with:
            - suggestions: List of creative ideas
            - category: Category used
            - fallback: True if fallback was used (optional)
        """
        category = category or "all"

        try:
            prompt = self._get_prompt(category)

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are a creative children's book illustrator. Generate imaginative, whimsical, and age-appropriate ideas."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.9,
                max_tokens=500
            )

            result = json.loads(response.choices[0].message.content)
            return {
                "suggestions": result.get("suggestions", []),
                "category": category,
            }

        except Exception as e:
            logger.error(
                f"Inspiration generation failed: {e}",
                extra={
                    "error_type": type(e).__name__,
                    "category": category,
                    "user_id_prefix": user_id[:8],  # Only log prefix for privacy
                },
                exc_info=True  # Include stack trace in logs
            )

            # Graceful degradation: Return fallback suggestions
            return {
                "suggestions": FALLBACK_SUGGESTIONS,
                "category": category,
                "fallback": True,
                # v1.0.0: GS-LOW-2 - Don't expose internal error details
            }

    def _get_prompt(self, category: str) -> str:
        """Get AI prompt for the given category."""
        return CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["all"])
