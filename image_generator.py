import asyncio
import fal_client
import os
import aiohttp
import uuid
from datetime import datetime

os.environ["FAL_KEY"] = "458c68bf-fa1a-46a4-b3e8-64b488f33c8b:6128a861bde9e796cd0f48517d6e87fd"

async def generate_and_download_single(session, prompt, index, save_dir):
    """
    单个任务：保存到指定的 save_dir 目录中，文件名为 P{index}.png
    """
    try:
        print(f"🎨 [Image {index}] Generating...")
        
        # 1. 调用 Fal.ai 生成
        handler = await fal_client.submit_async(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "landscape_4_3",
                "num_inference_steps": 4,
                "enable_safety_checker": True
            },
        )
        
        # 2. 获取结果 URL
        result = await handler.get()
        image_url = result['images'][0]['url']
        
        # 3. 下载图片到指定目录
        async with session.get(image_url) as response:
            if response.status == 200:
                filename = f"P{index}.png"
                filepath = os.path.join(save_dir, filename)
                
                content = await response.read()
                with open(filepath, "wb") as f:
                    f.write(content)
                
                print(f"✅ [Image {index}] Saved to: {filepath}")
                return filepath
            else:
                print(f"❌ [Image {index}] Download failed")
                return None
                
    except Exception as e:
        print(f"❌ [Image {index}] Error: {e}")
        return None

async def generate_8_images(prompts, base_output_dir="images"):
    """
    接收 8 个 Prompt
    1. 生成 {时间戳}_{UUID} 文件夹
    2. 并发下载图片到该文件夹
    3. 返回图片路径列表
    """
    # --- 1. 创建带时间戳的任务文件夹 ---
    # 格式: 20251223_123005 (年月日_时分秒)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uuid_str = uuid.uuid4().hex[:8] # 取前8位UUID就够了，不用太长
    
    # 组合文件夹名: 20251223_123005_a1b2c3d4
    task_folder_name = f"{timestamp}_{uuid_str}"
    task_dir = os.path.join(base_output_dir, task_folder_name)
    
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)
        print(f"📂 Created task directory: {task_dir}")

    # --- 2. 准备 Prompt ---
    if len(prompts) < 8:
        prompts += ["A cute illustration"] * (8 - len(prompts))
    prompts = prompts[:8]

    # --- 3. 并发执行 ---
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, prompt in enumerate(prompts):
            tasks.append(generate_and_download_single(session, prompt, i+1, task_dir))
        
        await asyncio.gather(*tasks)
    
    # --- 4. 整理返回路径 ---
    final_paths = []
    for i in range(1, 9):
        path = os.path.join(task_dir, f"P{i}.png")
        if os.path.exists(path):
            final_paths.append(path)
        else:
            final_paths.append(None)

    return final_paths, task_dir

# ==========================================
# 测试代码
# ==========================================
if __name__ == "__main__":
    test_prompts = [
        "A cute cat, P1", "A cute dog, P2", "A cute bird, P3", "A cute fish, P4",
        "A cute lion, P5", "A cute tiger, P6", "A cute bear, P7", "A cute wolf, P8"
    ]
    
    print("🚀 Starting generation...")
    paths, folder = asyncio.run(generate_8_images(test_prompts))
    
    print(f"\n🎉 Task Completed!")
    print(f"📂 Folder: {folder}")