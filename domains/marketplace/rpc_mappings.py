"""
Marketplace RPC Mappings - Translation layer between domain enums and RPC parameters.

@module domains.marketplace.rpc_mappings
@version 1.0.0

This module provides centralized mapping logic for converting domain-level enums
to database-friendly RPC parameters. This separation ensures:
- Domain layer remains independent of infrastructure concerns
- RPC interface can be changed without touching domain logic
- Mappings are testable and maintainable in one place
"""

from typing import Dict, Optional
from .value_objects import PriceFilter, AssetCategory, ListingSortOrder


class MarketplaceRPCMapper:
    """
    Centralized mapper for Marketplace RPC function parameters.

    Why separate from domain enums?
    - RPC is an infrastructure concern, not domain logic
    - Easier to change RPC interface without touching domain
    - Can be overridden for testing
    - Single source of truth for all RPC mappings
    """

    # Price filter mappings: Domain enum → RPC parameter
    PRICE_FILTER_TO_RPC: Dict[str, str] = {
        "free": "free",    # PriceFilter.FREE ("free") → "free" for RPC
        "paid": "paid",    # PriceFilter.PAID ("paid") → "paid" (no change)
        "all": "all",      # PriceFilter.ALL ("all") → "all" (no change)
    }

    # Category mappings: Domain enum → RPC parameter
    # Currently 1:1 mapping, but centralized for future changes
    # Category mappings: Domain enum → RPC parameter
    # Only includes values that exist in AssetCategory enum
    CATEGORY_TO_RPC: Dict[str, str] = {
        "asset": "asset",
        "project": "project",
        "element": "element",
        "template": "template",
        "sticker": "sticker",
        "background": "background",
        "frame": "frame",
        "font": "font",
        # Removed "text_style" and "filter" — not in AssetCategory enum (DR#2)
    }

    # Sort order mappings: Domain enum → RPC parameter
    # Currently 1:1 mapping, but centralized for future changes
    SORT_ORDER_TO_RPC: Dict[str, str] = {
        "latest": "latest",
        "popular": "popular",
        "best_selling": "best_selling",
        "price_asc": "price_asc",
        "price_desc": "price_desc",
    }

    @classmethod
    def map_price_filter(cls, price_filter: Optional[PriceFilter]) -> str:
        """
        Map PriceFilter enum to RPC parameter.

        Args:
            price_filter: PriceFilter enum value (can be None)

        Returns:
            RPC-compatible string ("free", "paid", or "all")

        Example:
            >>> mapper.map_price_filter(PriceFilter.FREE)
            "free"
            >>> mapper.map_price_filter(None)
            "all"
        """
        if price_filter is None:
            return "all"

        return cls.PRICE_FILTER_TO_RPC.get(price_filter.value, "all")

    @classmethod
    def map_category(cls, category: Optional[AssetCategory]) -> Optional[str]:
        """
        Map AssetCategory enum to RPC parameter.

        Args:
            category: AssetCategory enum value (can be None)

        Returns:
            RPC-compatible string or None (None means no filter)

        Example:
            >>> mapper.map_category(AssetCategory.ELEMENT)
            "element"
            >>> mapper.map_category(None)
            None
        """
        if category is None:
            return None

        return cls.CATEGORY_TO_RPC.get(category.value, category.value)

    @classmethod
    def map_sort_order(cls, sort_by: Optional[ListingSortOrder]) -> str:
        """
        Map ListingSortOrder enum to RPC parameter.

        Args:
            sort_by: ListingSortOrder enum value (can be None)

        Returns:
            RPC-compatible string (defaults to "latest")

        Example:
            >>> mapper.map_sort_order(ListingSortOrder.POPULAR)
            "popular"
            >>> mapper.map_sort_order(None)
            "latest"
        """
        if sort_by is None:
            return "latest"

        return cls.SORT_ORDER_TO_RPC.get(sort_by.value, "latest")

    @classmethod
    def map_all_filters(
        cls,
        category: Optional[AssetCategory] = None,
        price_filter: Optional[PriceFilter] = None,
        sort_by: Optional[ListingSortOrder] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Map all filter parameters at once.

        Convenience method for mapping multiple filters in one call.

        Args:
            category: Optional category filter
            price_filter: Optional price filter
            sort_by: Optional sort order

        Returns:
            Dict with RPC-compatible parameter values

        Example:
            >>> mapper.map_all_filters(
            ...     category=AssetCategory.ELEMENT,
            ...     price_filter=PriceFilter.FREE,
            ...     sort_by=ListingSortOrder.POPULAR
            ... )
            {
                "category": "element",
                "price_filter": "free",
                "sort_by": "popular"
            }
        """
        return {
            "category": cls.map_category(category),
            "price_filter": cls.map_price_filter(price_filter),
            "sort_by": cls.map_sort_order(sort_by),
        }
