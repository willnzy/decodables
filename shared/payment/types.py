"""
Payment Service Types - Common data structures for payment operations.

@module shared.payment.types
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==========================================
# Enums
# ==========================================

class PaymentMode(str, Enum):
    """Payment session mode."""
    PAYMENT = "payment"  # One-time payment
    SUBSCRIPTION = "subscription"  # Recurring subscription


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"


class RefundReason(str, Enum):
    """Refund reason."""
    DUPLICATE = "duplicate"
    FRAUDULENT = "fraudulent"
    REQUESTED_BY_CUSTOMER = "requested_by_customer"


# ==========================================
# Data Classes
# ==========================================

@dataclass
class CheckoutSession:
    """
    Checkout session result.

    Attributes:
        success: Whether session creation succeeded
        url: Checkout URL to redirect user to
        session_id: Provider session ID
        error: Error message if failed
    """
    success: bool
    url: Optional[str] = None
    session_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PortalSession:
    """
    Customer portal session result.

    Attributes:
        success: Whether portal session creation succeeded
        url: Portal URL to redirect user to
        error: Error message if failed
    """
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SubscriptionInfo:
    """
    Subscription information.

    Attributes:
        status: Subscription status
        tier: User tier (free/starter/pro)
        current_period_end: Subscription period end timestamp
        cancel_at_period_end: Whether subscription will cancel at period end
    """
    status: SubscriptionStatus
    tier: str
    current_period_end: Optional[int] = None
    cancel_at_period_end: bool = False


@dataclass
class PaymentIntent:
    """
    Payment intent information.

    Attributes:
        id: Payment intent ID
        amount: Amount in cents
        currency: Currency code (e.g., "usd")
        status: Payment status
        created: Creation timestamp
        metadata: Additional metadata
    """
    id: str
    amount: int
    currency: str
    status: str
    created: int
    metadata: Dict[str, Any]


@dataclass
class RefundResult:
    """
    Refund operation result.

    Attributes:
        success: Whether refund succeeded
        refund_id: Refund ID if successful
        amount: Refunded amount in cents
        error: Error message if failed
    """
    success: bool
    refund_id: Optional[str] = None
    amount: Optional[int] = None
    error: Optional[str] = None


@dataclass
class WebhookEvent:
    """
    Parsed webhook event.

    Attributes:
        type: Event type (e.g., "checkout.session.completed")
        data: Event data
        id: Event ID
    """
    type: str
    data: Dict[str, Any]
    id: str
