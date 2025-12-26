import asyncio
import fal_client
import os
import aiohttp
import uuid
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "generated-images" # 对应 PRD 的 Bucket

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

async def generate_and_upload_single(session, prompt, index, task_id):
    try:
        print(f"🎨 Generating {index}...")
        # 1. 调用 Fal
        handler = await fal_client.submit_async(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt + ", children's book style, safe for work, colorful",
                "image_size": "landscape_4_3",
                "num_inference_steps": 4,
                "enable_safety_checker": True
            },
        )
        result = await handler.get()
        image_url = result['images'][0]['url']
        
        # 2. 转存 Supabase
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

async def generate_8_images(prompts: list):
    task_id = uuid.uuid4().hex[:8]
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, prompt in enumerate(prompts):
            tasks.append(generate_and_upload_single(session, prompt, i, task_id))
        image_urls = await asyncio.gather(*tasks)
    return image_urls, task_id