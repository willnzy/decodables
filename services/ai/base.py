"""
AI Provider Base Classes
AI 提供商适配器基类

Provides abstract interfaces for:
- Text completion (chat)
- Image generation

All provider adapters must implement these interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AIProviderType(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    FAL = "fal"
    QWEN = "qwen"
    GEMINI = "gemini"
    GROK = "grok"
    JIMENG = "jimeng"
    ANTHROPIC = "anthropic"


class AICallType(str, Enum):
    """Types of AI calls"""
    TEXT = "text"
    IMAGE = "image"


@dataclass
class TextUsage:
    """Token usage for text completion"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class ImageUsage:
    """Usage for image generation"""
    images_generated: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "images_generated": self.images_generated,
        }


@dataclass
class TextCompletionResult:
    """Result of text completion"""
    content: str
    usage: TextUsage
    model: str
    provider: str
    finish_reason: str = "stop"
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "usage": self.usage.to_dict(),
            "model": self.model,
            "provider": self.provider,
            "finish_reason": self.finish_reason,
        }


@dataclass
class ImageGenerationResult:
    """Result of image generation"""
    images: List[str]  # URLs or base64 data
    usage: ImageUsage
    model: str
    provider: str
    
    def to_dict(self) -> Dict:
        return {
            "images": self.images,
            "usage": self.usage.to_dict(),
            "model": self.model,
            "provider": self.provider,
        }


class BaseTextAdapter(ABC):
    """
    Abstract base class for text completion adapters.
    
    All text/chat AI providers must implement this interface.
    """
    
    provider: AIProviderType
    
    @abstractmethod
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
        Perform chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (provider-specific)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            response_format: Response format (e.g., {"type": "json_object"})
            **kwargs: Provider-specific parameters
            
        Returns:
            TextCompletionResult with content and usage
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this adapter is properly configured.
        
        Returns:
            True if API key and other requirements are met
        """
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """
        Get list of supported models.
        
        Returns:
            List of model names
        """
        pass


class BaseImageAdapter(ABC):
    """
    Abstract base class for image generation adapters.
    
    All image generation AI providers must implement this interface.
    """
    
    provider: AIProviderType
    
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        model: str,
        size: str = "1024x1024",
        num_images: int = 1,
        **kwargs
    ) -> ImageGenerationResult:
        """
        Generate images from text prompt.
        
        Args:
            prompt: Text description of the image
            model: Model name (provider-specific)
            size: Image size (e.g., "1024x1024", "landscape", "portrait")
            num_images: Number of images to generate
            **kwargs: Provider-specific parameters
            
        Returns:
            ImageGenerationResult with image URLs and usage
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this adapter is properly configured.
        
        Returns:
            True if API key and other requirements are met
        """
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """
        Get list of supported models.
        
        Returns:
            List of model names
        """
        pass


class AIAdapterError(Exception):
    """Base exception for AI adapter errors"""
    
    def __init__(
        self,
        message: str,
        provider: str = None,
        model: str = None,
        retryable: bool = False
    ):
        self.message = message
        self.provider = provider
        self.model = model
        self.retryable = retryable
        super().__init__(message)


class AIRateLimitError(AIAdapterError):
    """Rate limit exceeded"""
    
    def __init__(self, message: str, provider: str = None, retry_after: int = None):
        super().__init__(message, provider=provider, retryable=True)
        self.retry_after = retry_after


class AIAuthenticationError(AIAdapterError):
    """Authentication/API key error"""
    
    def __init__(self, message: str, provider: str = None):
        super().__init__(message, provider=provider, retryable=False)


class AIModelNotFoundError(AIAdapterError):
    """Model not found or not available"""
    
    def __init__(self, message: str, provider: str = None, model: str = None):
        super().__init__(message, provider=provider, model=model, retryable=False)


class AITimeoutError(AIAdapterError):
    """Request timeout"""
    
    def __init__(self, message: str, provider: str = None, timeout: int = None):
        super().__init__(message, provider=provider, retryable=True)
        self.timeout = timeout


class AIContentFilterError(AIAdapterError):
    """Content filtered/blocked by provider"""
    
    def __init__(self, message: str, provider: str = None):
        super().__init__(message, provider=provider, retryable=False)
