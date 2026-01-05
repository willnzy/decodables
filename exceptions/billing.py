"""
Billing Exceptions

@module exceptions.billing
@version 3.24
"""

from typing import Optional
from .base import AppException, ErrorCode


class InsufficientCreditsException(AppException):
    """402: User doesn't have enough credits."""
    status_code = 402
    default_code = ErrorCode.BILLING_INSUFFICIENT_CREDITS
    default_message = "Insufficient credits"
    
    def __init__(self, required: int = None, available: int = None, **kwargs):
        if required is not None and available is not None:
            message = f"Insufficient credits. Required: {required}, Available: {available}"
        else:
            message = "You don't have enough credits for this action"
        super().__init__(
            message=message,
            context={"required": required, "available": available},
            details={"required": required, "available": available},
            **kwargs
        )


class PaymentFailedException(AppException):
    """402: Payment processing failed."""
    status_code = 402
    default_code = ErrorCode.BILLING_PAYMENT_FAILED
    default_message = "Payment processing failed"
    
    def __init__(self, reason: str = None, **kwargs):
        message = "Payment processing failed"
        if reason:
            message = f"Payment failed: {reason}"
        super().__init__(message=message, context={"reason": reason}, **kwargs)


class AlreadyPurchasedException(AppException):
    """200: Item already purchased."""
    status_code = 200
    default_code = ErrorCode.BILLING_ALREADY_PURCHASED
    default_message = "You already own this item"
    
    def __init__(self, item_id: str = None, item_type: str = "item", **kwargs):
        message = f"You already own this {item_type}"
        super().__init__(
            message=message,
            context={"item_id": item_id, "item_type": item_type},
            details={"already_owned": True},
            **kwargs
        )
