"""
System Configuration Service
系统配置服务 - 管理动态限频和系统参数
"""

import os
import json
from typing import Optional, Dict, Any, List
from functools import lru_cache
from datetime import datetime, timedelta
import threading

# Supabase client
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # Service role key

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 配置缓存
_config_cache: Dict[str, Any] = {}
_cache_timestamp: Dict[str, datetime] = {}
_cache_lock = threading.Lock()
CACHE_TTL_SECONDS = 60  # 缓存60秒

# 默认限频配置（用于数据库不可用时的回退）
DEFAULT_RATE_LIMITS = {
    # 支付相关
    "rate_limit.payment.checkout": {"limit": 5, "window": "minute", "enabled": True},
    "rate_limit.payment.portal": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.marketplace.purchase": {"limit": 10, "window": "minute", "enabled": True},
    
    # AI 生成
    "rate_limit.generate.story": {"limit": 20, "window": "minute", "enabled": True},
    "rate_limit.generate.images": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.tools.ocr": {"limit": 10, "window": "minute", "enabled": True},
    
    # 导出
    "rate_limit.export.pdf": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.export.zip": {"limit": 5, "window": "minute", "enabled": True},
    "rate_limit.export.preview": {"limit": 20, "window": "minute", "enabled": True},
    
    # 用户操作
    "rate_limit.projects.create": {"limit": 20, "window": "minute", "enabled": True},
    "rate_limit.assets.upload": {"limit": 20, "window": "minute", "enabled": True},
    "rate_limit.marketplace.publish": {"limit": 10, "window": "minute", "enabled": True},
    
    # 公开接口
    "rate_limit.support.email": {"limit": 3, "window": "minute", "enabled": True},
    "rate_limit.contact.form": {"limit": 3, "window": "minute", "enabled": True},
    "rate_limit.feedback.submit": {"limit": 3, "window": "minute", "enabled": True},
    
    # Admin
    "rate_limit.admin.credits": {"limit": 30, "window": "minute", "enabled": True},
    "rate_limit.admin.tier": {"limit": 30, "window": "minute", "enabled": True},
    "rate_limit.admin.refund": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.admin.subscription": {"limit": 10, "window": "minute", "enabled": True},
    "rate_limit.admin.broadcast": {"limit": 5, "window": "minute", "enabled": True},
    
    # 查询
    "rate_limit.admin.search": {"limit": 60, "window": "minute", "enabled": True},
    "rate_limit.marketplace.list": {"limit": 60, "window": "minute", "enabled": True},
    "rate_limit.analytics.events": {"limit": 60, "window": "minute", "enabled": True},
    
    # 全局
    "rate_limit.global.default": {"limit": 100, "window": "minute", "enabled": True},
    "rate_limit.global.enabled": {"enabled": True},
}


def get_config(config_key: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    获取系统配置
    
    Args:
        config_key: 配置键名
        use_cache: 是否使用缓存
        
    Returns:
        配置值（字典）或 None
    """
    global _config_cache, _cache_timestamp
    
    # 检查缓存
    if use_cache:
        with _cache_lock:
            if config_key in _config_cache:
                cache_time = _cache_timestamp.get(config_key)
                if cache_time and (datetime.now() - cache_time).total_seconds() < CACHE_TTL_SECONDS:
                    return _config_cache[config_key]
    
    # 从数据库获取
    if supabase:
        try:
            result = supabase.table("system_config")\
                .select("config_value, is_active")\
                .eq("config_key", config_key)\
                .single()\
                .execute()
            
            if result.data and result.data.get("is_active"):
                config_value = result.data["config_value"]
                
                # 更新缓存
                with _cache_lock:
                    _config_cache[config_key] = config_value
                    _cache_timestamp[config_key] = datetime.now()
                
                return config_value
        except Exception as e:
            print(f"[ConfigService] Error fetching config {config_key}: {e}")
    
    # 回退到默认值
    return DEFAULT_RATE_LIMITS.get(config_key)


def set_config(config_key: str, config_value: Dict[str, Any], updated_by: str = None) -> bool:
    """
    设置系统配置
    
    Args:
        config_key: 配置键名
        config_value: 配置值
        updated_by: 更新者ID
        
    Returns:
        是否成功
    """
    global _config_cache, _cache_timestamp
    
    if not supabase:
        print("[ConfigService] Supabase not configured")
        return False
    
    try:
        result = supabase.table("system_config")\
            .update({
                "config_value": config_value,
                "updated_by": updated_by
            })\
            .eq("config_key", config_key)\
            .execute()
        
        # 清除缓存
        with _cache_lock:
            if config_key in _config_cache:
                del _config_cache[config_key]
            if config_key in _cache_timestamp:
                del _cache_timestamp[config_key]
        
        return True
    except Exception as e:
        print(f"[ConfigService] Error setting config {config_key}: {e}")
        return False


def get_all_configs(category: str = None) -> List[Dict[str, Any]]:
    """
    获取所有配置
    
    Args:
        category: 可选，按分类筛选
        
    Returns:
        配置列表
    """
    if not supabase:
        # 返回默认配置
        configs = []
        for key, value in DEFAULT_RATE_LIMITS.items():
            if category is None or key.startswith(f"{category}."):
                configs.append({
                    "config_key": key,
                    "config_value": value,
                    "category": key.split(".")[0] + "." + key.split(".")[1] if "." in key else "general",
                    "is_active": True
                })
        return configs
    
    try:
        query = supabase.table("system_config").select("*")
        if category:
            query = query.eq("category", category)
        
        result = query.order("config_key").execute()
        return result.data or []
    except Exception as e:
        print(f"[ConfigService] Error fetching configs: {e}")
        return []


def get_rate_limit_string(config_key: str) -> str:
    """
    获取 slowapi 格式的限频字符串
    
    Args:
        config_key: 配置键名
        
    Returns:
        格式如 "10/minute"
    """
    config = get_config(config_key)
    if not config or not config.get("enabled", True):
        # 如果禁用，返回一个很高的限制
        return "10000/minute"
    
    limit = config.get("limit", 100)
    window = config.get("window", "minute")
    
    return f"{limit}/{window}"


def is_rate_limit_enabled(config_key: str = None) -> bool:
    """
    检查限频是否启用
    
    Args:
        config_key: 可选，特定接口的配置键
        
    Returns:
        是否启用
    """
    # 检查全局开关
    global_config = get_config("rate_limit.global.enabled")
    if global_config and not global_config.get("enabled", True):
        return False
    
    # 检查特定接口
    if config_key:
        config = get_config(config_key)
        if config and not config.get("enabled", True):
            return False
    
    return True


def clear_config_cache():
    """清除所有配置缓存"""
    global _config_cache, _cache_timestamp
    with _cache_lock:
        _config_cache.clear()
        _cache_timestamp.clear()


def batch_update_configs(updates: List[Dict[str, Any]], updated_by: str = None) -> Dict[str, bool]:
    """
    批量更新配置
    
    Args:
        updates: [{"config_key": "...", "config_value": {...}}, ...]
        updated_by: 更新者ID
        
    Returns:
        {"config_key": success_bool, ...}
    """
    results = {}
    for update in updates:
        config_key = update.get("config_key")
        config_value = update.get("config_value")
        if config_key and config_value is not None:
            results[config_key] = set_config(config_key, config_value, updated_by)
    
    return results


# 预设配置模板
RATE_LIMIT_PRESETS = {
    "strict": {
        "description": "严格模式 - 所有限频减半",
        "multiplier": 0.5
    },
    "normal": {
        "description": "正常模式 - 默认设置",
        "multiplier": 1.0
    },
    "relaxed": {
        "description": "宽松模式 - 所有限频翻倍",
        "multiplier": 2.0
    },
    "disabled": {
        "description": "禁用模式 - 关闭所有限频",
        "enabled": False
    }
}


def apply_rate_limit_preset(preset_name: str, updated_by: str = None) -> bool:
    """
    应用预设配置
    
    Args:
        preset_name: 预设名称
        updated_by: 更新者ID
        
    Returns:
        是否成功
    """
    preset = RATE_LIMIT_PRESETS.get(preset_name)
    if not preset:
        return False
    
    if preset.get("enabled") is False:
        # 禁用全局限频
        return set_config("rate_limit.global.enabled", {"enabled": False}, updated_by)
    
    # 启用全局限频
    set_config("rate_limit.global.enabled", {"enabled": True}, updated_by)
    
    multiplier = preset.get("multiplier", 1.0)
    if multiplier == 1.0:
        # 恢复默认值
        for key, value in DEFAULT_RATE_LIMITS.items():
            if key.startswith("rate_limit.") and key != "rate_limit.global.enabled":
                set_config(key, value, updated_by)
    else:
        # 应用倍率
        configs = get_all_configs("rate_limit")
        for config in configs:
            key = config["config_key"]
            if key != "rate_limit.global.enabled" and key != "rate_limit.global.default":
                value = config["config_value"]
                if "limit" in value:
                    new_limit = max(1, int(value["limit"] * multiplier))
                    set_config(key, {**value, "limit": new_limit}, updated_by)
    
    # 清除缓存
    clear_config_cache()
    return True

