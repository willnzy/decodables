"""
Config API - Public configuration endpoints (v2).

@module api.user.config
@version 2.0.0

Endpoints:
- GET /api/v2/user/config - Get all configs
- GET /api/v2/user/config/{key} - Get single config
- GET /api/v2/user/config/group/{group_name} - Get config group
"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from infrastructure.db_compat import get_public_configs, get_config_by_key, get_config_group

router = APIRouter(prefix="/config", tags=["user-config-v2"])


# ==========================================
# Response Models
# ==========================================

class ConfigResponse(BaseModel):
    """Single config response."""
    key: str
    value: Any
    description: Optional[str] = None


class ConfigGroupResponse(BaseModel):
    """Config group response."""
    group: str
    configs: List[Dict[str, Any]]


# ==========================================
# Endpoints
# ==========================================

@router.get("")
def list_configs() -> Dict[str, Any]:
    """Get all public configurations."""
    return get_public_configs()


@router.get("/group/{group_name}")
def get_group(group_name: str) -> ConfigGroupResponse:
    """Get all configurations in a group."""
    configs = get_config_group(group_name)
    return ConfigGroupResponse(group=group_name, configs=configs)


@router.get("/{key}")
def get_config(key: str) -> Dict[str, Any]:
    """Get a single configuration by key."""
    config = get_config_by_key(key)
    if not config:
        raise HTTPException(404, f"Config not found: {key}")
    return config
