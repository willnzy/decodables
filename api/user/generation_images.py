"""
Image Generation Router - AI image generation endpoints

@module api.user.generation_images
@version 3.25

Changes:
- v3.25: Migrate to DDD BillingService with atomic operations
         Use config-driven costs from generation_helpers
         Add transaction-based refund on generation failure

Endpoints:
- POST /api/v2/user/generate/images - Sync image generation
- POST /api/v2/user/generate/images/async - Async image generation (v3.23)
"""

import logging
import uuid
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Depends

from core.database import get_supabase_client
from container import get_container
from infrastructure.repositories import SupabaseAssetRepository
from shared.ai.image_generator import generate_8_images
from infrastructure.task_queue import task_queue
from domains.platform.analytics_service import track_ai_generation
from domains.billing.value_objects import TransactionType, CreditBucket
from domains.billing.exceptions import InsufficientCreditsException
from infrastructure.rate_limiter import limiter
from core.utils.timezone import get_request_timezone
from dependencies import get_current_user
from api.schemas.user.generation import ImageGenRequest
from application.services.generation_helpers import (
    check_prompt_safety,
    get_model_for_tier,
    validate_generation_mode,
    validate_creativity_level,
    calculate_cost,
    get_base_cost,
    enhance_prompts,
    build_generation_record,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate/images", tags=["generation-images-v2"])


# ==========================================
# Sync Image Generation
# ==========================================

@router.post("/images")
@limiter.limit("10/minute")
async def gen_images(request: Request, req: ImageGenRequest, user: dict = Depends(get_current_user)):
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
    # Safety check
    if check_prompt_safety(req.prompts):
        raise HTTPException(400, "Safety Violation")

    # Validate parameters
    num_images = max(1, min(4, req.num_images or 1))
    tier = (user.get("tier") or "free").lower()
    model = get_model_for_tier(tier)
    generation_mode = validate_generation_mode(req.generation_mode)
    creativity_level = validate_creativity_level(req.creativity_level)

    # Calculate cost using config-driven pricing
    has_reference = bool(req.reference_image)
    cost = calculate_cost(len(req.prompts), has_reference, num_images)
    base_cost = get_base_cost(has_reference)

    # Deduct credits using DDD BillingService with atomic operation
    billing_service = get_container().billing_service
    idempotency_key = f"gen_sync_{user['id']}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    try:
        tx = await billing_service.deduct_credits(
            user_id=user["id"],
            amount=cost,
            tx_type=TransactionType.GENERATION,
            description=f"Gen {len(req.prompts)} images" + (" with ref" if has_reference else ""),
            idempotency_key=idempotency_key,
        )
    except InsufficientCreditsException as e:
        raise HTTPException(402, f"Insufficient credits: need {e.required}, have {e.available}")
    except Exception as e:
        logger.error(f"Credit deduction failed: {e}")
        raise HTTPException(500, "Failed to process credits")

    # Get balance after deduction
    user_credits = await billing_service.get_user_credits(user["id"])
    balance_monthly = user_credits.monthly_credits if user_credits else 0
    balance_permanent = user_credits.permanent_credits if user_credits else 0
    balance_total = balance_monthly + balance_permanent

    # Enhance prompts if needed
    enhancement_data = enhance_prompts(
        prompts=req.prompts,
        theme=req.theme,
        character=req.character,
        style=req.style or "cartoon",
        mode=generation_mode,
        creativity_level=creativity_level,
        user_id=user["id"],
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

    # Generate unique batch ID
    batch_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    generation_start = time.time()
    tz = get_request_timezone(request, user_id=user.get("id"))

    # Generate images with automatic refund on failure
    try:
        urls, task_id = await generate_8_images(
            prompts_to_use,
            model=model,
            reference_image=req.reference_image,
            reference_strength=req.reference_strength or 0.7,
            image_size=req.image_size or "landscape_4_3",
            generation_mode=generation_mode,
            creativity_level=creativity_level,
            negative_prompt=req.negative_prompt,
            num_images=num_images,
            user_id=user["id"],
            tier=tier
        )
    except Exception as e:
        # Generation failed - refund credits atomically
        logger.error(f"Image generation failed, refunding {cost} credits: {e}")
        try:
            await billing_service.add_credits(
                user_id=user["id"],
                amount=cost,
                bucket=CreditBucket.PERMANENT,  # Refund to permanent as conservative choice
                tx_type=TransactionType.REFUND,
                description=f"Refund: generation failed - {str(e)[:50]}",
                idempotency_key=f"refund_{idempotency_key}",
            )
            logger.info(f"Refunded {cost} credits to user {user['id']}")
        except Exception as refund_error:
            logger.error(f"CRITICAL: Failed to refund credits: {refund_error}")
        raise HTTPException(500, "Image generation failed. Credits have been refunded.")

    generation_time_ms = int((time.time() - generation_start) * 1000)

    # Filter successful URLs
    successful_urls = [url for url in urls if url]

    # If no images generated, refund
    if not successful_urls:
        logger.warning(f"No images generated, refunding {cost} credits")
        try:
            await billing_service.add_credits(
                user_id=user["id"],
                amount=cost,
                bucket=CreditBucket.PERMANENT,
                tx_type=TransactionType.REFUND,
                description="Refund: no images generated",
                idempotency_key=f"refund_empty_{idempotency_key}",
            )
        except Exception as refund_error:
            logger.error(f"Failed to refund credits for empty result: {refund_error}")
        raise HTTPException(500, "No images were generated. Credits have been refunded.")

    # Save assets and generation history
    asset_repo = SupabaseAssetRepository(get_supabase_client())
    supabase = get_supabase_client()
    enhanced_prompt_text = enhancement_result.get("enhanced_prompt") if enhancement_result else None

    for idx, url in enumerate(urls):
        if not url:
            continue

        prompt_idx = idx // num_images if num_images > 1 else idx
        prompt_used = prompts_to_use[prompt_idx] if prompt_idx < len(prompts_to_use) else prompts_to_use[0]
        asset_prompt = f"[{req.theme}] {prompt_used}" if req.theme else prompt_used

        # Save to assets table
        await asset_repo.save_asset(user["id"], url, "ai_generated", req.project_id, asset_prompt, tz=tz)

        # Save to user_generations table
        try:
            generation_record = build_generation_record(
                user_id=user["id"],
                image_url=url,
                original_prompt=req.prompts[0] if req.prompts else None,
                enhanced_prompt=enhanced_prompt_text,
                negative_prompt=req.negative_prompt,
                style=req.style,
                moods=req.moods,
                aspect_ratio=req.image_size or "landscape_4_3",
                generation_mode=generation_mode,
                creativity_level=creativity_level,
                who=req.who,
                what=req.what,
                where=req.where,
                has_reference=has_reference,
                reference_strength=req.reference_strength if has_reference else None,
                batch_id=batch_id,
                batch_index=idx,
                credits_used=base_cost,
                model_used=model,
                generation_time_ms=generation_time_ms // num_images if num_images > 1 else generation_time_ms,
                timezone=tz,
            )
            supabase.table("user_generations").insert(generation_record).execute()
        except Exception as e:
            logger.warning(f"Failed to save generation history: {e}")

    response = {
        "image_urls": successful_urls,
        "balance": balance_total,
        "balance_monthly": balance_monthly,
        "balance_permanent": balance_permanent,
        "model_used": model,
        "used_reference": has_reference,
        "generation_mode": generation_mode,
        "creativity_level": creativity_level,
        "prompt_enhanced": prompt_enhanced,
        "batch_id": batch_id,
        "num_images": len(successful_urls),
        "generation_time_ms": generation_time_ms,
    }

    if enhancement_result:
        response["enhanced_prompt"] = enhancement_result.get("enhanced_prompt")
        response["key_elements"] = enhancement_result.get("key_elements", [])

    # Track analytics
    track_ai_generation(
        user_id=user["id"],
        success=True,
        model=model,
        cost_credits=cost,
        duration_ms=generation_time_ms,
        extra_properties={
            "batch_id": batch_id,
            "num_images": len(successful_urls),
            "generation_mode": generation_mode,
            "has_reference": has_reference,
            "prompt_enhanced": prompt_enhanced,
        }
    )

    return response


# ==========================================
# Async Image Generation (v3.23)
# ==========================================

@router.post("/images/async")
@limiter.limit("10/minute")
async def gen_images_async(request: Request, req: ImageGenRequest, user: dict = Depends(get_current_user)):
    """
    Async image generation using task queue (v3.23).

    Returns immediately with task_id for progress tracking.
    Use WebSocket (/ws/task/{task_id}) or polling (/api/tasks/{task_id}) for status.
    """
    # Safety check
    if check_prompt_safety(req.prompts):
        raise HTTPException(400, "Safety Violation")

    # Validate parameters
    num_images = max(1, min(4, req.num_images or 1))
    tier = (user.get("tier") or "free").lower()
    model = get_model_for_tier(tier)
    generation_mode = validate_generation_mode(req.generation_mode)
    creativity_level = validate_creativity_level(req.creativity_level)

    # Calculate cost using config-driven pricing
    has_reference = bool(req.reference_image)
    cost = calculate_cost(len(req.prompts), has_reference, num_images)

    # Generate task ID first (for idempotency)
    task_id = f"gen_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:8]}"

    # Deduct credits using DDD BillingService with atomic operation
    billing_service = get_container().billing_service

    try:
        tx = await billing_service.deduct_credits(
            user_id=user["id"],
            amount=cost,
            tx_type=TransactionType.GENERATION,
            description=f"Async gen {len(req.prompts)} images" + (" with ref" if has_reference else ""),
            idempotency_key=f"gen_async_{task_id}",
        )
    except InsufficientCreditsException as e:
        raise HTTPException(402, f"Insufficient credits: need {e.required}, have {e.available}")
    except Exception as e:
        logger.error(f"Credit deduction failed: {e}")
        raise HTTPException(500, "Failed to process credits")

    # Get balance after deduction
    user_credits = await billing_service.get_user_credits(user["id"])
    balance_monthly = user_credits.monthly_credits if user_credits else 0
    balance_permanent = user_credits.permanent_credits if user_credits else 0
    balance_total = balance_monthly + balance_permanent

    # Enhance prompts if needed
    enhancement_data = enhance_prompts(
        prompts=req.prompts,
        theme=req.theme,
        character=req.character,
        style=req.style or "cartoon",
        mode=generation_mode,
        creativity_level=creativity_level,
        user_id=user["id"],
        tier=tier,
        who=req.who,
        what=req.what,
        where=req.where,
        moods=req.moods,
        enhance_enabled=req.enhance_prompt,
    )
    prompts_to_use = enhancement_data["prompts"]
    enhancement_result = enhancement_data["result"]

    task_params = {
        "prompts": prompts_to_use,
        "model": model,
        "reference_image": req.reference_image,
        "reference_strength": req.reference_strength or 0.7,
        "image_size": req.image_size or "landscape_4_3",
        "generation_mode": generation_mode,
        "creativity_level": creativity_level,
        "negative_prompt": req.negative_prompt,
        "num_images": num_images,
        "project_id": req.project_id,
        "credits_charged": cost,
    }

    # Save task to database
    supabase = get_supabase_client()
    try:
        supabase.rpc("create_generation_task", {
            "p_task_id": task_id,
            "p_user_id": user["id"],
            "p_task_type": "image_generation",
            "p_params": task_params,
            "p_priority": 2 if tier == "pro" else (1 if tier == "starter" else 0),
            "p_total_steps": len(prompts_to_use) * num_images,
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to save task to DB: {e}")

    # Enqueue task
    enqueued_task_id = task_queue.enqueue_image_generation(
        user_id=user["id"],
        params=task_params,
        tier=tier,
        idempotency_key=task_id
    )

    if not enqueued_task_id:
        logger.error(f"[AsyncGen] Failed to enqueue task {task_id}")
        # Refund credits atomically
        try:
            await billing_service.add_credits(
                user_id=user["id"],
                amount=cost,
                bucket=CreditBucket.PERMANENT,
                tx_type=TransactionType.REFUND,
                description="Refund: task queue failed",
                idempotency_key=f"refund_{task_id}",
            )
            logger.info(f"Refunded {cost} credits to user {user['id']} after queue failure")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to refund credits after queue failure: {e}")
        raise HTTPException(503, "Generation service temporarily unavailable. Credits refunded.")

    # Track analytics
    track_ai_generation(
        user_id=user["id"],
        success=True,
        model=model,
        cost_credits=cost,
        duration_ms=0,
        extra_properties={
            "async": True,
            "task_id": task_id,
            "num_images": num_images,
            "generation_mode": generation_mode,
            "has_reference": has_reference,
        }
    )

    response = {
        "task_id": task_id,
        "status": "queued",
        "message": f"Task queued for {len(prompts_to_use) * num_images} images",
        "credits_charged": cost,
        "balance": balance_total,
        "balance_monthly": balance_monthly,
        "balance_permanent": balance_permanent,
        "websocket_url": f"/ws/task/{task_id}",
        "poll_url": f"/api/tasks/{task_id}",
        "model_used": model,
        "priority": "high" if tier == "pro" else ("normal" if tier == "starter" else "low"),
    }

    if enhancement_result:
        response["enhanced_prompt"] = enhancement_result.get("enhanced_prompt")

    return response
