"""
Entitlement API — Unified permissions endpoint (API-001 Phase 4).

@module api.user.entitlement
@version 1.0.0

GET /api/v2/user/entitlement/features — Returns 19 feature permissions for current user.

This endpoint provides the unified 19-feature permission set using PermissionService from Phase 3.
Returns permission status for all features in a single call with tier and trial information.

Endpoints:
- GET /api/v2/user/entitlement/features - Get all 19 feature permissions for current user
"""

import logging
from typing import Dict, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from domains.identity.aggregates.user_profile import UserProfile
from domains.identity.tier_service import FeatureKey
from dependencies import get_current_user
from infrastructure.rate_limiter import limiter
from container import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entitlement", tags=["user-entitlement-v2"])


# ==========================================
# Response Models
# ==========================================

class FeaturesResponse(BaseModel):
    """Response model for GET /features."""
    features: Dict[str, Union[bool, str]]  # feature_key -> True/False/'trial'
    tier: str
    is_trial_active: bool
    credits_monthly: int
    credits_permanent: int


# ==========================================
# Endpoints
# ==========================================

@router.get("/features", response_model=FeaturesResponse)
@limiter.limit("60/minute")  # Rate limiting: 60 requests per minute
async def get_user_features(
    request: Request,
    user: UserProfile = Depends(get_current_user),
):
    """
    Get unified 19-feature permission set for current user.

    Returns all 19 feature permissions with their resolved values:
    - True: feature enabled
    - False: feature disabled
    - 'trial': feature available in trial mode only

    This endpoint integrates with Phase 3 PermissionService to provide
    a complete view of user entitlements across all domains:
    - Export (pdf_export, pdf_print, zip_export)
    - Editor (clipboard_paste)
    - Assets (upload_image, upload_advanced, save_assets)
    - AI (ai_generate_asset, ai_generate_page, smart_scan)
    - Marketplace (browse_marketplace, purchase_marketplace, publish_paid, publish_free)
    - Team/Admin (member_management, trash_recovery, project_templates)
    - Share/Purchase (share_public_link, can_purchase_credits)

    Returns:
        FeaturesResponse containing:
            - features: Dict mapping feature_key to permission status (bool | 'trial')
            - tier: User's current tier (t1/t2/t3/t4)
            - is_trial_active: Whether user is in active trial period
            - credits_monthly: Monthly subscription credits
            - credits_permanent: Purchased permanent credits

    Raises:
        401: Unauthorized (not authenticated)
        429: Rate limit exceeded (max 60 requests per minute)
        500: Service unavailable or permission service error

    Security:
        - Authentication required
        - Rate limit: 60 requests per minute
        - User can only access their own features
        - Error messages sanitized (no internal details exposed)

    Usage:
        Used by frontend to:
        - Determine which features are available to user
        - Show/hide UI elements based on permissions
        - Display trial-only features with special indicators
        - Inform users of upgrade opportunities

    Example:
        GET /api/v2/user/entitlement/features

        Response:
        {
            "features": {
                "pdf_export": true,
                "pdf_print": "trial",
                "zip_export": false,
                "clipboard_paste": true,
                "upload_image": true,
                "upload_advanced": false,
                "save_assets": true,
                "ai_generate_asset": true,
                "ai_generate_page": "trial",
                "smart_scan": false,
                "browse_marketplace": true,
                "purchase_marketplace": true,
                "publish_paid": false,
                "publish_free": true,
                "member_management": false,
                "trash_recovery": true,
                "project_templates": true,
                "share_public_link": true,
                "can_purchase_credits": true
            },
            "tier": "t2",
            "is_trial_active": true,
            "credits_monthly": 200,
            "credits_permanent": 150
        }
    """
    container = get_container()

    # Get TierService for feature permission checks
    tier_service = await container._get_or_create_tier_service()

    # Build tier string from user object
    tier_str = user.tier.value if hasattr(user.tier, 'value') else str(user.tier)

    # Get trial status from user object
    is_trial_active = getattr(user, 'is_trial_active', False)

    # Check all 19 features
    features = {}
    for feature_key in FeatureKey:
        try:
            # Use get_feature_access for complete permission resolution (Phase 3 SVC-002)
            # This method returns True/False/'trial' based on tier configuration
            result = await tier_service.get_feature_access(
                tier_str,
                feature_key.value,
                is_trial_active
            )
            features[feature_key.value] = result if result is not None else False
        except Exception as e:
            # Graceful fallback on error (BR-014)
            logger.error(
                f"[Entitlement] Failed to check feature {feature_key.value} for user {user.user_id}: {e}"
            )
            features[feature_key.value] = False

    # Extract credit information from user object
    credits_monthly = getattr(user, 'credits_monthly', 0)
    credits_permanent = getattr(user, 'credits_permanent', 0)

    return FeaturesResponse(
        features=features,
        tier=tier_str,
        is_trial_active=is_trial_active,
        credits_monthly=credits_monthly,
        credits_permanent=credits_permanent,
    )
