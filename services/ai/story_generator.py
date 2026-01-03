import json
import os
from openai import OpenAI

# ==========================================
# 1.  OpenAI 
# ==========================================
# ： key，client  OPENAI_API_KEY
client = OpenAI()

def generate_story_json(topic, model="gpt-4o-mini"):
    """
    :  (Topic)
    : JSON  ( Title, Visual Style, Pages)
    """
    print(f"🧠 Brainstorming story about: {topic} (Model: {model})...")

    #  (System Prompt)
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
        #  OpenAI API
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"}, #  JSON
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Topic: {topic}"}
            ],
            temperature=0.7 # 0.7 
        )

        #  JSON 
        content = response.choices[0].message.content
        story_data = json.loads(content)
        
        print(f"✅ Story Generated: \"{story_data.get('title', 'Untitled')}\"")
        return story_data

    except Exception as e:
        print(f"❌ Story Generation Error: {e}")
        return None

#  ()
if __name__ == "__main__":
    test_topic = "A cat who wants to be a dog"
    result = generate_story_json(test_topic)
    if result:
        print(json.dumps(result, indent=2))