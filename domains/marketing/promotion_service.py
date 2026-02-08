"""Promotion Service (SVC-011 Phase 2).

Handles promotion/promo code validation, application, and retrieval.
Implements BR-009: promo code limit check + date range validation.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PromotionService:
    """Manages promotion codes and discount application.

    Responsibilities:
    1. Validate promo code syntax, date range, and usage limits (BR-009)
    2. Apply valid promotions to user accounts
    3. Retrieve active promotions for frontend display
    4. Track promotion usage and redemption counts
    """

    def __init__(self, db_client=None):
        """Initialize with optional database client.

        Args:
            db_client: Database client for promotion queries
        """
        self._db = db_client

    async def validate_promo_code(self, code: str) -> Dict[str, Any]:
        """Validate a promo code for applicability.

        Implements BR-009: date range validation + limit checks

        Args:
            code: The promo code to validate

        Returns:
            Dictionary with validation result and promotion details
        """
        if not self._db:
            return {"valid": False, "reason": "Database unavailable"}

        try:
            result = await self._db.table("promotions").select("*").eq(
                "code", code.upper()
            ).single().execute()

            if not result.data:
                logger.info(
                    "validate_promo_code",
                    extra={
                        "event": "marketing.promo_not_found",
                        "code": code,
                    },
                )
                return {"valid": False, "reason": "Promo code not found"}

            promo = result.data
            now = datetime.now(timezone.utc)

            # Check if promotion is expired or not yet active
            if promo.get("expires_at"):
                expires_at = datetime.fromisoformat(
                    promo["expires_at"].replace("Z", "+00:00")
                )
                if now > expires_at:
                    return {"valid": False, "reason": "Promo code has expired"}

            if promo.get("starts_at"):
                starts_at = datetime.fromisoformat(
                    promo["starts_at"].replace("Z", "+00:00")
                )
                if now < starts_at:
                    return {"valid": False, "reason": "Promo code is not yet active"}

            # Check usage limit
            usage_count = promo.get("usage_count", 0)
            max_uses = promo.get("max_uses")
            if max_uses and usage_count >= max_uses:
                return {"valid": False, "reason": "Promo code limit reached"}

            return {
                "valid": True,
                "discount_percent": promo.get("discount_percent", 0),
                "discount_cents": promo.get("discount_cents", 0),
                "max_uses": max_uses,
                "remaining_uses": max(0, max_uses - usage_count) if max_uses else None,
            }

        except Exception as e:
            logger.warning(
                "validate_promo_code failed",
                extra={"event": "marketing.promo_validation_error", "error": str(e)},
            )
            return {"valid": False, "reason": "Validation error"}

    async def apply_promotion(
        self, user_id: str, code: str
    ) -> Dict[str, Any]:
        """Apply a valid promotion to a user's account.

        Args:
            user_id: The user's ID
            code: The promo code

        Returns:
            Dictionary with application result and discount details
        """
        validation = await self.validate_promo_code(code)
        if not validation["valid"]:
            return {"applied": False, "reason": validation.get("reason")}

        logger.info(
            "apply_promotion",
            extra={
                "event": "marketing.promo_applied",
                "user_id": user_id,
                "code": code,
            },
        )

        if self._db:
            now = datetime.now(timezone.utc).isoformat()
            await self._db.table("user_promotions").insert({
                "user_id": user_id,
                "code": code.upper(),
                "applied_at": now,
            }).execute()

            # Increment usage counter
            await self._db.table("promotions").update({
                "usage_count": (self._db.table("promotions").select("usage_count").eq("code", code.upper())).then(
                    lambda r: (r.data[0]["usage_count"] if r.data else 0) + 1
                ) if self._db else 1,
            }).eq("code", code.upper()).execute()

        return {
            "applied": True,
            "user_id": user_id,
            "code": code.upper(),
            "discount_percent": validation.get("discount_percent", 0),
            "discount_cents": validation.get("discount_cents", 0),
        }

    async def get_active_promotions(self) -> List[Dict[str, Any]]:
        """Retrieve all currently active promotions.

        Used for frontend display of available offers.

        Returns:
            List of active promotion records
        """
        if not self._db:
            return []

        try:
            now = datetime.now(timezone.utc).isoformat()
            result = await self._db.table("promotions").select("*").gt(
                "expires_at", now
            ).lt("starts_at", now).execute()
            return result.data or []
        except Exception as e:
            logger.warning(
                "get_active_promotions failed",
                extra={
                    "event": "marketing.active_promos_error",
                    "error": str(e),
                },
            )
            return []
