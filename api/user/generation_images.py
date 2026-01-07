"""
Image Generation Router - AI image generation endpoints

@module api.user.generation_images
@version 3.24

Endpoints:
- POST /api/v2/user/generate/images - Sync image generation
- POST /api/v2/user/generate/images/async - Async image generation (v3.23)
"""

import logging
import uuid
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Depends

from services.db_service import (
    supabase, credit_deduct, add_credits, save_asset,
)
from services.ai.image_generator import generate_8_images
from services.ai.prompt_enhancer import enhance_prompt, enhance_asset_prompt
from infrastructure.task_queue import task_queue
from domains.platform.analytics_service import track_ai_generation
from infrastructure.rate_limiter import limiter
from timezone_utils import get_request_timezone
from dependencies import get_current_user
from schemas import ImageGenRequest

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
    blacklist = ["nsfw", "nude", "sex"]
    if any(w in p.lower() for p in req.prompts for w in blacklist):
        raise HTTPException(400, "Safety Violation")
    
    # Validate and clamp num_images (1-4)
    num_images = max(1, min(4, req.num_images or 1))
    
    # Reference image costs extra (7 credits vs 5)
    base_cost = 7 if req.reference_image else 5
    cost = len(req.prompts) * base_cost * num_images
    
    try:
        result = credit_deduct(user["id"], cost, "generation", 
            f"Gen {len(req.prompts)} images" + (" with ref" if req.reference_image else ""))
    except Exception as e:
        if "INSUFFICIENT" in str(e):
            raise HTTPException(402, "Insufficient credits")
        raise HTTPException(500, str(e))
    
    # Select model based on tier
    tier = (user.get("tier") or "free").lower()
    model = "flux-dev" if tier == "pro" else "flux-schnell"
    
    # Get generation parameters
    generation_mode = req.generation_mode or "guided"
    if generation_mode not in ["guided", "flexible"]:
        generation_mode = "guided"
    
    creativity_level = req.creativity_level if req.creativity_level is not None else 0.3
    creativity_level = max(0.0, min(1.0, creativity_level))
    
    # Prepare prompts with optional enhancement
    prompts_to_use = req.prompts
    prompt_enhanced = False
    enhancement_result = None
    
    if req.theme:
        # AI Design Page mode: enhance prompt using LLM
        try:
            enhancement_result = enhance_prompt(
                theme=req.theme,
                character=req.character,
                style=req.style or "cartoon",
                mode=generation_mode,
                creativity_level=creativity_level,
                user_id=user["id"],
                tier=tier
            )
            prompts_to_use = [enhancement_result["enhanced_prompt"]]
            prompt_enhanced = True
            logger.info(f"Prompt enhanced (theme) for user {user['id']}")
        except Exception as e:
            logger.warning(f"Prompt enhancement failed, using original: {e}")
    
    elif req.who and req.enhance_prompt:
        # 5W1H Asset Generation mode
        try:
            enhancement_result = enhance_asset_prompt(
                who=req.who,
                what=req.what,
                where=req.where,
                style=req.style or "cartoon",
                moods=req.moods,
                mode=generation_mode,
                creativity_level=creativity_level,
                user_id=user["id"],
                tier=tier
            )
            prompts_to_use = [enhancement_result["enhanced_prompt"]]
            prompt_enhanced = True
            logger.info(f"Prompt enhanced (5W1H) for user {user['id']}")
        except Exception as e:
            logger.warning(f"5W1H prompt enhancement failed, using original: {e}")
    
    # Generate unique batch ID
    batch_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    generation_start = time.time()
    
    # Generate images
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
    
    generation_time_ms = int((time.time() - generation_start) * 1000)
    
    # Save assets and generation history
    tz = get_request_timezone(request, user_id=user.get("id"))
    enhanced_prompt_text = enhancement_result.get("enhanced_prompt") if enhancement_result else None
    
    for idx, url in enumerate(urls):
        if not url:
            continue
        
        prompt_idx = idx // num_images if num_images > 1 else idx
        prompt_used = prompts_to_use[prompt_idx] if prompt_idx < len(prompts_to_use) else prompts_to_use[0]
        asset_prompt = f"[{req.theme}] {prompt_used}" if req.theme else prompt_used
        
        # Save to assets table
        save_asset(user["id"], url, "ai_generated", req.project_id, asset_prompt, timezone=tz)
        
        # Save to user_generations table
        try:
            generation_record = {
                "user_id": user["id"],
                "image_url": url,
                "original_prompt": req.prompts[0] if req.prompts else None,
                "enhanced_prompt": enhanced_prompt_text,
                "negative_prompt": req.negative_prompt,
                "style": req.style,
                "moods": req.moods,
                "aspect_ratio": req.image_size or "landscape_4_3",
                "generation_mode": generation_mode,
                "creativity_level": creativity_level,
                "who_param": req.who,
                "what_param": req.what,
                "where_param": req.where,
                "has_reference": bool(req.reference_image),
                "reference_strength": req.reference_strength if req.reference_image else None,
                "batch_id": batch_id,
                "batch_index": idx,
                "credits_used": base_cost,
                "model_used": model,
                "generation_time_ms": generation_time_ms // num_images if num_images > 1 else generation_time_ms,
                "timezone": tz,
            }
            supabase.table("user_generations").insert(generation_record).execute()
        except Exception as e:
            logger.warning(f"Failed to save generation history: {e}")
    
    response = {
        "image_urls": [url for url in urls if url],
        "balance": result["total"],
        "balance_monthly": result["balance_monthly"],
        "balance_permanent": result["balance_permanent"],
        "model_used": model,
        "used_reference": bool(req.reference_image),
        "generation_mode": generation_mode,
        "creativity_level": creativity_level,
        "prompt_enhanced": prompt_enhanced,
        "batch_id": batch_id,
        "num_images": len([url for url in urls if url]),
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
        cost_credits=base_cost,
        duration_ms=generation_time_ms,
        extra_properties={
            "batch_id": batch_id,
            "num_images": len([url for url in urls if url]),
            "generation_mode": generation_mode,
            "has_reference": bool(req.reference_image),
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
    blacklist = ["nsfw", "nude", "sex"]
    if any(w in p.lower() for p in req.prompts for w in blacklist):
        raise HTTPException(400, "Safety Violation")
    
    num_images = max(1, min(4, req.num_images or 1))
    base_cost = 7 if req.reference_image else 5
    cost = len(req.prompts) * base_cost * num_images
    
    # Deduct credits FIRST
    try:
        result = credit_deduct(user["id"], cost, "generation", 
            f"Async gen {len(req.prompts)} images" + (" with ref" if req.reference_image else ""))
    except Exception as e:
        if "INSUFFICIENT" in str(e):
            raise HTTPException(402, "Insufficient credits")
        raise HTTPException(500, str(e))
    
    tier = (user.get("tier") or "free").lower()
    model = "flux-dev" if tier == "pro" else "flux-schnell"
    
    generation_mode = req.generation_mode or "guided"
    if generation_mode not in ["guided", "flexible"]:
        generation_mode = "guided"
    
    creativity_level = req.creativity_level if req.creativity_level is not None else 0.3
    creativity_level = max(0.0, min(1.0, creativity_level))
    
    # Prepare prompts
    prompts_to_use = req.prompts
    enhancement_result = None
    
    if req.theme:
        try:
            enhancement_result = enhance_prompt(
                theme=req.theme,
                character=req.character,
                style=req.style or "cartoon",
                mode=generation_mode,
                creativity_level=creativity_level,
                user_id=user["id"],
                tier=tier
            )
            prompts_to_use = [enhancement_result["enhanced_prompt"]]
        except Exception as e:
            logger.warning(f"Prompt enhancement failed, using original: {e}")
    
    elif req.who and req.enhance_prompt:
        try:
            enhancement_result = enhance_asset_prompt(
                who=req.who,
                what=req.what,
                where=req.where,
                style=req.style or "cartoon",
                moods=req.moods,
                mode=generation_mode,
                creativity_level=creativity_level,
                user_id=user["id"],
                tier=tier
            )
            prompts_to_use = [enhancement_result["enhanced_prompt"]]
        except Exception as e:
            logger.warning(f"5W1H prompt enhancement failed, using original: {e}")
    
    # Generate task ID
    task_id = f"gen_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:8]}"
    
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
        try:
            add_credits(user["id"], cost, "refund", "Generation task queue failed")
        except Exception as e:
            logger.error(f"Failed to refund credits: {e}")
        raise HTTPException(503, "Generation service temporarily unavailable. Credits refunded.")
    
    # Track analytics
    track_ai_generation(
        user_id=user["id"],
        success=True,
        model=model,
        cost_credits=base_cost,
        duration_ms=0,
        extra_properties={
            "async": True,
            "task_id": task_id,
            "num_images": num_images,
            "generation_mode": generation_mode,
            "has_reference": bool(req.reference_image),
        }
    )
    
    response = {
        "task_id": task_id,
        "status": "queued",
        "message": f"Task queued for {len(prompts_to_use) * num_images} images",
        "credits_charged": cost,
        "balance": result["total"],
        "balance_monthly": result["balance_monthly"],
        "balance_permanent": result["balance_permanent"],
        "websocket_url": f"/ws/task/{task_id}",
        "poll_url": f"/api/tasks/{task_id}",
        "model_used": model,
        "priority": "high" if tier == "pro" else ("normal" if tier == "starter" else "low"),
    }
    
    if enhancement_result:
        response["enhanced_prompt"] = enhancement_result.get("enhanced_prompt")
    
    return response
