"""
Experiments CRUD - Create, Read, Update, Delete operations

@module services.experiments.crud
@version 3.24
"""

import json
from typing import Optional, Dict, List
from datetime import datetime

from .core import (
    supabase, logger, parse_experiment,
    get_cached_experiment, set_cached_experiment, invalidate_cache
)


def create_experiment(
    experiment_key: str,
    name: str,
    variants: List[Dict],
    description: str = None,
    experiment_type: str = "ab",
    targeting: Dict = None,
    traffic_allocation: int = 100,
    metrics: List[Dict] = None,
    start_at: datetime = None,
    end_at: datetime = None,
    created_by: str = None
) -> Optional[Dict]:
    """Create new experiment."""
    if not supabase:
        logger.error("[Experiment] Supabase not configured")
        return None
    
    try:
        total_weight = sum(v.get("weight", 0) for v in variants)
        if total_weight != 100:
            logger.error(f"[Experiment] Variants weight sum must be 100, got {total_weight}")
            return None
        
        data = {
            "experiment_key": experiment_key,
            "name": name,
            "description": description,
            "experiment_type": experiment_type,
            "variants": json.dumps(variants),
            "targeting": json.dumps(targeting or {"include_anonymous": True}),
            "traffic_allocation": traffic_allocation,
            "metrics": json.dumps(metrics or []),
            "status": "draft",
            "created_by": created_by,
            "updated_by": created_by,
        }
        
        if start_at:
            data["start_at"] = start_at.isoformat()
        if end_at:
            data["end_at"] = end_at.isoformat()
        
        result = supabase.table("experiments").insert(data).execute()
        
        if result.data:
            return parse_experiment(result.data[0])
        return None
        
    except Exception as e:
        logger.error(f"[Experiment] Failed to create: {e}")
        return None


def get_experiment(experiment_key: str, use_cache: bool = True) -> Optional[Dict]:
    """Get experiment by key."""
    if not supabase:
        return None
    
    if use_cache:
        cached = get_cached_experiment(experiment_key)
        if cached:
            return cached
    
    try:
        result = supabase.table("experiments").select("*")\
            .eq("experiment_key", experiment_key).execute()
        
        if result.data:
            exp = parse_experiment(result.data[0])
            if use_cache:
                set_cached_experiment(experiment_key, exp)
            return exp
        return None
        
    except Exception as e:
        logger.error(f"[Experiment] Failed to get {experiment_key}: {e}")
        return None


def get_experiment_by_id(experiment_id: str) -> Optional[Dict]:
    """Get experiment by ID."""
    if not supabase:
        return None
    
    try:
        result = supabase.table("experiments").select("*")\
            .eq("id", experiment_id).execute()
        
        if result.data:
            return parse_experiment(result.data[0])
        return None
        
    except Exception as e:
        logger.error(f"[Experiment] Failed to get by ID {experiment_id}: {e}")
        return None


def list_experiments(
    status: str = None,
    experiment_type: str = None,
    page: int = 1,
    limit: int = 20
) -> Dict:
    """List experiments with filters."""
    if not supabase:
        return {"items": [], "total": 0}
    
    try:
        offset = (page - 1) * limit
        query = supabase.table("experiments").select("*", count="exact")
        
        if status:
            query = query.eq("status", status)
        if experiment_type:
            query = query.eq("experiment_type", experiment_type)
        
        result = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1).execute()
        
        items = [parse_experiment(e) for e in (result.data or [])]
        return {"items": items, "total": result.count or 0}
        
    except Exception as e:
        logger.error(f"[Experiment] Failed to list: {e}")
        return {"items": [], "total": 0}


def update_experiment(
    experiment_key: str,
    name: str = None,
    description: str = None,
    variants: List[Dict] = None,
    targeting: Dict = None,
    traffic_allocation: int = None,
    metrics: List[Dict] = None,
    updated_by: str = None
) -> Optional[Dict]:
    """Update experiment."""
    if not supabase:
        return None
    
    try:
        update_data = {}
        
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if variants is not None:
            update_data["variants"] = json.dumps(variants)
        if targeting is not None:
            update_data["targeting"] = json.dumps(targeting)
        if traffic_allocation is not None:
            update_data["traffic_allocation"] = traffic_allocation
        if metrics is not None:
            update_data["metrics"] = json.dumps(metrics)
        if updated_by:
            update_data["updated_by"] = updated_by
        
        if not update_data:
            return get_experiment(experiment_key)
        
        result = supabase.table("experiments").update(update_data)\
            .eq("experiment_key", experiment_key).execute()
        
        invalidate_cache(experiment_key)
        
        if result.data:
            return parse_experiment(result.data[0])
        return None
        
    except Exception as e:
        logger.error(f"[Experiment] Failed to update {experiment_key}: {e}")
        return None


def update_experiment_status(
    experiment_key: str,
    status: str,
    updated_by: str = None
) -> Optional[Dict]:
    """Update experiment status."""
    if not supabase:
        return None
    
    valid_statuses = ["draft", "running", "paused", "completed", "archived"]
    if status not in valid_statuses:
        logger.error(f"[Experiment] Invalid status: {status}")
        return None
    
    try:
        update_data = {"status": status}
        if updated_by:
            update_data["updated_by"] = updated_by
        
        result = supabase.table("experiments").update(update_data)\
            .eq("experiment_key", experiment_key).execute()
        
        invalidate_cache(experiment_key)
        
        if result.data:
            return parse_experiment(result.data[0])
        return None
        
    except Exception as e:
        logger.error(f"[Experiment] Failed to update status: {e}")
        return None


def delete_experiment(experiment_key: str) -> bool:
    """Delete experiment."""
    if not supabase:
        return False
    
    try:
        supabase.table("experiments").delete()\
            .eq("experiment_key", experiment_key).execute()
        
        invalidate_cache(experiment_key)
        return True
        
    except Exception as e:
        logger.error(f"[Experiment] Failed to delete {experiment_key}: {e}")
        return False


def get_active_experiments() -> List[Dict]:
    """Get all active experiments."""
    if not supabase:
        return []
    
    try:
        result = supabase.table("experiments").select("*")\
            .eq("status", "running").execute()
        
        return [parse_experiment(e) for e in (result.data or [])]
        
    except Exception as e:
        logger.error(f"[Experiment] Failed to get active: {e}")
        return []
