"""
Marketplace Domain - Asset listings and purchases.

This domain handles:
- Asset publishing and listing
- Asset categories and tagging
- Purchase and download tracking
- Featured assets and recommendations

@package domains.marketplace
@version 1.0.0

Note: This domain manages the marketplace where users can
share and sell their creations.
"""

from .value_objects import (
    ListingId,
    ListingStatus,
    ResourceType,
    AssetCategory,
    ListingSource,
    PriceType,
    ListingMetadata,
    ListingSortOrder,
    PriceFilter,
)
from .aggregates.listing import Listing
from .exceptions import (
    ListingNotFoundException,
    ListingAccessDeniedException,
    InvalidListingDataException,
    PurchaseFailedException,
)
from .repository import IListingRepository
from .service import MarketplaceService

__all__ = [
    # Value Objects
    'ListingId',
    'ListingStatus',
    'ResourceType',
    'AssetCategory',
    'ListingSource',
    'PriceType',
    'ListingMetadata',
    'ListingSortOrder',
    'PriceFilter',
    # Aggregates
    'Listing',
    # Exceptions
    'ListingNotFoundException',
    'ListingAccessDeniedException',
    'InvalidListingDataException',
    'PurchaseFailedException',
    # Repository
    'IListingRepository',
    # Service
    'MarketplaceService',
]
