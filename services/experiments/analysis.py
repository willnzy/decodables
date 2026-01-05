"""
Experiments Analysis - Results aggregation and statistics

@module services.experiments.analysis
@version 3.24
"""

import math
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from .core import supabase, logger
from .crud import get_experiment, list_experiments


def aggregate_experiment_results(experiment_key: str = None) -> bool:
    """
    Aggregate results for experiment(s).
    
    Args:
        experiment_key: Specific experiment, or None for all active
        
    Returns:
        Success status
    """
    if not supabase:
        return False
    
    try:
        if experiment_key:
            experiments = [get_experiment(experiment_key)]
        else:
            result = list_experiments(status="running")
            experiments = result.get("items", [])
        
        for exp in experiments:
            if not exp:
                continue
            _aggregate_single_experiment(exp)
        
        return True
        
    except Exception as e:
        logger.error(f"[Analysis] Aggregation failed: {e}")
        return False


def _aggregate_single_experiment(experiment: Dict):
    """Aggregate results for a single experiment."""
    exp_key = experiment.get('experiment_key')
    exp_id = experiment.get('id')
    
    # Get exposures by variant
    exposures = supabase.table("experiment_exposures").select("variant_key")\
        .eq("experiment_key", exp_key).execute()
    
    exposure_counts = defaultdict(int)
    for e in (exposures.data or []):
        exposure_counts[e.get('variant_key')] += 1
    
    # Get conversions by variant
    conversions = supabase.table("experiment_conversions").select(
        "variant_key, metric_key, value"
    ).eq("experiment_key", exp_key).execute()
    
    conversion_data = defaultdict(lambda: defaultdict(lambda: {"count": 0, "total": 0}))
    for c in (conversions.data or []):
        vk = c.get('variant_key')
        mk = c.get('metric_key')
        conversion_data[vk][mk]["count"] += 1
        conversion_data[vk][mk]["total"] += c.get('value', 0)
    
    # Build results
    results = {}
    for variant in experiment.get('variants', []):
        vk = variant.get('key')
        exp_count = exposure_counts.get(vk, 0)
        
        variant_result = {
            "exposures": exp_count,
            "metrics": {}
        }
        
        for mk, data in conversion_data.get(vk, {}).items():
            conv_count = data["count"]
            rate = conv_count / exp_count if exp_count > 0 else 0
            
            variant_result["metrics"][mk] = {
                "conversions": conv_count,
                "rate": round(rate, 4),
                "total_value": data["total"]
            }
        
        results[vk] = variant_result
    
    # Store aggregated results
    supabase.table("experiment_results").upsert({
        "experiment_id": exp_id,
        "experiment_key": exp_key,
        "results": results,
        "aggregated_at": datetime.now(timezone.utc).isoformat()
    }, on_conflict="experiment_key").execute()


def get_experiment_results(
    experiment_key: str,
    start_date: datetime = None,
    end_date: datetime = None
) -> Optional[Dict]:
    """
    Get experiment results.
    
    Args:
        experiment_key: Experiment identifier
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        Results dictionary
    """
    if not supabase:
        return None
    
    experiment = get_experiment(experiment_key)
    if not experiment:
        return None
    
    try:
        # Get cached results
        cached = supabase.table("experiment_results").select("*")\
            .eq("experiment_key", experiment_key).execute()
        
        if cached.data:
            return {
                "experiment": experiment,
                "results": cached.data[0].get("results", {}),
                "aggregated_at": cached.data[0].get("aggregated_at")
            }
        
        # No cached results, aggregate now
        _aggregate_single_experiment(experiment)
        
        # Fetch again
        cached = supabase.table("experiment_results").select("*")\
            .eq("experiment_key", experiment_key).execute()
        
        if cached.data:
            return {
                "experiment": experiment,
                "results": cached.data[0].get("results", {}),
                "aggregated_at": cached.data[0].get("aggregated_at")
            }
        
        return {"experiment": experiment, "results": {}}
        
    except Exception as e:
        logger.error(f"[Analysis] Failed to get results: {e}")
        return None


def calculate_statistical_significance(
    control_conversions: int,
    control_trials: int,
    treatment_conversions: int,
    treatment_trials: int
) -> Dict:
    """
    Calculate statistical significance between control and treatment.
    
    Uses two-proportion z-test.
    
    Returns:
        Dict with z_score, p_value, confidence, and lift
    """
    if control_trials == 0 or treatment_trials == 0:
        return {
            "z_score": 0,
            "p_value": 1.0,
            "confidence": 0,
            "lift": 0,
            "significant": False
        }
    
    p1 = control_conversions / control_trials
    p2 = treatment_conversions / treatment_trials
    
    # Pooled proportion
    p_pooled = (control_conversions + treatment_conversions) / (control_trials + treatment_trials)
    
    # Standard error
    se = math.sqrt(p_pooled * (1 - p_pooled) * (1/control_trials + 1/treatment_trials))
    
    if se == 0:
        return {
            "z_score": 0,
            "p_value": 1.0,
            "confidence": 0,
            "lift": 0,
            "significant": False
        }
    
    # Z-score
    z_score = (p2 - p1) / se
    
    # P-value (two-tailed)
    p_value = 2 * (1 - _normal_cdf(abs(z_score)))
    
    # Confidence level
    confidence = (1 - p_value) * 100
    
    # Lift
    lift = ((p2 - p1) / p1 * 100) if p1 > 0 else 0
    
    return {
        "z_score": round(z_score, 4),
        "p_value": round(p_value, 4),
        "confidence": round(confidence, 2),
        "lift": round(lift, 2),
        "significant": p_value < 0.05
    }


def _normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))
