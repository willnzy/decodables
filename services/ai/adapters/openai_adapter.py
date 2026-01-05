"""
OpenAI Adapter
OpenAI API 适配器

Supports:
- GPT-4o, GPT-4o-mini, o1, o1-mini
- DALL-E 3 for image generation
- JSON mode response format

v3.22: Added retry mechanism and timeout configuration
"""

import os
import time
import logging
from typing import List, Dict, Optional, Any

import openai
import httpx

from ..base import (
    BaseTextAdapter, 
    BaseImageAdapter, 
    AIResponse, 
    AIUsage,
    AIErrorType,
    classify_error
)
from ..retry import with_retry

logger = logging.getLogger(__name__)

# ==========================================
# Configuration
# ==========================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Available models
OPENAI_TEXT_MODELS = [
    "gpt-4o-mini",
    "gpt-4o", 
    "o1-mini",
    "o1",
]

OPENAI_IMAGE_MODELS = [
    "dall-e-3",
]

# Timeout configuration (seconds)
OPENAI_TIMEOUTS = {
    "text": {
        "gpt-4o-mini": 30,
        "gpt-4o": 60,
        "o1-mini": 90,
        "o1": 120,
        "default": 60,
    },
    "image": {
        "dall-e-3": 120,
        "default": 120,
    }
}


def get_openai_timeout(model: str, call_type: str = "text") -> int:
    """Get timeout for OpenAI operation."""
    timeouts = OPENAI_TIMEOUTS.get(call_type, OPENAI_TIMEOUTS["text"])
    return timeouts.get(model, timeouts["default"])


# ==========================================
# Text Adapter
# ==========================================

class OpenAITextAdapter(BaseTextAdapter):
    """
    OpenAI 文本模型适配器
    
    支持模型:
    - gpt-4o-mini: 快速、低成本
    - gpt-4o: 高质量、多模态
    - o1-mini: 推理优化（轻量）
    - o1: 推理优化（完整）
    
    v3.22 Features:
    - Automatic retry on transient errors
    - Configurable timeout per model
    - Custom HTTP client with timeout
    """
    
    provider_name = "openai"
    
    def __init__(self):
        self._client = None
        if OPENAI_API_KEY:
            # Create HTTP client with timeout configuration
            timeout = httpx.Timeout(
                connect=10.0,    # Connection timeout
                read=60.0,       # Read timeout (overridden per-call)
                write=10.0,      # Write timeout
                pool=5.0         # Pool timeout
            )
            http_client = httpx.AsyncClient(timeout=timeout)
            self._client = openai.AsyncOpenAI(
                api_key=OPENAI_API_KEY,
                http_client=http_client
            )
    
    def is_available(self) -> bool:
        return self._client is not None
    
    def get_available_models(self) -> List[str]:
        return OPENAI_TEXT_MODELS.copy()
    
    @with_retry(max_attempts=3, min_wait=1, max_wait=20)
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> AIResponse:
        """
        OpenAI Chat Completion (with retry and timeout)
        
        Note:
        - o1/o1-mini 不支持 system message，需要转换为 user message
        - o1/o1-mini 不支持 temperature 和 response_format
        """
        if not self._client:
            return AIResponse.from_error(
                "OpenAI API key not configured",
                AIErrorType.AUTH_ERROR,
                self.provider_name,
                model
            )
        
        start_time = time.time()
        timeout = get_openai_timeout(model, "text")
        
        try:
            # 处理 o1 系列模型的特殊要求
            processed_messages = messages
            params = {
                "model": model,
                "messages": processed_messages,
                "timeout": timeout,  # Request-level timeout
            }
            
            if model.startswith("o1"):
                # o1 不支持 system message，转换为 user message
                processed_messages = self._convert_system_to_user(messages)
                params["messages"] = processed_messages
                # o1 也不支持 temperature 和某些参数
                if max_tokens:
                    params["max_completion_tokens"] = max_tokens
            else:
                # 常规模型
                params["temperature"] = temperature
                if max_tokens:
                    params["max_tokens"] = max_tokens
                if response_format:
                    params["response_format"] = response_format
            
            # Remove timeout from params (handled at client level)
            params.pop("timeout", None)
            
            # 调用 API
            response = await self._client.chat.completions.create(**params)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 提取响应
            content = response.choices[0].message.content or ""
            usage = AIUsage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )
            
            return AIResponse(
                success=True,
                content=content,
                usage=usage,
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = classify_error(e, self.provider_name)
            logger.error(f"[OpenAI] Chat completion error: {e}")
            
            return AIResponse(
                success=False,
                error=str(e),
                error_type=error_type,
                provider=self.provider_name,
                model=model,
                latency_ms=latency_ms
            )
    
    def _convert_system_to_user(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        将 system message 转换为 user message (用于 o1 系列)
        
        o1 不支持 system role，需要将 system prompt 作为 user message 的一部分
        """
        result = []
        system_content = None
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                result.append(msg)
        
        # 将 system content 添加到第一个 user message
        if system_content and result:
            for i, msg in enumerate(result):
                if msg["role"] == "user":
                    result[i] = {
                        "role": "user",
                        "content": f"[System Instructions]\n{system_content}\n\n[User Message]\n{msg['content']}"
                    }
                    break
        
        return result


# ==========================================
# Image Adapter
# ==========================================

class OpenAIImageAdapter(BaseImageAdapter):
    """
    OpenAI DALL-E 图像生成适配器
    
    支持模型:
    - dall-e-3: 高质量图像生成
    
    v3.22 Features:
    - Automatic retry on transient errors
    - Configurable timeout
    """
    
    provider_name = "openai"
    
    def __init__(self):
        self._client = None
        if OPENAI_API_KEY:
            # Create HTTP client with timeout configuration
            timeout = httpx.Timeout(
                connect=10.0,
                read=120.0,  # Longer read timeout for image generation
                write=10.0,
                pool=5.0
            )
            http_client = httpx.AsyncClient(timeout=timeout)
            self._client = openai.AsyncOpenAI(
                api_key=OPENAI_API_KEY,
                http_client=http_client
            )
    
    def is_available(self) -> bool:
        return self._client is not None
    
    def get_available_models(self) -> List[str]:
        return OPENAI_IMAGE_MODELS.copy()
    
    @with_retry(max_attempts=3, min_wait=2, max_wait=30)
    async def generate_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        num_images: int = 1,
        negative_prompt: Optional[str] = None,
        quality: str = "standard",
        style: str = "vivid",
        **kwargs
    ) -> AIResponse:
        """
        DALL-E 图像生成 (with retry and timeout)
        
        Args:
            prompt: 图像描述
            model: 模型 (dall-e-3)
            size: 尺寸 (1024x1024, 1792x1024, 1024x1792)
            num_images: 生成数量 (DALL-E 3 仅支持 1)
            quality: 质量 (standard, hd)
            style: 风格 (vivid, natural)
        """
        if not self._client:
            return AIResponse.from_error(
                "OpenAI API key not configured",
                AIErrorType.AUTH_ERROR,
                self.provider_name,
                model
            )
        
        start_time = time.time()
        
        try:
            # DALL-E 3 只支持 n=1
            if model == "dall-e-3":
                num_images = 1
            
            # 如果有 negative prompt，追加到 prompt
            full_prompt = prompt
            if negative_prompt:
                full_prompt = f"{prompt}. Avoid: {negative_prompt}"
            
            response = await self._client.images.generate(
                model=model,
                prompt=full_prompt,
                size=size,
                n=num_images,
                quality=quality,
                style=style,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 提取图像 URL
            image_urls = [img.url for img in response.data if img.url]
            
            return AIResponse(
                success=True,
                content=image_urls,
                usage=AIUsage(images_generated=len(image_urls)),
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms,
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = classify_error(e, self.provider_name)
            logger.error(f"[OpenAI] Image generation error: {e}")
            
            return AIResponse(
                success=False,
                content=[],
                error=str(e),
                error_type=error_type,
                provider=self.provider_name,
                model=model,
                latency_ms=latency_ms
            )
    
    async def image_to_image(
        self,
        prompt: str,
        image_url: str,
        model: str = "dall-e-3",
        strength: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """
        DALL-E 不直接支持 image-to-image，返回不支持错误
        """
        return AIResponse.from_error(
            "DALL-E 3 does not support image-to-image generation",
            AIErrorType.INVALID_REQUEST,
            self.provider_name,
            model
        )
