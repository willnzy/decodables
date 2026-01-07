"""
Shared Payment Service Layer - Abstractions for payment providers.

This module provides:
- Abstract interfaces for payment services
- Standardized request/response types
- Provider-agnostic payment operations
- Common data structures for payments, subscriptions, and refunds

@module shared.payment
@version 1.0.0
"""

from .interfaces import IPaymentService

from .types import (
    PaymentMode,
    SubscriptionStatus,
    RefundReason,
    CheckoutSession,
    PortalSession,
    SubscriptionInfo,
    PaymentIntent,
    RefundResult,
    WebhookEvent,
)

__all__ = [
    # Interfaces
    "IPaymentService",
    # Enums
    "PaymentMode",
    "SubscriptionStatus",
    "RefundReason",
    # Types
    "CheckoutSession",
    "PortalSession",
    "SubscriptionInfo",
    "PaymentIntent",
    "RefundResult",
    "WebhookEvent",
]
