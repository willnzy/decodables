"""Themes API - Holiday themes endpoint (v3).

@module api.user.themes
@version 3.0.0

Changes:
- v3.0.0: DDD architecture upgrade - CQRS Query pattern
  - Created ThemesService with date matching business logic
  - Added GetCurrentThemeHandler (Query Handler)
  - Eliminated direct Supabase calls from API layer
  - Moved all business logic (date matching) to Service layer
  - Improved testability and maintainability

- v2.1.0: Security improvements
  - THM-LOW-1: Added rate limiting (60/minute)

Endpoints:
- GET /api/v2/user/themes/current - Get current active theme
"""

from datetime import date
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from container import get_container
from application.queries.themes import GetCurrentThemeQuery
from infrastructure.rate_limiter import limiter


router = APIRouter(prefix="/themes", tags=["user-themes-v3"])


# ==========================================
# Response Models
# ==========================================

class ThemeConfig(BaseModel):
    """Theme configuration."""
    colors: Optional[Dict[str, str]] = None
    badge: Optional[Dict[str, Any]] = None
    decorations: Optional[Dict[str, Any]] = None
    banner_style: Optional[Dict[str, Any]] = None


class CurrentThemeResponse(BaseModel):
    """Current theme response."""
    theme_id: Optional[str] = None
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


# ==========================================
# Endpoints
# ==========================================

@router.get("/current")
@limiter.limit("60/minute")
async def get_current_theme(request: Request) -> CurrentThemeResponse:
    """
    Get the currently active holiday theme based on today's date.

    v3.0.0: Now uses GetCurrentThemeHandler (CQRS Query pattern).

    Returns the highest-priority theme that matches today's date,
    or null values if no theme is active.
    """
    container = get_container()
    handler = await container.get_current_theme_handler()

    query = GetCurrentThemeQuery(check_date=date.today())
    result = await handler.handle(query)

    if not result.theme:
        return CurrentThemeResponse()

    theme = result.theme
    return CurrentThemeResponse(
        theme_id=theme["id"],
        name=theme["name"],
        config=theme["theme_config"],
    )
