"""
Pricing Service - Manages pricing plans and configurations.

@module domains.billing.pricing_service
@version 2.0.0 (AsyncClient migration)

Changes in v2.0:
- Removed unused get_supabase_client import (AsyncClient passed via DI)

This service provides centralized access to pricing configurations from the database,
replacing hard-coded prices in constants and environment variables.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PricingPlan:
    """Pricing plan value object."""

    def __init__(self, data: Dict[str, Any]):
        self.id: int = data.get("id")
        self.plan_code: str = data.get("plan_code")
        self.plan_type: str = data.get("plan_type")  # 'subscription' or 'credits'
        self.plan_name: str = data.get("plan_name")
        self.description: Optional[str] = data.get("description")

        # Pricing
        self.price_cents: int = data.get("price_cents")
        self.original_price_cents: Optional[int] = data.get("original_price_cents")
        self.currency: str = data.get("currency", "USD")

        # Subscription-specific
        self.billing_interval: Optional[str] = data.get("billing_interval")
        self.tier: Optional[str] = data.get("tier")
        self.monthly_credits: Optional[int] = data.get("monthly_credits")

        # Credits pack-specific
        self.credits_amount: Optional[int] = data.get("credits_amount")

        # Stripe integration
        self.stripe_price_id_prod: Optional[str] = data.get("stripe_price_id_prod")
        self.stripe_price_id_dev: Optional[str] = data.get("stripe_price_id_dev")
        self.stripe_product_id: Optional[str] = data.get("stripe_product_id")

        # Status
        self.is_active: bool = data.get("is_active", True)
        self.is_visible: bool = data.get("is_visible", True)
        self.is_featured: bool = data.get("is_featured", False)

        # Versioning
        self.version: int = data.get("version", 1)
        self.effective_from: Optional[datetime] = self._parse_datetime(data.get("effective_from"))
        self.effective_until: Optional[datetime] = self._parse_datetime(data.get("effective_until"))

        # Metadata
        self.metadata: Dict[str, Any] = data.get("metadata", {})
        self.sort_order: int = data.get("sort_order", 0)

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not dt_str:
            return None
        if isinstance(dt_str, datetime):
            return dt_str
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    @property
    def price_usd(self) -> float:
        """Get price in USD (cents to dollars)."""
        return self.price_cents / 100.0

    @property
    def original_price_usd(self) -> Optional[float]:
        """Get original price in USD."""
        return self.original_price_cents / 100.0 if self.original_price_cents else None

    @property
    def stripe_price_id(self) -> Optional[str]:
        """Get appropriate Stripe Price ID based on environment."""
        env = os.environ.get("ENV", "development")
        if env == "production":
            return self.stripe_price_id_prod
        return self.stripe_price_id_dev

    @property
    def discount_percent(self) -> Optional[int]:
        """Get discount percentage from metadata."""
        return self.metadata.get("discount_percent")

    @property
    def badge(self) -> Optional[str]:
        """Get badge label from metadata (e.g., POPULAR, BEST VALUE, RECOMMENDED)."""
        return self.metadata.get("badge")

    def is_effective_now(self) -> bool:
        """Check if this plan is currently effective."""
        now = datetime.now(timezone.utc)
        if self.effective_from and now < self.effective_from:
            return False
        if self.effective_until and now > self.effective_until:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "plan_code": self.plan_code,
            "plan_type": self.plan_type,
            "plan_name": self.plan_name,
            "description": self.description,
            "price": self.price_usd,
            "original_price": self.original_price_usd,
            "currency": self.currency,
            "billing_interval": self.billing_interval,
            "tier": self.tier,
            "monthly_credits": self.monthly_credits,
            "credits_amount": self.credits_amount,
            "is_featured": self.is_featured,
            "discount_percent": self.discount_percent,
            "badge": self.badge,
            "metadata": self.metadata,
        }


class PricingService:
    """
    Service for managing pricing plans and configurations.

    This service provides centralized access to pricing data from the database,
    replacing hard-coded prices and environment variables.
    """

    def __init__(self):
        # AsyncClient should be passed via dependency injection

        self.db_client = None  # Set by caller
        self._cache: Dict[str, PricingPlan] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_timestamp:
            return False
        age = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age < self._cache_ttl_seconds

    async def _fetch_all_plans(self) -> List[PricingPlan]:
        """Fetch all active pricing plans from database."""
        try:
            response = self.db_client.table("pricing_plans")\
                .select("*")\
                .eq("is_active", True)\
                .order("sort_order")\
                .execute()

            if not response.data:
                logger.warning("No pricing plans found in database")
                return []

            plans = [PricingPlan(plan_data) for plan_data in response.data]

            # Update cache
            self._cache = {plan.plan_code: plan for plan in plans}
            self._cache_timestamp = datetime.now(timezone.utc)

            return plans

        except Exception as e:
            logger.error(f"Failed to fetch pricing plans: {e}")
            raise

    async def get_plan_by_code(self, plan_code: str, use_cache: bool = True) -> Optional[PricingPlan]:
        """
        Get a pricing plan by plan_code.

        Args:
            plan_code: Plan code (e.g., 'tier_t2_monthly', 'credits_500')
            use_cache: Whether to use cached data

        Returns:
            PricingPlan object or None if not found
        """
        # Check cache first
        if use_cache and self._is_cache_valid() and plan_code in self._cache:
            return self._cache[plan_code]

        # Fetch from database
        try:
            response = self.db_client.table("pricing_plans")\
                .select("*")\
                .eq("plan_code", plan_code)\
                .eq("is_active", True)\
                .single()\
                .execute()

            if not response.data:
                logger.warning(f"Pricing plan not found: {plan_code}")
                return None

            plan = PricingPlan(response.data)

            # Update cache
            self._cache[plan_code] = plan

            return plan

        except Exception as e:
            logger.error(f"Failed to fetch pricing plan {plan_code}: {e}")
            return None

    async def get_subscription_plans(self) -> List[PricingPlan]:
        """
        Get all active subscription plans.

        Returns:
            List of subscription PricingPlan objects, sorted by sort_order
        """
        plans = await self._fetch_all_plans()
        return [p for p in plans if p.plan_type == "subscription" and p.is_visible and p.is_effective_now()]

    async def get_credits_packs(self) -> List[PricingPlan]:
        """
        Get all active credits packs.

        Returns:
            List of credits PricingPlan objects, sorted by sort_order
        """
        plans = await self._fetch_all_plans()
        return [p for p in plans if p.plan_type == "credits" and p.is_visible and p.is_effective_now()]

    async def get_stripe_price_id(self, plan_code: str) -> Optional[str]:
        """
        Get Stripe Price ID for a plan based on current environment.

        Args:
            plan_code: Plan code (e.g., 'tier_t2_monthly')

        Returns:
            Stripe Price ID or None if not found
        """
        plan = await self.get_plan_by_code(plan_code)
        if not plan:
            return None
        return plan.stripe_price_id

    async def get_monthly_credits_for_tier(self, tier: str) -> int:
        """
        Get monthly credits amount for a subscription tier.

        Args:
            tier: Tier code (e.g., 't2', 't3')

        Returns:
            Monthly credits amount, defaults to 0 for unknown tiers
        """
        # Find subscription plan for this tier
        plans = await self._fetch_all_plans()
        for plan in plans:
            if plan.plan_type == "subscription" and plan.tier == tier and plan.is_active:
                return plan.monthly_credits or 0

        logger.warning(f"No subscription plan found for tier {tier}")
        return 0

    async def get_user_price(self, user_id: str, plan_code: str) -> Optional[int]:
        """
        Get price for a specific user, including user-specific overrides.

        Args:
            user_id: User ID
            plan_code: Plan code

        Returns:
            Price in cents, or None if plan not found
        """
        # Check for user-specific override first
        try:
            override_response = self.db_client.table("user_price_overrides")\
                .select("*, pricing_plans!inner(plan_code)")\
                .eq("user_id", user_id)\
                .eq("pricing_plans.plan_code", plan_code)\
                .gte("valid_until", datetime.now(timezone.utc).isoformat())\
                .or_("valid_until.is.null")\
                .single()\
                .execute()

            if override_response.data:
                logger.info(f"Using price override for user {user_id}, plan {plan_code}")
                return override_response.data["override_price_cents"]

        except Exception as e:
            # No override found, continue to default pricing
            logger.debug(f"No price override for user {user_id}, plan {plan_code}: {e}")

        # Use default plan pricing
        plan = await self.get_plan_by_code(plan_code)
        return plan.price_cents if plan else None

    def clear_cache(self):
        """Clear the pricing cache (useful for testing or after updates)."""
        self._cache.clear()
        self._cache_timestamp = None
        logger.info("Pricing cache cleared")
