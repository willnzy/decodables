"""
AI Service Interfaces - Abstract base classes for AI providers.

Defines the contracts that all AI service providers must implement.
This enables dependency inversion: domains depend on these abstractions,
not on concrete implementations.

Migrated from services/ai/base.py to establish shared layer.

@module shared.ai.interfaces
@version 1.0.0
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from .types import AIResponse


# ==========================================
# Abstract Interfaces
# ==========================================

class ITextAIService(ABC):
    """
    Abstract interface for text AI services.

    All text AI providers (OpenAI, Qwen, Gemini, etc.) must implement
    this interface to be compatible with the domain layer.
    """

    provider_name: str = "base"

    @abstractmethod
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
        Generate chat completion.

        Args:
            messages: Conversation messages [{"role": "user", "content": "..."}]
            model: Model name/identifier
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum output tokens
            response_format: Response format specification (e.g., {"type": "json_object"})
            **kwargs: Provider-specific parameters

        Returns:
            AIResponse with text content

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    def is_available(self) -> bool:
        """
        Check if provider is available (e.g., API key configured).

        Returns:
            True if provider can be used
        """
        return True


class IImageAIService(ABC):
    """
    Abstract interface for image AI services.

    All image AI providers (FAL, DALL-E, Stable Diffusion, etc.) must
    implement this interface to be compatible with the domain layer.
    """

    provider_name: str = "base"

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        model: str,
        size: str = "1024x1024",
        num_images: int = 1,
        negative_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """
        Generate images from text prompt.

        Args:
            prompt: Image description
            model: Model name/identifier
            size: Image dimensions (e.g., "1024x1024")
            num_images: Number of images to generate
            negative_prompt: Negative prompt (what to avoid)
            **kwargs: Provider-specific parameters

        Returns:
            AIResponse with content as list of image URLs

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    async def image_to_image(
        self,
        prompt: str,
        image_url: str,
        model: str,
        strength: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """
        Generate image based on reference image.

        Args:
            prompt: Modification description
            image_url: Reference image URL
            model: Model name/identifier
            strength: Influence strength of reference image (0-1)
            **kwargs: Provider-specific parameters

        Returns:
            AIResponse with content as list of image URLs

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    def is_available(self) -> bool:
        """
        Check if provider is available (e.g., API key configured).

        Returns:
            True if provider can be used
        """
        return True
