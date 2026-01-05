"""
Story Generator Service
故事生成服务

Uses unified AI service to generate children's book stories in JSON format.
基于统一 AI 服务生成儿童故事书 JSON 格式内容。

Features:
- Automatic model selection from admin configuration
- Canary release support
- Usage tracking
- Automatic fallback on errors
"""

import json
import asyncio
import logging
from typing import Optional
from openai import OpenAI

from .unified_text_service import unified_text_service

logger = logging.getLogger(__name__)

# ==========================================
# Legacy OpenAI Client (向后兼容)
# ==========================================
# 用于 app.py 中其他需要直接访问 OpenAI API 的功能
# 例如: Assistants API, Beta Threads, 等
client = OpenAI()


# ==========================================
# System Prompt
# ==========================================

STORY_SYSTEM_PROMPT = """You are a professional children's book author.
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


# ==========================================
# Main Function
# ==========================================

def generate_story_json(
    topic: str,
    model: str = None,  # 保留用于向后兼容，但不再使用
    user_id: Optional[str] = None,
    tier: str = "free"
) -> Optional[dict]:
    """
    生成儿童故事书 JSON 数据
    
    Args:
        topic: 故事主题
        model: [已废弃] 保留用于向后兼容，实际使用配置的模型
        user_id: 用户 ID (用于灰度分流和使用量追踪)
        tier: 用户等级 (free, starter, pro)
    
    Returns:
        故事数据字典，失败返回 None
        
    Note:
        - 模型选择由 Admin 配置管理
        - 自动支持灰度发布测试新模型
        - 自动追踪使用量
        - 失败时自动 fallback 到备用模型
    """
    print(f"🧠 Brainstorming story about: {topic}...")
    
    async def _generate_async():
        """异步生成故事"""
        response = await unified_text_service.chat(
            messages=[
                {"role": "system", "content": STORY_SYSTEM_PROMPT},
                {"role": "user", "content": f"Topic: {topic}"}
            ],
            user_id=user_id,
            tier=tier,
            temperature=0.7,
            response_format={"type": "json_object"},
            use_cache=False,  # 故事每次应该不同
        )
        return response
    
    try:
        # 在同步函数中执行异步代码
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # 如果已经在异步上下文中，创建新的任务
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _generate_async())
                response = future.result()
        else:
            # 否则直接运行
            response = asyncio.run(_generate_async())
        
        # 处理响应
        if not response.success:
            logger.error(f"[StoryGenerator] AI call failed: {response.error}")
            print(f"❌ Story Generation Error: {response.error}")
            return None
        
        # 解析 JSON
        content = response.content
        story_data = json.loads(content)
        
        # 记录成功信息
        title = story_data.get('title', 'Untitled')
        model_info = f"{response.provider}/{response.model}" if response.provider else "unknown"
        print(f"✅ Story Generated: \"{title}\" (via {model_info})")
        logger.info(f"[StoryGenerator] Story generated: {title}, model: {model_info}")
        
        return story_data
        
    except json.JSONDecodeError as e:
        logger.error(f"[StoryGenerator] JSON parse error: {e}")
        print(f"❌ Story Generation Error: Invalid JSON response")
        return None
    except Exception as e:
        logger.error(f"[StoryGenerator] Unexpected error: {e}")
        print(f"❌ Story Generation Error: {e}")
        return None


# ==========================================
# Async Version (for direct async usage)
# ==========================================

async def generate_story_json_async(
    topic: str,
    user_id: Optional[str] = None,
    tier: str = "free"
) -> Optional[dict]:
    """
    异步版本的故事生成函数
    
    Args:
        topic: 故事主题
        user_id: 用户 ID
        tier: 用户等级
    
    Returns:
        故事数据字典，失败返回 None
    """
    print(f"🧠 Brainstorming story about: {topic}...")
    
    try:
        response = await unified_text_service.chat(
            messages=[
                {"role": "system", "content": STORY_SYSTEM_PROMPT},
                {"role": "user", "content": f"Topic: {topic}"}
            ],
            user_id=user_id,
            tier=tier,
            temperature=0.7,
            response_format={"type": "json_object"},
            use_cache=False,
        )
        
        if not response.success:
            logger.error(f"[StoryGenerator] AI call failed: {response.error}")
            print(f"❌ Story Generation Error: {response.error}")
            return None
        
        content = response.content
        story_data = json.loads(content)
        
        title = story_data.get('title', 'Untitled')
        model_info = f"{response.provider}/{response.model}" if response.provider else "unknown"
        print(f"✅ Story Generated: \"{title}\" (via {model_info})")
        
        return story_data
        
    except json.JSONDecodeError as e:
        logger.error(f"[StoryGenerator] JSON parse error: {e}")
        print(f"❌ Story Generation Error: Invalid JSON response")
        return None
    except Exception as e:
        logger.error(f"[StoryGenerator] Unexpected error: {e}")
        print(f"❌ Story Generation Error: {e}")
        return None


# ==========================================
# Test
# ==========================================

if __name__ == "__main__":
    test_topic = "A cat who wants to be a dog"
    result = generate_story_json(test_topic)
    if result:
        print(json.dumps(result, indent=2))
