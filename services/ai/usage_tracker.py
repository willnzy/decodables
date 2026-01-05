"""
AI Usage Tracker
AI 使用量追踪

Tracks AI API calls and aggregates to daily statistics.
Used for cost monitoring and usage analytics.
"""

import os
import logging
from datetime import date, datetime, timezone
from typing import Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

# Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    from supabase import create_client
    if not SUPABASE_URL.endswith('/'):
        SUPABASE_URL = SUPABASE_URL + '/'
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


async def track_ai_usage(
    provider: str,
    model: str,
    call_type: str,
    success: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    images: int = 0,
    latency_ms: int = 0,
    cost_usd: float = 0.0
):
    """
    Track an AI API call.
    
    This function writes to ai_usage_daily table using upsert.
    It's designed to be called after each AI operation.
    
    Args:
        provider: AI provider name (e.g., "openai", "fal")
        model: Model name (e.g., "gpt-4o-mini", "flux-schnell")
        call_type: Type of call ("text" or "image")
        success: Whether the call succeeded
        input_tokens: Number of input tokens (text only)
        output_tokens: Number of output tokens (text only)
        images: Number of images generated (image only)
        latency_ms: Request latency in milliseconds
        cost_usd: Estimated cost in USD
        
    Example:
        >>> await track_ai_usage(
        ...     provider="openai",
        ...     model="gpt-4o-mini",
        ...     call_type="text",
        ...     success=True,
        ...     input_tokens=150,
        ...     output_tokens=200,
        ...     latency_ms=320,
        ...     cost_usd=0.0005
        ... )
    """
    if not supabase:
        logger.warning("[UsageTracker] Supabase not configured, skipping tracking")
        return
    
    today = date.today().isoformat()
    
    try:
        # Use the upsert function we created in the migration
        result = supabase.rpc("upsert_ai_usage_daily", {
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
        }).execute()
        
        logger.debug(
            f"[UsageTracker] Tracked: {provider}/{model} "
            f"({'success' if success else 'failed'})"
        )
        
    except Exception as e:
        # Don't let tracking failures affect the main operation
        logger.error(f"[UsageTracker] Error tracking usage: {e}")


def track_ai_usage_sync(
    provider: str,
    model: str,
    call_type: str,
    success: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    images: int = 0,
    latency_ms: int = 0,
    cost_usd: float = 0.0
):
    """
    Synchronous version of track_ai_usage.
    
    For use in sync code paths.
    """
    if not supabase:
        return
    
    today = date.today().isoformat()
    
    try:
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
        }).execute()
        
    except Exception as e:
        logger.error(f"[UsageTracker] Error tracking usage: {e}")


# ==========================================
# Cost Estimation
# ==========================================

def estimate_text_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Estimate cost for a text completion.
    
    Args:
        provider: Provider name
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        
    Returns:
        Estimated cost in USD
    """
    from .model_config import get_model_cost
    
    # Get cost per 1M tokens
    cost_per_million = get_model_cost(provider, model)
    
    if cost_per_million <= 0:
        return 0.0
    
    # Calculate cost
    # Most providers charge differently for input vs output
    # For simplicity, we use average (can be refined per provider)
    total_tokens = input_tokens + output_tokens
    cost = (total_tokens / 1_000_000) * cost_per_million
    
    return round(cost, 6)


def estimate_image_cost(provider: str, model: str, num_images: int = 1) -> float:
    """
    Estimate cost for image generation.
    
    Args:
        provider: Provider name
        model: Model name
        num_images: Number of images generated
        
    Returns:
        Estimated cost in USD
    """
    from .model_config import get_model_cost
    
    # Get cost per image
    cost_per_image = get_model_cost(provider, model)
    
    if cost_per_image <= 0:
        return 0.0
    
    return round(cost_per_image * num_images, 6)


# ==========================================
# Usage Statistics (Admin)
# ==========================================

def get_usage_summary(days: int = 30) -> dict:
    """
    Get usage summary for the last N days.
    
    Args:
        days: Number of days to include
        
    Returns:
        Summary dict with totals and breakdowns
    """
    if not supabase:
        return {"error": "Database not configured"}
    
    from datetime import timedelta
    
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    try:
        result = supabase.table("ai_usage_daily")\
            .select("*")\
            .gte("date", start_date)\
            .order("date", desc=True)\
            .execute()
        
        if not result.data:
            return {
                "period_days": days,
                "total_calls": 0,
                "total_cost_usd": 0,
                "by_provider": {},
                "by_model": {},
            }
        
        # Aggregate
        total_calls = 0
        total_cost = 0.0
        successful_calls = 0
        by_provider = {}
        by_model = {}
        
        for row in result.data:
            calls = row.get("total_calls", 0)
            cost = float(row.get("estimated_cost_usd", 0) or 0)
            success = row.get("successful_calls", 0)
            provider = row.get("provider", "unknown")
            model = row.get("model", "unknown")
            
            total_calls += calls
            total_cost += cost
            successful_calls += success
            
            # By provider
            if provider not in by_provider:
                by_provider[provider] = {"calls": 0, "cost": 0, "success": 0}
            by_provider[provider]["calls"] += calls
            by_provider[provider]["cost"] += cost
            by_provider[provider]["success"] += success
            
            # By model
            model_key = f"{provider}/{model}"
            if model_key not in by_model:
                by_model[model_key] = {"calls": 0, "cost": 0, "success": 0}
            by_model[model_key]["calls"] += calls
            by_model[model_key]["cost"] += cost
            by_model[model_key]["success"] += success
        
        return {
            "period_days": days,
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": round(successful_calls / total_calls * 100, 1) if total_calls > 0 else 0,
            "total_cost_usd": round(total_cost, 2),
            "by_provider": by_provider,
            "by_model": by_model,
        }
        
    except Exception as e:
        logger.error(f"[UsageTracker] Error getting summary: {e}")
        return {"error": str(e)}


def get_daily_usage(days: int = 30) -> list:
    """
    Get daily usage data for charts.
    
    Args:
        days: Number of days
        
    Returns:
        List of daily usage records
    """
    if not supabase:
        return []
    
    from datetime import timedelta
    
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    try:
        result = supabase.table("ai_usage_daily")\
            .select("date, provider, model, call_type, total_calls, successful_calls, estimated_cost_usd, avg_latency_ms")\
            .gte("date", start_date)\
            .order("date", desc=False)\
            .execute()
        
        return result.data or []
        
    except Exception as e:
        logger.error(f"[UsageTracker] Error getting daily usage: {e}")
        return []
