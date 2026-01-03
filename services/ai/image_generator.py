"""
Image Generator Service

Uses FAL AI's Flux models to generate images from text prompts.
Supports:
- Text-to-image generation
- Image-to-image with reference
- Generation modes: guided (accurate) vs flexible (creative)

Model selection based on user tier:
- Free/Starter: flux-schnell (fast, 4 steps)
- Pro: flux-dev (high quality, 28+ steps)
"""

import asyncio
import fal_client
import os
import aiohttp
import uuid
import base64
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "generated-images"  # PRD Bucket

# Ensure URL has trailing slash to avoid SDK warning
if SUPABASE_URL and not SUPABASE_URL.endswith('/'):
    SUPABASE_URL = SUPABASE_URL + '/'

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


# ===========================================
# Generation Mode Parameters
# ===========================================
# These parameters control the accuracy vs creativity trade-off
# Based on industry standard CFG (Classifier-Free Guidance) tuning

GENERATION_MODE_PARAMS = {
    "guided": {
        # More accurate: strictly follows the prompt
        "flux-dev": {
            "num_inference_steps": 35,  # More steps = finer details
            "guidance_scale": 4.5,      # Higher CFG = stricter prompt adherence
        },
        "flux-schnell": {
            "num_inference_steps": 4,   # Schnell is optimized for 4 steps
            "guidance_scale": 3.5,      # Slightly higher for accuracy
        },
    },
    "flexible": {
        # More creative: allows artistic interpretation
        "flux-dev": {
            "num_inference_steps": 28,  # Standard steps
            "guidance_scale": 2.5,      # Lower CFG = more freedom
        },
        "flux-schnell": {
            "num_inference_steps": 4,   # Schnell is optimized for 4 steps
            "guidance_scale": 2.5,      # Standard for creativity
        },
    },
}


def get_generation_params(model: str, mode: str, creativity_level: float = 0.3) -> dict:
    """
    Get generation parameters based on model, mode, and creativity level.
    
    Args:
        model: Model name (flux-dev or flux-schnell)
        mode: Generation mode (guided or flexible)
        creativity_level: 0.0-1.0 slider value (0=precise, 1=very creative)
                         Only affects flexible mode
    
    Returns:
        dict with num_inference_steps and guidance_scale
    """
    if mode == "guided":
        # Guided mode: use fixed high-accuracy settings
        mode_params = GENERATION_MODE_PARAMS["guided"]
        return mode_params.get(model, mode_params.get("flux-schnell"))
    else:
        # Flexible mode: interpolate guidance_scale based on creativity_level
        # Higher creativity = lower guidance_scale (more artistic freedom)
        base_params = GENERATION_MODE_PARAMS["flexible"].get(model, GENERATION_MODE_PARAMS["flexible"]["flux-schnell"])
        
        # Interpolate guidance_scale: creativity 0 -> cfg 4.0, creativity 1 -> cfg 1.5
        # This gives a range from "somewhat creative" to "very creative"
        max_cfg = 4.0  # More precise
        min_cfg = 1.5  # Very creative
        guidance_scale = max_cfg - (creativity_level * (max_cfg - min_cfg))
        
        return {
            "num_inference_steps": base_params["num_inference_steps"],
            "guidance_scale": guidance_scale
        }


async def upload_reference_image(session, reference_image: str, task_id: str) -> str:
    """
    Upload reference image to Supabase and return public URL.
    
    Args:
        reference_image: Base64 encoded image (with or without data URI prefix) or URL
        task_id: Task ID for organizing files
    
    Returns:
        Public URL of the uploaded reference image
    """
    try:
        # Check if it's already a URL
        if reference_image.startswith('http://') or reference_image.startswith('https://'):
            return reference_image
        
        # Handle base64 data
        # Remove data URI prefix if present
        if ',' in reference_image:
            reference_image = reference_image.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(reference_image)
        
        # Upload to Supabase
        filename = f"{task_id}/reference_{uuid.uuid4().hex[:8]}.png"
        supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=image_bytes,
            file_options={"content-type": "image/png"}
        )
        
        return supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
    except Exception as e:
        print(f"❌ Error uploading reference image: {e}")
        return None


async def generate_and_upload_single(
    session, 
    prompt, 
    index, 
    task_id, 
    model="flux-schnell",
    reference_image_url=None,
    reference_strength=0.7,
    image_size="landscape_4_3",
    generation_mode="guided",
    creativity_level=0.3,
    negative_prompt=None
):
    """
    Generate a single image and upload to Supabase Storage.
    
    Args:
        session: aiohttp session
        prompt: Text prompt for generation
        index: Image index
        task_id: Task ID for organizing files
        model: Model name (flux-schnell for standard, flux-dev for high-quality)
        reference_image_url: Optional URL of reference image for image-to-image
        reference_strength: Strength of reference influence (0.0-1.0)
        image_size: Image aspect ratio (landscape_4_3, square, portrait_4_3, etc.)
        generation_mode: "guided" (accurate) or "flexible" (creative)
        creativity_level: 0.0-1.0, controls creativity in flexible mode
        negative_prompt: Optional negative prompt (elements to avoid)
    """
    try:
        # Get mode-specific parameters (creativity_level only affects flexible mode)
        gen_params = get_generation_params(model, generation_mode, creativity_level)
        num_inference_steps = gen_params["num_inference_steps"]
        guidance_scale = gen_params["guidance_scale"]
        
        # Determine if using image-to-image or text-to-image
        use_img2img = reference_image_url is not None
        
        # Prepare the prompt with children's book context
        full_prompt = f"{prompt}, children's book style, safe for work, colorful"
        
        # Build base arguments
        base_args = {
            "prompt": full_prompt,
            "image_size": image_size,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "enable_safety_checker": True
        }
        
        # Add negative prompt if provided (supported by flux models)
        if negative_prompt:
            # Append default safe content guidelines to negative prompt
            full_negative = f"{negative_prompt}, nsfw, violence, gore, disturbing"
            base_args["negative_prompt"] = full_negative
        
        if use_img2img:
            print(f"🎨 [{generation_mode}] Generating {index} with reference (strength={reference_strength}, steps={num_inference_steps}, cfg={guidance_scale})...")
            # Image-to-image mode using flux-dev
            model_endpoint = "fal-ai/flux/dev/image-to-image"
            
            handler = await fal_client.submit_async(
                model_endpoint,
                arguments={
                    **base_args,
                    "image_url": reference_image_url,
                    "strength": reference_strength,  # 0.0 = identical to input, 1.0 = ignore input
                },
            )
        else:
            neg_info = f", neg={len(negative_prompt)}chars" if negative_prompt else ""
            print(f"🎨 [{generation_mode}] Generating {index} with {model} (steps={num_inference_steps}, cfg={guidance_scale}{neg_info})...")
            
            # Select model endpoint based on model type
            if model == "flux-dev":
                model_endpoint = "fal-ai/flux/dev"
            else:
                model_endpoint = "fal-ai/flux/schnell"
            
            handler = await fal_client.submit_async(
                model_endpoint,
                arguments=base_args,
            )
        
        result = await handler.get()
        image_url = result['images'][0]['url']
        
        # Upload to Supabase
        async with session.get(image_url) as response:
            if response.status == 200:
                image_bytes = await response.read()
                filename = f"{task_id}/{uuid.uuid4().hex}.png"
                
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=filename,
                    file=image_bytes,
                    file_options={"content-type": "image/png"}
                )
                return supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        return None
    except Exception as e:
        print(f"❌ Error generating image: {e}")
        return None


async def generate_8_images(
    prompts: list, 
    model="flux-schnell",
    reference_image: str = None,
    reference_strength: float = 0.7,
    image_size: str = "landscape_4_3",
    generation_mode: str = "guided",
    creativity_level: float = 0.3,
    negative_prompt: str = None,
    num_images: int = 1
):
    """
    Generate images using specified model, optionally with reference image.
    
    Args:
        prompts: List of prompts for image generation
        model: Model name (flux-schnell for standard, flux-dev for high-quality)
        reference_image: Optional base64 image or URL for style reference
        reference_strength: How much to follow reference (0.0-1.0, higher = more similar)
        image_size: Image aspect ratio (landscape_4_3, square, portrait_4_3, etc.)
        generation_mode: "guided" (accurate) or "flexible" (creative)
        creativity_level: 0.0-1.0 slider value (0=precise, 1=very creative)
        negative_prompt: Optional text describing what to avoid in the image
        num_images: Number of variations to generate per prompt (1-4)
    
    Returns:
        Tuple of (image_urls, task_id)
    """
    task_id = uuid.uuid4().hex[:8]
    reference_image_url = None
    
    # Validate generation_mode
    if generation_mode not in ["guided", "flexible"]:
        generation_mode = "guided"
    
    # Clamp creativity_level to valid range
    creativity_level = max(0.0, min(1.0, creativity_level))
    
    # Clamp num_images to valid range (1-4)
    num_images = max(1, min(4, num_images))
    
    neg_info = f", negative_prompt={len(negative_prompt) if negative_prompt else 0}chars" if negative_prompt else ""
    print(f"🚀 Starting image generation: model={model}, mode={generation_mode}, creativity={creativity_level:.2f}, prompts={len(prompts)}, variations={num_images}{neg_info}")
    
    async with aiohttp.ClientSession() as session:
        # Upload reference image if provided
        if reference_image:
            reference_image_url = await upload_reference_image(session, reference_image, task_id)
            if not reference_image_url:
                print("⚠️ Failed to process reference image, falling back to text-only generation")
        
        # Generate images - if num_images > 1, generate variations for each prompt
        tasks = []
        total_index = 0
        for prompt in prompts:
            for variation in range(num_images):
                tasks.append(generate_and_upload_single(
                    session, 
                    prompt, 
                    total_index, 
                    task_id, 
                    model=model,
                    reference_image_url=reference_image_url,
                    reference_strength=reference_strength,
                    image_size=image_size,
                    generation_mode=generation_mode,
                    creativity_level=creativity_level,
                    negative_prompt=negative_prompt
                ))
                total_index += 1
        image_urls = await asyncio.gather(*tasks)
    
    success_count = len([u for u in image_urls if u])
    total_requested = len(prompts) * num_images
    print(f"✅ Generation complete: {success_count}/{total_requested} images generated")
    
    return image_urls, task_id
