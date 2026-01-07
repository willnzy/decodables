"""
Unified Text AI Service
统一文本 AI 服务

Provides:
- Single entry point for all text AI operations
- Automatic model selection based on configuration
- Canary release support
- Caching and usage tracking
- Automatic fallback on errors
"""

import time
import logging
from typing import List, Dict, Optional, Any

from .base import AIResponse, AIUsage, AIErrorType
from .adapters import get_text_adapter
from .model_config import (
    get_text_model_config,
    get_admin_model_config,
    get_fallback_config,
    is_provider_enabled
)
from .canary import should_use_canary
from .ai_cache import get_cached_result, set_cached_result
from .usage_tracker import track_ai_usage

logger = logging.getLogger(__name__)


class UnifiedTextService:
    """
    统一文本 AI 服务
    
    集成了:
    - 模型配置管理
    - 灰度发布
    - 缓存
    - 使用量追踪
    - 自动降级
    """
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        user_id: Optional[str] = None,
        tier: str = "free",
        use_admin_model: bool = False,
        use_cache: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> AIResponse:
        """
        统一聊天接口
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            user_id: 用户 ID (用于灰度分流和追踪)
            tier: 用户等级 (free, starter, pro)
            use_admin_model: 是否使用 Admin 模型
            use_cache: 是否使用缓存
            temperature: 温度 (0-2)
            max_tokens: 最大输出 token 数
            response_format: 响应格式
            **kwargs: 其他参数
            
        Returns:
            AIResponse 对象
        """
        # 1. 获取模型配置
        if use_admin_model:
            config = get_admin_model_config()
        else:
            config = get_text_model_config()
        
        provider = config.get("provider", "openai")
        model = config.get("model", "gpt-4o-mini")
        
        # 2. 检查灰度 (仅用户模型)
        is_canary = False
        if user_id and not use_admin_model:
            use_canary, canary_config = should_use_canary(user_id, "text_reasoning", tier)
            if use_canary and canary_config:
                provider = canary_config["provider"]
                model = canary_config["model"]
                is_canary = True
                logger.info(f"[UnifiedText] Using canary: {provider}/{model}")
        
        # 3. 检查缓存
        prompt = messages[-1]["content"] if messages else ""
        if use_cache:
            cached = get_cached_result(
                provider, model, prompt, "text",
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
            if cached:
                logger.debug(f"[UnifiedText] Cache hit for {provider}/{model}")
                return AIResponse(
                    success=True,
                    content=cached,
                    model=model,
                    provider=provider,
                    usage=AIUsage()  # 缓存不消耗 token
                )
        
        # 4. 检查提供商是否启用
        if not is_provider_enabled(provider):
            logger.warning(f"[UnifiedText] Provider not enabled: {provider}")
            # 尝试使用 fallback
            fallback = get_fallback_config(config)
            if fallback:
                provider = fallback["provider"]
                model = fallback["model"]
            else:
                return AIResponse.from_error(
                    f"Provider {provider} is not enabled",
                    AIErrorType.AUTH_ERROR,
                    provider,
                    model
                )
        
        # 5. 获取适配器
        adapter = get_text_adapter(provider)
        if not adapter:
            logger.error(f"[UnifiedText] Adapter not available: {provider}")
            # 尝试 fallback
            return await self._try_fallback(
                config, messages, temperature, max_tokens, response_format, user_id, **kwargs
            )
        
        # 6. 调用 AI
        response = await adapter.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            **kwargs
        )
        
        # 7. 追踪使用量 (异步)
        await track_ai_usage(
            provider=provider,
            model=model,
            call_type="text",
            success=response.success,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=response.latency_ms,
            error_type=response.error_type
        )
        
        # 8. 缓存成功结果
        if response.success and use_cache and response.content:
            set_cached_result(
                provider, model, prompt, response.content, "text",
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
        
        # 9. 失败时尝试 fallback
        if not response.success and not is_canary:
            fallback_response = await self._try_fallback(
                config, messages, temperature, max_tokens, response_format, user_id, **kwargs
            )
            if fallback_response.success:
                return fallback_response
        
        return response
    
    async def _try_fallback(
        self,
        config: Dict[str, Any],
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[Dict],
        user_id: Optional[str],
        **kwargs
    ) -> AIResponse:
        """
        尝试使用 fallback 模型
        """
        fallback = get_fallback_config(config)
        if not fallback:
            return AIResponse.from_error(
                "No fallback configured",
                AIErrorType.API_ERROR,
                config.get("provider", ""),
                config.get("model", "")
            )
        
        fb_provider = fallback["provider"]
        fb_model = fallback["model"]
        
        logger.info(f"[UnifiedText] Trying fallback: {fb_provider}/{fb_model}")
        
        adapter = get_text_adapter(fb_provider)
        if not adapter:
            return AIResponse.from_error(
                f"Fallback adapter not available: {fb_provider}",
                AIErrorType.AUTH_ERROR,
                fb_provider,
                fb_model
            )
        
        response = await adapter.chat_completion(
            messages=messages,
            model=fb_model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            **kwargs
        )
        
        # 追踪 fallback 使用量
        await track_ai_usage(
            provider=fb_provider,
            model=fb_model,
            call_type="text",
            success=response.success,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=response.latency_ms,
            error_type=response.error_type
        )
        
        return response


# 单例
unified_text_service = UnifiedTextService()


# ==========================================
# Convenience Functions
# ==========================================

async def chat(
    messages: List[Dict[str, str]],
    user_id: Optional[str] = None,
    tier: str = "free",
    **kwargs
) -> AIResponse:
    """
    便捷函数: 用户文本聊天
    """
    return await unified_text_service.chat(
        messages=messages,
        user_id=user_id,
        tier=tier,
        use_admin_model=False,
        **kwargs
    )


async def admin_chat(
    messages: List[Dict[str, str]],
    **kwargs
) -> AIResponse:
    """
    便捷函数: Admin 分析聊天
    """
    return await unified_text_service.chat(
        messages=messages,
        use_admin_model=True,
        use_cache=False,  # Admin 分析通常不缓存
        **kwargs
    )
