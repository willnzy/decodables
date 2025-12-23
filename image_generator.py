import asyncio
import fal_client
import os
import aiohttp
import uuid
from datetime import datetime
from supabase import create_client, Client

# 从环境变量获取 Supabase 配置
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "magic-zine-images"

# 初始化 Supabase 客户端 (如果配置了的话)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

async def generate_and_upload_single(session, prompt, index, task_id):
    """
    生成图片 -> 上传到 Supabase -> 返回公开访问的 URL
    """
    try:
        print(f"🎨 [Image {index}] Generating...")
        
        # 1. Fal.ai 生图
        handler = await fal_client.submit_async(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "landscape_4_3",
                "num_inference_steps": 4,
                "enable_safety_checker": True
            },
        )
        result = await handler.get()
        image_url = result['images'][0]['url']
        
        # 2. 下载图片数据流 (Bytes)
        async with session.get(image_url) as response:
            if response.status == 200:
                image_bytes = await response.read()
                
                # 3. 上传到 Supabase
                filename = f"{task_id}/P{index}.png"
                # 指定 content-type 否则可能是 octet-stream
                res = supabase.storage.from_(BUCKET_NAME).upload(
                    path=filename,
                    file=image_bytes,
                    file_options={"content-type": "image/png"}
                )
                
                # 4. 获取公开 URL
                public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
                print(f"✅ [Image {index}] Uploaded to: {public_url}")
                return public_url
            else:
                return None
    except Exception as e:
        print(f"❌ [Image {index}] Error: {e}")
        return None

async def generate_8_images(prompts):
    """
    接收 prompts，返回 8 个云端图片 URL
    """
    task_id = uuid.uuid4().hex[:8]
    
    # 补齐 prompt
    if len(prompts) < 8:
        prompts += ["A cute illustration"] * (8 - len(prompts))
    prompts = prompts[:8]

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, prompt in enumerate(prompts):
            tasks.append(generate_and_upload_single(session, prompt, i+1, task_id))
        
        # 等待所有结果
        image_urls = await asyncio.gather(*tasks)
    
    return image_urls, task_id