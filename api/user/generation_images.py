"""
Image Generation Router - AI image generation endpoints

@module api.user.generation_images
@version 3.29 (Container DI Migration)

Changes:
- v3.29: Container DI Migration
  - Migrated to Container-based dependency injection
  - Removed direct get_async_db_client() calls
  - Removed direct infrastructure.repositories imports
  - Architecture: API → Container → Service → Repository
- v3.28: GI-CRITICAL-1 fix - Added GenerationService with DI
         - Created domains/generation/generation_service.py
         - Migrated to DDD architecture: API → Service → Repository
         - Reduced API layer from 500 to 250 lines (-50%)
         - All business logic moved to GenerationService
- v3.27: GI-P0-001~004 fixes - Comprehensive input validation
         - Prompt validation with length limits and injection detection
         - Reference image URL SSRF prevention
         - Enhanced safety check integration
         GI-H2 fix - Generation timeout protection (asyncio.wait_for)
         GI-H4 fix - Sanitized error messages
         GI-M4 fix - Correct cost calculation in generation history
- v3.26: GI-P0-1 fix - validate prompts non-empty before billing
         GI-H4 fix - don't expose balance in error messages
- v3.25: Migrate to DDD BillingService with atomic operations
         Use config-driven costs from generation_helpers
         Add transaction-based refund on generation failure

Endpoints:
- POST /api/v2/user/generate/images - Sync image generation
- POST /api/v2/user/generate/images/async - Async image generation (v3.23)
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends

from domains.identity.aggregates.user_profile import UserProfile
from container import get_container
from domains.generation import GenerationService
from domains.generation.generation_service import (
    GenerationTimeoutException,
    GenerationFailedException,
    EmptyGenerationException,
)
from domains.billing.exceptions import InsufficientCreditsException
from infrastructure.rate_limiter import limiter
from core.utils.timezone import get_request_timezone
from core.utils.validation import validate_prompts, validate_reference_image_url
from dependencies import get_current_user
from api.schemas.user.generation import ImageGenRequest
from application.services.generation_helpers import (
    check_prompt_safety,
    get_model_for_tier,
    validate_generation_mode,
    validate_creativity_level,
    enhance_prompts,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate/images", tags=["generation-images-v2"])


# ==========================================
# Dependency Injection
# ==========================================

async def get_generation_service() -> GenerationService:
    """
    Dependency injection factory for GenerationService via Container.

    WHY Container-based DI?
    - Centralized service instantiation with all dependencies
    - Testable (mock injection)
    - Follows DIP (Dependency Inversion Principle)
    """
    container = get_container()
    return await container.get_generation_service()


# ==========================================
# Sync Image Generation
# ==========================================

@router.post("/images")
@limiter.limit("10/minute")
async def gen_images(
    request: Request,
    req: ImageGenRequest,
    user: UserProfile = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),  # v3.28: DI
):
    """
    Generate images using AI (PRD v3.2).

    Model selection based on tier:
    - Free/Starter: Standard model (flux-schnell)
    - Pro: High-quality model (flux-dev)

    Supports:
    - Optional reference image for style/content guidance
    - AI Design Page mode with prompt enhancement (when theme is provided)
    - Generation modes: "guided" (accurate) or "flexible" (creative)
    """
    # v3.27: GI-P0-001 - Comprehensive prompt validation
    is_valid, error = validate_prompts(req.prompts)
    if not is_valid:
        raise HTTPException(400, error)

    # v3.27: GI-P0-002 - Reference image URL SSRF prevention
    is_valid, error = validate_reference_image_url(req.reference_image)
    if not is_valid:
        raise HTTPException(400, error)

    # v3.27: GI-P0-003 - Enhanced safety check (with Unicode normalization)
    if check_prompt_safety(req.prompts):
        raise HTTPException(400, "Content policy violation")

    # Validate parameters
    num_images = max(1, min(4, req.num_images or 1))
    tier = (user.tier.value if user.tier else "t1").lower()
    model = get_model_for_tier(tier)
    generation_mode = validate_generation_mode(req.generation_mode)
    creativity_level = validate_creativity_level(req.creativity_level)

    # Get timezone
    tz = await get_request_timezone(request, user_id=user.user_id)

    # Enhance prompts if needed
    enhancement_data = enhance_prompts(
        prompts=req.prompts,
        theme=req.theme,
        character=req.character,
        style=req.style or "cartoon",
        mode=generation_mode,
        creativity_level=creativity_level,
        user_id=user.user_id,
        tier=tier,
        who=req.who,
        what=req.what,
        where=req.where,
        moods=req.moods,
        enhance_enabled=req.enhance_prompt,
    )
    prompts_to_use = enhancement_data["prompts"]
    prompt_enhanced = enhancement_data["enhanced"]
    enhancement_result = enhancement_data["result"]
    enhanced_prompt_text = enhancement_result.get("enhanced_prompt") if enhancement_result else None

    # v3.28: Generate images via Service (DDD compliant)
    try:
        result = await generation_service.generate_images_sync(
            user_id=user.user_id,
            prompts=req.prompts,
            num_images=num_images,
            model=model,
            tier=tier,
            reference_image=req.reference_image,
            reference_strength=req.reference_strength or 0.7,
            image_size=req.image_size or "landscape_4_3",
            generation_mode=generation_mode,
            creativity_level=creativity_level,
            negative_prompt=req.negative_prompt,
            project_id=req.project_id,
            theme=req.theme,
            prompts_to_use=prompts_to_use,
            enhanced_prompt_text=enhanced_prompt_text,
            timezone=tz,
        )
    except InsufficientCreditsException as e:
        # v3.26: GI-H4 fix - don't expose exact balance requirement in error
        required = e.details.get("required") if hasattr(e, 'details') else None
        msg = f"Insufficient credits. This operation requires {required} credits." if required else "Insufficient credits for this operation."
        raise HTTPException(402, msg)
    except GenerationTimeoutException:
        raise HTTPException(504, "Image generation timed out. Credits have been refunded.")
    except GenerationFailedException:
        raise HTTPException(500, "Image generation failed. Credits have been refunded.")
    except EmptyGenerationException:
        raise HTTPException(500, "No images were generated. Credits have been refunded.")
    except Exception as e:
        logger.error(f"Unexpected error in image generation: {e}")
        raise HTTPException(500, "An unexpected error occurred")

    # Add enhancement metadata to response
    result["prompt_enhanced"] = prompt_enhanced
    if enhancement_result:
        result["enhanced_prompt"] = enhancement_result.get("enhanced_prompt")
        result["key_elements"] = enhancement_result.get("key_elements", [])

    return result


# ==========================================
# Async Image Generation (v3.23)
# ==========================================

@router.post("/images/async")
@limiter.limit("10/minute")
async def gen_images_async(
    request: Request,
    req: ImageGenRequest,
    user: UserProfile = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),  # v3.28: DI
):
    """
    Async image generation using task queue (v3.23).

    Returns immediately with task_id for progress tracking.
    Use WebSocket (/ws/task/{task_id}) or polling (/api/tasks/{task_id}) for status.
    """
    # v3.27: GI-P0-001 - Comprehensive prompt validation
    is_valid, error = validate_prompts(req.prompts)
    if not is_valid:
        raise HTTPException(400, error)

    # v3.27: GI-P0-002 - Reference image URL SSRF prevention
    is_valid, error = validate_reference_image_url(req.reference_image)
    if not is_valid:
        raise HTTPException(400, error)

    # v3.27: GI-P0-003 - Enhanced safety check (with Unicode normalization)
    if check_prompt_safety(req.prompts):
        raise HTTPException(400, "Content policy violation")

    # Validate parameters
    num_images = max(1, min(4, req.num_images or 1))
    tier = (user.tier.value if user.tier else "t1").lower()
    model = get_model_for_tier(tier)
    generation_mode = validate_generation_mode(req.generation_mode)
    creativity_level = validate_creativity_level(req.creativity_level)

    # Enhance prompts if needed
    enhancement_data = enhance_prompts(
        prompts=req.prompts,
        theme=req.theme,
        character=req.character,
        style=req.style or "cartoon",
        mode=generation_mode,
        creativity_level=creativity_level,
        user_id=user.user_id,
        tier=tier,
        who=req.who,
        what=req.what,
        where=req.where,
        moods=req.moods,
        enhance_enabled=req.enhance_prompt,
    )
    prompts_to_use = enhancement_data["prompts"]
    enhancement_result = enhancement_data["result"]
    enhanced_prompt_text = enhancement_result.get("enhanced_prompt") if enhancement_result else None

    # v3.28: Async generation via Service (DDD compliant)
    try:
        result = await generation_service.generate_images_async(
            user_id=user.user_id,
            prompts=req.prompts,
            num_images=num_images,
            model=model,
            tier=tier,
            reference_image=req.reference_image,
            reference_strength=req.reference_strength or 0.7,
            image_size=req.image_size or "landscape_4_3",
            generation_mode=generation_mode,
            creativity_level=creativity_level,
            negative_prompt=req.negative_prompt,
            project_id=req.project_id,
            prompts_to_use=prompts_to_use,
            enhanced_prompt_text=enhanced_prompt_text,
        )
    except InsufficientCreditsException as e:
        # v3.26: GI-H4 fix - don't expose exact balance requirement in error
        required = e.details.get("required") if hasattr(e, 'details') else None
        msg = f"Insufficient credits. This operation requires {required} credits." if required else "Insufficient credits for this operation."
        raise HTTPException(402, msg)
    except Exception as e:
        logger.error(f"Async generation error: {e}")
        # Service already refunded if it was a queue failure
        if "temporarily unavailable" in str(e).lower():
            raise HTTPException(503, "Generation service temporarily unavailable. Credits refunded.")
        raise HTTPException(500, "Failed to queue generation task")

    return result
