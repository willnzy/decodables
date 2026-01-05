"""
OpenAI Adapter
OpenAI 适配器

Supports:
- GPT-4o, GPT-4o-mini, o1, o1-mini (text)
- DALL-E 3 (image)
"""

import os
import logging
from typing import List, Dict, Optional
import openai

from ..base import (
    BaseTextAdapter,
    BaseImageAdapter,
    AIProviderType,
    TextCompletionResult,
    ImageGenerationResult,
    TextUsage,
    ImageUsage,
    AIAdapterError,
    AIRateLimitError,
    AIAuthenticationError,
    AITimeoutError,
    AIContentFilterError,
)

logger = logging.getLogger(__name__)

# API Key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class OpenAITextAdapter(BaseTextAdapter):
    """
    OpenAI text completion adapter.
    
    Supports models:
    - gpt-4o-mini (fast, cost-effective)
    - gpt-4o (powerful, multimodal)
    - o1-mini (reasoning, fast)
    - o1 (reasoning, advanced)
    """
    
    provider = AIProviderType.OPENAI
    
    SUPPORTED_MODELS = [
        "gpt-4o-mini",
        "gpt-4o",
        "o1-mini",
        "o1",
        "gpt-4-turbo",
    ]
    
    def __init__(self):
        self._client = None
        if OPENAI_API_KEY:
            self._client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    def is_available(self) -> bool:
        return self._client is not None
    
    def get_supported_models(self) -> List[str]:
        return self.SUPPORTED_MODELS.copy()
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> TextCompletionResult:
        """
        Perform chat completion using OpenAI API.
        """
        if not self._client:
            raise AIAuthenticationError(
                "OpenAI API key not configured",
                provider="openai"
            )
        
        try:
            # Build request params
            params = {
                "model": model,
                "messages": messages,
            }
            
            # o1 models have different parameter requirements
            if model.startswith("o1"):
                # o1 doesn't support temperature, max_tokens uses max_completion_tokens
                if max_tokens:
                    params["max_completion_tokens"] = max_tokens
            else:
                params["temperature"] = temperature
                if max_tokens:
                    params["max_tokens"] = max_tokens
                if response_format:
                    params["response_format"] = response_format
            
            # Make request
            response = await self._client.chat.completions.create(**params)
            
            # Extract result
            choice = response.choices[0]
            content = choice.message.content or ""
            
            usage = TextUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
            
            return TextCompletionResult(
                content=content,
                usage=usage,
                model=model,
                provider="openai",
                finish_reason=choice.finish_reason or "stop",
            )
            
        except openai.RateLimitError as e:
            raise AIRateLimitError(
                f"OpenAI rate limit: {e}",
                provider="openai"
            )
        except openai.AuthenticationError as e:
            raise AIAuthenticationError(
                f"OpenAI auth error: {e}",
                provider="openai"
            )
        except openai.APITimeoutError as e:
            raise AITimeoutError(
                f"OpenAI timeout: {e}",
                provider="openai"
            )
        except openai.BadRequestError as e:
            if "content_filter" in str(e).lower():
                raise AIContentFilterError(
                    f"Content filtered: {e}",
                    provider="openai"
                )
            raise AIAdapterError(
                f"OpenAI error: {e}",
                provider="openai",
                model=model
            )
        except Exception as e:
            logger.error(f"[OpenAI] Unexpected error: {e}")
            raise AIAdapterError(
                f"OpenAI error: {e}",
                provider="openai",
                model=model,
                retryable=True
            )


class OpenAIImageAdapter(BaseImageAdapter):
    """
    OpenAI image generation adapter (DALL-E 3).
    
    Supports models:
    - dall-e-3 (high quality)
    - dall-e-2 (legacy)
    """
    
    provider = AIProviderType.OPENAI
    
    SUPPORTED_MODELS = ["dall-e-3", "dall-e-2"]
    
    # Size mappings
    SIZE_MAPPING = {
        "1024x1024": "1024x1024",
        "1792x1024": "1792x1024",  # landscape
        "1024x1792": "1024x1792",  # portrait
        "landscape": "1792x1024",
        "portrait": "1024x1792",
        "square": "1024x1024",
    }
    
    def __init__(self):
        self._client = None
        if OPENAI_API_KEY:
            self._client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    def is_available(self) -> bool:
        return self._client is not None
    
    def get_supported_models(self) -> List[str]:
        return self.SUPPORTED_MODELS.copy()
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        num_images: int = 1,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate images using DALL-E.
        """
        if not self._client:
            raise AIAuthenticationError(
                "OpenAI API key not configured",
                provider="openai"
            )
        
        try:
            # Map size
            actual_size = self.SIZE_MAPPING.get(size, "1024x1024")
            
            # Build params
            params = {
                "model": model,
                "prompt": prompt,
                "size": actual_size,
                "n": min(num_images, 1) if model == "dall-e-3" else num_images,
                "quality": kwargs.get("quality", "standard"),
                "style": kwargs.get("style", "vivid"),
            }
            
            # Make request
            response = await self._client.images.generate(**params)
            
            # Extract URLs
            images = [img.url for img in response.data if img.url]
            
            return ImageGenerationResult(
                images=images,
                usage=ImageUsage(images_generated=len(images)),
                model=model,
                provider="openai",
            )
            
        except openai.RateLimitError as e:
            raise AIRateLimitError(
                f"OpenAI rate limit: {e}",
                provider="openai"
            )
        except openai.BadRequestError as e:
            if "content_policy" in str(e).lower():
                raise AIContentFilterError(
                    f"Content filtered: {e}",
                    provider="openai"
                )
            raise AIAdapterError(
                f"OpenAI error: {e}",
                provider="openai",
                model=model
            )
        except Exception as e:
            logger.error(f"[OpenAI Image] Unexpected error: {e}")
            raise AIAdapterError(
                f"OpenAI image error: {e}",
                provider="openai",
                model=model,
                retryable=True
            )
