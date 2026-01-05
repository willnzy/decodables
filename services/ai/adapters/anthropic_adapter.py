"""
Anthropic (Claude) Adapter
Anthropic Claude 适配器

Supports:
- claude-3-5-sonnet-latest (powerful, balanced)
- claude-3-5-haiku-latest (fast, cost-effective)
"""

import os
import logging
from typing import List, Dict, Optional

from ..base import (
    BaseTextAdapter,
    AIProviderType,
    TextCompletionResult,
    TextUsage,
    AIAdapterError,
    AIRateLimitError,
    AIAuthenticationError,
    AITimeoutError,
    AIContentFilterError,
)

logger = logging.getLogger(__name__)

# API Key
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


class AnthropicTextAdapter(BaseTextAdapter):
    """
    Anthropic Claude text adapter.
    
    Supports models:
    - claude-3-5-sonnet-latest (powerful)
    - claude-3-5-haiku-latest (fast)
    """
    
    provider = AIProviderType.ANTHROPIC
    
    SUPPORTED_MODELS = [
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-latest",
    ]
    
    def __init__(self):
        self._client = None
        if ANTHROPIC_API_KEY:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            except ImportError:
                logger.warning("[Anthropic] anthropic package not installed")
    
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
        Perform chat completion using Anthropic Claude.
        """
        if not self._client:
            raise AIAuthenticationError(
                "Anthropic API key not configured",
                provider="anthropic"
            )
        
        try:
            # Convert messages to Anthropic format
            # Anthropic uses separate system parameter
            system_message = None
            converted_messages = []
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    system_message = content
                else:
                    # Map assistant to assistant, user to user
                    converted_messages.append({
                        "role": role,
                        "content": content
                    })
            
            # Build params
            params = {
                "model": model,
                "messages": converted_messages,
                "max_tokens": max_tokens or 4096,
                "temperature": temperature,
            }
            
            if system_message:
                params["system"] = system_message
            
            # Make request
            response = await self._client.messages.create(**params)
            
            # Extract result
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text
            
            usage = TextUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )
            
            return TextCompletionResult(
                content=content,
                usage=usage,
                model=model,
                provider="anthropic",
                finish_reason=response.stop_reason or "stop",
            )
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "rate_limit" in error_str or "429" in error_str:
                raise AIRateLimitError(
                    f"Anthropic rate limit: {e}",
                    provider="anthropic"
                )
            elif "authentication" in error_str or "401" in error_str:
                raise AIAuthenticationError(
                    f"Anthropic auth error: {e}",
                    provider="anthropic"
                )
            elif "timeout" in error_str:
                raise AITimeoutError(
                    f"Anthropic timeout: {e}",
                    provider="anthropic"
                )
            
            logger.error(f"[Anthropic] Unexpected error: {e}")
            raise AIAdapterError(
                f"Anthropic error: {e}",
                provider="anthropic",
                model=model,
                retryable=True
            )
