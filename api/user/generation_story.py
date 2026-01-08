"""
Story Generation Router - AI story and inspiration endpoints

@module api.user.generation_story
@version 3.25

Changes:
- v3.25: Add config-driven credit deduction for story generation
         Use DDD BillingService with automatic refund on failure

Endpoints:
- POST /api/v2/user/generate/story - Generate story JSON
- POST /api/generate/inspiration - AI inspiration suggestions (free)
"""

import json
import logging

from fastapi import APIRouter, HTTPException, Request, Depends

from container import get_container
from shared.ai.story_generator import generate_story_json, client as openai_client
from infrastructure.rate_limiter import limiter
from dependencies import get_current_user
from api.schemas.user.generation import StoryGenRequest, InspirationRequest
from application.services.generation_helpers import get_text_generation_cost
from domains.billing.value_objects import TransactionType, CreditBucket
from domains.billing.exceptions import InsufficientCreditsException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate/story", tags=["generation-story-v2"])


# ==========================================
# Story Generation
# ==========================================

@router.post("/story")
@limiter.limit("20/minute")
async def gen_story(request: Request, req: StoryGenRequest, user: dict = Depends(get_current_user)):
    """
    Generate story JSON using AI.

    Credit cost is config-driven (credits.cost.text_generation).
    Currently set to 0 (free), but can be changed via database config.
    """
    user_id = user["id"]
    tier = (user.get("tier") or "free").lower()

    # Get cost from config (currently 0, but can be changed)
    cost = get_text_generation_cost()

    # Only deduct credits if cost > 0
    billing_service = get_container().billing_service
    idempotency_key = None

    if cost > 0:
        import time
        import uuid
        idempotency_key = f"gen_story_{user_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        try:
            await billing_service.deduct_credits(
                user_id=user_id,
                amount=cost,
                tx_type=TransactionType.GENERATION,
                description=f"Story generation: {req.topic[:30]}..." if len(req.topic) > 30 else f"Story generation: {req.topic}",
                idempotency_key=idempotency_key,
            )
        except InsufficientCreditsException as e:
            raise HTTPException(402, f"Insufficient credits: need {e.required}, have {e.available}")
        except Exception as e:
            logger.error(f"Credit deduction failed: {e}")
            raise HTTPException(500, "Failed to process credits")

    # Generate story with automatic refund on failure
    try:
        result = generate_story_json(
            req.topic,
            user_id=user_id,
            tier=tier
        )
        return result
    except Exception as e:
        # Generation failed - refund credits if we charged
        if cost > 0 and idempotency_key:
            logger.error(f"Story generation failed, refunding {cost} credits: {e}")
            try:
                await billing_service.add_credits(
                    user_id=user_id,
                    amount=cost,
                    bucket=CreditBucket.PERMANENT,
                    tx_type=TransactionType.REFUND,
                    description=f"Refund: story generation failed - {str(e)[:50]}",
                    idempotency_key=f"refund_{idempotency_key}",
                )
                logger.info(f"Refunded {cost} credits to user {user_id}")
            except Exception as refund_error:
                logger.error(f"CRITICAL: Failed to refund credits: {refund_error}")

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
