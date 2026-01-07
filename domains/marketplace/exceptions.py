"""
Marketplace Domain Exceptions.

@module domains.marketplace.exceptions
@version 1.0.0
"""

from core.exceptions import AppException, ErrorCode


class MarketplaceException(AppException):
    """Base exception for marketplace domain."""
    pass


class ListingNotFoundException(MarketplaceException):
    """Raised when a listing is not found."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Listing not found"

    def __init__(self, listing_id: str = None, **kwargs):
        message = "Listing not found"
        if listing_id:
            message = f"Listing not found: {listing_id}"

        super().__init__(
            message=message,
            context={"listing_id": listing_id},
            **kwargs
        )


class ListingAccessDeniedException(MarketplaceException):
    """Raised when user doesn't have access to a listing."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Listing access denied"

    def __init__(
        self,
        listing_id: str = None,
        user_id: str = None,
        action: str = "access",
        **kwargs
    ):
        message = "Listing access denied"
        if listing_id and user_id:
            message = f"User {user_id} cannot {action} listing {listing_id}"

        super().__init__(
            message=message,
            context={"listing_id": listing_id, "user_id": user_id, "action": action},
            **kwargs
        )


class InvalidListingDataException(MarketplaceException):
    """Raised when listing data is invalid."""
    status_code = 400
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Invalid listing data"

    def __init__(self, field: str = None, reason: str = None, **kwargs):
        message = "Invalid listing data"
        if field and reason:
            message = f"Invalid listing data for field '{field}': {reason}"

        super().__init__(
            message=message,
            context={"field": field, "reason": reason},
            **kwargs
        )


class PurchaseFailedException(MarketplaceException):
    """Raised when a purchase fails."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Purchase failed"

    def __init__(
        self,
        listing_id: str = None,
        user_id: str = None,
        reason: str = None,
        **kwargs
    ):
        message = "Purchase failed"
        if listing_id:
            message = f"Purchase failed for listing {listing_id}"
            if reason:
                message += f": {reason}"

        super().__init__(
            message=message,
            context={"listing_id": listing_id, "user_id": user_id, "reason": reason},
            **kwargs
        )


class ListingNotPublishedException(MarketplaceException):
    """Raised when trying to access unpublished listing."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Listing not published"

    def __init__(self, listing_id: str = None, **kwargs):
        message = "Listing not published"
        if listing_id:
            message = f"Listing {listing_id} is not published"

        super().__init__(
            message=message,
            context={"listing_id": listing_id},
            **kwargs
        )


class AlreadyPurchasedException(MarketplaceException):
    """Raised when user already owns the asset."""
    status_code = 409
    default_code = ErrorCode.RESOURCE_CONFLICT
    default_message = "Already purchased"

    def __init__(self, listing_id: str = None, user_id: str = None, **kwargs):
        message = "Already purchased"
        if listing_id and user_id:
            message = f"User {user_id} already owns listing {listing_id}"

        super().__init__(
            message=message,
            context={"listing_id": listing_id, "user_id": user_id},
            **kwargs
        )
