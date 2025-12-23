import os
import json
from openai import OpenAI

# 确保你已经设置了环境变量，或者直接在这里填入
os.environ["OPENAI_API_KEY"] = "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"

# 初始化客户端
client = OpenAI()

def generate_story_json(topic, model="gpt-4o-mini"): # <--- 修改这里：默认使用省钱版
    """
    输入: 用户的主题
    输出: JSON 故事数据
    """
    print(f"🧠 Brainstorming story about: {topic} (Model: {model})...")

    system_prompt = """
    You are a professional children's book author.
    Create an 8-page mini-zine based on the user's topic.
    
    CRITICAL RULES:
    1. Output ONLY valid JSON.
    2. Exactly 8 pages.
    3. Page 1 is intro, Page 8 is ending.
    4. Maintain character consistency in image_prompts.

    JSON STRUCTURE:
    {
        "title": "Book Title",
        "visual_style": "Art style description",
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
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Topic: {topic}"}
            ],
            temperature=0.7
        )

        content = response.choices[0].message.content
        story_data = json.loads(content)
        print(f"✅ Story Generated: \"{story_data.get('title')}\"")
        return story_data

    except Exception as e:
        print(f"❌ Story Error: {e}")
        return None