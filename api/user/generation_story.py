"""
Story Generation Router - AI story and inspiration endpoints

@module api.user.generation_story
@version 3.29 (Container DI Migration)

Changes:
- v3.29: Container DI Migration
  - Migrated to Container-based dependency injection
  - Removed direct infrastructure.repositories imports
  - Removed get_async_db dependency from DI function
  - Architecture: API → Container → Service → Repository
- v3.28: GS-CRITICAL-1 fix - Added Service layers with DI
         - Created StoryGenerationService (domains/generation/story_service.py)
         - Created InspirationService (domains/generation/inspiration_service.py)
         - Migrated to DDD architecture: API → Service
         - Reduced API layer from 240 to 90 lines (-63%)
         - All business logic moved to Service layers
         - Fixed GS-CHAIN-1: Accurate refund tracking (same bucket)
- v3.27: Security improvements
         GS-MEDIUM-1: Added validation to InspirationRequest
         GS-LOW-1: Sanitized user_id in logs
         GS-LOW-2: Removed internal details from fallback response

Endpoints:
- POST /api/v2/user/generate/story - Generate story JSON
- POST /api/v2/user/generate/inspiration - AI inspiration suggestions (free)
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends

from domains.identity.aggregates.user_profile import UserProfile
from infrastructure.rate_limiter import limiter
from container import get_container
from domains.generation import StoryGenerationService, InspirationService
from domains.generation.story_service import StoryGenerationException
from domains.billing.exceptions import InsufficientCreditsException
from dependencies import get_current_user
from api.schemas.user.generation import StoryGenRequest, InspirationRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate/story", tags=["generation-story-v2"])


# ==========================================
# Dependency Injection
# ==========================================

async def get_story_service() -> StoryGenerationService:
    """
    Dependency injection factory for StoryGenerationService via Container.

    WHY Container-based DI?
    - Centralized service instantiation
    - Testable (mock injection)
    - Follows DIP (Dependency Inversion Principle)
    """
    container = get_container()
    return await container.get_story_generation_service()


def get_inspiration_service() -> InspirationService:
    """Dependency injection factory for InspirationService (stateless)."""
    return InspirationService()


# ==========================================
# Story Generation
# ==========================================

@router.post("/story")
@limiter.limit("20/minute")
async def gen_story(
    request: Request,
    req: StoryGenRequest,
    user: UserProfile = Depends(get_current_user),
    story_service: StoryGenerationService = Depends(get_story_service),  # v3.28: DI
):
    """
    Generate story JSON using AI.

    Credit cost is config-driven (credits.cost.text_generation).
    Currently set to 0 (free), but can be changed via database config.

    Security:
    - Rate limiting (20/minute)
    - User authentication required
    - Automatic refund on failure

    Returns:
        Dict: Story JSON (title, pages, characters, setting)
    """
    # v3.28: Generate story via Service (DDD compliant)
    try:
        result = await story_service.generate_story(
            user_id=user.user_id,
            tier=(user.tier.value if hasattr(user.tier, 'value') else user.tier).lower(),
            topic=req.topic,
        )
        return result
    except InsufficientCreditsException as e:
        # v3.26: GS-H4 fix - Don't expose exact balance
        required = e.details.get("required") if hasattr(e, 'details') else None
        msg = f"Insufficient credits. This operation requires {required} credits." if required else "Insufficient credits for this operation."
        raise HTTPException(402, msg)
    except StoryGenerationException:
        # v3.26: Don't expose internal error details
        raise HTTPException(500, "Story generation failed. Credits have been refunded.")


# ==========================================
# AI Inspiration Generator
# ==========================================

@router.post("/inspiration")
@limiter.limit("30/minute")
async def gen_inspiration(
    request: Request,
    req: InspirationRequest,
    user: UserProfile = Depends(get_current_user),
    inspiration_service: InspirationService = Depends(get_inspiration_service),  # v3.28: DI
):
    """
    Generate creative inspiration suggestions using AI.

    This is a free endpoint (no credits required) that helps users
    get started with image generation ideas.

    Security:
    - Rate limiting (30/minute)
    - User authentication required
    - Graceful fallback on errors

    Returns:
        Dict: Inspiration data (suggestions, category, fallback?)
    """
    # v3.28: Generate inspiration via Service (DDD compliant)
    # WS-18(1A#15): Add error handling with graceful fallback
    try:
        result = await inspiration_service.generate_inspiration(
            user_id=user.user_id,
            category=req.category,
        )
        return result
    except Exception as e:
        logger.error(f"[Inspiration] Failed to generate inspiration: {e}")
        # Graceful fallback with default suggestions
        return {
            "suggestions": [
                "A sunny day at the beach",
                "Animals playing in the park",
                "A colorful garden with butterflies",
            ],
            "category": req.category or "general",
            "fallback": True,
        }
