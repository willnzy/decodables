import asyncio
import fal_client
import os
import aiohttp
import uuid
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "generated-images" #  PRD  Bucket

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

async def generate_and_upload_single(session, prompt, index, task_id, model="flux-schnell"):
    """
    Generate a single image and upload to Supabase Storage.
    
    Args:
        model: Model name (flux-schnell for standard, flux-dev for high-quality)
    """
    try:
        print(f"🎨 Generating {index} with model {model}...")
        
        # Select model endpoint and parameters based on model type
        if model == "flux-dev":
            # High-quality model for Pro users
            model_endpoint = "fal-ai/flux/dev"
            num_inference_steps = 28  # Higher quality, more steps
        else:
            # Standard model for Free/Starter users (default: flux-schnell)
            model_endpoint = "fal-ai/flux/schnell"
            num_inference_steps = 4  # Faster generation
        
        # 1.  Fal
        handler = await fal_client.submit_async(
            model_endpoint,
            arguments={
                "prompt": prompt + ", children's book style, safe for work, colorful",
                "image_size": "landscape_4_3",
                "num_inference_steps": num_inference_steps,
                "enable_safety_checker": True
            },
        )
        result = await handler.get()
        image_url = result['images'][0]['url']
        
        # 2.  Supabase
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
        print(f"❌ Error: {e}")
        return None

async def generate_8_images(prompts: list, model="flux-schnell"):
    """
    Generate 8 images using specified model.
    
    Args:
        prompts: List of prompts for image generation
        model: Model name (flux-schnell for standard, flux-dev for high-quality)
    
    Returns:
        Tuple of (image_urls, task_id)
    """
    task_id = uuid.uuid4().hex[:8]
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, prompt in enumerate(prompts):
            tasks.append(generate_and_upload_single(session, prompt, i, task_id, model=model))
        image_urls = await asyncio.gather(*tasks)
    return image_urls, task_id