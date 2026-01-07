"""
Shared AI Service Layer - Abstractions for AI providers.

This module provides:
- Abstract interfaces for text and image AI services
- Standardized request/response types
- Provider-agnostic error handling
- Common data structures for AI operations

@module shared.ai
@version 1.0.0
"""

from .interfaces import (
    ITextAIService,
    IImageAIService,
)

from .types import (
    AICallType,
    AIMessage,
    AIUsage,
    AIResponse,
    AIErrorType,
    classify_error,
)

__all__ = [
    # Interfaces
    "ITextAIService",
    "IImageAIService",
    "AICallType",
    # Types
    "AIMessage",
    "AIUsage",
    "AIResponse",
    "AIErrorType",
    "classify_error",
]
