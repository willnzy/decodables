"""
Generation API - AI content generation endpoints.

@module api.user.generation
@version 1.0.0

Endpoints:
- POST /api/v2/user/generate/images - Sync image generation
- POST /api/v2/user/generate/images/async - Async image generation
- POST /api/v2/user/generate/story - Generate story JSON
- POST /api/v2/user/generate/inspiration - AI inspiration suggestions
- POST /api/v2/user/generate/pdf - PDF generation
"""

import json
import uuid
import time
import logging
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from dependencies import get_current_user
from core.database import get_supabase_client
from infrastructure.repositories import (
    SupabaseCreditRepositoryExtended,
    SupabaseAssetRepositoryExtended,
    SupabaseProjectRepositoryExtended,
)
from shared.ai.image_generator import generate_8_images
from shared.ai.prompt_enhancer import enhance_prompt, enhance_asset_prompt
from shared.ai.story_generator import generate_story_json, client as openai_client
from shared.ai.zine_generator import create_foldable_book
from infrastructure.task_queue import task_queue
from domains.platform.analytics_service import track_ai_generation
from infrastructure.rate_limiter import limiter
from timezone_utils import get_request_timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["user-generation-v2"])


# ==========================================
# Request/Response Models
# ==========================================

class ImageGenRequest(BaseModel):
    """Image generation request."""
    prompts: List[str]
    project_id: Optional[str] = None
    num_images: int = Field(1, ge=1, le=4)
    image_size: str = "landscape_4_3"
    reference_image: Optional[str] = None
    reference_strength: float = Field(0.7, ge=0.0, le=1.0)
    generation_mode: str = Field("guided", pattern="^(guided|flexible)$")
    creativity_level: float = Field(0.3, ge=0.0, le=1.0)
    negative_prompt: Optional[str] = None
    # AI Design Page mode
    theme: Optional[str] = None
    character: Optional[str] = None
    style: Optional[str] = None
    # 5W1H Asset mode
    who: Optional[str] = None
    what: Optional[str] = None
    where: Optional[str] = None
    moods: Optional[List[str]] = None
    enhance_prompt: bool = False


class ImageGenResponse(BaseModel):
    """Image generation response."""
    image_urls: List[str]
    balance: int
    balance_monthly: int
    balance_permanent: int
    model_used: str
    generation_mode: str
    creativity_level: float
    prompt_enhanced: bool = False
    enhanced_prompt: Optional[str] = None
    key_elements: Optional[List[str]] = None
    batch_id: Optional[str] = None
    num_images: int
    generation_time_ms: int
    used_reference: bool = False


class AsyncImageGenResponse(BaseModel):
    """Async image generation response."""
    task_id: str
    status: str
    message: str
    credits_charged: int
    balance: int
    balance_monthly: int
    balance_permanent: int
    websocket_url: str
    poll_url: str
    model_used: str
    priority: str
    enhanced_prompt: Optional[str] = None


class StoryGenRequest(BaseModel):
    """Story generation request."""
    topic: str


class InspirationRequest(BaseModel):
    """Inspiration request."""
    category: Optional[str] = Field("all", pattern="^(all|character|scene|story)$")


class InspirationSuggestion(BaseModel):
    """Inspiration suggestion."""
    character: Optional[str] = None
    action: Optional[str] = None
    setting: Optional[str] = None
    style: Optional[str] = None
    moods: Optional[List[str]] = None


class InspirationResponse(BaseModel):
    """Inspiration response."""
    suggestions: List[Dict[str, Any]]
    category: str
    fallback: bool = False


class PdfGenRequest(BaseModel):
    """PDF generation request."""
    project_id: str
    image_urls: List[str]
    texts: List[str]
    current_hash: Optional[str] = None


# ==========================================
# Image Generation Endpoints
# ==========================================

@router.post("/images")
@limiter.limit("10/minute")
async def generate_images(
    request: Request,
    req: ImageGenRequest,
    user: dict = Depends(get_current_user),
) -> ImageGenResponse:
    """
    Generate images using AI.

    Model selection based on tier:
    - Free/Starter: Standard model (flux-schnell)
    - Pro: High-quality model (flux-dev)

    Supports:
    - Optional reference image for style/content guidance
    - AI Design Page mode with prompt enhancement
    - Generation modes: "guided" (accurate) or "flexible" (creative)
    """
    # Safety check
    blacklist = ["nsfw", "nude", "sex"]
    if any(w in p.lower() for p in req.prompts for w in blacklist):
        raise HTTPException(400, "Safety Violation")

    num_images = max(1, min(4, req.num_images))
    base_cost = 7 if req.reference_image else 5
    cost = len(req.prompts) * base_cost * num_images

    # Deduct credits
    credit_repo = SupabaseCreditRepositoryExtended(get_supabase_client())
    tz = get_request_timezone(request, user_id=user.get("id"))

    result = await credit_repo.deduct_credits(
        user["id"], cost, "generation",
        f"Gen {len(req.prompts)} images" + (" with ref" if req.reference_image else ""),
        tz=tz
    )

    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        if "INSUFFICIENT" in error_msg:
            raise HTTPException(402, "Insufficient credits")
        raise HTTPException(500, error_msg)

    # Select model based on tier
    tier = (user.get("tier") or "free").lower()
    model = "flux-dev" if tier == "pro" else "flux-schnell"

    generation_mode = req.generation_mode
    creativity_level = max(0.0, min(1.0, req.creativity_level))

    # Prepare prompts with optional enhancement
    prompts_to_use = req.prompts
    prompt_enhanced = False
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
                tier=tier,
            )
            prompts_to_use = [enhancement_result["enhanced_prompt"]]
            prompt_enhanced = True
        except Exception as e:
            logger.warning(f"Prompt enhancement failed: {e}")

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
                tier=tier,
            )
            prompts_to_use = [enhancement_result["enhanced_prompt"]]
            prompt_enhanced = True
        except Exception as e:
            logger.warning(f"5W1H enhancement failed: {e}")

    batch_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    generation_start = time.time()

    # Generate images
    urls, task_id = await generate_8_images(
        prompts_to_use,
        model=model,
        reference_image=req.reference_image,
        reference_strength=req.reference_strength,
        image_size=req.image_size,
        generation_mode=generation_mode,
        creativity_level=creativity_level,
        negative_prompt=req.negative_prompt,
        num_images=num_images,
        user_id=user["id"],
        tier=tier,
    )

    generation_time_ms = int((time.time() - generation_start) * 1000)

    # Save assets
    asset_repo = SupabaseAssetRepositoryExtended(get_supabase_client())
    for idx, url in enumerate(urls):
        if url:
            prompt_idx = idx // num_images if num_images > 1 else idx
            prompt_used = prompts_to_use[prompt_idx] if prompt_idx < len(prompts_to_use) else prompts_to_use[0]
            await asset_repo.save_asset(user["id"], url, "ai_generated", req.project_id, prompt_used, tz=tz)

    # Track analytics
    track_ai_generation(
        user_id=user["id"],
        success=True,
        model=model,
        cost_credits=base_cost,
        duration_ms=generation_time_ms,
        extra_properties={"batch_id": batch_id, "num_images": len([u for u in urls if u])},
    )

    return ImageGenResponse(
        image_urls=[url for url in urls if url],
        balance=result["total"],
        balance_monthly=result["balance_monthly"],
        balance_permanent=result["balance_permanent"],
        model_used=model,
        generation_mode=generation_mode,
        creativity_level=creativity_level,
        prompt_enhanced=prompt_enhanced,
        enhanced_prompt=enhancement_result.get("enhanced_prompt") if enhancement_result else None,
        key_elements=enhancement_result.get("key_elements", []) if enhancement_result else None,
        batch_id=batch_id,
        num_images=len([url for url in urls if url]),
        generation_time_ms=generation_time_ms,
        used_reference=bool(req.reference_image),
    )


@router.post("/images/async")
@limiter.limit("10/minute")
async def generate_images_async(
    request: Request,
    req: ImageGenRequest,
    user: dict = Depends(get_current_user),
) -> AsyncImageGenResponse:
    """
    Async image generation using task queue.

    Returns immediately with task_id for progress tracking.
    Use WebSocket or polling for status updates.
    """
    # Safety check
    blacklist = ["nsfw", "nude", "sex"]
    if any(w in p.lower() for p in req.prompts for w in blacklist):
        raise HTTPException(400, "Safety Violation")

    num_images = max(1, min(4, req.num_images))
    base_cost = 7 if req.reference_image else 5
    cost = len(req.prompts) * base_cost * num_images

    # Deduct credits FIRST
    credit_repo = SupabaseCreditRepositoryExtended(get_supabase_client())
    tz = get_request_timezone(request, user_id=user.get("id"))

    result = await credit_repo.deduct_credits(
        user["id"], cost, "generation",
        f"Async gen {len(req.prompts)} images",
        tz=tz
    )

    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        if "INSUFFICIENT" in error_msg:
            raise HTTPException(402, "Insufficient credits")
        raise HTTPException(500, error_msg)

    tier = (user.get("tier") or "free").lower()
    model = "flux-dev" if tier == "pro" else "flux-schnell"

    generation_mode = req.generation_mode
    creativity_level = max(0.0, min(1.0, req.creativity_level))

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
                tier=tier,
            )
            prompts_to_use = [enhancement_result["enhanced_prompt"]]
        except Exception as e:
            logger.warning(f"Prompt enhancement failed: {e}")

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
                tier=tier,
            )
            prompts_to_use = [enhancement_result["enhanced_prompt"]]
        except Exception as e:
            logger.warning(f"5W1H enhancement failed: {e}")

    task_id = f"gen_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:8]}"

    task_params = {
        "prompts": prompts_to_use,
        "model": model,
        "reference_image": req.reference_image,
        "reference_strength": req.reference_strength,
        "image_size": req.image_size,
        "generation_mode": generation_mode,
        "creativity_level": creativity_level,
        "negative_prompt": req.negative_prompt,
        "num_images": num_images,
        "project_id": req.project_id,
        "credits_charged": cost,
    }

    # Enqueue task
    enqueued_task_id = task_queue.enqueue_image_generation(
        user_id=user["id"],
        params=task_params,
        tier=tier,
        idempotency_key=task_id,
    )

    if not enqueued_task_id:
        try:
            await credit_repo.add_credits(user["id"], cost, "Task queue failed", "refund", tz=tz)
        except Exception as e:
            logger.error(f"Failed to refund credits: {e}")
        raise HTTPException(503, "Generation service unavailable. Credits refunded.")

    priority = "high" if tier == "pro" else ("normal" if tier == "starter" else "low")

    return AsyncImageGenResponse(
        task_id=task_id,
        status="queued",
        message=f"Task queued for {len(prompts_to_use) * num_images} images",
        credits_charged=cost,
        balance=result["total"],
        balance_monthly=result["balance_monthly"],
        balance_permanent=result["balance_permanent"],
        websocket_url=f"/ws/task/{task_id}",
        poll_url=f"/api/v2/tasks/{task_id}",
        model_used=model,
        priority=priority,
        enhanced_prompt=enhancement_result.get("enhanced_prompt") if enhancement_result else None,
    )


# ==========================================
# Story Generation Endpoints
# ==========================================

@router.post("/story")
@limiter.limit("20/minute")
async def generate_story(
    request: Request,
    req: StoryGenRequest,
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Generate story JSON using AI.

    Returns 8-page story structure with text for each page.
    """
    try:
        tier = (user.get("tier") or "free").lower()
        return generate_story_json(
            req.topic,
            user_id=user["id"],
            tier=tier,
        )
    except Exception as e:
        logger.error(f"Story generation failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/inspiration")
@limiter.limit("30/minute")
async def generate_inspiration(
    request: Request,
    req: InspirationRequest,
    user: dict = Depends(get_current_user),
) -> InspirationResponse:
    """
    Generate creative inspiration suggestions using AI.

    Free endpoint (no credits required) to help users get started.
    """
    try:
        category = req.category or "all"

        # Build prompt based on category
        if category == "character":
            prompt = """Generate 3 creative character ideas for children's book illustrations.
Return JSON: {"suggestions": [{"character": "desc", "personality": "trait"}]}"""
        elif category == "scene":
            prompt = """Generate 3 creative scene/setting ideas for children's book illustrations.
Return JSON: {"suggestions": [{"setting": "desc", "atmosphere": "mood"}]}"""
        elif category == "story":
            prompt = """Generate 3 creative mini-story ideas for children's book illustrations.
Return JSON: {"suggestions": [{"character": "who", "action": "what", "setting": "where", "mood": "atmosphere"}]}"""
        else:
            prompt = """Generate 3 complete creative ideas for children's book illustrations.
Return JSON: {"suggestions": [{"character": "desc", "action": "what", "setting": "where", "style": "art style", "moods": ["mood1"]}]}"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a creative children's book illustrator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            max_tokens=500,
        )

        result = json.loads(response.choices[0].message.content)
        return InspirationResponse(
            suggestions=result.get("suggestions", []),
            category=category,
        )

    except Exception as e:
        logger.error(f"Inspiration generation failed: {e}")
        return InspirationResponse(
            suggestions=[
                {"character": "A friendly robot", "action": "learning to dance", "setting": "in a cozy playroom", "style": "cartoon", "moods": ["joyful"]},
                {"character": "A brave little mouse", "action": "exploring", "setting": "a magical library", "style": "fantasy", "moods": ["adventurous"]},
                {"character": "A wise owl", "action": "teaching", "setting": "forest clearing", "style": "watercolor", "moods": ["warm"]},
            ],
            category=req.category or "all",
            fallback=True,
        )


# ==========================================
# PDF Generation Endpoint
# ==========================================

@router.post("/pdf")
@limiter.limit("10/minute")
async def generate_pdf(
    request: Request,
    req: PdfGenRequest,
    user: dict = Depends(get_current_user),
):
    """
    Generate a PDF (always free).

    Creates a foldable 8-page mini-book PDF.
    """
    project_repo = SupabaseProjectRepositoryExtended(get_supabase_client())
    proj = await project_repo.get_project_detail(req.project_id, user["id"])
    if proj and req.current_hash != proj.get("last_downloaded_hash"):
        await project_repo.update_project_hash(req.project_id, req.current_hash)

    buf = BytesIO()
    create_foldable_book(req.image_urls, req.texts, buf)
    buf.seek(0)

    # Log activity using Supabase client directly
    supabase = get_supabase_client()
    try:
        supabase.table("activity_logs").insert({
            "user_id": user["id"],
            "activity_type": "download_pdf",
            "metadata": {"project_id": req.project_id},
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log activity: {e}")

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=zine.pdf"},
    )
