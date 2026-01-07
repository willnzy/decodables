"""
AI Chat Service - Support chat with OpenAI Assistants and Vision

@module services.ai_chat_service
@version 3.24
"""

import time
import logging
from typing import List, Optional

from config import OPENAI_ASSISTANT_ID
from services.ai.story_generator import client as openai_client

logger = logging.getLogger(__name__)

SUPPORT_SYSTEM_PROMPT_FALLBACK = """You are a friendly and helpful customer support assistant for Make Decodables.

Your role is to:
1. Answer questions about Make Decodables product features, pricing, and usage
2. Help users troubleshoot common issues
3. Guide users on how to use different features
4. Be concise, friendly, and professional

Important guidelines:
- Keep responses short and helpful (2-4 sentences when possible)
- If you're not sure about something, suggest the user contact human support via WhatsApp (+1 725 290 0525) or email (info@makedecodables.com)
- Always be encouraging and positive
- Use simple language suitable for teachers and parents
- If a question is outside the scope of Make Decodables, politely redirect

Key product info:
- Make Decodables creates 8-page foldable mini-books
- Free plan: 50 bonus credits, PDF export
- Starter ($14.9/mo): 500 monthly credits, ZIP export, marketplace
- Pro ($29.9/mo): 1000 monthly credits, OCR, all features
- AI image: 5 credits, OCR: 5 credits
- Contact: WhatsApp +1 725 290 0525, email info@makedecodables.com

Remember: Be helpful, concise, and friendly!"""


async def chat_with_assistant(
    message: str, 
    conversation_history: list, 
    max_retries: int = 3
) -> dict:
    """Use OpenAI Assistants API with RAG for text-only chat."""
    if not openai_client or not OPENAI_ASSISTANT_ID:
        raise Exception("OpenAI client or Assistant ID not configured")
    
    last_error = None
    thread = None
    
    for attempt in range(max_retries):
        try:
            thread = openai_client.beta.threads.create()
            
            for msg in conversation_history[-6:]:
                if msg.get("role") in ["user", "assistant"]:
                    openai_client.beta.threads.messages.create(
                        thread_id=thread.id,
                        role=msg["role"],
                        content=msg["content"]
                    )
            
            openai_client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message
            )
            
            run = openai_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=OPENAI_ASSISTANT_ID
            )
            
            max_wait = 30
            start_time = time.time()
            while run.status in ["queued", "in_progress"]:
                if time.time() - start_time > max_wait:
                    raise TimeoutError("Assistant response timed out")
                time.sleep(0.5)
                run = openai_client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status != "completed":
                raise Exception(f"Run failed with status: {run.status}")
            
            break
            
        except Exception as e:
            last_error = e
            logger.warning(f"AI Chat attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
            else:
                raise last_error
    
    messages = openai_client.beta.threads.messages.list(
        thread_id=thread.id,
        order="desc",
        limit=1
    )
    
    assistant_message = messages.data[0].content[0].text.value
    
    try:
        openai_client.beta.threads.delete(thread.id)
    except:
        pass
    
    return {
        "status": "ok",
        "message": assistant_message,
        "source": "assistant"
    }


async def chat_with_vision(
    message: str, 
    images: list, 
    conversation_history: list, 
    max_retries: int = 3
) -> dict:
    """Use Chat Completions API with GPT-4o for image analysis."""
    if not openai_client:
        raise Exception("OpenAI client not configured")
    
    messages = [{"role": "system", "content": SUPPORT_SYSTEM_PROMPT_FALLBACK}]
    
    for msg in conversation_history[-10:]:
        if msg.get("role") in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    content = []
    
    if message.strip():
        content.append({"type": "text", "text": message})
    else:
        content.append({"type": "text", "text": "Please describe what you see in these images."})
    
    for img in images[:4]:
        if img.startswith("data:"):
            content.append({
                "type": "image_url",
                "image_url": {"url": img, "detail": "low"}
            })
        elif img.startswith("http"):
            content.append({
                "type": "image_url",
                "image_url": {"url": img, "detail": "low"}
            })
    
    messages.append({"role": "user", "content": content})
    
    last_error = None
    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return {
                "status": "ok",
                "message": response.choices[0].message.content,
                "source": "vision"
            }
            
        except Exception as e:
            last_error = e
            logger.warning(f"Vision chat attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
    
    raise last_error
