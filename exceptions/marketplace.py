"""
Marketplace Exceptions

@module exceptions.marketplace
@version 3.24
"""

from typing import Optional
from .base import AppException, ErrorCode


class ListingNotApprovedException(AppException):
    """400: Listing not approved for public viewing."""
    status_code = 400
    default_code = ErrorCode.MARKETPLACE_NOT_APPROVED
    default_message = "This listing is not yet approved"
    
    def __init__(self, listing_id: str = None, **kwargs):
        super().__init__(
            context={"listing_id": listing_id},
            **kwargs
        )


class ListingNotPublicException(AppException):
    """400: Listing is not public."""
    status_code = 400
    default_code = ErrorCode.MARKETPLACE_NOT_PUBLIC
    default_message = "This listing is not publicly available"
    
    def __init__(self, listing_id: str = None, **kwargs):
        super().__init__(
            context={"listing_id": listing_id},
            **kwargs
        )


class CannotEditPendingException(AppException):
    """400: Cannot edit listing in pending state."""
    status_code = 400
    default_code = ErrorCode.MARKETPLACE_CANNOT_EDIT
    default_message = "Cannot edit a listing while it's under review"
    
    def __init__(self, listing_id: str = None, current_status: str = None, **kwargs):
        super().__init__(
            context={"listing_id": listing_id, "current_status": current_status},
            **kwargs
        )


class SelfPurchaseException(AppException):
    """400: Cannot purchase own listing."""
    status_code = 400
    default_code = ErrorCode.MARKETPLACE_SELF_PURCHASE
    default_message = "You cannot purchase your own listing"
    
    def __init__(self, listing_id: str = None, **kwargs):
        message = "You cannot purchase your own listing"
        super().__init__(
            message=message,
            context={"listing_id": listing_id},
            details={"is_own_listing": True},
            **kwargs
        )
