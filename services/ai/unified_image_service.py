"""
Unified Image Service
统一图像服务

Provides a single interface for all image generation operations.
Handles:
- Model configuration (tier-based)
- Canary releases
- Usage tracking
- Fallback handling
"""

import time
import logging
from typing import Optional, Dict, List

from .model_config import get_image_model_config, ModelConfig
from .canary import should_use_canary
from .usage_tracker import track_ai_usage, estimate_image_cost
from .adapters import get_image_adapter
from .base import (
    ImageGenerationResult,
    AIAdapterError,
)

logger = logging.getLogger(__name__)


class UnifiedImageService:
    """
    Unified image generation service.
    
    Provides a single interface for all image generation,
    abstracting away provider details and handling:
    - Tier-based model selection
    - Canary releases
    - Usage tracking
    - Automatic fallback
    
    Usage:
        >>> from services.ai.unified_image_service import unified_image
        >>> result = await unified_image.generate("A cute cat")
        >>> print(result.images[0])  # URL
    """
    
    async def generate(
        self,
        prompt: str,
        user_id: str = None,
        tier: str = "free",
        size: str = "square",
        num_images: int = 1,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate images from text prompt.
        
        Args:
            prompt: Text description of the image
            user_id: User identifier (for canary bucketing)
            tier: User tier ("free", "starter", "pro")
            size: Image size/aspect ("square", "landscape", "portrait")
            num_images: Number of images to generate
            **kwargs: Provider-specific parameters
                - num_inference_steps: Denoising steps
                - guidance_scale: CFG scale
                - seed: Random seed
                
        Returns:
            ImageGenerationResult with image URLs
        """
        start_time = time.time()
        
        # 1. Get model configuration based on tier
        config = get_image_model_config(tier)
        provider = config.provider
        model = config.model
        
        # 2. Check canary release
        if user_id:
            use_canary, canary_config = should_use_canary(
                user_id, "image_generation", tier
            )
            if use_canary and canary_config:
                provider = canary_config["provider"]
                model = canary_config["model"]
                logger.info(f"[UnifiedImage] Using canary: {provider}/{model}")
        
        # 3. Call AI provider
        result = None
        success = False
        
        try:
            adapter = get_image_adapter(provider)
            result = await adapter.generate_image(
                prompt=prompt,
                model=model,
                size=size,
                num_images=num_images,
                **kwargs
            )
            success = True
            
        except AIAdapterError as e:
            logger.warning(f"[UnifiedImage] Primary failed: {e}")
            
            # Try fallback
            if config.fallback_provider and config.fallback_model:
                try:
                    logger.info(
                        f"[UnifiedImage] Trying fallback: "
                        f"{config.fallback_provider}/{config.fallback_model}"
                    )
                    fallback_adapter = get_image_adapter(config.fallback_provider)
                    result = await fallback_adapter.generate_image(
                        prompt=prompt,
                        model=config.fallback_model,
                        size=size,
                        num_images=num_images,
                        **kwargs
                    )
                    provider = config.fallback_provider
                    model = config.fallback_model
                    success = True
                    
                except Exception as fb_error:
                    logger.error(f"[UnifiedImage] Fallback failed: {fb_error}")
                    raise
            else:
                raise
        
        # 4. Track usage
        latency_ms = int((time.time() - start_time) * 1000)
        images_count = len(result.images) if result else 0
        cost = estimate_image_cost(provider, model, images_count)
        
        await track_ai_usage(
            provider=provider,
            model=model,
            call_type="image",
            success=success,
            images=images_count,
            latency_ms=latency_ms,
            cost_usd=cost,
        )
        
        return result
    
    async def generate_with_params(
        self,
        prompt: str,
        user_id: str = None,
        tier: str = "free",
        size: str = "square",
        mode: str = "flexible",
        creativity_level: float = 0.3,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate images with generation mode parameters.
        
        This method translates generation mode and creativity level
        into provider-specific parameters.
        
        Args:
            prompt: Text description
            user_id: User identifier
            tier: User tier
            size: Image size
            mode: "guided" (accurate) or "flexible" (creative)
            creativity_level: 0.0-1.0 (only for flexible mode)
            **kwargs: Additional parameters
            
        Returns:
            ImageGenerationResult
        """
        # Get model config to determine which model we'll use
        config = get_image_model_config(tier)
        model = config.model
        
        # Translate mode to parameters
        if mode == "guided":
            # More accurate: higher CFG, more steps
            if "flux-dev" in model or "flux-pro" in model:
                kwargs.setdefault("num_inference_steps", 35)
                kwargs.setdefault("guidance_scale", 4.5)
            else:  # flux-schnell
                kwargs.setdefault("num_inference_steps", 4)
                kwargs.setdefault("guidance_scale", 3.5)
        else:  # flexible
            # More creative: lower CFG, adjusted by creativity level
            base_cfg = 2.5
            # Lower CFG = more creative
            adjusted_cfg = base_cfg - (creativity_level * 1.0)
            adjusted_cfg = max(1.5, adjusted_cfg)
            
            if "flux-dev" in model or "flux-pro" in model:
                kwargs.setdefault("num_inference_steps", 28)
            else:
                kwargs.setdefault("num_inference_steps", 4)
            
            kwargs.setdefault("guidance_scale", adjusted_cfg)
        
        return await self.generate(
            prompt=prompt,
            user_id=user_id,
            tier=tier,
            size=size,
            **kwargs
        )


# Module-level singleton
unified_image = UnifiedImageService()


# Convenience function
async def generate_image(
    prompt: str,
    **kwargs
) -> ImageGenerationResult:
    """
    Convenience function for unified_image.generate().
    
    Usage:
        >>> from services.ai.unified_image_service import generate_image
        >>> result = await generate_image("A sunset over mountains")
    """
    return await unified_image.generate(prompt, **kwargs)
