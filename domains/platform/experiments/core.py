"""
Experiments Core - Client and shared utilities

@module services.experiments.core
@version 3.25

Changes in v3.25:
- Migrated to shared Supabase client from core/database
- Added warning logs for JSON parse failures
"""

import json
import hashlib
import logging
from typing import Dict, Optional
from datetime import datetime, timezone

from core.database import get_db_client

logger = logging.getLogger(__name__)

# Use shared Supabase client (singleton)
supabase = get_db_client()

# Cache config
CACHE_TTL = 300  # 5 minutes
_experiment_cache = {}


def get_cached_experiment(key: str) -> Optional[Dict]:
    """Get experiment from cache."""
    cached = _experiment_cache.get(key)
    if cached:
        exp, timestamp = cached
        if (datetime.now(timezone.utc).timestamp() - timestamp) < CACHE_TTL:
            return exp
    return None


def set_cached_experiment(key: str, experiment: Dict):
    """Cache experiment."""
    _experiment_cache[key] = (experiment, datetime.now(timezone.utc).timestamp())


def invalidate_cache(experiment_key: str = None):
    """Invalidate experiment cache."""
    if experiment_key:
        _experiment_cache.pop(experiment_key, None)
    else:
        _experiment_cache.clear()


def parse_experiment(data: Dict) -> Dict:
    """Parse experiment data from database."""
    if not data:
        return None
    
    exp = dict(data)
    
    # Parse JSON fields
    for field in ['variants', 'targeting', 'metrics']:
        if field in exp and isinstance(exp[field], str):
            try:
                exp[field] = json.loads(exp[field])
            except json.JSONDecodeError as e:
                logger.warning(
                    f"[Experiment] Failed to parse {field} for experiment "
                    f"{exp.get('experiment_key', 'unknown')}: {e}"
                )
                exp[field] = [] if field in ['variants', 'metrics'] else {}
    
    return exp


def get_hash(input_string: str) -> int:
    """Generate deterministic hash for variant assignment."""
    return int(hashlib.md5(input_string.encode()).hexdigest(), 16)


def calculate_variant(experiment: Dict, user_identifier: str) -> str:
    """Calculate which variant a user should be assigned to."""
    variants = experiment.get('variants', [])
    if not variants:
        return None
    
    # Deterministic hash
    hash_input = f"{experiment.get('experiment_key')}:{user_identifier}"
    hash_value = get_hash(hash_input) % 100
    
    # Check traffic allocation
    traffic = experiment.get('traffic_allocation', 100)
    if hash_value >= traffic:
        return None
    
    # Assign variant based on weights
    cumulative = 0
    variant_hash = get_hash(f"{hash_input}:variant") % 100
    
    for variant in variants:
        cumulative += variant.get('weight', 0)
        if variant_hash < cumulative:
            return variant.get('key')
    
    # Fallback to first variant
    return variants[0].get('key') if variants else None
