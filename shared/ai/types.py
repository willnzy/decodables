"""
AI Service Types - Common data structures for AI operations.

Migrated from services/ai/base.py to establish shared layer.

@module shared.ai.types
@version 1.0.0
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from enum import Enum


# ==========================================
# Enums
# ==========================================

class AICallType(str, Enum):
    """AI call type enumeration."""
    TEXT = "text"
    IMAGE = "image"


# ==========================================
# Data Classes
# ==========================================

@dataclass
class AIMessage:
    """
    Chat message structure.

    Attributes:
        role: Message role ("system", "user", "assistant")
        content: Message content
    """
    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for API calls."""
        return {"role": self.role, "content": self.content}


@dataclass
class AIUsage:
    """
    Token/resource usage tracking.

    Attributes:
        input_tokens: Number of input tokens consumed
        output_tokens: Number of output tokens generated
        total_tokens: Total tokens (input + output)
        images_generated: Number of images generated
    """
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    images_generated: int = 0

    @property
    def total(self) -> int:
        """Calculate total usage (tokens or images)."""
        return self.total_tokens or (self.input_tokens + self.output_tokens)


@dataclass
class AIResponse:
    """
    Unified AI response format across all providers.

    Attributes:
        success: Whether the operation succeeded
        content: Response content (text or list of image URLs)
        usage: Resource usage information
        model: Actual model used
        provider: Provider that handled the request
        latency_ms: Response latency in milliseconds
        raw_response: Raw provider response (for debugging)
        error: Error message if failed
        error_type: Standardized error type
    """
    success: bool
    content: Union[str, List[str]] = ""
    usage: AIUsage = field(default_factory=AIUsage)
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    raw_response: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None

    @classmethod
    def from_error(
        cls,
        error: str,
        error_type: str = "unknown",
        provider: str = "",
        model: str = ""
    ) -> "AIResponse":
        """
        Create an error response.

        Args:
            error: Error message
            error_type: Standardized error type
            provider: Provider name
            model: Model name

        Returns:
            AIResponse with success=False
        """
        return cls(
            success=False,
            error=error,
            error_type=error_type,
            provider=provider,
            model=model
        )


# ==========================================
# Error Types
# ==========================================

class AIErrorType:
    """Standardized error type constants."""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    AUTH_ERROR = "auth_error"
    INVALID_REQUEST = "invalid_request"
    MODEL_NOT_FOUND = "model_not_found"
    CONTENT_FILTER = "content_filter"
    QUOTA_EXCEEDED = "quota_exceeded"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


def classify_error(exception: Exception, provider: str = "") -> str:
    """
    Classify exception into standardized error type.

    Args:
        exception: Caught exception
        provider: Provider name (for context)

    Returns:
        Standardized error type string
    """
    error_str = str(exception).lower()
    exception_type = type(exception).__name__.lower()

    # Rate limiting
    if any(x in error_str for x in ["rate limit", "rate_limit", "429", "too many requests"]):
        return AIErrorType.RATE_LIMIT

    # Timeout
    if any(x in error_str for x in ["timeout", "timed out"]) or "timeout" in exception_type:
        return AIErrorType.TIMEOUT

    # Authentication
    if any(x in error_str for x in ["auth", "api key", "unauthorized", "401", "403"]):
        return AIErrorType.AUTH_ERROR

    # Content filter
    if any(x in error_str for x in ["content filter", "safety", "blocked", "nsfw"]):
        return AIErrorType.CONTENT_FILTER

    # Quota
    if any(x in error_str for x in ["quota", "insufficient", "credit"]):
        return AIErrorType.QUOTA_EXCEEDED

    # Model not found
    if any(x in error_str for x in ["model not found", "model_not_found", "invalid model"]):
        return AIErrorType.MODEL_NOT_FOUND

    # Invalid request
    if any(x in error_str for x in ["invalid", "bad request", "400"]):
        return AIErrorType.INVALID_REQUEST

    # Network
    if any(x in error_str for x in ["connection", "network", "dns"]) or "connection" in exception_type:
        return AIErrorType.NETWORK_ERROR

    # API error (500s)
    if any(x in error_str for x in ["500", "502", "503", "504", "internal"]):
        return AIErrorType.API_ERROR

    return AIErrorType.UNKNOWN
