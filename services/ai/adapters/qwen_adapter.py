"""
阿里云 DashScope AI 适配器

包含两个独立的模型系列:
1. Qwen (通义千问) - 文本大模型
   - qwen-turbo, qwen-plus, qwen-max
   
2. Wanx (通义万相) - 图像生成模型  
   - wan2.6-t2i (文生图)
   - wan2.6-image (图像编辑)

注意: Qwen 和 Wanx 是两个不同的模型系列，不要混淆！
两者共用同一个 DASHSCOPE_API_KEY。

API Docs:
- Qwen: https://help.aliyun.com/zh/dashscope/developer-reference/api-details
- Wanx: https://help.aliyun.com/zh/model-studio/developer-reference/tongyi-wanxiang
"""

import time
import logging
import aiohttp
from typing import List, Dict, Optional

from ..base import (
    BaseTextAdapter,
    BaseImageAdapter,
    AIResponse,
    AIUsage,
    AIErrorType,
    classify_error
)
from .qwen_config import (
    DASHSCOPE_API_KEY,
    TEXT_API_URL,
    IMAGE_API_URL,
    QWEN_TEXT_MODELS,
    WANX_IMAGE_MODELS,
    SIZE_MAPPING,
)

logger = logging.getLogger(__name__)


class QwenTextAdapter(BaseTextAdapter):
    """
    通义千问文本模型适配器
    
    支持模型:
    - qwen-turbo: 快速响应
    - qwen-plus: 平衡性能
    - qwen-max: 最高质量
    """
    
    provider_name = "qwen"
    
    def __init__(self):
        self._api_key = DASHSCOPE_API_KEY
    
    def is_available(self) -> bool:
        return self._api_key is not None
    
    def get_available_models(self) -> List[str]:
        return QWEN_TEXT_MODELS.copy()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> AIResponse:
        """千问 Chat Completion"""
        if not self._api_key:
            return AIResponse.from_error(
                "DASHSCOPE_API_KEY not configured",
                AIErrorType.AUTH_ERROR,
                self.provider_name,
                model
            )
        
        start_time = time.time()
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            }
            
            payload = {
                "model": model,
                "input": {"messages": messages},
                "parameters": {
                    "temperature": temperature,
                    "result_format": "message",
                }
            }
            
            if max_tokens:
                payload["parameters"]["max_tokens"] = max_tokens
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    TEXT_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    result = await resp.json()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if "code" in result and result["code"]:
                return AIResponse(
                    success=False,
                    error=result.get("message", "Unknown error"),
                    error_type=AIErrorType.API_ERROR,
                    provider=self.provider_name,
                    model=model,
                    latency_ms=latency_ms
                )
            
            output = result.get("output", {})
            choices = output.get("choices", [])
            content = ""
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
            
            usage_data = result.get("usage", {})
            usage = AIUsage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            
            return AIResponse(
                success=True,
                content=content,
                usage=usage,
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                raw_response=result
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = classify_error(e, self.provider_name)
            logger.error(f"[Qwen] Chat completion error: {e}")
            
            return AIResponse(
                success=False,
                error=str(e),
                error_type=error_type,
                provider=self.provider_name,
                model=model,
                latency_ms=latency_ms
            )


class WanxImageAdapter(BaseImageAdapter):
    """
    通义万相 (Wanx) 图像生成适配器
    
    注意: Wanx 是独立的图像生成模型，与 Qwen 文本模型不同！
    
    支持模型:
    - wan2.6-t2i: 文生图 (推荐)
    - wan2.6-image: 图像编辑
    - wanx-v1: 旧版本
    """
    
    provider_name = "wanx"
    
    def __init__(self):
        self._api_key = DASHSCOPE_API_KEY
    
    def is_available(self) -> bool:
        return self._api_key is not None
    
    def get_available_models(self) -> List[str]:
        return WANX_IMAGE_MODELS.copy()
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "wan2.6-t2i",
        size: str = "1024*1024",
        num_images: int = 1,
        negative_prompt: Optional[str] = None,
        prompt_extend: bool = True,
        watermark: bool = False,
        seed: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """万相图像生成"""
        if not self._api_key:
            return AIResponse.from_error(
                "DASHSCOPE_API_KEY not configured",
                AIErrorType.AUTH_ERROR,
                self.provider_name,
                model
            )
        
        start_time = time.time()
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            }
            
            wanx_size = SIZE_MAPPING.get(size, size)
            if "x" in wanx_size:
                wanx_size = wanx_size.replace("x", "*")
            
            num_images = max(1, min(4, num_images))
            
            payload = {
                "model": model,
                "input": {
                    "messages": [{"role": "user", "content": [{"text": prompt}]}]
                },
                "parameters": {
                    "size": wanx_size,
                    "n": num_images,
                    "prompt_extend": prompt_extend,
                    "watermark": watermark,
                }
            }
            
            if negative_prompt:
                payload["parameters"]["negative_prompt"] = negative_prompt
            if seed is not None:
                payload["parameters"]["seed"] = seed
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    IMAGE_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as resp:
                    result = await resp.json()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if "code" in result and result["code"]:
                return AIResponse(
                    success=False,
                    content=[],
                    error=result.get("message", "Unknown error"),
                    error_type=AIErrorType.API_ERROR,
                    provider=self.provider_name,
                    model=model,
                    latency_ms=latency_ms
                )
            
            image_urls = []
            output = result.get("output", {})
            choices = output.get("choices", [])
            
            for choice in choices:
                message = choice.get("message", {})
                content_list = message.get("content", [])
                for content_item in content_list:
                    if "image" in content_item:
                        image_urls.append(content_item["image"])
            
            usage_data = result.get("usage", {})
            usage = AIUsage(images_generated=usage_data.get("image_count", len(image_urls)))
            
            return AIResponse(
                success=True,
                content=image_urls,
                usage=usage,
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                raw_response=result
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = classify_error(e, self.provider_name)
            logger.error(f"[Wanx] Image generation error: {e}")
            
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
        model: str = "wan2.6-image",
        strength: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """万相图像编辑 (图生图)"""
        if not self._api_key:
            return AIResponse.from_error(
                "DASHSCOPE_API_KEY not configured",
                AIErrorType.AUTH_ERROR,
                self.provider_name,
                model
            )
        
        start_time = time.time()
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            }
            
            payload = {
                "model": model,
                "input": {
                    "messages": [{
                        "role": "user",
                        "content": [{"text": prompt}, {"image": image_url}]
                    }]
                },
                "parameters": {
                    "prompt_extend": True,
                    "watermark": False,
                    "n": 1,
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    IMAGE_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as resp:
                    result = await resp.json()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if "code" in result and result["code"]:
                return AIResponse(
                    success=False,
                    content=[],
                    error=result.get("message", "Unknown error"),
                    error_type=AIErrorType.API_ERROR,
                    provider=self.provider_name,
                    model=model,
                    latency_ms=latency_ms
                )
            
            image_urls = []
            output = result.get("output", {})
            choices = output.get("choices", [])
            
            for choice in choices:
                message = choice.get("message", {})
                content_list = message.get("content", [])
                for content_item in content_list:
                    if "image" in content_item:
                        image_urls.append(content_item["image"])
            
            usage = AIUsage(images_generated=len(image_urls))
            
            return AIResponse(
                success=True,
                content=image_urls,
                usage=usage,
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                raw_response=result
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = classify_error(e, self.provider_name)
            logger.error(f"[Wanx] Image-to-image error: {e}")
            
            return AIResponse(
                success=False,
                content=[],
                error=str(e),
                error_type=error_type,
                provider=self.provider_name,
                model=model,
                latency_ms=latency_ms
            )
