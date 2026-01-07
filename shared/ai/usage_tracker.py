"""
AI Usage Tracker
AI 使用量追踪器

Provides:
- Track AI API calls (async, non-blocking)
- Daily aggregation via database function
- Cost estimation
"""

import logging
import asyncio
from datetime import date, datetime, timezone
from typing import Optional
from decimal import Decimal

from core.database import supabase
from .model_config import get_model_cost

logger = logging.getLogger(__name__)


# ==========================================
# Usage Tracking
# ==========================================

async def track_ai_usage(
    provider: str,
    model: str,
    call_type: str,
    success: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    images: int = 0,
    latency_ms: int = 0,
    error_type: Optional[str] = None
):
    """
    追踪 AI 调用使用量 (异步，非阻塞)
    
    这个函数调用数据库的 upsert_ai_usage_daily 函数，
    将使用量写入日汇总表。
    
    Args:
        provider: 提供商名称 (openai, fal, qwen, etc.)
        model: 模型名称
        call_type: 调用类型 ('text' | 'image')
        success: 是否成功
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
        images: 生成的图像数
        latency_ms: 延迟毫秒数
        error_type: 错误类型 (如果失败)
    """
    try:
        today = date.today().isoformat()
        
        # 估算成本
        cost_usd = _estimate_cost(
            provider=provider,
            model=model,
            call_type=call_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            images=images
        )
        
        # 调用数据库函数
        if supabase:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: supabase.rpc("upsert_ai_usage_daily", {
                    "p_date": today,
                    "p_provider": provider,
                    "p_model": model,
                    "p_call_type": call_type,
                    "p_success": success,
                    "p_input_tokens": input_tokens,
                    "p_output_tokens": output_tokens,
                    "p_images": images,
                    "p_latency_ms": latency_ms,
                    "p_cost_usd": float(cost_usd),
                    "p_error_type": error_type
                }).execute()
            )
            
            logger.debug(
                f"[UsageTracker] Tracked: {provider}/{model} "
                f"{'✓' if success else '✗'} "
                f"tokens={input_tokens}+{output_tokens} "
                f"cost=${cost_usd:.4f}"
            )
        
    except Exception as e:
        # 非关键操作，仅记录错误
        logger.warning(f"[UsageTracker] Failed to track usage: {e}")


def track_ai_usage_sync(
    provider: str,
    model: str,
    call_type: str,
    success: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    images: int = 0,
    latency_ms: int = 0,
    error_type: Optional[str] = None
):
    """
    同步版本的使用量追踪
    
    用于非异步上下文。
    """
    try:
        today = date.today().isoformat()
        
        cost_usd = _estimate_cost(
            provider=provider,
            model=model,
            call_type=call_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            images=images
        )
        
        if supabase:
            supabase.rpc("upsert_ai_usage_daily", {
                "p_date": today,
                "p_provider": provider,
                "p_model": model,
                "p_call_type": call_type,
                "p_success": success,
                "p_input_tokens": input_tokens,
                "p_output_tokens": output_tokens,
                "p_images": images,
                "p_latency_ms": latency_ms,
                "p_cost_usd": float(cost_usd),
                "p_error_type": error_type
            }).execute()
            
    except Exception as e:
        logger.warning(f"[UsageTracker] Failed to track usage (sync): {e}")


def _estimate_cost(
    provider: str,
    model: str,
    call_type: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    images: int = 0
) -> Decimal:
    """
    估算 API 调用成本
    
    基于配置的成本参考值计算。
    文本模型: 成本 = (input_tokens + output_tokens) / 1M * cost_per_1M
    图像模型: 成本 = images * cost_per_image
    """
    cost_per_unit = get_model_cost(provider, model)
    
    if call_type == "text":
        # 文本模型: 按 token 计费 (cost 是 per 1M tokens)
        total_tokens = input_tokens + output_tokens
        cost = Decimal(str(cost_per_unit)) * Decimal(str(total_tokens)) / Decimal("1000000")
    else:
        # 图像模型: 按图像计费
        cost = Decimal(str(cost_per_unit)) * Decimal(str(images))
    
    return cost.quantize(Decimal("0.0001"))


# ==========================================
# Query Functions
# ==========================================

def get_usage_summary(days: int = 30) -> dict:
    """
    获取使用量汇总
    
    Args:
        days: 天数范围
        
    Returns:
        {
            "total_calls": 12345,
            "total_cost_usd": 156.78,
            "by_provider": {...},
            "by_model": {...}
        }
    """
    if not supabase:
        return {}
    
    try:
        # 使用视图查询
        result = supabase.from_("v_ai_usage_last_30_days").select("*").execute()
        
        if not result.data:
            return {
                "total_calls": 0,
                "total_cost_usd": 0,
                "by_provider": {},
                "by_model": {}
            }
        
        # 汇总
        total_calls = sum(row.get("total_calls", 0) for row in result.data)
        total_cost = sum(float(row.get("total_cost_usd", 0)) for row in result.data)
        
        # 按提供商汇总
        by_provider = {}
        for row in result.data:
            provider = row.get("provider")
            if provider not in by_provider:
                by_provider[provider] = {"calls": 0, "cost_usd": 0}
            by_provider[provider]["calls"] += row.get("total_calls", 0)
            by_provider[provider]["cost_usd"] += float(row.get("total_cost_usd", 0))
        
        # 按模型汇总
        by_model = {}
        for row in result.data:
            model = row.get("model")
            if model not in by_model:
                by_model[model] = {"calls": 0, "cost_usd": 0}
            by_model[model]["calls"] += row.get("total_calls", 0)
            by_model[model]["cost_usd"] += float(row.get("total_cost_usd", 0))
        
        return {
            "total_calls": total_calls,
            "total_cost_usd": round(total_cost, 2),
            "by_provider": by_provider,
            "by_model": by_model,
            "details": result.data
        }
        
    except Exception as e:
        logger.error(f"[UsageTracker] Failed to get usage summary: {e}")
        return {}


def get_daily_trend(days: int = 30) -> list:
    """
    获取每日成本趋势
    
    Args:
        days: 天数范围
        
    Returns:
        [
            {"date": "2025-01-01", "cost_usd": 5.23, "calls": 456},
            ...
        ]
    """
    if not supabase:
        return []
    
    try:
        result = supabase.from_("v_ai_daily_cost_trend").select("*").execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[UsageTracker] Failed to get daily trend: {e}")
        return []
