"""
Qwen / Wanx Adapter (阿里云通义千问/万相)
通义千问文本 + 万相图像生成适配器

Supports:
- Qwen text models (qwen-turbo, qwen-plus, qwen-max)
- Wanx image generation (wan2.6-t2i, wan2.6-image)

API Docs:
- Text: https://help.aliyun.com/zh/dashscope/developer-reference/api-details
- Image: https://help.aliyun.com/zh/model-studio/developer-reference/tongyi-wanxiang
"""

import os
import time
import logging
import aiohttp
from typing import List, Dict, Optional, Any

from ..base import (
    BaseTextAdapter,
    BaseImageAdapter,
    AIResponse,
    AIUsage,
    AIErrorType,
    classify_error
)

logger = logging.getLogger(__name__)

# ==========================================
# Configuration
# ==========================================

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY")

# API Endpoints (International)
# 新加坡: dashscope-intl.aliyuncs.com
# 北京: dashscope.aliyuncs.com
DASHSCOPE_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL", 
    "https://dashscope-intl.aliyuncs.com"
)

# Text API endpoint
TEXT_API_URL = f"{DASHSCOPE_BASE_URL}/api/v1/services/aigc/text-generation/generation"

# Image API endpoint (万相)
IMAGE_API_URL = f"{DASHSCOPE_BASE_URL}/api/v1/services/aigc/multimodal-generation/generation"

# Available models
QWEN_TEXT_MODELS = [
    "qwen-turbo",      # 快速，低成本
    "qwen-plus",       # 平衡
    "qwen-max",        # 最高质量
    "qwen-max-longcontext",  # 长上下文
]

WANX_IMAGE_MODELS = [
    "wanx-v1",         # 万相 v1
    "wan2.6-t2i",      # 万相 2.6 文生图
    "wan2.6-image",    # 万相 2.6 图像编辑
]

# Size mapping: our format -> Wanx format
# 万相使用 "宽*高" 格式
SIZE_MAPPING = {
    "square": "1024*1024",
    "1:1": "1024*1024",
    "landscape_4_3": "1280*960",
    "4:3": "1280*960",
    "portrait_4_3": "960*1280",
    "3:4": "960*1280",
    "landscape_16_9": "1280*720",
    "16:9": "1280*720",
    "portrait_9_16": "720*1280",
    "9:16": "720*1280",
    # 默认
    "1024x1024": "1024*1024",
    "1280x1280": "1280*1280",
}


# ==========================================
# Text Adapter (千问)
# ==========================================

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
        """
        千问 Chat Completion
        """
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
            
            # 构建请求体
            payload = {
                "model": model,
                "input": {
                    "messages": messages
                },
                "parameters": {
                    "temperature": temperature,
                    "result_format": "message",  # 返回 message 格式
                }
            }
            
            if max_tokens:
                payload["parameters"]["max_tokens"] = max_tokens
            
            # JSON 模式
            if response_format and response_format.get("type") == "json_object":
                # 千问通过 prompt 指示返回 JSON
                pass
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    TEXT_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    result = await resp.json()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 检查错误
            if "code" in result and result["code"]:
                return AIResponse(
                    success=False,
                    error=result.get("message", "Unknown error"),
                    error_type=AIErrorType.API_ERROR,
                    provider=self.provider_name,
                    model=model,
                    latency_ms=latency_ms
                )
            
            # 提取响应
            output = result.get("output", {})
            choices = output.get("choices", [])
            
            content = ""
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
            
            # 提取 usage
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


# ==========================================
# Image Adapter (万相)
# ==========================================

class QwenImageAdapter(BaseImageAdapter):
    """
    通义万相图像生成适配器
    
    支持模型:
    - wan2.6-t2i: 文生图 (推荐)
    - wan2.6-image: 图像编辑
    - wanx-v1: 旧版本
    """
    
    provider_name = "qwen"
    
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
        """
        万相图像生成
        
        Args:
            prompt: 图像描述 (支持中英文)
            model: 模型名称 (wan2.6-t2i, wan2.6-image, wanx-v1)
            size: 图像尺寸 (支持多种格式，会自动转换)
            num_images: 生成数量 (1-4)
            negative_prompt: 负面提示词
            prompt_extend: 是否启用提示词智能扩展
            watermark: 是否添加水印
            seed: 随机种子 (可选)
        """
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
            
            # 转换尺寸格式
            wanx_size = SIZE_MAPPING.get(size, size)
            # 确保格式正确 (宽*高)
            if "x" in wanx_size:
                wanx_size = wanx_size.replace("x", "*")
            
            # 限制生成数量
            num_images = max(1, min(4, num_images))
            
            # 构建请求体 (万相 API 格式)
            payload = {
                "model": model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"text": prompt}
                            ]
                        }
                    ]
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
                    timeout=aiohttp.ClientTimeout(total=180)  # 图像生成可能较慢
                ) as resp:
                    result = await resp.json()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 检查错误
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
            
            # 提取图像 URL
            # 响应格式: output.choices[].message.content[].image
            image_urls = []
            output = result.get("output", {})
            choices = output.get("choices", [])
            
            for choice in choices:
                message = choice.get("message", {})
                content_list = message.get("content", [])
                for content_item in content_list:
                    if "image" in content_item:
                        image_urls.append(content_item["image"])
            
            # 提取 usage
            usage_data = result.get("usage", {})
            usage = AIUsage(
                images_generated=usage_data.get("image_count", len(image_urls))
            )
            
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
        """
        万相图像编辑 (图生图)
        
        Args:
            prompt: 编辑指令
            image_url: 参考图像 URL
            model: 模型 (推荐 wan2.6-image)
            strength: 编辑强度 (0-1)
        """
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
            
            # 构建请求体 (图像编辑模式)
            payload = {
                "model": model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"text": prompt},
                                {"image": image_url}
                            ]
                        }
                    ]
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
            
            # 检查错误
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
            
            # 提取图像 URL
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
