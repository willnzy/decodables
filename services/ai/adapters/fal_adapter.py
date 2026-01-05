"""
FAL AI Adapter
FAL AI API 适配器

Supports:
- Flux models (schnell, dev, pro)
- Text-to-image generation
- Image-to-image with reference
"""

import os
import time
import logging
from typing import List, Optional

from ..base import (
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

FAL_KEY = os.environ.get("FAL_KEY")

# Available models
FAL_IMAGE_MODELS = [
    "flux-schnell",
    "flux-dev",
    "flux-pro",
]

# Model endpoint mapping
FAL_MODEL_ENDPOINTS = {
    "flux-schnell": "fal-ai/flux/schnell",
    "flux-dev": "fal-ai/flux/dev",
    "flux-pro": "fal-ai/flux-pro",
}

# Default generation parameters by model
FAL_MODEL_DEFAULTS = {
    "flux-schnell": {
        "num_inference_steps": 4,
        "guidance_scale": 3.5,
    },
    "flux-dev": {
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
    },
    "flux-pro": {
        "num_inference_steps": 40,
        "guidance_scale": 3.5,
    },
}


# ==========================================
# Image Adapter
# ==========================================

class FALImageAdapter(BaseImageAdapter):
    """
    FAL AI Flux 图像生成适配器
    
    支持模型:
    - flux-schnell: 快速生成 (4 steps)
    - flux-dev: 高质量 (28 steps)
    - flux-pro: 最高质量 (40 steps)
    """
    
    provider_name = "fal"
    
    def __init__(self):
        self._client = None
        if FAL_KEY:
            try:
                import fal_client
                self._fal = fal_client
                self._client = True  # FAL client uses module-level functions
            except ImportError:
                logger.warning("[FAL] fal_client package not installed")
                self._client = None
    
    def is_available(self) -> bool:
        return self._client is not None and FAL_KEY is not None
    
    def get_available_models(self) -> List[str]:
        return FAL_IMAGE_MODELS.copy()
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "flux-schnell",
        size: str = "landscape_4_3",
        num_images: int = 1,
        negative_prompt: Optional[str] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        enable_safety_checker: bool = True,
        **kwargs
    ) -> AIResponse:
        """
        FAL Flux 图像生成
        
        Args:
            prompt: 图像描述
            model: 模型 (flux-schnell, flux-dev, flux-pro)
            size: 尺寸 (square, landscape_4_3, portrait_4_3, etc.)
            num_images: 生成数量
            negative_prompt: 负面提示词
            num_inference_steps: 推理步数 (可选，使用默认值)
            guidance_scale: CFG 值 (可选，使用默认值)
            enable_safety_checker: 启用安全检查
        """
        if not self._client:
            return AIResponse.from_error(
                "FAL API key not configured or fal_client not installed",
                AIErrorType.AUTH_ERROR,
                self.provider_name,
                model
            )
        
        # 获取模型端点
        endpoint = FAL_MODEL_ENDPOINTS.get(model)
        if not endpoint:
            return AIResponse.from_error(
                f"Unknown FAL model: {model}",
                AIErrorType.MODEL_NOT_FOUND,
                self.provider_name,
                model
            )
        
        start_time = time.time()
        
        try:
            # 获取默认参数
            defaults = FAL_MODEL_DEFAULTS.get(model, FAL_MODEL_DEFAULTS["flux-schnell"])
            steps = num_inference_steps or defaults["num_inference_steps"]
            cfg = guidance_scale or defaults["guidance_scale"]
            
            # 构建参数
            arguments = {
                "prompt": prompt,
                "image_size": size,
                "num_inference_steps": steps,
                "guidance_scale": cfg,
                "enable_safety_checker": enable_safety_checker,
            }
            
            if negative_prompt:
                arguments["negative_prompt"] = negative_prompt
            
            # 异步调用 FAL
            handler = await self._fal.submit_async(endpoint, arguments=arguments)
            result = await handler.get()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 提取图像 URL
            image_urls = []
            if result and "images" in result:
                image_urls = [img["url"] for img in result["images"] if "url" in img]
            
            return AIResponse(
                success=True,
                content=image_urls,
                usage=AIUsage(images_generated=len(image_urls)),
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                raw_response=result
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = classify_error(e, self.provider_name)
            logger.error(f"[FAL] Image generation error: {e}")
            
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
        model: str = "flux-dev",
        strength: float = 0.7,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        enable_safety_checker: bool = True,
        **kwargs
    ) -> AIResponse:
        """
        FAL Flux 图生图
        
        Args:
            prompt: 图像描述
            image_url: 参考图像 URL
            model: 模型 (推荐 flux-dev)
            strength: 参考强度 (0-1, 0=完全参考, 1=忽略参考)
            num_inference_steps: 推理步数
            guidance_scale: CFG 值
        """
        if not self._client:
            return AIResponse.from_error(
                "FAL API key not configured or fal_client not installed",
                AIErrorType.AUTH_ERROR,
                self.provider_name,
                model
            )
        
        # 图生图使用 dev 端点的 image-to-image
        endpoint = "fal-ai/flux/dev/image-to-image"
        
        start_time = time.time()
        
        try:
            # 获取默认参数
            defaults = FAL_MODEL_DEFAULTS.get(model, FAL_MODEL_DEFAULTS["flux-dev"])
            steps = num_inference_steps or defaults["num_inference_steps"]
            cfg = guidance_scale or defaults["guidance_scale"]
            
            # 构建参数
            arguments = {
                "prompt": prompt,
                "image_url": image_url,
                "strength": strength,
                "num_inference_steps": steps,
                "guidance_scale": cfg,
                "enable_safety_checker": enable_safety_checker,
            }
            
            # 异步调用 FAL
            handler = await self._fal.submit_async(endpoint, arguments=arguments)
            result = await handler.get()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 提取图像 URL
            image_urls = []
            if result and "images" in result:
                image_urls = [img["url"] for img in result["images"] if "url" in img]
            
            return AIResponse(
                success=True,
                content=image_urls,
                usage=AIUsage(images_generated=len(image_urls)),
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                raw_response=result
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = classify_error(e, self.provider_name)
            logger.error(f"[FAL] Image-to-image error: {e}")
            
            return AIResponse(
                success=False,
                content=[],
                error=str(e),
                error_type=error_type,
                provider=self.provider_name,
                model=model,
                latency_ms=latency_ms
            )
