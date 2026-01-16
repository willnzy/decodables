"""
Subscription Domain Exceptions.

@module domains.subscriptions.exceptions
@version 1.0.0

Domain-specific exceptions for subscription operations.
API layer catches these and converts to HTTPException.
"""

from core.exceptions import AppException, ErrorCode


class SubscriptionException(AppException):
    """Base exception for subscriptions domain."""
    pass


# ==========================================
# User Verification Exceptions
# ==========================================

class UserNotFoundException(SubscriptionException):
    """User not found in database."""
    status_code = 404
    default_code = ErrorCode.USER_NOT_FOUND
    default_message = "User not found"


class UserCodeMissingException(SubscriptionException):
    """User has no user code assigned."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "User has no user code assigned"


class UserCodeMismatchException(SubscriptionException):
    """User code does not match stored value."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "User code does not match. Please verify the user code."


class UserEmailMismatchException(SubscriptionException):
    """User email does not match stored value."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "User email does not match"


class NoStripeCustomerException(SubscriptionException):
    """User has no Stripe customer ID."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "User has no Stripe customer ID"


# ==========================================
# Payment/Refund Exceptions
# ==========================================

class PaymentNotFoundException(SubscriptionException):
    """Payment not found in Stripe."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Payment not found"


class PaymentOwnershipException(SubscriptionException):
    """Payment does not belong to this user."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Payment does not belong to this user"


class PaymentStatusException(SubscriptionException):
    """Payment status does not allow requested operation."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Cannot perform operation on payment with current status"

    def __init__(self, status: str = None, **kwargs):
        if status:
            message = f"Cannot refund payment with status: {status}"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)


class AlreadyRefundedException(SubscriptionException):
    """Payment has already been fully refunded."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Payment has already been fully refunded"


class InvalidRefundAmountException(SubscriptionException):
    """Refund amount is invalid."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Invalid refund amount"

    def __init__(self, amount: int = None, refundable: int = None, **kwargs):
        if amount is not None and amount <= 0:
            message = "Refund amount must be positive"
        elif amount and refundable:
            message = f"Refund amount ({amount}) exceeds refundable amount ({refundable})"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)


class RefundFailedException(SubscriptionException):
    """Refund operation failed."""
    status_code = 400
    default_code = ErrorCode.PAYMENT_FAILED
    default_message = "Refund operation failed"


# ==========================================
# Subscription Exceptions
# ==========================================

class SubscriptionNotFoundException(SubscriptionException):
    """Subscription not found in Stripe."""
    status_code = 404
    default_code = ErrorCode.RESOURCE_NOT_FOUND
    default_message = "Subscription not found or access denied"


class SubscriptionOwnershipException(SubscriptionException):
    """Subscription does not belong to this user."""
    status_code = 403
    default_code = ErrorCode.AUTH_FORBIDDEN
    default_message = "Subscription does not belong to this user"


class SubscriptionStatusException(SubscriptionException):
    """Subscription status does not allow requested operation."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Cannot perform operation on subscription with current status"

    def __init__(self, status: str = None, operation: str = None, **kwargs):
        if status and operation:
            message = f"Cannot {operation} subscription with status: {status}"
        elif status:
            message = f"Cannot perform operation on subscription with status: {status}"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)


class AlreadyCancelScheduledException(SubscriptionException):
    """Subscription is already scheduled for cancellation."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Subscription is already scheduled for cancellation"


class SubscriptionCancelFailedException(SubscriptionException):
    """Failed to cancel subscription."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Failed to cancel subscription"


class SubscriptionModifyFailedException(SubscriptionException):
    """Failed to modify subscription."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Subscription modification failed"


class NoActiveSubscriptionException(SubscriptionException):
    """No active subscription found."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "No active subscription found to downgrade"


# ==========================================
# Tier Exceptions
# ==========================================

class InvalidTierException(SubscriptionException):
    """Invalid tier specified."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Invalid tier"

    def __init__(self, tier: str = None, valid_tiers: list = None, **kwargs):
        if tier and valid_tiers:
            message = f"Invalid target tier: {tier}. Must be one of: {', '.join(sorted(valid_tiers))}"
        elif tier:
            message = f"Invalid tier: {tier}"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)


class InvalidDowngradePathException(SubscriptionException):
    """Invalid downgrade path (cannot upgrade via downgrade)."""
    status_code = 400
    default_code = ErrorCode.BAD_REQUEST
    default_message = "Invalid downgrade path"

    def __init__(self, from_tier: str = None, to_tier: str = None, **kwargs):
        if from_tier and to_tier:
            message = f"Cannot downgrade from {from_tier} to {to_tier}"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)


# ==========================================
# Configuration Exceptions
# ==========================================

class PriceIdNotConfiguredException(SubscriptionException):
    """Stripe Price ID not configured."""
    status_code = 500
    default_code = ErrorCode.SERVICE_UNAVAILABLE
    default_message = "Price ID not configured"

    def __init__(self, tier: str = None, **kwargs):
        if tier:
            message = f"{tier} price ID not configured"
        else:
            message = self.default_message
        super().__init__(message=message, **kwargs)
