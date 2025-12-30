"""
Dynamic Rate Limiter
动态限频器 - 从配置服务读取限频规则
"""

from functools import wraps
from typing import Callable, Optional
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from config_service import get_rate_limit_string, is_rate_limit_enabled, get_config


def create_dynamic_limiter():
    """创建动态限频器实例"""
    return Limiter(key_func=get_remote_address)


# 创建全局限频器实例
limiter = create_dynamic_limiter()


def dynamic_limit(config_key: str):
    """
    动态限频装饰器
    
    从配置服务读取限频规则，支持运行时动态调整
    
    Args:
        config_key: 配置键名，如 "rate_limit.payment.checkout"
    
    Usage:
        @app.post("/api/payment/checkout")
        @dynamic_limit("rate_limit.payment.checkout")
        def pay(request: Request, ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(request: Request, *args, **kwargs):
            # 检查是否启用限频
            if not is_rate_limit_enabled(config_key):
                # 限频已禁用，直接执行
                return await func(request, *args, **kwargs)
            
            # 获取限频配置
            limit_string = get_rate_limit_string(config_key)
            
            # 使用 slowapi 的限频逻辑
            # 注意：这里我们手动实现限频检查，因为 slowapi 的装饰器不支持动态值
            from slowapi.util import get_remote_address
            from slowapi.errors import RateLimitExceeded
            
            key = get_remote_address(request)
            
            # 解析限频字符串
            parts = limit_string.split("/")
            limit = int(parts[0])
            window = parts[1] if len(parts) > 1 else "minute"
            
            # 使用 limiter 的内部存储检查
            # 简化实现：使用装饰器方式
            try:
                # 动态应用限频
                limited_func = limiter.limit(limit_string)(func)
                return await limited_func(request, *args, **kwargs)
            except Exception as e:
                if "RateLimitExceeded" in str(type(e)):
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Please try again later. (Limit: {limit_string})"
                    )
                raise
        
        @wraps(func)
        def sync_wrapper(request: Request, *args, **kwargs):
            # 检查是否启用限频
            if not is_rate_limit_enabled(config_key):
                return func(request, *args, **kwargs)
            
            limit_string = get_rate_limit_string(config_key)
            
            try:
                limited_func = limiter.limit(limit_string)(func)
                return limited_func(request, *args, **kwargs)
            except Exception as e:
                if "RateLimitExceeded" in str(type(e)):
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded. Please try again later. (Limit: {limit_string})"
                    )
                raise
        
        # 判断是否是异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def get_current_limits() -> dict:
    """
    获取当前所有限频配置（用于 API 返回）
    
    Returns:
        {
            "global_enabled": True,
            "limits": {
                "rate_limit.payment.checkout": {"limit": 5, "window": "minute", "enabled": True},
                ...
            }
        }
    """
    from config_service import get_all_configs, DEFAULT_RATE_LIMITS
    
    configs = get_all_configs("rate_limit")
    
    limits = {}
    global_enabled = True
    
    for config in configs:
        key = config["config_key"]
        value = config["config_value"]
        
        if key == "rate_limit.global.enabled":
            global_enabled = value.get("enabled", True)
        else:
            limits[key] = value
    
    # 如果没有从数据库获取到，使用默认值
    if not limits:
        limits = {k: v for k, v in DEFAULT_RATE_LIMITS.items() if k != "rate_limit.global.enabled"}
    
    return {
        "global_enabled": global_enabled,
        "limits": limits
    }

