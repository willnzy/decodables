"""
Experiments Trend Analysis - Daily and hourly trend data

@module services.experiments.trend
@version 1.0.0 (created for v3.26 refactor)
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone

from .core import supabase, logger


def get_daily_trend(experiment_key: str, days: int = 30) -> Optional[Dict]:
    """
    Get daily trend data for an experiment.

    Args:
        experiment_key: Experiment key
        days: Number of days to fetch (default 30)

    Returns:
        Trend data dict or None if experiment not found
    """
    if not supabase:
        logger.error("[Experiment] Supabase not configured")
        return None

    try:
        # Get experiment
        exp_result = supabase.table("experiments").select("id, variants")\
            .eq("experiment_key", experiment_key).execute()

        if not exp_result.data:
            return None

        experiment = exp_result.data[0]
        experiment_id = experiment.get("id")
        variants = experiment.get("variants", [])

        # Parse variants
        import json
        if isinstance(variants, str):
            variants = json.loads(variants)

        variant_keys = [v.get("key") for v in variants]

        # Calculate start date
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")

        # Query results with limit (EXP-HIGH-2)
        results_data = supabase.table("experiment_results").select("*")\
            .eq("experiment_id", experiment_id)\
            .gte("date", start_date)\
            .order("date")\
            .limit(10000)\
            .execute()

        # Aggregate by date
        daily_data = {}
        for result in results_data.data or []:
            date_str = result.get("date", "")
            if not date_str:
                continue
            if date_str not in daily_data:
                daily_data[date_str] = {vk: {"exposures": 0, "conversions": 0} for vk in variant_keys}

            variant_key = result.get("variant_key")
            if variant_key in daily_data[date_str]:
                daily_data[date_str][variant_key]["exposures"] += result.get("exposures", 0)
                daily_data[date_str][variant_key]["conversions"] += result.get("conversions", 0)

        # Format output
        trend_list = []
        for date_str in sorted(daily_data.keys()):
            day_entry = {"date": date_str}
            for variant_key in variant_keys:
                vdata = daily_data[date_str].get(variant_key, {"exposures": 0, "conversions": 0})
                day_entry[f"{variant_key}_exposures"] = vdata["exposures"]
                day_entry[f"{variant_key}_conversions"] = vdata["conversions"]
                rate = (vdata["conversions"] / vdata["exposures"] * 100) if vdata["exposures"] > 0 else 0
                day_entry[f"{variant_key}_rate"] = round(rate, 2)
            trend_list.append(day_entry)

        return {
            "experiment_key": experiment_key,
            "variants": variant_keys,
            "days": days,
            "trend": trend_list
        }

    except Exception as e:
        logger.error(f"[Experiment] Failed to get daily trend for {experiment_key}: {e}")
        return None


def get_hourly_trend(experiment_key: str, hours: int = 24) -> Optional[Dict]:
    """
    Get hourly trend data for an experiment.

    Args:
        experiment_key: Experiment key
        hours: Number of hours to fetch (default 24)

    Returns:
        Trend data dict or None if experiment not found
    """
    if not supabase:
        logger.error("[Experiment] Supabase not configured")
        return None

    try:
        # Get experiment
        exp_result = supabase.table("experiments").select("id, variants")\
            .eq("experiment_key", experiment_key).execute()

        if not exp_result.data:
            return None

        experiment = exp_result.data[0]
        experiment_id = experiment.get("id")
        variants = experiment.get("variants", [])

        # Parse variants
        import json
        if isinstance(variants, str):
            variants = json.loads(variants)

        variant_keys = [v.get("key") for v in variants]

        # Calculate start time
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours)
        start_date = start_time.strftime("%Y-%m-%d")

        # Query results with limit (EXP-HIGH-2)
        results_data = supabase.table("experiment_results").select("*")\
            .eq("experiment_id", experiment_id)\
            .gte("date", start_date)\
            .order("date").order("hour")\
            .limit(10000)\
            .execute()

        # Filter and format by hour
        trend_list = []
        for result in results_data.data or []:
            date_str = result.get("date", "")
            hour = result.get("hour", 0)
            variant_key = result.get("variant_key")
            time_str = f"{date_str}T{hour:02d}:00:00"

            # Parse datetime and check if within range
            try:
                result_datetime = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                if result_datetime.tzinfo is None:
                    result_datetime = result_datetime.replace(tzinfo=timezone.utc)

                if result_datetime < start_time:
                    continue
            except Exception:
                continue

            # Find or create entry
            existing = next((t for t in trend_list if t.get("time") == time_str), None)
            if not existing:
                existing = {"time": time_str}
                for vk in variant_keys:
                    existing[f"{vk}_exposures"] = 0
                    existing[f"{vk}_conversions"] = 0
                trend_list.append(existing)

            # Add data
            if variant_key in variant_keys:
                existing[f"{variant_key}_exposures"] = result.get("exposures", 0)
                existing[f"{variant_key}_conversions"] = result.get("conversions", 0)

        # Sort by time
        trend_list.sort(key=lambda x: x.get("time", ""))

        return {
            "experiment_key": experiment_key,
            "variants": variant_keys,
            "hours": hours,
            "trend": trend_list
        }

    except Exception as e:
        logger.error(f"[Experiment] Failed to get hourly trend for {experiment_key}: {e}")
        return None
