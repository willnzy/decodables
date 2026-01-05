"""
Config Router - Public configuration endpoints

@module routers.config
@version 3.24

Endpoints:
- GET /api/configs - Get all configs
- GET /api/configs/{key} - Get single config
- GET /api/configs/group/{group_name} - Get config group
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from services.db_service import get_public_configs, get_config_by_key, get_config_group

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/configs", tags=["config"])


@router.get("")
def get_configs():
    """Get all public configurations."""
    return get_public_configs()


@router.get("/{key}")
def get_config(key: str):
    """Get a single configuration by key."""
    config = get_config_by_key(key)
    if not config:
        raise HTTPException(404, f"Config not found: {key}")
    return config


@router.get("/group/{group_name}")
def get_group(group_name: str):
    """Get all configurations in a group."""
    configs = get_config_group(group_name)
    return {"group": group_name, "configs": configs}
