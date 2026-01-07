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

from infrastructure.repositories import SupabaseConfigRepository
from core.database import get_database_client

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
async def list_configs() -> Dict[str, Any]:
    """Get all public configurations."""
    db = get_database_client()
    config_repo = SupabaseConfigRepository(db)
    configs = await config_repo.get_all()
    # Convert list to dict format
    return {c["key"]: c for c in configs}


@router.get("/group/{group_name}")
async def get_group(group_name: str) -> ConfigGroupResponse:
    """Get all configurations in a group."""
    db = get_database_client()
    config_repo = SupabaseConfigRepository(db)
    configs = await config_repo.get_all(group=group_name)
    return ConfigGroupResponse(group=group_name, configs=configs)


@router.get("/{key}")
async def get_config(key: str) -> Dict[str, Any]:
    """Get a single configuration by key."""
    db = get_database_client()
    config_repo = SupabaseConfigRepository(db)
    value = await config_repo.get_by_key(key)
    if not value:
        raise HTTPException(404, f"Config not found: {key}")
    return {"key": key, "value": value}
