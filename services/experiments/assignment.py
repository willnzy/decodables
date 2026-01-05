"""
Experiments Assignment - Variant assignment logic

@module services.experiments.assignment
@version 3.24
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone

from .core import supabase, logger, calculate_variant
from .crud import get_experiment


def assign_variant(
    experiment_key: str,
    user_identifier: str,
    user_properties: Dict = None
) -> Optional[str]:
    """
    Assign a variant to a user for an experiment.
    
    Args:
        experiment_key: Experiment identifier
        user_identifier: User ID or anonymous ID
        user_properties: Optional user properties for targeting
        
    Returns:
        Assigned variant key or None
    """
    if not supabase:
        return None
    
    experiment = get_experiment(experiment_key)
    if not experiment:
        logger.warning(f"[Assignment] Experiment not found: {experiment_key}")
        return None
    
    # Check if experiment is running
    if experiment.get('status') != 'running':
        return None
    
    # Check targeting
    targeting = experiment.get('targeting', {})
    if not _check_targeting(targeting, user_identifier, user_properties):
        return None
    
    # Check for existing assignment
    try:
        existing = supabase.table("experiment_assignments").select("variant_key")\
            .eq("experiment_id", experiment.get('id'))\
            .eq("user_identifier", user_identifier).execute()
        
        if existing.data:
            return existing.data[0].get('variant_key')
    except:
        pass
    
    # Calculate variant
    variant_key = calculate_variant(experiment, user_identifier)
    if not variant_key:
        return None
    
    # Save assignment
    try:
        supabase.table("experiment_assignments").insert({
            "experiment_id": experiment.get('id'),
            "experiment_key": experiment_key,
            "user_identifier": user_identifier,
            "variant_key": variant_key,
            "user_properties": user_properties or {},
        }).execute()
    except Exception as e:
        # Assignment might already exist (race condition)
        logger.debug(f"[Assignment] Insert failed (may be duplicate): {e}")
    
    return variant_key


def _check_targeting(targeting: Dict, user_identifier: str, user_properties: Dict = None) -> bool:
    """Check if user matches targeting criteria."""
    if not targeting:
        return True
    
    # Include anonymous users
    include_anonymous = targeting.get('include_anonymous', True)
    is_anonymous = user_identifier.startswith('anon_') if user_identifier else True
    
    if is_anonymous and not include_anonymous:
        return False
    
    # Check tier targeting
    if 'tiers' in targeting and user_properties:
        user_tier = user_properties.get('tier', 'free')
        if user_tier not in targeting['tiers']:
            return False
    
    # Check user ID inclusion/exclusion lists
    if 'include_users' in targeting:
        if user_identifier not in targeting['include_users']:
            return False
    
    if 'exclude_users' in targeting:
        if user_identifier in targeting['exclude_users']:
            return False
    
    return True


def get_user_variant(experiment_key: str, user_identifier: str) -> Optional[str]:
    """Get user's assigned variant for an experiment."""
    if not supabase:
        return None
    
    try:
        result = supabase.table("experiment_assignments").select("variant_key")\
            .eq("experiment_key", experiment_key)\
            .eq("user_identifier", user_identifier).execute()
        
        if result.data:
            return result.data[0].get('variant_key')
        return None
        
    except Exception as e:
        logger.error(f"[Assignment] Failed to get variant: {e}")
        return None


def get_user_experiments(user_identifier: str) -> List[Dict]:
    """Get all experiments a user is assigned to."""
    if not supabase:
        return []
    
    try:
        result = supabase.table("experiment_assignments").select(
            "experiment_key, variant_key, created_at"
        ).eq("user_identifier", user_identifier).execute()
        
        return result.data or []
        
    except Exception as e:
        logger.error(f"[Assignment] Failed to get user experiments: {e}")
        return []
