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
    image_size="landscape_4_3"
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
    """
    try:
        # Determine if using image-to-image or text-to-image
        use_img2img = reference_image_url is not None
        
        if use_img2img:
            print(f"🎨 Generating {index} with reference image (strength={reference_strength})...")
            # Image-to-image mode using flux-dev
            model_endpoint = "fal-ai/flux/dev/image-to-image"
            
            handler = await fal_client.submit_async(
                model_endpoint,
                arguments={
                    "prompt": prompt + ", children's book style, safe for work, colorful",
                    "image_url": reference_image_url,
                    "strength": reference_strength,  # 0.0 = identical to input, 1.0 = ignore input
                    "image_size": image_size,
                    "num_inference_steps": 28,
                    "enable_safety_checker": True
                },
            )
        else:
            print(f"🎨 Generating {index} with model {model}...")
            
            # Select model endpoint and parameters based on model type
            if model == "flux-dev":
                model_endpoint = "fal-ai/flux/dev"
                num_inference_steps = 28
            else:
                model_endpoint = "fal-ai/flux/schnell"
                num_inference_steps = 4
            
            handler = await fal_client.submit_async(
                model_endpoint,
                arguments={
                    "prompt": prompt + ", children's book style, safe for work, colorful",
                    "image_size": image_size,
                    "num_inference_steps": num_inference_steps,
                    "enable_safety_checker": True
                },
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
    image_size: str = "landscape_4_3"
):
    """
    Generate images using specified model, optionally with reference image.
    
    Args:
        prompts: List of prompts for image generation
        model: Model name (flux-schnell for standard, flux-dev for high-quality)
        reference_image: Optional base64 image or URL for style reference
        reference_strength: How much to follow reference (0.0-1.0, higher = more similar)
        image_size: Image aspect ratio (landscape_4_3, square, portrait_4_3, etc.)
    
    Returns:
        Tuple of (image_urls, task_id)
    """
    task_id = uuid.uuid4().hex[:8]
    reference_image_url = None
    
    async with aiohttp.ClientSession() as session:
        # Upload reference image if provided
        if reference_image:
            reference_image_url = await upload_reference_image(session, reference_image, task_id)
            if not reference_image_url:
                print("⚠️ Failed to process reference image, falling back to text-only generation")
        
        # Generate images
        tasks = []
        for i, prompt in enumerate(prompts):
            tasks.append(generate_and_upload_single(
                session, 
                prompt, 
                i, 
                task_id, 
                model=model,
                reference_image_url=reference_image_url,
                reference_strength=reference_strength,
                image_size=image_size
            ))
        image_urls = await asyncio.gather(*tasks)
    
    return image_urls, task_id
