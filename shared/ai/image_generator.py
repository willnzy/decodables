"""
Image Generator Service
图像生成服务

Uses unified AI service to generate images from text prompts.
基于统一 AI 服务生成图像。

Features:
- Automatic model selection from admin configuration (based on user tier)
- Canary release support
- Usage tracking
- Automatic fallback on errors
- Support for text-to-image and image-to-image generation
- Generation modes: guided (accurate) vs flexible (creative)

Supports:
- Text-to-image generation
- Image-to-image with reference
- Multiple variations per prompt
"""

import asyncio
import os
import uuid
import base64
import logging
import aiohttp
from typing import List, Optional, Tuple
from datetime import datetime, timezone

from supabase import create_client, Client

from .unified_image_service import unified_image_service

logger = logging.getLogger(__name__)


# ==========================================
# Supabase Configuration
# ==========================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "make-decodables-u"  # User content bucket (v3.18)

# Ensure URL has trailing slash
if SUPABASE_URL and not SUPABASE_URL.endswith('/'):
    SUPABASE_URL = SUPABASE_URL + '/'

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


# ==========================================
# Generation Mode Parameters
# ==========================================

GENERATION_MODE_PARAMS = {
    "guided": {
        # More accurate: strictly follows the prompt
        "flux-dev": {
            "num_inference_steps": 35,
            "guidance_scale": 4.5,
        },
        "flux-schnell": {
            "num_inference_steps": 4,
            "guidance_scale": 3.5,
        },
        # Default for other models
        "default": {
            "num_inference_steps": 28,
            "guidance_scale": 4.0,
        },
    },
    "flexible": {
        # More creative: allows artistic interpretation
        "flux-dev": {
            "num_inference_steps": 28,
            "guidance_scale": 2.5,
        },
        "flux-schnell": {
            "num_inference_steps": 4,
            "guidance_scale": 2.5,
        },
        "default": {
            "num_inference_steps": 28,
            "guidance_scale": 2.5,
        },
    },
}


def get_generation_params(model: str, mode: str, creativity_level: float = 0.3) -> dict:
    """
    Get generation parameters based on model, mode, and creativity level.
    
    Args:
        model: Model name (flux-dev, flux-schnell, etc.)
        mode: Generation mode (guided or flexible)
        creativity_level: 0.0-1.0 slider value (0=precise, 1=very creative)
                         Only affects flexible mode
    
    Returns:
        dict with num_inference_steps and guidance_scale
    """
    if mode == "guided":
        mode_params = GENERATION_MODE_PARAMS["guided"]
        return mode_params.get(model, mode_params.get("default", {}))
    else:
        base_params = GENERATION_MODE_PARAMS["flexible"].get(
            model, 
            GENERATION_MODE_PARAMS["flexible"]["default"]
        )
        
        # Interpolate guidance_scale: creativity 0 -> cfg 4.0, creativity 1 -> cfg 1.5
        max_cfg = 4.0
        min_cfg = 1.5
        guidance_scale = max_cfg - (creativity_level * (max_cfg - min_cfg))
        
        return {
            "num_inference_steps": base_params["num_inference_steps"],
            "guidance_scale": guidance_scale
        }


# ==========================================
# Helper Functions
# ==========================================

async def upload_reference_image(
    session: aiohttp.ClientSession, 
    reference_image: str, 
    task_id: str, 
    user_id: str = None
) -> Optional[str]:
    """
    Upload reference image to Supabase and return public URL.
    
    Args:
        session: aiohttp session
        reference_image: Base64 encoded image (with or without data URI prefix) or URL
        task_id: Task ID for organizing files
        user_id: User ID for path organization (v3.18)
    
    Returns:
        Public URL of the uploaded reference image
    """
    if not supabase:
        logger.error("[ImageGenerator] Supabase client not available")
        return None
    
    try:
        # Check if it's already a URL
        if reference_image.startswith('http://') or reference_image.startswith('https://'):
            return reference_image
        
        # Handle base64 data
        if ',' in reference_image:
            reference_image = reference_image.split(',')[1]
        
        image_bytes = base64.b64decode(reference_image)
        
        # Build path (v3.18)
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if user_id:
            filename = f"{user_id}/temp/{today}/{task_id}/reference_{uuid.uuid4().hex[:8]}.png"
        else:
            filename = f"anonymous/temp/{today}/{task_id}/reference_{uuid.uuid4().hex[:8]}.png"
        
        supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=image_bytes,
            file_options={"content-type": "image/png"}
        )
        
        return supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
    except Exception as e:
        logger.error(f"[ImageGenerator] Error uploading reference image: {e}")
        print(f"❌ Error uploading reference image: {e}")
        return None


async def download_and_upload_image(
    session: aiohttp.ClientSession,
    image_url: str,
    task_id: str,
    index: int,
    user_id: str = None
) -> Optional[str]:
    """
    Download image from URL and upload to Supabase.
    
    Args:
        session: aiohttp session
        image_url: URL of the generated image
        task_id: Task ID for organizing files
        index: Image index
        user_id: User ID for path organization
    
    Returns:
        Public URL of the uploaded image
    """
    if not supabase:
        logger.error("[ImageGenerator] Supabase client not available")
        return None
    
    try:
        async with session.get(image_url) as response:
            if response.status == 200:
                image_bytes = await response.read()
                
                today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                if user_id:
                    filename = f"{user_id}/temp/{today}/{task_id}/{uuid.uuid4().hex}.png"
                else:
                    filename = f"anonymous/temp/{today}/{task_id}/{uuid.uuid4().hex}.png"
                
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=filename,
                    file=image_bytes,
                    file_options={"content-type": "image/png"}
                )
                
                return supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        return None
    except Exception as e:
        logger.error(f"[ImageGenerator] Error downloading/uploading image: {e}")
        return None


# ==========================================
# Main Generation Functions
# ==========================================

async def generate_and_upload_single(
    session: aiohttp.ClientSession, 
    prompt: str, 
    index: int, 
    task_id: str, 
    model: str = "flux-schnell",
    reference_image_url: Optional[str] = None,
    reference_strength: float = 0.7,
    image_size: str = "landscape_4_3",
    generation_mode: str = "guided",
    creativity_level: float = 0.3,
    negative_prompt: Optional[str] = None,
    user_id: Optional[str] = None,
    tier: str = "t1"
) -> Optional[str]:
    """
    Generate a single image and upload to Supabase Storage.
    
    Args:
        session: aiohttp session
        prompt: Text prompt for generation
        index: Image index
        task_id: Task ID for organizing files
        model: Model name (保留用于向后兼容，实际由 tier 决定)
        reference_image_url: Optional URL of reference image for image-to-image
        reference_strength: Strength of reference influence (0.0-1.0)
        image_size: Image aspect ratio
        generation_mode: "guided" (accurate) or "flexible" (creative)
        creativity_level: 0.0-1.0 slider value
        negative_prompt: Optional negative prompt
        user_id: User ID for tracking and path organization
        tier: User tier (free, starter, pro) for model selection
    """
    try:
        # Get mode-specific parameters
        gen_params = get_generation_params(model, generation_mode, creativity_level)
        num_inference_steps = gen_params.get("num_inference_steps")
        guidance_scale = gen_params.get("guidance_scale")
        
        # Prepare the prompt with children's book context
        full_prompt = f"{prompt}, children's book style, safe for work, colorful"
        
        # Add safe content guidelines to negative prompt
        if negative_prompt:
            full_negative = f"{negative_prompt}, nsfw, violence, gore, disturbing"
        else:
            full_negative = "nsfw, violence, gore, disturbing"
        
        # Determine if using image-to-image or text-to-image
        use_img2img = reference_image_url is not None
        
        if use_img2img:
            print(f"🎨 [{generation_mode}] Generating {index} with reference (strength={reference_strength})...")
            
            # Image-to-image using unified service
            response = await unified_image_service.image_to_image(
                prompt=full_prompt,
                image_url=reference_image_url,
                user_id=user_id,
                tier=tier,
                strength=reference_strength,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
            )
        else:
            neg_info = f", neg={len(full_negative)}chars" if full_negative else ""
            print(f"🎨 [{generation_mode}] Generating {index} (steps={num_inference_steps}, cfg={guidance_scale:.1f}{neg_info})...")
            
            # Text-to-image using unified service
            response = await unified_image_service.generate(
                prompt=full_prompt,
                user_id=user_id,
                tier=tier,
                size=image_size,
                num_images=1,
                negative_prompt=full_negative,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
            )
        
        # Check response
        if not response.success:
            logger.error(f"[ImageGenerator] Generation failed: {response.error}")
            print(f"❌ Error generating image: {response.error}")
            return None
        
        # Get generated image URL from response
        if not response.content or len(response.content) == 0:
            logger.error("[ImageGenerator] No images in response")
            return None
        
        generated_url = response.content[0]
        
        # Download and upload to Supabase
        return await download_and_upload_image(
            session, generated_url, task_id, index, user_id
        )
        
    except Exception as e:
        logger.error(f"[ImageGenerator] Error generating image: {e}")
        print(f"❌ Error generating image: {e}")
        return None


async def generate_8_images(
    prompts: List[str], 
    model: str = "flux-schnell",  # 保留用于向后兼容，实际由 tier 决定
    reference_image: Optional[str] = None,
    reference_strength: float = 0.7,
    image_size: str = "landscape_4_3",
    generation_mode: str = "guided",
    creativity_level: float = 0.3,
    negative_prompt: Optional[str] = None,
    num_images: int = 1,
    user_id: Optional[str] = None,
    tier: str = "t1"
) -> Tuple[List[Optional[str]], str]:
    """
    Generate images using unified AI service.
    
    Args:
        prompts: List of prompts for image generation
        model: [已废弃] 保留用于向后兼容，实际由 tier 和配置决定
        reference_image: Optional base64 image or URL for style reference
        reference_strength: How much to follow reference (0.0-1.0)
        image_size: Image aspect ratio (landscape_4_3, square, portrait_4_3, etc.)
        generation_mode: "guided" (accurate) or "flexible" (creative)
        creativity_level: 0.0-1.0 slider value
        negative_prompt: Optional text describing what to avoid
        num_images: Number of variations to generate per prompt (1-4)
        user_id: User ID for tracking and path organization
        tier: User tier (free, starter, pro) for model selection
    
    Returns:
        Tuple of (image_urls, task_id)
        
    Note:
        - 模型选择由 Admin 配置管理（基于 tier）
        - 自动支持灰度发布测试新模型
        - 自动追踪使用量
        - 失败时自动 fallback 到备用模型
    """
    task_id = uuid.uuid4().hex[:8]
    reference_image_url = None
    
    # Validate inputs
    if generation_mode not in ["guided", "flexible"]:
        generation_mode = "guided"
    creativity_level = max(0.0, min(1.0, creativity_level))
    num_images = max(1, min(4, num_images))
    
    neg_info = f", negative_prompt={len(negative_prompt) if negative_prompt else 0}chars" if negative_prompt else ""
    print(f"🚀 Starting image generation: mode={generation_mode}, creativity={creativity_level:.2f}, "
          f"prompts={len(prompts)}, variations={num_images}, tier={tier}{neg_info}")
    
    async with aiohttp.ClientSession() as session:
        # Upload reference image if provided
        if reference_image:
            reference_image_url = await upload_reference_image(session, reference_image, task_id, user_id)
            if not reference_image_url:
                print("⚠️ Failed to process reference image, falling back to text-only generation")
        
        # Generate images
        tasks = []
        total_index = 0
        for prompt in prompts:
            for variation in range(num_images):
                tasks.append(generate_and_upload_single(
                    session=session,
                    prompt=prompt,
                    index=total_index,
                    task_id=task_id,
                    model=model,  # 传递但实际由统一服务决定
                    reference_image_url=reference_image_url,
                    reference_strength=reference_strength,
                    image_size=image_size,
                    generation_mode=generation_mode,
                    creativity_level=creativity_level,
                    negative_prompt=negative_prompt,
                    user_id=user_id,
                    tier=tier
                ))
                total_index += 1
        
        image_urls = await asyncio.gather(*tasks)
    
    success_count = len([u for u in image_urls if u])
    total_requested = len(prompts) * num_images
    print(f"✅ Generation complete: {success_count}/{total_requested} images generated")
    
    return list(image_urls), task_id


# ==========================================
# Async convenience function
# ==========================================

async def generate_images_async(
    prompts: List[str],
    user_id: Optional[str] = None,
    tier: str = "t1",
    **kwargs
) -> Tuple[List[Optional[str]], str]:
    """
    Async convenience function for generate_8_images.
    """
    return await generate_8_images(
        prompts=prompts,
        user_id=user_id,
        tier=tier,
        **kwargs
    )
