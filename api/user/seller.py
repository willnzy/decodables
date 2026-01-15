"""
Seller API - Unified seller statistics endpoint.

@module api.user.seller
@version 1.0.0

Created: Phase 3 of API Consolidation (2026-01-16)

This module consolidates three separate seller stats endpoints:
- GET /api/v2/user/projects/seller-stats (deprecated)
- GET /api/v2/user/marketplace/seller/stats (deprecated)
- GET /api/v3/user/assets/seller-stats (deprecated)

Into a single unified endpoint:
- GET /api/v2/user/seller/stats?include=projects,listings,assets

Endpoints:
- GET /api/v2/user/seller/stats - Unified seller statistics
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from domains.identity.aggregates.user_profile import UserProfile
from dependencies import get_current_user
from container import get_container
from application.queries.marketplace import GetSellerStatsQuery as MarketplaceSellerStatsQuery
from application.queries.assets import GetSellerStatsQuery as AssetSellerStatsQuery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seller", tags=["user-seller-v2"])


# ==========================================
# Response Models
# ==========================================

class ProjectSellerStats(BaseModel):
    """Project-specific seller statistics."""
    total_selling: int = Field(0, description="Number of projects currently for sale")
    total_sales: int = Field(0, description="Total number of project sales")
    unique_buyers: int = Field(0, description="Number of unique buyers")
    total_revenue: float = Field(0.0, description="Total revenue from project sales")


class ListingSellerStats(BaseModel):
    """Marketplace listing statistics."""
    total_earned_credits: int = Field(0, description="Total credits earned from listings")
    listings_count: int = Field(0, description="Number of active listings")
    total_sales: int = Field(0, description="Total number of listing sales")
    total_usage: int = Field(0, description="Total usage count across all listings")


class AssetSellerStats(BaseModel):
    """Asset-specific seller statistics."""
    total_assets: int = Field(0, description="Total assets for sale")
    total_downloads: int = Field(0, description="Total download count")
    total_revenue: float = Field(0.0, description="Total revenue from asset sales")


class SellerStatsSummary(BaseModel):
    """Summary of all seller statistics."""
    total_revenue: float = Field(0.0, description="Combined revenue from all sources")
    total_sales: int = Field(0, description="Total sales across all categories")
    total_items: int = Field(0, description="Total items for sale (projects + listings + assets)")


class UnifiedSellerStatsResponse(BaseModel):
    """
    Unified seller statistics response.

    Combines data from projects, marketplace listings, and assets
    into a single response. Use 'include' parameter to select which
    sections to include (defaults to all).

    Example:
        GET /api/v2/user/seller/stats?include=projects,listings

        Response:
        {
            "projects": {
                "total_selling": 5,
                "total_sales": 120,
                "unique_buyers": 45,
                "total_revenue": 6000.0
            },
            "listings": {
                "total_earned_credits": 2500,
                "listings_count": 10,
                "total_sales": 80,
                "total_usage": 520
            },
            "summary": {
                "total_revenue": 8500.0,
                "total_sales": 200,
                "total_items": 15
            }
        }
    """
    projects: Optional[ProjectSellerStats] = Field(None, description="Project sales statistics")
    listings: Optional[ListingSellerStats] = Field(None, description="Marketplace listing statistics")
    assets: Optional[AssetSellerStats] = Field(None, description="Asset sales statistics")
    summary: SellerStatsSummary = Field(..., description="Aggregated summary across all categories")


# ==========================================
# Endpoints
# ==========================================

@router.get("/stats", response_model=UnifiedSellerStatsResponse)
async def get_unified_seller_stats(
    include: Optional[str] = Query(
        None,
        description="Comma-separated list of sections to include: projects, listings, assets. "
                    "If not specified, includes all sections.",
    ),
    user: UserProfile = Depends(get_current_user),
) -> UnifiedSellerStatsResponse:
    """
    Get unified seller statistics across all sales channels.

    Consolidates data from:
    - Projects: Items sold as complete projects
    - Listings: Marketplace resource listings (templates, assets)
    - Assets: Individual uploaded assets for sale

    Args:
        include: Optional comma-separated list of sections to include.
                 Valid values: projects, listings, assets
                 Default: include all sections

    Returns:
        UnifiedSellerStatsResponse with requested sections and summary

    Raises:
        400: Invalid include parameter
        401: Unauthorized
        500: Service error
    """
    container = get_container()

    # Parse include parameter
    if include:
        sections = {s.strip().lower() for s in include.split(",")}
        valid_sections = {"projects", "listings", "assets"}
        invalid = sections - valid_sections
        if invalid:
            raise HTTPException(400, f"Invalid sections: {invalid}. Valid: projects, listings, assets")
    else:
        sections = {"projects", "listings", "assets"}

    # Initialize response data
    projects_stats = None
    listings_stats = None
    assets_stats = None

    # Aggregate summary values
    total_revenue = 0.0
    total_sales = 0
    total_items = 0

    # Fetch projects stats
    if "projects" in sections:
        try:
            creation_service = await container.get_creation_service()
            stats = await creation_service.get_seller_project_stats(user.user_id)
            projects_stats = ProjectSellerStats(
                total_selling=stats.get("total_selling", 0),
                total_sales=stats.get("total_sales", 0),
                unique_buyers=stats.get("unique_buyers", 0),
                total_revenue=stats.get("total_revenue", 0.0),
            )
            total_revenue += projects_stats.total_revenue
            total_sales += projects_stats.total_sales
            total_items += projects_stats.total_selling
        except Exception as e:
            logger.warning(f"Failed to get project seller stats: {e}")
            projects_stats = ProjectSellerStats()

    # Fetch listings stats
    if "listings" in sections:
        try:
            handler = await container.get_seller_stats_handler()
            query = MarketplaceSellerStatsQuery(seller_id=user.user_id)
            result = await handler.handle(query)
            if result.success:
                listings_stats = ListingSellerStats(
                    total_earned_credits=result.stats.get("total_earned_credits", 0),
                    listings_count=result.stats.get("listings_count", 0),
                    total_sales=result.stats.get("total_sales", 0),
                    total_usage=result.stats.get("total_usage", 0),
                )
                # Convert credits to revenue estimate (1 credit ≈ $0.05)
                total_revenue += listings_stats.total_earned_credits * 0.05
                total_sales += listings_stats.total_sales
                total_items += listings_stats.listings_count
        except Exception as e:
            logger.warning(f"Failed to get listing seller stats: {e}")
            listings_stats = ListingSellerStats()

    # Fetch assets stats (uses same handler as listings but different query)
    if "assets" in sections:
        try:
            # Assets use the same get_seller_stats_handler with AssetSellerStatsQuery
            handler = await container.get_seller_stats_handler()
            query = AssetSellerStatsQuery(user_id=user.user_id)
            result = await handler.handle(query)
            # Asset stats have different fields from marketplace stats
            assets_stats = AssetSellerStats(
                total_assets=result.stats.get("total_assets", 0),
                total_downloads=result.stats.get("total_downloads", 0),
                total_revenue=result.stats.get("total_revenue", 0.0),
            )
            total_revenue += assets_stats.total_revenue
            total_sales += assets_stats.total_downloads
            total_items += assets_stats.total_assets
        except Exception as e:
            logger.warning(f"Failed to get asset seller stats: {e}")
            assets_stats = AssetSellerStats()

    return UnifiedSellerStatsResponse(
        projects=projects_stats,
        listings=listings_stats,
        assets=assets_stats,
        summary=SellerStatsSummary(
            total_revenue=total_revenue,
            total_sales=total_sales,
            total_items=total_items,
        ),
    )
