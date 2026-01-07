"""
Marketplace Domain Exceptions.

@module domains.marketplace.exceptions
@version 1.0.0
"""

from core.exceptions import DomainException


class MarketplaceException(DomainException):
    """Base exception for marketplace domain."""

    def __init__(self, message: str, code: str = "MARKETPLACE_ERROR"):
        super().__init__(message, code)


class ListingNotFoundException(MarketplaceException):
    """Raised when a listing is not found."""

    def __init__(self, listing_id: str):
        super().__init__(
            message=f"Listing not found: {listing_id}",
            code="LISTING_NOT_FOUND"
        )
        self.listing_id = listing_id
        self.status_code = 404


class ListingAccessDeniedException(MarketplaceException):
    """Raised when user doesn't have access to a listing."""

    def __init__(self, listing_id: str, user_id: str, action: str = "access"):
        super().__init__(
            message=f"User {user_id} cannot {action} listing {listing_id}",
            code="LISTING_ACCESS_DENIED"
        )
        self.listing_id = listing_id
        self.user_id = user_id
        self.action = action
        self.status_code = 403


class InvalidListingDataException(MarketplaceException):
    """Raised when listing data is invalid."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Invalid listing data for field '{field}': {reason}",
            code="INVALID_LISTING_DATA"
        )
        self.field = field
        self.reason = reason
        self.status_code = 400


class PurchaseFailedException(MarketplaceException):
    """Raised when a purchase fails."""

    def __init__(self, listing_id: str, user_id: str, reason: str):
        super().__init__(
            message=f"Purchase failed for listing {listing_id}: {reason}",
            code="PURCHASE_FAILED"
        )
        self.listing_id = listing_id
        self.user_id = user_id
        self.reason = reason
        self.status_code = 400


class ListingNotPublishedException(MarketplaceException):
    """Raised when trying to access unpublished listing."""

    def __init__(self, listing_id: str):
        super().__init__(
            message=f"Listing {listing_id} is not published",
            code="LISTING_NOT_PUBLISHED"
        )
        self.listing_id = listing_id
        self.status_code = 403


class AlreadyPurchasedException(MarketplaceException):
    """Raised when user already owns the asset."""

    def __init__(self, listing_id: str, user_id: str):
        super().__init__(
            message=f"User {user_id} already owns listing {listing_id}",
            code="ALREADY_PURCHASED"
        )
        self.listing_id = listing_id
        self.user_id = user_id
        self.status_code = 409
