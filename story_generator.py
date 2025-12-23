import json
import os
from openai import OpenAI

# ==========================================
# 1. 初始化 OpenAI 客户端
# ==========================================
# 注意：这里不需要手动设置 key，client 会自动读取系统环境变量中的 OPENAI_API_KEY
client = OpenAI()

def generate_story_json(topic, model="gpt-4o-mini"):
    """
    输入: 用户的主题 (Topic)
    输出: JSON 格式的故事数据 (包含 Title, Visual Style, Pages)
    """
    print(f"🧠 Brainstorming story about: {topic} (Model: {model})...")

    # 定义系统提示词 (System Prompt)
    system_prompt = """
    You are a professional children's book author.
    Create an 8-page mini-zine based on the user's topic.
    
    CRITICAL RULES:
    1. Output ONLY valid JSON.
    2. Exactly 8 pages.
    3. Page 1 is intro, Page 8 is ending.
    4. Maintain character consistency in image_prompts.
    5. The story text per page should be short (1-2 sentences), suitable for young kids.

    JSON STRUCTURE:
    {
        "title": "Book Title",
        "visual_style": "Art style description (e.g. watercolor, pixel art)",
        "main_character": "Character description",
        "pages": [
            {
                "page_number": 1,
                "story_text": "Story text...",
                "image_prompt": "Image prompt with visual_style and main_character included."
            },
            ... (8 pages total)
        ]
    }
    """

    try:
        # 调用 OpenAI API
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"}, # 强制输出 JSON
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Topic: {topic}"}
            ],
            temperature=0.7 # 0.7 比较适合创意写作
        )

        # 解析返回的 JSON 内容
        content = response.choices[0].message.content
        story_data = json.loads(content)
        
        print(f"✅ Story Generated: \"{story_data.get('title', 'Untitled')}\"")
        return story_data

    except Exception as e:
        print(f"❌ Story Generation Error: {e}")
        return None

# 本地测试用 (部署时不会执行)
if __name__ == "__main__":
    test_topic = "A cat who wants to be a dog"
    result = generate_story_json(test_topic)
    if result:
        print(json.dumps(result, indent=2))