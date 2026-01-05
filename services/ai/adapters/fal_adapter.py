"""
FAL AI Adapter
FAL AI 适配器

Supports Flux models for image generation:
- flux-schnell (fast, 4 steps)
- flux-dev (high quality, 28+ steps)
- flux-pro (professional)
"""

import os
import asyncio
import logging
from typing import List, Dict, Optional

from ..base import (
    BaseImageAdapter,
    AIProviderType,
    ImageGenerationResult,
    ImageUsage,
    AIAdapterError,
    AIRateLimitError,
    AIAuthenticationError,
    AITimeoutError,
    AIContentFilterError,
)

logger = logging.getLogger(__name__)

# FAL API Key
FAL_KEY = os.environ.get("FAL_KEY")


class FALImageAdapter(BaseImageAdapter):
    """
    FAL AI image generation adapter.
    
    Supports Flux models:
    - flux-schnell: Fast generation (4 steps), best for iteration
    - flux-dev: High quality (28+ steps), best for final output
    - flux-pro: Professional quality
    """
    
    provider = AIProviderType.FAL
    
    SUPPORTED_MODELS = [
        "flux-schnell",
        "flux-dev",
        "flux-pro",
        "flux-pro-v1.1",
    ]
    
    # Model to FAL endpoint mapping
    MODEL_ENDPOINTS = {
        "flux-schnell": "fal-ai/flux/schnell",
        "flux-dev": "fal-ai/flux/dev",
        "flux-pro": "fal-ai/flux-pro",
        "flux-pro-v1.1": "fal-ai/flux-pro/v1.1",
    }
    
    # Aspect ratio mappings
    ASPECT_RATIOS = {
        "square": "square",
        "1:1": "square",
        "landscape": "landscape_16_9",
        "16:9": "landscape_16_9",
        "portrait": "portrait_9_16",
        "9:16": "portrait_9_16",
        "4:3": "landscape_4_3",
        "3:4": "portrait_3_4",
    }
    
    def __init__(self):
        self._fal_client = None
        if FAL_KEY:
            try:
                import fal_client
                self._fal_client = fal_client
            except ImportError:
                logger.warning("[FAL] fal_client not installed")
    
    def is_available(self) -> bool:
        return self._fal_client is not None and FAL_KEY is not None
    
    def get_supported_models(self) -> List[str]:
        return self.SUPPORTED_MODELS.copy()
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "flux-schnell",
        size: str = "square",
        num_images: int = 1,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate images using FAL Flux models.
        
        Additional kwargs:
        - num_inference_steps: Number of denoising steps
        - guidance_scale: CFG scale (prompt adherence)
        - seed: Random seed for reproducibility
        - enable_safety_checker: Enable/disable NSFW filter
        """
        if not self._fal_client:
            raise AIAuthenticationError(
                "FAL API key not configured or fal_client not installed",
                provider="fal"
            )
        
        # Get endpoint
        endpoint = self.MODEL_ENDPOINTS.get(model)
        if not endpoint:
            raise AIAdapterError(
                f"Unsupported FAL model: {model}",
                provider="fal",
                model=model
            )
        
        try:
            # Map aspect ratio
            aspect_ratio = self.ASPECT_RATIOS.get(size, "square")
            
            # Build request
            request_params = {
                "prompt": prompt,
                "image_size": aspect_ratio,
                "num_images": num_images,
                "enable_safety_checker": kwargs.get("enable_safety_checker", True),
            }
            
            # Model-specific parameters
            if model in ["flux-dev", "flux-pro", "flux-pro-v1.1"]:
                request_params["num_inference_steps"] = kwargs.get(
                    "num_inference_steps", 28
                )
                request_params["guidance_scale"] = kwargs.get(
                    "guidance_scale", 3.5
                )
            else:  # flux-schnell
                request_params["num_inference_steps"] = kwargs.get(
                    "num_inference_steps", 4
                )
            
            # Add seed if provided
            if "seed" in kwargs:
                request_params["seed"] = kwargs["seed"]
            
            # Run in thread pool (fal_client is sync)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._fal_client.subscribe(
                    endpoint,
                    arguments=request_params,
                    with_logs=False,
                )
            )
            
            # Extract images
            images = []
            if result and "images" in result:
                for img in result["images"]:
                    if isinstance(img, dict) and "url" in img:
                        images.append(img["url"])
                    elif isinstance(img, str):
                        images.append(img)
            
            if not images:
                raise AIAdapterError(
                    "FAL returned no images",
                    provider="fal",
                    model=model
                )
            
            return ImageGenerationResult(
                images=images,
                usage=ImageUsage(images_generated=len(images)),
                model=model,
                provider="fal",
            )
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "rate limit" in error_str or "429" in error_str:
                raise AIRateLimitError(
                    f"FAL rate limit: {e}",
                    provider="fal"
                )
            elif "unauthorized" in error_str or "401" in error_str:
                raise AIAuthenticationError(
                    f"FAL auth error: {e}",
                    provider="fal"
                )
            elif "timeout" in error_str:
                raise AITimeoutError(
                    f"FAL timeout: {e}",
                    provider="fal"
                )
            elif "nsfw" in error_str or "safety" in error_str:
                raise AIContentFilterError(
                    f"Content filtered: {e}",
                    provider="fal"
                )
            
            logger.error(f"[FAL] Unexpected error: {e}")
            raise AIAdapterError(
                f"FAL error: {e}",
                provider="fal",
                model=model,
                retryable=True
            )
    
    async def generate_with_reference(
        self,
        prompt: str,
        reference_image_url: str,
        model: str = "flux-dev",
        strength: float = 0.75,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate image with reference (image-to-image).
        
        Args:
            prompt: Text prompt
            reference_image_url: URL of reference image
            strength: How much to follow reference (0.0-1.0)
        """
        if not self._fal_client:
            raise AIAuthenticationError(
                "FAL API key not configured",
                provider="fal"
            )
        
        # Use flux-dev for img2img
        endpoint = "fal-ai/flux/dev/image-to-image"
        
        try:
            request_params = {
                "prompt": prompt,
                "image_url": reference_image_url,
                "strength": strength,
                "num_inference_steps": kwargs.get("num_inference_steps", 28),
                "guidance_scale": kwargs.get("guidance_scale", 3.5),
            }
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._fal_client.subscribe(
                    endpoint,
                    arguments=request_params,
                    with_logs=False,
                )
            )
            
            images = []
            if result and "images" in result:
                for img in result["images"]:
                    if isinstance(img, dict) and "url" in img:
                        images.append(img["url"])
            
            return ImageGenerationResult(
                images=images,
                usage=ImageUsage(images_generated=len(images)),
                model=model,
                provider="fal",
            )
            
        except Exception as e:
            logger.error(f"[FAL img2img] Error: {e}")
            raise AIAdapterError(
                f"FAL img2img error: {e}",
                provider="fal",
                model=model,
                retryable=True
            )
