"""
Static Pages Domain Service

Business logic for static page management.

@version 2.1.0
- Removed hardcoded configurations
- Now fetches all config values from database (system_configs)
- Uses TierService for tier-related configurations
- Uses ConfigRepository for other configurations
"""

import logging
import re
from datetime import datetime
from typing import Optional, Any, Dict, TYPE_CHECKING
from uuid import UUID, uuid4

from .entities import StaticPage, StaticPageSummary, StaticPageType
from .repository import StaticPageRepository

if TYPE_CHECKING:
    from domains.identity.tier_service import TierService
    from domains.platform.config_repository import IConfigRepository

logger = logging.getLogger(__name__)


# ==========================================
# Emergency Fallback Configuration
# ==========================================
# These values are ONLY used when database is completely unavailable.
# Normal operation reads all values from system_configs table.
# ==========================================

EMERGENCY_FALLBACK = {
    "site": {
        "name": "Make Decodables",
        "email": "support@makedecodables.com",
        "whatsapp": "+1 (555) 123-4567",
        "privacy_updated": "January 2026",
        "terms_updated": "January 2026",
        "billing_updated": "January 2026",
    },
    "tiers": {
        "t1": {
            "displayName": "Free Plan",
            "monthlyPrice": "0",
            "originalPrice": "0",
            "monthlyCredits": "0",
            "signupBonus": "100",
            "maxProjects": "1",
        },
        "t2": {
            "displayName": "Starter Plan",
            "monthlyPrice": "6.9",
            "originalPrice": "9.9",
            "monthlyCredits": "100",
            "signupBonus": "0",
            "maxProjects": "10",
        },
        "t3": {
            "displayName": "Pro Plan",
            "monthlyPrice": "9.9",
            "originalPrice": "15.9",
            "monthlyCredits": "200",
            "signupBonus": "0",
            "maxProjects": "200",
        },
    },
    "creditCosts": {
        "ai_image": "5",
        "ai_page": "5",
        "ocr": "10",
    },
    "pricing": {
        "credits_100": {"amount": "100", "price": "2.99", "original_price": "2.99"},
        "credits_500": {"amount": "500", "price": "13.46", "original_price": "14.95"},
        "credits_2000": {"amount": "2000", "price": "47.84", "original_price": "59.80"},
    },
    "support": {
        "response_hours": "24",
    },
    "marketplace": {
        "seller_share_percent": "90",
        "platform_fee_percent": "10",
        "max_listing_price": "500",
        "review_hours": "48",
        "example_earning_30": "27",
        "example_fee_30": "3",
    },
    "trial": {
        "duration_days": "30",
    },
}


class StaticPageService:
    """
    Static page management service.

    Handles business logic for static pages CMS.

    @version 2.1.0
    - Now fetches template variable values from database
    - Injected TierService for tier configurations
    - Injected ConfigRepository for other configurations
    """

    def __init__(
        self,
        repository: StaticPageRepository,
        tier_service: Optional["TierService"] = None,
        config_repo: Optional["IConfigRepository"] = None,
    ):
        """
        Initialize StaticPageService.

        Args:
            repository: Static page repository
            tier_service: TierService for tier-related configs (optional, for backward compatibility)
            config_repo: ConfigRepository for other configs (optional, for backward compatibility)
        """
        self._repository = repository
        self._tier_service = tier_service
        self._config_repo = config_repo
        self._template_config_cache: Optional[Dict[str, Any]] = None

    # ==========================================
    # Public Operations
    # ==========================================

    async def get_static_page(self, slug: str) -> Optional[StaticPage]:
        """
        Get a published static page by slug.

        Args:
            slug: Page URL identifier

        Returns:
            StaticPage if found and published, None otherwise
        """
        logger.info(f"[StaticPageService] Getting static page: {slug}")
        page = await self._repository.get_by_slug(slug)

        if not page:
            logger.warning(f"[StaticPageService] Static page not found: {slug}")
            return None

        # Replace template variables in content
        if page.content:
            page.content = await self._replace_template_variables(page.content)

        # Replace template variables in meta fields
        if page.meta_title:
            page.meta_title = await self._replace_template_variables(page.meta_title)
        if page.meta_description:
            page.meta_description = await self._replace_template_variables(page.meta_description)

        return page

    async def list_static_pages(
        self,
        page_type: Optional[StaticPageType] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[StaticPageSummary]:
        """
        List published static pages.

        Args:
            page_type: Filter by page type
            offset: Pagination offset
            limit: Maximum results

        Returns:
            List of StaticPageSummary objects
        """
        logger.info(f"[StaticPageService] Listing static pages: type={page_type}, offset={offset}, limit={limit}")
        return await self._repository.list_published(
            page_type=page_type,
            offset=offset,
            limit=limit,
        )

    async def get_static_page_count(
        self,
        page_type: Optional[StaticPageType] = None,
    ) -> int:
        """
        Count published static pages.

        Args:
            page_type: Filter by page type

        Returns:
            Number of published static pages
        """
        return await self._repository.count_published(page_type=page_type)

    # ==========================================
    # Admin Operations
    # ==========================================

    async def admin_get_static_page(self, page_id: UUID) -> Optional[StaticPage]:
        """
        Get a static page by ID (admin, includes drafts).

        Args:
            page_id: Page UUID

        Returns:
            StaticPage if found, None otherwise
        """
        logger.info(f"[StaticPageService] Admin getting static page: {page_id}")
        return await self._repository.get_by_id(page_id)

    async def admin_list_static_pages(
        self,
        page_type: Optional[StaticPageType] = None,
        include_drafts: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> list[StaticPageSummary]:
        """
        List all static pages (admin).

        Args:
            page_type: Filter by page type
            include_drafts: Include unpublished pages
            offset: Pagination offset
            limit: Maximum results

        Returns:
            List of StaticPageSummary objects
        """
        logger.info(f"[StaticPageService] Admin listing static pages: type={page_type}, drafts={include_drafts}")
        return await self._repository.list_all(
            page_type=page_type,
            include_drafts=include_drafts,
            offset=offset,
            limit=limit,
        )

    async def admin_get_count(
        self,
        page_type: Optional[StaticPageType] = None,
        published_only: bool = False,
    ) -> int:
        """
        Count static pages (admin).

        Args:
            page_type: Filter by page type
            published_only: Only count published pages

        Returns:
            Number of static pages
        """
        return await self._repository.count_all(
            page_type=page_type,
            published_only=published_only,
        )

    async def create_static_page(
        self,
        slug: str,
        title: str,
        content: str,
        page_type: StaticPageType,
        subtitle: Optional[str] = None,
        icon: Optional[str] = None,
        hero_gradient: Optional[str] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        schema_data: Optional[dict[str, Any]] = None,
        extra_data: Optional[dict[str, Any]] = None,
        last_updated_display: Optional[str] = None,
        sort_order: int = 0,
    ) -> StaticPage:
        """
        Create a new static page.

        Args:
            slug: URL identifier (will be normalized)
            title: Page title
            content: Markdown content
            page_type: Page type
            subtitle: Optional subtitle
            icon: Lucide icon name
            hero_gradient: CSS gradient classes
            meta_title: SEO title
            meta_description: SEO description
            schema_data: JSON-LD schema
            extra_data: Additional structured data
            last_updated_display: Display date string
            sort_order: Sort weight

        Returns:
            Created StaticPage

        Raises:
            ValueError: If slug already exists
        """
        logger.info(f"[StaticPageService] Creating static page: {slug}")

        # Normalize slug
        normalized_slug = self._normalize_slug(slug)

        # Check slug uniqueness
        if await self._repository.slug_exists(normalized_slug):
            raise ValueError(f"Slug already exists: {normalized_slug}")

        # Create page entity
        page = StaticPage(
            id=uuid4(),
            slug=normalized_slug,
            title=title,
            content=content,
            page_type=page_type,
            subtitle=subtitle,
            icon=icon,
            hero_gradient=hero_gradient,
            meta_title=meta_title,
            meta_description=meta_description,
            schema_data=schema_data,
            extra_data=extra_data or {},
            is_published=False,
            published_at=None,
            last_updated_display=last_updated_display,
            sort_order=sort_order,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        created = await self._repository.create(page)
        logger.info(f"[StaticPageService] Static page created: {created.id}")
        return created

    async def update_static_page(
        self,
        page_id: UUID,
        slug: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        page_type: Optional[StaticPageType] = None,
        subtitle: Optional[str] = None,
        icon: Optional[str] = None,
        hero_gradient: Optional[str] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        schema_data: Optional[dict[str, Any]] = None,
        extra_data: Optional[dict[str, Any]] = None,
        last_updated_display: Optional[str] = None,
        sort_order: Optional[int] = None,
    ) -> Optional[StaticPage]:
        """
        Update an existing static page.

        Args:
            page_id: Page UUID
            slug: New slug (optional)
            title: New title (optional)
            content: New content (optional)
            page_type: New page type (optional)
            subtitle: New subtitle (optional)
            icon: New icon (optional)
            hero_gradient: New gradient (optional)
            meta_title: New SEO title (optional)
            meta_description: New SEO description (optional)
            schema_data: New schema data (optional)
            extra_data: New extra data (optional)
            last_updated_display: New display date (optional)
            sort_order: New sort order (optional)

        Returns:
            Updated StaticPage if found, None otherwise

        Raises:
            ValueError: If new slug already exists
        """
        logger.info(f"[StaticPageService] Updating static page: {page_id}")

        # Get existing page
        page = await self._repository.get_by_id(page_id)
        if not page:
            logger.warning(f"[StaticPageService] Static page not found: {page_id}")
            return None

        # Handle slug update
        if slug is not None:
            normalized_slug = self._normalize_slug(slug)
            if normalized_slug != page.slug:
                if await self._repository.slug_exists(normalized_slug, exclude_id=page_id):
                    raise ValueError(f"Slug already exists: {normalized_slug}")
                page.slug = normalized_slug

        # Update fields if provided
        if title is not None:
            page.title = title
        if content is not None:
            page.content = content
        if page_type is not None:
            page.page_type = page_type
        if subtitle is not None:
            page.subtitle = subtitle
        if icon is not None:
            page.icon = icon
        if hero_gradient is not None:
            page.hero_gradient = hero_gradient
        if meta_title is not None:
            page.meta_title = meta_title
        if meta_description is not None:
            page.meta_description = meta_description
        if schema_data is not None:
            page.schema_data = schema_data
        if extra_data is not None:
            page.extra_data = extra_data
        if last_updated_display is not None:
            page.last_updated_display = last_updated_display
        if sort_order is not None:
            page.sort_order = sort_order

        page.updated_at = datetime.utcnow()

        updated = await self._repository.update(page)
        logger.info(f"[StaticPageService] Static page updated: {page_id}")
        return updated

    async def publish_static_page(self, page_id: UUID) -> Optional[StaticPage]:
        """
        Publish a static page.

        Args:
            page_id: Page UUID

        Returns:
            Published StaticPage if found, None otherwise
        """
        logger.info(f"[StaticPageService] Publishing static page: {page_id}")
        page = await self._repository.publish(page_id)

        if page:
            logger.info(f"[StaticPageService] Static page published: {page_id}")
        else:
            logger.warning(f"[StaticPageService] Static page not found for publish: {page_id}")

        return page

    async def unpublish_static_page(self, page_id: UUID) -> Optional[StaticPage]:
        """
        Unpublish a static page (revert to draft).

        Args:
            page_id: Page UUID

        Returns:
            Unpublished StaticPage if found, None otherwise
        """
        logger.info(f"[StaticPageService] Unpublishing static page: {page_id}")
        page = await self._repository.unpublish(page_id)

        if page:
            logger.info(f"[StaticPageService] Static page unpublished: {page_id}")
        else:
            logger.warning(f"[StaticPageService] Static page not found for unpublish: {page_id}")

        return page

    async def delete_static_page(self, page_id: UUID) -> bool:
        """
        Delete a static page.

        Args:
            page_id: Page UUID

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"[StaticPageService] Deleting static page: {page_id}")
        result = await self._repository.delete(page_id)

        if result:
            logger.info(f"[StaticPageService] Static page deleted: {page_id}")
        else:
            logger.warning(f"[StaticPageService] Static page not found for delete: {page_id}")

        return result

    # ==========================================
    # Template Variable Replacement
    # ==========================================

    async def _get_template_config(self) -> Dict[str, Any]:
        """
        Get all template variable configurations from database.

        Returns:
            Dict with all template variable values

        Note:
            Results are cached for performance. Call clear_template_cache()
            to refresh values from database.
        """
        if self._template_config_cache is not None:
            return self._template_config_cache

        config: Dict[str, Any] = {
            "site": {},
            "tiers": {"t1": {}, "t2": {}, "t3": {}},
            "creditCosts": {},
            "pricing": {},
            "support": {},
            "marketplace": {},
            "trial": {},
        }

        try:
            # Fetch site config
            config["site"] = await self._get_site_config()

            # Fetch tier config (from TierService)
            config["tiers"] = await self._get_tiers_config()

            # Fetch credit costs
            config["creditCosts"] = await self._get_credit_costs_config()

            # Fetch pricing config
            config["pricing"] = await self._get_pricing_config()

            # Fetch support config
            config["support"] = await self._get_support_config()

            # Fetch marketplace config
            config["marketplace"] = await self._get_marketplace_config()

            # Fetch trial config
            config["trial"] = await self._get_trial_config()

            self._template_config_cache = config
            return config

        except Exception as e:
            logger.error(f"[StaticPageService] Failed to fetch template config from database: {e}")
            logger.warning("[StaticPageService] Using emergency fallback configuration")
            return EMERGENCY_FALLBACK

    async def _get_site_config(self) -> Dict[str, str]:
        """Fetch site configuration from database."""
        fallback = EMERGENCY_FALLBACK["site"]

        if not self._config_repo:
            return fallback

        try:
            result = {}
            for key in ["name", "email", "whatsapp", "privacy_updated", "terms_updated", "billing_updated"]:
                value = await self._config_repo.get_by_key(f"site.{key}")
                result[key] = value if value else fallback.get(key, "")
            return result
        except Exception as e:
            logger.warning(f"[StaticPageService] Failed to fetch site config: {e}")
            return fallback

    async def _get_tiers_config(self) -> Dict[str, Dict[str, str]]:
        """Fetch tier configurations from TierService."""
        fallback = EMERGENCY_FALLBACK["tiers"]

        if not self._tier_service:
            return fallback

        try:
            result = {}
            for tier in ["t1", "t2", "t3"]:
                tier_config = await self._tier_service.get_tier_config(tier)
                display_name = await self._tier_service.get_tier_display_name(tier)

                result[tier] = {
                    "displayName": display_name,
                    "monthlyCredits": str(tier_config.get("monthly_credits", 0)),
                    "maxProjects": str(tier_config.get("max_projects", 1)),
                }

                # Fetch price from config_repo (tier prices are stored separately)
                if self._config_repo:
                    monthly_price = await self._config_repo.get_by_key(f"tier.{tier}.monthly_price")
                    original_price = await self._config_repo.get_by_key(f"tier.{tier}.original_price")
                    signup_bonus = await self._config_repo.get_by_key(f"tier.{tier}.signup_bonus")

                    result[tier]["monthlyPrice"] = monthly_price or fallback[tier].get("monthlyPrice", "0")
                    result[tier]["originalPrice"] = original_price or fallback[tier].get("originalPrice", "0")
                    result[tier]["signupBonus"] = signup_bonus or fallback[tier].get("signupBonus", "0")
                else:
                    result[tier].update({
                        "monthlyPrice": fallback[tier].get("monthlyPrice", "0"),
                        "originalPrice": fallback[tier].get("originalPrice", "0"),
                        "signupBonus": fallback[tier].get("signupBonus", "0"),
                    })

            return result
        except Exception as e:
            logger.warning(f"[StaticPageService] Failed to fetch tier config: {e}")
            return fallback

    async def _get_credit_costs_config(self) -> Dict[str, str]:
        """Fetch credit costs from database."""
        fallback = EMERGENCY_FALLBACK["creditCosts"]

        if not self._tier_service:
            return fallback

        try:
            result = {}
            for operation in ["ai_image", "ai_page", "ocr"]:
                # Map template variable names to operation names
                op_name = {
                    "ai_image": "image_generation",
                    "ai_page": "page_generation",
                    "ocr": "ocr",
                }.get(operation, operation)

                cost = await self._tier_service.get_operation_cost(op_name)
                result[operation] = str(cost)
            return result
        except Exception as e:
            logger.warning(f"[StaticPageService] Failed to fetch credit costs: {e}")
            return fallback

    async def _get_pricing_config(self) -> Dict[str, Dict[str, str]]:
        """Fetch credits package pricing from database."""
        fallback = EMERGENCY_FALLBACK["pricing"]

        if not self._config_repo:
            return fallback

        try:
            result = {}
            for package in ["credits_100", "credits_500", "credits_2000"]:
                amount = await self._config_repo.get_by_key(f"pricing.{package}.amount")
                price = await self._config_repo.get_by_key(f"pricing.{package}.price")
                original_price = await self._config_repo.get_by_key(f"pricing.{package}.original_price")

                result[package] = {
                    "amount": amount or fallback[package].get("amount", "0"),
                    "price": price or fallback[package].get("price", "0"),
                    "original_price": original_price or fallback[package].get("original_price", "0"),
                }
            return result
        except Exception as e:
            logger.warning(f"[StaticPageService] Failed to fetch pricing config: {e}")
            return fallback

    async def _get_support_config(self) -> Dict[str, str]:
        """Fetch support configuration from database."""
        fallback = EMERGENCY_FALLBACK["support"]

        if not self._config_repo:
            return fallback

        try:
            response_hours = await self._config_repo.get_by_key("support.response_hours")
            return {
                "response_hours": response_hours or fallback.get("response_hours", "24"),
            }
        except Exception as e:
            logger.warning(f"[StaticPageService] Failed to fetch support config: {e}")
            return fallback

    async def _get_marketplace_config(self) -> Dict[str, str]:
        """Fetch marketplace configuration from database."""
        fallback = EMERGENCY_FALLBACK["marketplace"]

        if not self._config_repo:
            return fallback

        try:
            result = {}
            for key in ["seller_share_percent", "platform_fee_percent", "max_listing_price",
                       "review_hours", "example_earning_30", "example_fee_30"]:
                value = await self._config_repo.get_by_key(f"marketplace.{key}")
                result[key] = value or fallback.get(key, "")
            return result
        except Exception as e:
            logger.warning(f"[StaticPageService] Failed to fetch marketplace config: {e}")
            return fallback

    async def _get_trial_config(self) -> Dict[str, str]:
        """Fetch trial configuration from database."""
        fallback = EMERGENCY_FALLBACK["trial"]

        if not self._tier_service:
            return fallback

        try:
            duration_days = await self._tier_service.get_trial_duration_days()
            return {
                "duration_days": str(duration_days),
            }
        except Exception as e:
            logger.warning(f"[StaticPageService] Failed to fetch trial config: {e}")
            return fallback

    async def _replace_template_variables(self, content: str) -> str:
        """
        Replace template variables in content with actual values from database.

        Supports variables like:
        - {{site.name}} - Site configuration
        - {{tiers.t2.displayName}} - Tier configuration
        - {{creditCosts.ai_image}} - Credit costs
        - {{pricing.credits_100.price}} - Pricing
        - {{support.response_hours}} - Support config
        - {{marketplace.seller_share_percent}} - Marketplace config
        - {{trial.duration_days}} - Trial config

        Args:
            content: Content with template variables

        Returns:
            Content with variables replaced
        """
        if not content:
            return content

        # Get config from database (cached)
        config = await self._get_template_config()

        # Build replacement map
        replacements: dict[str, str] = {}

        # Site config
        for key, value in config.get("site", {}).items():
            replacements[f"{{{{site.{key}}}}}"] = str(value)

        # Tier config
        for tier, tier_config in config.get("tiers", {}).items():
            for key, value in tier_config.items():
                replacements[f"{{{{tiers.{tier}.{key}}}}}"] = str(value)

        # Credit costs
        for key, value in config.get("creditCosts", {}).items():
            replacements[f"{{{{creditCosts.{key}}}}}"] = str(value)

        # Pricing
        for plan, plan_config in config.get("pricing", {}).items():
            if isinstance(plan_config, dict):
                for key, value in plan_config.items():
                    replacements[f"{{{{pricing.{plan}.{key}}}}}"] = str(value)
            else:
                replacements[f"{{{{pricing.{plan}}}}}"] = str(plan_config)

        # Support config
        for key, value in config.get("support", {}).items():
            replacements[f"{{{{support.{key}}}}}"] = str(value)

        # Marketplace config
        for key, value in config.get("marketplace", {}).items():
            replacements[f"{{{{marketplace.{key}}}}}"] = str(value)

        # Trial config
        for key, value in config.get("trial", {}).items():
            replacements[f"{{{{trial.{key}}}}}"] = str(value)

        # Perform replacements
        result = content
        for pattern, replacement in replacements.items():
            result = result.replace(pattern, replacement)

        return result

    def clear_template_cache(self):
        """Clear the template configuration cache."""
        self._template_config_cache = None
        logger.debug("[StaticPageService] Template config cache cleared")

    # ==========================================
    # Utility Methods
    # ==========================================

    def _normalize_slug(self, slug: str) -> str:
        """
        Normalize slug to URL-safe format.

        Args:
            slug: Raw slug input

        Returns:
            Normalized slug (lowercase, hyphens only)
        """
        # Convert to lowercase
        normalized = slug.lower().strip()

        # Replace spaces and underscores with hyphens
        normalized = re.sub(r'[\s_]+', '-', normalized)

        # Remove non-alphanumeric characters except hyphens
        normalized = re.sub(r'[^a-z0-9-]', '', normalized)

        # Remove multiple consecutive hyphens
        normalized = re.sub(r'-+', '-', normalized)

        # Remove leading/trailing hyphens
        normalized = normalized.strip('-')

        return normalized
