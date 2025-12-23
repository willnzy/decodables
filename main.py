import asyncio
import os
# 引入我们写好的三个模块
from story_generator import generate_story_json
from image_generator import generate_8_images
from zine_generator import create_foldable_book

async def run_full_flow(user_topic):
    print("🎬 === Starting Workflow (Extreme Saver Mode) ===")
    
    # 1. 大脑：生成故事 (GPT-4o-mini)
    # 成本估算: 约 $0.0001 (几乎免费)
    story_data = generate_story_json(user_topic, model="gpt-4o-mini")
    
    if not story_data:
        print("❌ Failed to generate story. Aborting.")
        return

    # 提取 8 个 Prompt
    # 注意：我们要确保顺序是 P1 到 P8
    prompts = []
    print("\n📝 Story Outline:")
    for page in story_data['pages']:
        print(f"  [P{page['page_number']}] {page['story_text'][:30]}...")
        prompts.append(page['image_prompt'])

    # 2. 眼睛：生成图片 (Flux Schnell)
    # 成本估算: 8张图 x $0.003 = $0.024 (约 0.17 元人民币)
    print("\n🎨 Generating Images (Flux Schnell)...")
    image_paths, task_folder = await generate_8_images(prompts)
    
    # 3. 身体：生成 PDF (ReportLab)
    # 成本: $0
    print("\n📄 Assembling PDF...")
    # 使用生成的标题作为文件名
    safe_title = "".join([c for c in story_data['title'] if c.isalnum() or c==' ']).strip().replace(" ", "_")
    pdf_filename = f"{safe_title}.pdf"
    
    create_foldable_book(
        image_paths, 
        filename=pdf_filename, 
        paper_type="US_LETTER",
        draw_outer_border=True # 加上剪切线方便测试
    )
    
    print("\n" + "="*40)
    print(f"🎉 DONE! Workflow Complete.")
    print(f"📂 Images: {task_folder}")
    print(f"📕 PDF: {pdf_filename}")
    print("="*40)

if __name__ == "__main__":
    # 在这里输入你想测试的主题
    topic = input("Enter a topic for your mini-book: ")
    # topic = "A robot learning to cook" # 或者直接写死
    
    asyncio.run(run_full_flow(topic))