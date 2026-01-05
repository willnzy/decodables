"""
Unified Text Service
统一文本服务

Provides a single interface for all text/chat AI operations.
Handles:
- Model configuration
- Canary releases
- Caching
- Usage tracking
- Fallback handling
"""

import time
import logging
from typing import List, Dict, Optional, Any

from .model_config import (
    get_text_model_config,
    get_admin_model_config,
    ModelConfig,
)
from .canary import should_use_canary
from .usage_tracker import track_ai_usage, estimate_text_cost
from .adapters import get_text_adapter
from .base import (
    TextCompletionResult,
    AIAdapterError,
    AIRateLimitError,
)
from ..cache import cache_service

logger = logging.getLogger(__name__)


class UnifiedTextService:
    """
    Unified text completion service.
    
    Provides a single interface for all text/chat operations,
    abstracting away provider details and handling:
    - Dynamic model selection
    - Canary releases
    - Caching (for identical prompts)
    - Usage tracking
    - Automatic fallback
    
    Usage:
        >>> from services.ai.unified_text_service import unified_text
        >>> result = await unified_text.chat([
        ...     {"role": "user", "content": "Hello!"}
        ... ])
        >>> print(result.content)
    """
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        user_id: str = None,
        tier: str = "free",
        use_admin_model: bool = False,
        use_cache: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> TextCompletionResult:
        """
        Perform chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User identifier (for canary bucketing)
            tier: User tier ("free", "starter", "pro")
            use_admin_model: Use admin analysis model instead
            use_cache: Enable response caching
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            response_format: Response format (e.g., {"type": "json_object"})
            **kwargs: Additional provider-specific parameters
            
        Returns:
            TextCompletionResult with content and usage
        """
        start_time = time.time()
        
        # 1. Get model configuration
        if use_admin_model:
            config = get_admin_model_config()
        else:
            config = get_text_model_config()
        
        provider = config.provider
        model = config.model
        
        # 2. Check canary release
        if user_id and not use_admin_model:
            use_canary, canary_config = should_use_canary(
                user_id, "text_reasoning", tier
            )
            if use_canary and canary_config:
                provider = canary_config["provider"]
                model = canary_config["model"]
                logger.info(f"[UnifiedText] Using canary: {provider}/{model}")
        
        # 3. Check cache
        prompt_key = self._make_cache_key(messages, provider, model, kwargs)
        if use_cache:
            cached = cache_service.get_ai_result(prompt_key)
            if cached:
                logger.debug(f"[UnifiedText] Cache hit: {prompt_key[:16]}")
                return TextCompletionResult(
                    content=cached.get("content", ""),
                    usage=cached.get("usage", {}),
                    model=model,
                    provider=provider,
                    finish_reason="cached",
                )
        
        # 4. Call AI provider
        result = None
        success = False
        error_message = None
        
        try:
            adapter = get_text_adapter(provider)
            result = await adapter.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                **kwargs
            )
            success = True
            
        except AIAdapterError as e:
            error_message = str(e)
            logger.warning(f"[UnifiedText] Primary failed: {e}")
            
            # Try fallback
            if config.fallback_provider and config.fallback_model:
                try:
                    logger.info(
                        f"[UnifiedText] Trying fallback: "
                        f"{config.fallback_provider}/{config.fallback_model}"
                    )
                    fallback_adapter = get_text_adapter(config.fallback_provider)
                    result = await fallback_adapter.chat_completion(
                        messages=messages,
                        model=config.fallback_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format,
                        **kwargs
                    )
                    # Update provider/model to fallback
                    provider = config.fallback_provider
                    model = config.fallback_model
                    success = True
                    
                except Exception as fb_error:
                    logger.error(f"[UnifiedText] Fallback also failed: {fb_error}")
                    raise AIAdapterError(
                        f"Both primary and fallback failed: {error_message}",
                        provider=provider,
                        model=model
                    )
            else:
                raise
        
        # 5. Track usage
        latency_ms = int((time.time() - start_time) * 1000)
        input_tokens = result.usage.input_tokens if result else 0
        output_tokens = result.usage.output_tokens if result else 0
        cost = estimate_text_cost(provider, model, input_tokens, output_tokens)
        
        await track_ai_usage(
            provider=provider,
            model=model,
            call_type="text",
            success=success,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )
        
        # 6. Cache result
        if use_cache and result:
            cache_service.set_ai_result(
                prompt_key,
                {
                    "content": result.content,
                    "usage": result.usage.to_dict(),
                },
                ttl=86400  # 24 hours
            )
        
        return result
    
    async def chat_simple(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> str:
        """
        Simple chat interface for single-turn conversations.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters for chat()
            
        Returns:
            Response content string
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        result = await self.chat(messages, **kwargs)
        return result.content
    
    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict:
        """
        Chat with JSON response format.
        
        Args:
            messages: Message list
            **kwargs: Additional parameters
            
        Returns:
            Parsed JSON response
        """
        import json
        
        kwargs["response_format"] = {"type": "json_object"}
        result = await self.chat(messages, **kwargs)
        
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            logger.warning("[UnifiedText] Failed to parse JSON response")
            return {"error": "Invalid JSON", "raw": result.content}
    
    def _make_cache_key(
        self,
        messages: List[Dict],
        provider: str,
        model: str,
        kwargs: Dict
    ) -> str:
        """Generate cache key for request."""
        import json
        
        # Create deterministic string from request
        prompt_str = json.dumps(messages, sort_keys=True)
        params_str = json.dumps(kwargs, sort_keys=True)
        
        return cache_service.get_ai_hash(
            prompt=prompt_str,
            model=f"{provider}/{model}",
            params={"kwargs": params_str}
        )


# Module-level singleton
unified_text = UnifiedTextService()


# Convenience function
async def chat(
    messages: List[Dict[str, str]],
    **kwargs
) -> TextCompletionResult:
    """
    Convenience function for unified_text.chat().
    
    Usage:
        >>> from services.ai.unified_text_service import chat
        >>> result = await chat([{"role": "user", "content": "Hello"}])
    """
    return await unified_text.chat(messages, **kwargs)
