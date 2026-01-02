"""
Dynamic Rate Limiter
动态速率限制器 - 从数据库读取配置
"""

import json
from functools import wraps
from typing import Callable, Optional
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from config_service import get_rate_limit_string, is_rate_limit_enabled, get_config


def create_dynamic_limiter():
    """"""
    return Limiter(key_func=get_remote_address)


# 
limiter = create_dynamic_limiter()


def dynamic_limit(config_key: str):
    """
    
    
    ，
    
    Args:
        config_key: ， "rate_limit.payment.checkout"
    
    Usage:
        @app.post("/api/payment/checkout")
        @dynamic_limit("rate_limit.payment.checkout")
        def pay(request: Request, ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(request: Request, *args, **kwargs):
            # 
            if not is_rate_limit_enabled(config_key):
                # ，
                return await func(request, *args, **kwargs)
            
            # 
            limit_string = get_rate_limit_string(config_key)
            
            #  slowapi 
            # ：， slowapi 
            from slowapi.util import get_remote_address
            from slowapi.errors import RateLimitExceeded
            
            key = get_remote_address(request)
            
            # 
            parts = limit_string.split("/")
            limit = int(parts[0])
            window = parts[1] if len(parts) > 1 else "minute"
            
            #  limiter 
            # ：
            try:
                # 
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
            # 
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
        
        # 
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def get_current_limits() -> dict:
    """
    （ API ）
    
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
        key = config.get("key")
        # value is TEXT in v3.10 schema, may need JSON parsing
        raw_value = config.get("value")
        try:
            value = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
        except:
            value = raw_value
        
        if key == "rate_limit.global.enabled":
            global_enabled = value.get("enabled", True) if isinstance(value, dict) else True
        else:
            limits[key] = value
    
    # ，
    if not limits:
        limits = {k: v for k, v in DEFAULT_RATE_LIMITS.items() if k != "rate_limit.global.enabled"}
    
    return {
        "global_enabled": global_enabled,
        "limits": limits
    }

