"""Theme Generator - AI-powered theme suggestion service.

@module shared.ai.theme_generator
@version 2.1.0

Generates theme suggestions for specific dates using AI analysis.
Part of the Theme System v2.1 batch generation feature.
"""

import json
import logging
import uuid
from datetime import date
from typing import Dict, Any, List, Optional

from shared.ai import admin_chat

logger = logging.getLogger(__name__)


# ==========================================
# Prompt Templates
# ==========================================

THEME_GENERATION_PROMPT = """You are a theme designer for Make Decodables, a platform that helps teachers create decodable books for children.

Today's date for theme design: {date} ({weekday})

Please analyze this date for any significant events, holidays, or occasions, and generate 3 theme design alternatives.

## Selection Criteria (use these to rank alternatives)

Alternative A should be the MOST recommended, based on:
1. **Education Relevance** (40%): Connection to education, children, reading, learning
2. **Visual Appeal** (30%): Child-friendly, engaging design potential
3. **Holiday Importance** (20%): Global recognition of the day/event
4. **Brand Fit** (10%): Alignment with Make Decodables brand tone

## Output Format

Return a JSON object with this structure:
```json
{{
  "analysis": {{
    "date": "{date}",
    "events": ["List of significant events on this date"],
    "holidays": ["List of holidays"],
    "notable_days": ["World X Day, National Y Day, etc."]
  }},
  "alternatives": [
    {{
      "id": "A",
      "name": "Theme Name",
      "name_i18n": {{"en": "English Name", "zh": "中文名称"}},
      "category": "holiday|memorial|historical|notable|campaign|special",
      "priority": 50-95,
      "slogan": "Catchy slogan for the theme",
      "slogan_i18n": {{"en": "English slogan", "zh": "中文标语"}},
      "description": "Brief description of why this theme is appropriate",
      "theme_config": {{
        "colors": {{
          "primary": "#HEXCOLOR",
          "secondary": "#HEXCOLOR",
          "accent": "#HEXCOLOR",
          "background": "#HEXCOLOR"
        }},
        "badge": {{
          "icon": "emoji or icon name",
          "text": "Badge text"
        }}
      }},
      "source_url": "URL to learn more about this day (optional)"
    }},
    {{
      "id": "B",
      "name": "Alternative Theme 2",
      ...
    }},
    {{
      "id": "C",
      "name": "Alternative Theme 3",
      ...
    }}
  ],
  "recommendation": {{
    "selected_id": "A",
    "reason": "Why Alternative A is the best choice",
    "scores": {{
      "education_relevance": 85,
      "visual_appeal": 90,
      "holiday_importance": 70,
      "brand_fit": 80
    }}
  }}
}}
```

## Category Guidelines

- **holiday**: Major holidays (Christmas, New Year, Chinese New Year)
- **memorial**: Memorial/awareness days (MLK Day, Earth Day)
- **historical**: Historical events (Moon landing anniversary)
- **notable**: Fun observance days (Pi Day, Star Wars Day)
- **campaign**: Marketing campaign tie-ins
- **special**: Special occasions

## Priority Guidelines

- 95: Major global holidays (Christmas, New Year)
- 85: Significant regional holidays (Thanksgiving, Chinese New Year)
- 75: Important awareness days (Earth Day, World Book Day)
- 65: Notable historical events
- 55: Fun observance days (Pi Day)
- 50: Default/fallback

## Important Notes

- If no significant events exist for this date, create general seasonal themes
- Ensure themes are appropriate for children and educational contexts
- Include at least one creative/playful option
- Colors should be vibrant and child-friendly

Return ONLY the JSON object, no additional text.
"""


# ==========================================
# Theme Generator Service
# ==========================================

class ThemeGeneratorService:
    """Service for generating theme suggestions using AI."""

    async def generate_theme_suggestions(
        self,
        target_date: date,
    ) -> Dict[str, Any]:
        """
        Generate theme suggestions for a specific date.

        Args:
            target_date: Date to generate themes for

        Returns:
            Dict with analysis, alternatives, and recommendation
        """
        try:
            # Build prompt
            weekday = target_date.strftime("%A")
            prompt = THEME_GENERATION_PROMPT.format(
                date=target_date.isoformat(),
                weekday=weekday,
            )

            # Call AI service
            response = await admin_chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )

            # Parse response
            content = response.get("content", "")

            # Try to extract JSON from response
            result = self._parse_json_response(content)

            if not result:
                logger.warning(f"Failed to parse AI response for {target_date}, using fallback")
                return self._generate_fallback_theme(target_date)

            # Ensure all alternatives have unique IDs
            for alt in result.get("alternatives", []):
                if not alt.get("id"):
                    alt["id"] = str(uuid.uuid4())[:8].upper()

            return result

        except Exception as e:
            logger.error(f"Failed to generate theme suggestions for {target_date}: {e}")
            return self._generate_fallback_theme(target_date)

    def _parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from AI response."""
        try:
            # Try direct parse
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in response
        try:
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        return None

    def _generate_fallback_theme(self, target_date: date) -> Dict[str, Any]:
        """Generate a fallback theme when AI fails."""
        month_themes = {
            1: ("New Beginnings", "#4A90D9", "fresh_start"),
            2: ("Kindness Month", "#E91E63", "heart"),
            3: ("Spring Awakening", "#8BC34A", "flower"),
            4: ("Earth Month", "#4CAF50", "earth"),
            5: ("Bloom & Grow", "#FFEB3B", "sun"),
            6: ("Summer Fun", "#FF9800", "beach"),
            7: ("Adventure Time", "#2196F3", "explore"),
            8: ("Back to School", "#9C27B0", "book"),
            9: ("Harvest Season", "#FF5722", "leaf"),
            10: ("Creativity Month", "#673AB7", "palette"),
            11: ("Gratitude Month", "#795548", "thanks"),
            12: ("Holiday Magic", "#F44336", "star"),
        }

        month = target_date.month
        theme_name, primary_color, icon = month_themes.get(
            month, ("Daily Learning", "#2196F3", "book")
        )

        alt_id = str(uuid.uuid4())[:8].upper()

        return {
            "analysis": {
                "date": target_date.isoformat(),
                "events": [],
                "holidays": [],
                "notable_days": [],
            },
            "alternatives": [
                {
                    "id": alt_id,
                    "name": theme_name,
                    "name_i18n": {"en": theme_name},
                    "category": "special",
                    "priority": 50,
                    "slogan": f"Learning is always in season!",
                    "slogan_i18n": {"en": "Learning is always in season!"},
                    "description": f"A general theme for {target_date.strftime('%B')}",
                    "theme_config": {
                        "colors": {
                            "primary": primary_color,
                            "secondary": "#FFFFFF",
                            "accent": primary_color,
                            "background": "#F5F5F5",
                        },
                        "badge": {
                            "icon": icon,
                            "text": theme_name,
                        },
                    },
                }
            ],
            "recommendation": {
                "selected_id": alt_id,
                "reason": "Fallback theme for date without specific events",
                "scores": {
                    "education_relevance": 70,
                    "visual_appeal": 70,
                    "holiday_importance": 30,
                    "brand_fit": 80,
                },
            },
        }


# ==========================================
# Module-level instance and helper
# ==========================================

_theme_generator = None


def get_theme_generator() -> ThemeGeneratorService:
    """Get singleton instance of ThemeGeneratorService."""
    global _theme_generator
    if _theme_generator is None:
        _theme_generator = ThemeGeneratorService()
    return _theme_generator


async def generate_theme_suggestions(target_date: date) -> Dict[str, Any]:
    """
    Generate theme suggestions for a specific date.

    Convenience function that uses the singleton instance.

    Args:
        target_date: Date to generate themes for

    Returns:
        Dict with analysis, alternatives, and recommendation
    """
    generator = get_theme_generator()
    return await generator.generate_theme_suggestions(target_date)
