"""Admin Themes API - Theme management for admins.

@module api.admin.themes
@version 2.1.0

v2.1.0: Full implementation with CRUD, batch generation, review workflow

Endpoints:
- GET /themes - List themes
- GET /themes/{id} - Get theme details
- POST /themes - Create theme
- PUT /themes/{id} - Update theme
- DELETE /themes/{id} - Delete theme
- POST /themes/batch-generate - Batch generate themes
- GET /themes/generation-status - Get generation status
- GET /themes/calendar - Get calendar view
- POST /themes/{id}/review - Review theme
- POST /themes/{id}/regenerate - Regenerate theme
- GET /themes/{id}/history - Get theme history
- POST /themes/review/batch-approve - Batch approve themes
"""

import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from dependencies import require_admin
from infrastructure.rate_limiter import limiter
from core.database import get_async_db_client

from domains.themes import ThemesService
from domains.themes.constants import (
    VALID_CATEGORIES,
    VALID_REVIEW_STATUSES,
    DEFAULT_LIMIT,
    MAX_LIMIT,
)
from shared.ai.theme_generator import generate_theme_suggestions

from api.admin.themes_models import (
    ThemeCreateRequest,
    ThemeUpdateRequest,
    ThemeReviewRequest,
    ThemeRegenerateRequest,
    BatchApproveRequest,
    BatchGenerateRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/themes", tags=["admin-themes-v2"])


def _get_themes_service() -> ThemesService:
    """Get ThemesService instance."""
    return ThemesService(await get_async_db_client())


# ==========================================
# List and Get Endpoints
# ==========================================

@router.get("")
@limiter.limit("60/minute")
async def list_themes(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    category: str = Query(None, description="Filter by category"),
    status: str = Query(None, description="Filter by status"),
    review_status: str = Query(None, description="Filter by review status"),
    date_from: str = Query(None, description="Filter by date from (YYYY-MM-DD)"),
    date_to: str = Query(None, description="Filter by date to (YYYY-MM-DD)"),
    ai_generated: bool = Query(None, description="Filter by AI generated"),
    admin: dict = Depends(require_admin),
):
    """List all themes with pagination and filters."""
    # Validate filters
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}")
    if review_status and review_status not in VALID_REVIEW_STATUSES:
        raise HTTPException(400, f"Invalid review_status. Must be one of: {', '.join(VALID_REVIEW_STATUSES)}")

    # Build filters
    filters = {}
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status
    if review_status:
        filters["review_status"] = review_status
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if ai_generated is not None:
        filters["ai_generated"] = ai_generated

    service = _get_themes_service()
    result = await service.list_themes(offset=offset, limit=limit, filters=filters)

    return result


@router.get("/generation-status")
@limiter.limit("30/minute")
async def get_generation_status(
    request: Request,
    days: int = Query(300, ge=1, le=365),
    admin: dict = Depends(require_admin),
):
    """Get theme generation status overview."""
    service = _get_themes_service()
    return await service.get_generation_status(days=days)


@router.get("/calendar")
@limiter.limit("30/minute")
async def get_calendar_view(
    request: Request,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    admin: dict = Depends(require_admin),
):
    """Get calendar view of themes."""
    service = _get_themes_service()

    filters = {
        "date_from": start_date,
        "date_to": end_date,
    }

    result = await service.list_themes(offset=0, limit=366, filters=filters)

    # Group by date
    calendar = {}
    for theme in result["themes"]:
        theme_date = theme.get("date")
        if theme_date:
            calendar[theme_date] = theme

    return {
        "start_date": start_date,
        "end_date": end_date,
        "themes": calendar,
        "total": len(calendar),
    }


@router.get("/review/pending")
@limiter.limit("30/minute")
async def get_pending_reviews(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    review_status: str = Query(None, description="Filter by review status"),
    admin: dict = Depends(require_admin),
):
    """Get themes pending review."""
    if review_status and review_status not in VALID_REVIEW_STATUSES:
        raise HTTPException(400, f"Invalid review_status. Must be one of: {', '.join(VALID_REVIEW_STATUSES)}")

    filters = {}
    if review_status:
        filters["review_status"] = review_status

    service = _get_themes_service()
    result = await service.list_themes(offset=offset, limit=limit, filters=filters)

    return result


@router.get("/{theme_id}")
@limiter.limit("60/minute")
async def get_theme(
    request: Request,
    theme_id: str,
    admin: dict = Depends(require_admin),
):
    """Get theme details."""
    service = _get_themes_service()
    theme = await service.get_theme_by_id(theme_id)

    if not theme:
        raise HTTPException(404, "Theme not found")

    return theme


@router.get("/{theme_id}/history")
@limiter.limit("30/minute")
async def get_theme_history(
    request: Request,
    theme_id: str,
    admin: dict = Depends(require_admin),
):
    """Get theme generation history."""
    service = _get_themes_service()

    try:
        return await service.get_theme_history(theme_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ==========================================
# Create, Update, Delete Endpoints
# ==========================================

@router.post("")
@limiter.limit("30/minute")
async def create_theme(
    request: Request,
    req: ThemeCreateRequest,
    admin: dict = Depends(require_admin),
):
    """Create a new theme."""
    try:
        service = _get_themes_service()

        target_date = None
        if req.date:
            target_date = date.fromisoformat(req.date)

        theme = await service.create_theme(
            name=req.name,
            target_date=target_date,
            category=req.category,
            priority=req.priority,
            description=req.description,
            slogan=req.slogan,
            theme_config=req.theme_config,
            name_i18n=req.name_i18n,
            slogan_i18n=req.slogan_i18n,
            description_i18n=req.description_i18n,
            regions=req.regions,
            date_rule=req.date_rule,
            linked_campaign_id=req.linked_campaign_id,
            source_url=req.source_url,
            learn_more_url=req.learn_more_url,
            ai_generated=False,
            review_status="pending",
        )

        return theme

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Failed to create theme: {e}")
        raise HTTPException(500, "Failed to create theme")


@router.put("/{theme_id}")
@limiter.limit("30/minute")
async def update_theme(
    request: Request,
    theme_id: str,
    req: ThemeUpdateRequest,
    admin: dict = Depends(require_admin),
):
    """Update a theme."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(400, "No fields to update")

    try:
        service = _get_themes_service()
        theme = await service.update_theme(theme_id, update_data)

        if not theme:
            raise HTTPException(404, "Theme not found")

        return theme

    except ValueError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update theme: {e}")
        raise HTTPException(500, "Failed to update theme")


@router.delete("/{theme_id}")
@limiter.limit("20/minute")
async def delete_theme(
    request: Request,
    theme_id: str,
    admin: dict = Depends(require_admin),
):
    """Delete a theme (soft delete)."""
    try:
        service = _get_themes_service()
        success = await service.delete_theme(theme_id)

        if not success:
            raise HTTPException(404, "Theme not found")

        return {"status": "deleted", "theme_id": theme_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete theme: {e}")
        raise HTTPException(500, "Failed to delete theme")


# ==========================================
# Batch Generation Endpoints
# ==========================================

@router.post("/batch-generate")
@limiter.limit("5/minute")
async def batch_generate_themes(
    request: Request,
    req: BatchGenerateRequest,
    admin: dict = Depends(require_admin),
):
    """
    Batch generate themes for multiple dates.

    This endpoint generates themes using AI for each date in the range.
    Each theme gets 3 alternatives, and AI automatically selects the best one.
    """
    try:
        start = date.fromisoformat(req.start_date)
    except ValueError:
        raise HTTPException(400, "Invalid start_date format. Use YYYY-MM-DD")

    service = _get_themes_service()

    results = {
        "generated": 0,
        "skipped": 0,
        "failed": 0,
        "details": [],
    }

    for i in range(req.days):
        target_date = start + timedelta(days=i)

        # Check if theme already exists
        existing = await service.get_theme_by_date(target_date)
        if existing and not req.overwrite:
            results["skipped"] += 1
            results["details"].append({
                "date": target_date.isoformat(),
                "status": "skipped",
                "reason": "Theme already exists",
            })
            continue

        try:
            # Generate AI suggestions
            suggestions = await generate_theme_suggestions(target_date)

            alternatives = suggestions.get("alternatives", [])
            recommendation = suggestions.get("recommendation", {})
            recommended_id = recommendation.get("selected_id", "A")

            # Find recommended alternative
            recommended = None
            for alt in alternatives:
                if alt.get("id") == recommended_id:
                    recommended = alt
                    break

            if not recommended and alternatives:
                recommended = alternatives[0]
                recommended_id = recommended.get("id", "A")

            if not recommended:
                raise ValueError("No alternatives generated")

            # Create or update theme
            if existing and req.overwrite:
                theme = await service.update_theme(
                    existing["id"],
                    {
                        "name": recommended.get("name"),
                        "name_i18n": recommended.get("name_i18n", {}),
                        "category": recommended.get("category", "notable"),
                        "priority": recommended.get("priority", 50),
                        "slogan": recommended.get("slogan"),
                        "slogan_i18n": recommended.get("slogan_i18n", {}),
                        "description": recommended.get("description"),
                        "theme_config": recommended.get("theme_config"),
                        "ai_generated": True,
                        "ai_alternatives": alternatives,
                        "ai_recommended_id": recommended_id,
                        "selected_alternative_id": recommended_id,
                        "review_status": "auto_approved",
                        "source_url": recommended.get("source_url"),
                    }
                )
            else:
                theme = await service.create_theme(
                    name=recommended.get("name", f"Theme for {target_date}"),
                    target_date=target_date,
                    category=recommended.get("category", "notable"),
                    priority=recommended.get("priority", 50),
                    slogan=recommended.get("slogan"),
                    description=recommended.get("description"),
                    theme_config=recommended.get("theme_config"),
                    name_i18n=recommended.get("name_i18n"),
                    slogan_i18n=recommended.get("slogan_i18n"),
                    ai_generated=True,
                    ai_alternatives=alternatives,
                    ai_recommended_id=recommended_id,
                    selected_alternative_id=recommended_id,
                    review_status="auto_approved",
                    source_url=recommended.get("source_url"),
                )

            results["generated"] += 1
            results["details"].append({
                "date": target_date.isoformat(),
                "theme_id": str(theme["id"]),
                "name": recommended.get("name"),
                "status": "success",
            })

        except Exception as e:
            logger.error(f"Failed to generate theme for {target_date}: {e}")
            results["failed"] += 1
            results["details"].append({
                "date": target_date.isoformat(),
                "status": "failed",
                "error": str(e),
            })

    return results


# ==========================================
# Review Endpoints
# ==========================================

@router.post("/{theme_id}/review")
@limiter.limit("30/minute")
async def review_theme(
    request: Request,
    theme_id: str,
    req: ThemeReviewRequest,
    admin: dict = Depends(require_admin),
):
    """
    Review a theme.

    Actions:
    - approve: Confirm current selection, status becomes 'reviewed'
    - reject: Reject current theme, status becomes 'rejected'
    - switch: Switch to another alternative, status becomes 'reviewed'
    """
    try:
        service = _get_themes_service()
        result = await service.review_theme(
            theme_id=theme_id,
            action=req.action,
            admin_id=admin["id"],
            alternative_id=req.alternative_id,
            notes=req.notes,
        )

        return result

    except ValueError as e:
        raise HTTPException(400 if "not found" not in str(e).lower() else 404, str(e))
    except Exception as e:
        logger.error(f"Failed to review theme: {e}")
        raise HTTPException(500, "Failed to review theme")


@router.post("/{theme_id}/regenerate")
@limiter.limit("10/minute")
async def regenerate_theme(
    request: Request,
    theme_id: str,
    req: ThemeRegenerateRequest,
    admin: dict = Depends(require_admin),
):
    """
    Regenerate a theme with new AI alternatives.

    This preserves the generation history and increments regenerate_count.
    """
    try:
        service = _get_themes_service()

        # Get current theme to get its date
        theme = await service.get_theme_by_id(theme_id)
        if not theme:
            raise HTTPException(404, "Theme not found")

        theme_date = theme.get("date")
        if not theme_date:
            raise HTTPException(400, "Theme has no date, cannot regenerate")

        if isinstance(theme_date, str):
            theme_date = date.fromisoformat(theme_date)

        # Generate new suggestions
        suggestions = await generate_theme_suggestions(theme_date)
        alternatives = suggestions.get("alternatives", [])
        recommendation = suggestions.get("recommendation", {})
        recommended_id = recommendation.get("selected_id", "A")

        if not alternatives:
            raise HTTPException(500, "Failed to generate new alternatives")

        # Regenerate theme
        result = await service.regenerate_theme(
            theme_id=theme_id,
            admin_id=admin["id"],
            new_alternatives=alternatives,
            recommended_id=recommended_id,
            reason=req.reason,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Failed to regenerate theme: {e}")
        raise HTTPException(500, "Failed to regenerate theme")


@router.post("/review/batch-approve")
@limiter.limit("10/minute")
async def batch_approve_themes(
    request: Request,
    req: BatchApproveRequest,
    admin: dict = Depends(require_admin),
):
    """Batch approve multiple themes."""
    try:
        service = _get_themes_service()
        result = await service.batch_approve_themes(
            theme_ids=req.theme_ids,
            admin_id=admin["id"],
        )

        return result

    except Exception as e:
        logger.error(f"Failed to batch approve themes: {e}")
        raise HTTPException(500, "Failed to batch approve themes")
