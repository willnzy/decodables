"""
Unified Image AI Service
统一图像 AI 服务

Provides:
- Single entry point for all image AI operations
- Automatic model selection based on user tier
- Canary release support
- Usage tracking (no caching for images)
- Automatic fallback on errors
"""

import logging
from typing import List, Optional, Any, Dict

from .base import AIResponse, AIUsage, AIErrorType
from .adapters import get_image_adapter
from .model_config import (
    get_image_model_config,
    get_fallback_config,
    is_provider_enabled
)
from .canary import should_use_canary
from .usage_tracker import track_ai_usage

logger = logging.getLogger(__name__)


class UnifiedImageService:
    """
    统一图像 AI 服务
    
    集成了:
    - 模型配置管理 (按用户等级)
    - 灰度发布
    - 使用量追踪
    - 自动降级
    """
    
    async def generate(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        tier: str = "free",
        size: str = "landscape_4_3",
        num_images: int = 1,
        negative_prompt: Optional[str] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        **kwargs
    ) -> AIResponse:
        """
        统一图像生成接口
        
        Args:
            prompt: 图像描述
            user_id: 用户 ID (用于灰度分流和追踪)
            tier: 用户等级 (free, starter, pro)
            size: 图像尺寸 (landscape_4_3, square, portrait_4_3, etc.)
            num_images: 生成数量
            negative_prompt: 负面提示词
            num_inference_steps: 推理步数 (可选)
            guidance_scale: CFG 值 (可选)
            **kwargs: 其他参数
            
        Returns:
            AIResponse 对象，content 为图像 URL 列表
        """
        # 1. 获取模型配置 (基于用户等级)
        config = get_image_model_config(tier)
        provider = config.get("provider", "fal")
        model = config.get("model", "flux-schnell")
        
        # 2. 检查灰度
        is_canary = False
        if user_id:
            use_canary, canary_config = should_use_canary(user_id, "image_generation", tier)
            if use_canary and canary_config:
                provider = canary_config["provider"]
                model = canary_config["model"]
                is_canary = True
                logger.info(f"[UnifiedImage] Using canary: {provider}/{model}")
        
        # 3. 检查提供商是否启用
        if not is_provider_enabled(provider):
            logger.warning(f"[UnifiedImage] Provider not enabled: {provider}")
            # 尝试使用 fallback
            fallback = get_fallback_config(config)
            if fallback:
                provider = fallback["provider"]
                model = fallback["model"]
            else:
                return AIResponse.from_error(
                    f"Provider {provider} is not enabled",
                    AIErrorType.AUTH_ERROR,
                    provider,
                    model
                )
        
        # 4. 获取适配器
        adapter = get_image_adapter(provider)
        if not adapter:
            logger.error(f"[UnifiedImage] Adapter not available: {provider}")
            return await self._try_fallback(
                config, prompt, size, num_images, negative_prompt,
                num_inference_steps, guidance_scale, user_id, **kwargs
            )
        
        # 5. 调用 AI
        response = await adapter.generate_image(
            prompt=prompt,
            model=model,
            size=size,
            num_images=num_images,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            **kwargs
        )
        
        # 6. 追踪使用量 (异步)
        await track_ai_usage(
            provider=provider,
            model=model,
            call_type="image",
            success=response.success,
            images=len(response.content) if isinstance(response.content, list) else 0,
            latency_ms=response.latency_ms,
            error_type=response.error_type
        )
        
        # 7. 失败时尝试 fallback
        if not response.success and not is_canary:
            fallback_response = await self._try_fallback(
                config, prompt, size, num_images, negative_prompt,
                num_inference_steps, guidance_scale, user_id, **kwargs
            )
            if fallback_response.success:
                return fallback_response
        
        return response
    
    async def image_to_image(
        self,
        prompt: str,
        image_url: str,
        user_id: Optional[str] = None,
        tier: str = "free",
        strength: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """
        图生图接口
        
        Args:
            prompt: 图像描述
            image_url: 参考图像 URL
            user_id: 用户 ID
            tier: 用户等级
            strength: 参考强度 (0-1)
            **kwargs: 其他参数
            
        Returns:
            AIResponse 对象
        """
        # 获取配置 (图生图推荐使用 flux-dev)
        config = get_image_model_config(tier)
        provider = config.get("provider", "fal")
        
        # 图生图强制使用 flux-dev (质量更好)
        model = "flux-dev" if provider == "fal" else config.get("model")
        
        # 检查灰度
        if user_id:
            use_canary, canary_config = should_use_canary(user_id, "image_generation", tier)
            if use_canary and canary_config:
                provider = canary_config["provider"]
                model = canary_config["model"]
        
        # 获取适配器
        adapter = get_image_adapter(provider)
        if not adapter:
            return AIResponse.from_error(
                f"Adapter not available: {provider}",
                AIErrorType.AUTH_ERROR,
                provider,
                model
            )
        
        # 调用 AI
        response = await adapter.image_to_image(
            prompt=prompt,
            image_url=image_url,
            model=model,
            strength=strength,
            **kwargs
        )
        
        # 追踪使用量
        await track_ai_usage(
            provider=provider,
            model=model,
            call_type="image",
            success=response.success,
            images=len(response.content) if isinstance(response.content, list) else 0,
            latency_ms=response.latency_ms,
            error_type=response.error_type
        )
        
        return response
    
    async def _try_fallback(
        self,
        config: Dict[str, Any],
        prompt: str,
        size: str,
        num_images: int,
        negative_prompt: Optional[str],
        num_inference_steps: Optional[int],
        guidance_scale: Optional[float],
        user_id: Optional[str],
        **kwargs
    ) -> AIResponse:
        """
        尝试使用 fallback 模型
        """
        fallback = get_fallback_config(config)
        if not fallback:
            return AIResponse.from_error(
                "No fallback configured",
                AIErrorType.API_ERROR,
                config.get("provider", ""),
                config.get("model", "")
            )
        
        fb_provider = fallback["provider"]
        fb_model = fallback["model"]
        
        logger.info(f"[UnifiedImage] Trying fallback: {fb_provider}/{fb_model}")
        
        adapter = get_image_adapter(fb_provider)
        if not adapter:
            return AIResponse.from_error(
                f"Fallback adapter not available: {fb_provider}",
                AIErrorType.AUTH_ERROR,
                fb_provider,
                fb_model
            )
        
        response = await adapter.generate_image(
            prompt=prompt,
            model=fb_model,
            size=size,
            num_images=num_images,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            **kwargs
        )
        
        # 追踪 fallback 使用量
        await track_ai_usage(
            provider=fb_provider,
            model=fb_model,
            call_type="image",
            success=response.success,
            images=len(response.content) if isinstance(response.content, list) else 0,
            latency_ms=response.latency_ms,
            error_type=response.error_type
        )
        
        return response


# 单例
unified_image_service = UnifiedImageService()


# ==========================================
# Convenience Functions
# ==========================================

async def generate_image(
    prompt: str,
    user_id: Optional[str] = None,
    tier: str = "free",
    **kwargs
) -> AIResponse:
    """
    便捷函数: 生成图像
    """
    return await unified_image_service.generate(
        prompt=prompt,
        user_id=user_id,
        tier=tier,
        **kwargs
    )


async def image_to_image(
    prompt: str,
    image_url: str,
    user_id: Optional[str] = None,
    tier: str = "free",
    **kwargs
) -> AIResponse:
    """
    便捷函数: 图生图
    """
    return await unified_image_service.image_to_image(
        prompt=prompt,
        image_url=image_url,
        user_id=user_id,
        tier=tier,
        **kwargs
    )
