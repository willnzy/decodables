"""
Story Generation Router - AI story and inspiration endpoints

@module api.user.generation_story
@version 3.28

Changes:
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

from core.database import get_database_client
from infrastructure.repositories.user_repository import SupabaseUserRepository
from infrastructure.rate_limiter import limiter
from domains.billing import BillingService
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

def get_story_service() -> StoryGenerationService:
    """Dependency injection factory for StoryGenerationService."""
    db = get_database_client()
    user_repo = SupabaseUserRepository(db)
    billing_service = BillingService(user_repository=user_repo)
    return StoryGenerationService(billing_service=billing_service)


def get_inspiration_service() -> InspirationService:
    """Dependency injection factory for InspirationService."""
    return InspirationService()


# ==========================================
# Story Generation
# ==========================================

@router.post("/story")
@limiter.limit("20/minute")
async def gen_story(
    request: Request,
    req: StoryGenRequest,
    user: dict = Depends(get_current_user),
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
            user_id=user["id"],
            tier=(user.get("tier") or "free").lower(),
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
    user: dict = Depends(get_current_user),
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
    result = await inspiration_service.generate_inspiration(
        user_id=user["id"],
        category=req.category,
    )
    return result
