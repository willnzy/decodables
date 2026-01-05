"""
Qwen (通义千问) Adapter
阿里云通义千问适配器

Supports:
- qwen-turbo (fast)
- qwen-plus (balanced)
- qwen-max (powerful)

Note: Requires DASHSCOPE_API_KEY environment variable.
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
)

logger = logging.getLogger(__name__)

# API Key (阿里云 DashScope)
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY")


class QwenTextAdapter(BaseTextAdapter):
    """
    Qwen (通义千问) text adapter.
    
    Uses Alibaba Cloud DashScope API.
    
    Supports models:
    - qwen-turbo: Fast, cost-effective
    - qwen-plus: Balanced performance
    - qwen-max: Most powerful
    """
    
    provider = AIProviderType.QWEN
    
    SUPPORTED_MODELS = [
        "qwen-turbo",
        "qwen-plus",
        "qwen-max",
        "qwen-max-longcontext",
    ]
    
    def __init__(self):
        self._available = False
        if DASHSCOPE_API_KEY:
            try:
                import dashscope
                dashscope.api_key = DASHSCOPE_API_KEY
                self._dashscope = dashscope
                self._available = True
            except ImportError:
                logger.warning("[Qwen] dashscope package not installed")
    
    def is_available(self) -> bool:
        return self._available
    
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
        Perform chat completion using Qwen.
        """
        if not self._available:
            raise AIAuthenticationError(
                "DashScope API key not configured or dashscope not installed",
                provider="qwen"
            )
        
        try:
            from dashscope import Generation
            import asyncio
            
            # Build params
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "result_format": "message",
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Run in thread pool (dashscope is sync)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: Generation.call(**params)
            )
            
            # Check for errors
            if response.status_code != 200:
                raise AIAdapterError(
                    f"Qwen error: {response.message}",
                    provider="qwen",
                    model=model
                )
            
            # Extract result
            content = response.output.choices[0].message.content
            
            usage = TextUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.total_tokens,
            )
            
            return TextCompletionResult(
                content=content,
                usage=usage,
                model=model,
                provider="qwen",
                finish_reason="stop",
            )
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "rate limit" in error_str or "throttl" in error_str:
                raise AIRateLimitError(
                    f"Qwen rate limit: {e}",
                    provider="qwen"
                )
            elif "auth" in error_str or "key" in error_str:
                raise AIAuthenticationError(
                    f"Qwen auth error: {e}",
                    provider="qwen"
                )
            elif "timeout" in error_str:
                raise AITimeoutError(
                    f"Qwen timeout: {e}",
                    provider="qwen"
                )
            
            logger.error(f"[Qwen] Unexpected error: {e}")
            raise AIAdapterError(
                f"Qwen error: {e}",
                provider="qwen",
                model=model,
                retryable=True
            )
