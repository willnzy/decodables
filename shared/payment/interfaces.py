"""
Payment Service Interfaces - Abstract base classes for payment providers.

Defines the contracts that all payment service providers must implement.
This enables dependency inversion: domains depend on these abstractions,
not on concrete implementations (Stripe, PayPal, etc.).

@module shared.payment.interfaces
@version 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from .types import (
    CheckoutSession,
    PortalSession,
    SubscriptionInfo,
    PaymentIntent,
    RefundResult,
    WebhookEvent,
    RefundReason,
)


# ==========================================
# Abstract Interfaces
# ==========================================

class IPaymentService(ABC):
    """
    Abstract interface for payment services.

    All payment providers (Stripe, PayPal, etc.) must implement this
    interface to be compatible with the domain layer.
    """

    provider_name: str = "base"

    # ==========================================
    # Checkout & Sessions
    # ==========================================

    @abstractmethod
    def create_checkout_session(
        self,
        user_id: str,
        plan_type: str,
        discount_percent: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CheckoutSession:
        """
        Create a checkout session for payment or subscription.

        Args:
            user_id: User ID
            plan_type: Plan identifier (e.g., "credits_100", "starter", "pro")
            discount_percent: Discount percentage (0-100)
            metadata: Additional metadata to attach

        Returns:
            CheckoutSession with URL or error

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    def create_portal_session(
        self,
        user_id: str,
        customer_id: str
    ) -> PortalSession:
        """
        Create a customer portal session for managing subscriptions.

        Args:
            user_id: User ID
            customer_id: Provider's customer ID

        Returns:
            PortalSession with URL or error

        Raises:
            May raise provider-specific exceptions
        """
        pass

    # ==========================================
    # Subscriptions
    # ==========================================

    @abstractmethod
    def get_subscription_status(
        self,
        customer_id: str
    ) -> Optional[SubscriptionInfo]:
        """
        Get active subscription status for a customer.

        Args:
            customer_id: Provider's customer ID

        Returns:
            SubscriptionInfo or None if no active subscription

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    def get_customer_subscriptions(
        self,
        customer_id: str,
        limit: int = 10
    ) -> List[Any]:
        """
        Get all subscriptions for a customer (active and inactive).

        Args:
            customer_id: Provider's customer ID
            limit: Maximum number of subscriptions to return

        Returns:
            List of subscription objects

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.

        Args:
            subscription_id: Provider's subscription ID
            immediate: If True, cancel immediately; if False, cancel at period end

        Returns:
            Dictionary with success, subscription, and error fields

        Raises:
            May raise provider-specific exceptions
        """
        pass

    # ==========================================
    # Payments & Refunds
    # ==========================================

    @abstractmethod
    def get_customer_payments(
        self,
        customer_id: str,
        limit: int = 10
    ) -> List[PaymentIntent]:
        """
        Get successful payment history for a customer.

        Args:
            customer_id: Provider's customer ID
            limit: Maximum number of payments to return

        Returns:
            List of PaymentIntent objects

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    def get_payment_intent_details(
        self,
        payment_intent_id: str
    ) -> Optional[Any]:
        """
        Get details of a specific payment intent.

        Args:
            payment_intent_id: Provider's payment intent ID

        Returns:
            Payment intent object or None if not found

        Raises:
            May raise provider-specific exceptions
        """
        pass

    @abstractmethod
    def create_refund(
        self,
        payment_intent_id: str,
        amount_cents: Optional[int] = None,
        reason: RefundReason = RefundReason.REQUESTED_BY_CUSTOMER
    ) -> RefundResult:
        """
        Create a refund for a payment.

        Args:
            payment_intent_id: Provider's payment intent ID
            amount_cents: Amount to refund in cents (None for full refund)
            reason: Refund reason

        Returns:
            RefundResult with success status and refund ID

        Raises:
            May raise provider-specific exceptions
        """
        pass

    # ==========================================
    # Webhooks
    # ==========================================

    @abstractmethod
    def construct_webhook_event(
        self,
        payload: bytes,
        signature_header: str
    ) -> WebhookEvent:
        """
        Verify and parse webhook event from provider.

        Args:
            payload: Raw webhook payload
            signature_header: Webhook signature header

        Returns:
            Parsed WebhookEvent

        Raises:
            Exception if signature verification fails
        """
        pass

    # ==========================================
    # Utility
    # ==========================================

    def is_configured(self) -> bool:
        """
        Check if payment provider is properly configured.

        Returns:
            True if provider can be used (API keys configured, etc.)
        """
        return True
