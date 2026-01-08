"""
Story Generation Router - AI story and inspiration endpoints

@module api.user.generation_story
@version 3.24

Endpoints:
- POST /api/v2/user/generate/story - Generate story JSON
- POST /api/generate/inspiration - AI inspiration suggestions
"""

import json
import logging

from fastapi import APIRouter, HTTPException, Request, Depends

from shared.ai.story_generator import generate_story_json, client as openai_client
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user
from api.schemas.user.generation import StoryGenRequest, InspirationRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate/story", tags=["generation-story-v2"])


# ==========================================
# Story Generation
# ==========================================

@router.post("/story")
@limiter.limit("20/minute")
def gen_story(request: Request, req: StoryGenRequest, user: dict = Depends(get_current_user)):
    """Generate story JSON using AI."""
    try:
        tier = (user.get("tier") or "free").lower()
        return generate_story_json(
            req.topic, 
            user_id=user["id"],
            tier=tier
        )
    except Exception as e:
        raise HTTPException(500, str(e))


# ==========================================
# AI Inspiration Generator
# ==========================================

@router.post("/inspiration")
@limiter.limit("30/minute")
async def gen_inspiration(request: Request, req: InspirationRequest, user: dict = Depends(get_current_user)):
    """
    Generate creative inspiration suggestions using AI.
    
    This is a free endpoint (no credits required) that helps users
    get started with image generation ideas.
    """
    try:
        category = req.category or "all"
        
        # Build prompt based on category
        if category == "character":
            prompt = """Generate 3 creative character ideas for children's book illustrations.
Each character should be unique, imaginative, and child-friendly.

Return JSON:
{
  "suggestions": [
    {"character": "description", "personality": "trait"}
  ]
}"""
        elif category == "scene":
            prompt = """Generate 3 creative scene/setting ideas for children's book illustrations.
Each scene should be vivid, magical, and spark imagination.

Return JSON:
{
  "suggestions": [
    {"setting": "description", "atmosphere": "mood description"}
  ]
}"""
        elif category == "story":
            prompt = """Generate 3 creative mini-story ideas for children's book illustrations.
Each story should have a character, action, and setting that work together.

Return JSON:
{
  "suggestions": [
    {"character": "who", "action": "what they're doing", "setting": "where", "mood": "atmosphere"}
  ]
}"""
        else:  # "all"
            prompt = """Generate 3 complete creative ideas for children's book illustrations.
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
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a creative children's book illustrator. Generate imaginative, whimsical, and age-appropriate ideas."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=500
        )
        
        result = json.loads(response.choices[0].message.content)
        return {"suggestions": result.get("suggestions", []), "category": category}
        
    except Exception as e:
        logger.error(f"Inspiration generation failed: {e}")
        # Return fallback suggestions
        return {
            "suggestions": [
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
            ],
            "category": category,
            "fallback": True
        }
