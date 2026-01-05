"""
AI Result Caching
AI 结果缓存

Provides:
- Cache AI text results (24h TTL)
- No caching for images (each generation is unique)
- Integration with unified cache service
"""

import hashlib
import json
import logging
from typing import Optional, Any, Dict

from ..cache import cache_service, CacheTTL

logger = logging.getLogger(__name__)


# ==========================================
# Cache Configuration
# ==========================================

# TTL 配置 (秒)
AI_CACHE_TTL = {
    "text": CacheTTL.AI_TEXT,    # 24 hours
    "image": CacheTTL.AI_IMAGE,  # 0 (不缓存)
}


# ==========================================
# Cache Functions
# ==========================================

def generate_cache_key(
    provider: str,
    model: str,
    prompt: str,
    call_type: str = "text",
    **kwargs
) -> str:
    """
    生成缓存键
    
    基于 provider, model, prompt 和其他参数的哈希。
    
    Args:
        provider: 提供商名称
        model: 模型名称
        prompt: 提示词或消息内容
        call_type: 调用类型
        **kwargs: 其他影响结果的参数 (temperature, etc.)
        
    Returns:
        缓存键哈希
    """
    # 构建缓存内容字符串
    # 只包含影响结果的参数
    relevant_params = {
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "call_type": call_type,
    }
    
    # 添加其他影响结果的参数
    for key in ["temperature", "max_tokens", "response_format"]:
        if key in kwargs and kwargs[key] is not None:
            relevant_params[key] = kwargs[key]
    
    content = json.dumps(relevant_params, sort_keys=True)
    hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    return hash_value


def get_cached_result(
    provider: str,
    model: str,
    prompt: str,
    call_type: str = "text",
    **kwargs
) -> Optional[str]:
    """
    获取缓存的 AI 结果
    
    Args:
        provider: 提供商名称
        model: 模型名称
        prompt: 提示词
        call_type: 调用类型 ('text' | 'image')
        
    Returns:
        缓存的结果，如果不存在或已过期则返回 None
    """
    # 图像不缓存
    if call_type == "image":
        return None
    
    # TTL 为 0 不缓存
    ttl = AI_CACHE_TTL.get(call_type, 0)
    if ttl <= 0:
        return None
    
    hash_key = generate_cache_key(provider, model, prompt, call_type, **kwargs)
    
    try:
        result = cache_service.get_ai_result(hash_key)
        if result:
            logger.debug(f"[AICache] Cache HIT: {provider}/{model} key={hash_key[:8]}...")
            return result
        logger.debug(f"[AICache] Cache MISS: {provider}/{model} key={hash_key[:8]}...")
    except Exception as e:
        logger.warning(f"[AICache] Get cache error: {e}")
    
    return None


def set_cached_result(
    provider: str,
    model: str,
    prompt: str,
    result: str,
    call_type: str = "text",
    **kwargs
) -> bool:
    """
    设置 AI 结果缓存
    
    Args:
        provider: 提供商名称
        model: 模型名称
        prompt: 提示词
        result: AI 响应结果
        call_type: 调用类型
        
    Returns:
        是否成功
    """
    # 图像不缓存
    if call_type == "image":
        return False
    
    # TTL 为 0 不缓存
    ttl = AI_CACHE_TTL.get(call_type, 0)
    if ttl <= 0:
        return False
    
    hash_key = generate_cache_key(provider, model, prompt, call_type, **kwargs)
    
    try:
        success = cache_service.set_ai_result(hash_key, result, ttl)
        if success:
            logger.debug(f"[AICache] Cached: {provider}/{model} key={hash_key[:8]}... ttl={ttl}s")
        return success
    except Exception as e:
        logger.warning(f"[AICache] Set cache error: {e}")
        return False


def invalidate_ai_cache():
    """
    清除所有 AI 缓存
    
    用于配置变更后强制刷新。
    """
    try:
        from ..cache.cache_keys import CacheNamespace
        cache_service.delete_pattern(f"{CacheNamespace.AI}*")
        logger.info("[AICache] All AI cache invalidated")
    except Exception as e:
        logger.warning(f"[AICache] Invalidate cache error: {e}")


# ==========================================
# Cache-aware Wrapper
# ==========================================

async def with_cache(
    provider: str,
    model: str,
    prompt: str,
    call_type: str,
    fetch_func,
    use_cache: bool = True,
    **kwargs
) -> Any:
    """
    带缓存的 AI 调用包装器
    
    自动处理缓存读取和写入。
    
    Args:
        provider: 提供商名称
        model: 模型名称
        prompt: 提示词
        call_type: 调用类型
        fetch_func: 实际调用 AI 的异步函数
        use_cache: 是否使用缓存
        **kwargs: 传递给 fetch_func 的参数
        
    Returns:
        AI 响应结果
    """
    # 尝试从缓存获取
    if use_cache:
        cached = get_cached_result(provider, model, prompt, call_type, **kwargs)
        if cached is not None:
            return cached
    
    # 调用 AI
    result = await fetch_func(**kwargs)
    
    # 写入缓存
    if use_cache and result:
        set_cached_result(provider, model, prompt, result, call_type, **kwargs)
    
    return result
