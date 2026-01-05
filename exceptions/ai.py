"""
AI Generation Exceptions

@module exceptions.ai
@version 3.24
"""

from typing import Optional
from .base import AppException, ErrorCode


class AIGenerationException(AppException):
    """500: AI generation failed."""
    status_code = 500
    default_code = ErrorCode.AI_GENERATION_FAILED
    default_message = "AI generation failed"
    
    def __init__(self, reason: str = None, provider: str = None, **kwargs):
        message = "AI generation failed"
        if reason:
            message = f"AI generation failed: {reason}"
        super().__init__(
            message=message,
            context={"reason": reason, "provider": provider},
            **kwargs
        )


class AIProviderTimeoutException(AppException):
    """504: AI provider timed out."""
    status_code = 504
    default_code = ErrorCode.AI_PROVIDER_TIMEOUT
    default_message = "AI service timed out. Please try again."
    
    def __init__(self, provider: str = None, timeout_seconds: int = None, **kwargs):
        message = "AI service timed out. Please try again."
        super().__init__(
            message=message,
            context={"provider": provider, "timeout_seconds": timeout_seconds},
            **kwargs
        )


class AIProviderErrorException(AppException):
    """502: AI provider returned an error."""
    status_code = 502
    default_code = ErrorCode.AI_PROVIDER_ERROR
    default_message = "AI service is temporarily unavailable"
    
    def __init__(self, provider: str = None, error: str = None, **kwargs):
        message = "AI service is temporarily unavailable"
        super().__init__(
            message=message,
            context={"provider": provider, "error": error},
            **kwargs
        )


class ContentPolicyViolationException(AppException):
    """400: Content violates safety policy."""
    status_code = 400
    default_code = ErrorCode.AI_CONTENT_POLICY
    default_message = "Your request was flagged as potentially inappropriate"
    
    def __init__(self, reason: str = None, **kwargs):
        message = "Your request was flagged as potentially inappropriate. Please modify your prompt."
        super().__init__(
            message=message,
            context={"reason": reason},
            details={"policy_violation": True},
            **kwargs
        )
