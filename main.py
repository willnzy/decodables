# 伪代码逻辑
import image_generator
import story_generator
import zine_generator

def main(user_topic):
    # 1. LLM 生成故事板
    story_json = generate_story(user_topic) 
    # story_json = [{"text": "...", "prompt": "..."}, ...]

    # 2. 并发调用 Flux 生成 8 张图
    image_paths = generate_images_parallel([item['prompt'] for item in story_json])

    # 3. 生成 PDF (传入图片路径 + 对应的文字)
    # 注意：这里需要修改你的 create_foldable_book 函数，让它支持传入 text_list
    create_foldable_book(image_paths, text_list=[item['text'] for item in story_json])

    print("Done!")