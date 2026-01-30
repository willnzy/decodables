"""
Stripe Payment Provider - Concrete implementation of IPaymentService.

This provider wraps the existing services/payment_service.py functions
to provide a class-based interface compatible with the shared layer.

@module shared.payment.providers.stripe_provider
@version 1.0.0
"""

from typing import Optional, List, Dict, Any
import logging

# Import existing payment service functions
import domains.billing.payment_service as stripe_service

# Import shared layer types
from shared.payment.interfaces import IPaymentService
from shared.payment.types import (
    CheckoutSession,
    PortalSession,
    SubscriptionInfo,
    SubscriptionStatus,
    PaymentIntent,
    RefundResult,
    RefundReason,
    WebhookEvent,
)

logger = logging.getLogger(__name__)


class StripePaymentProvider(IPaymentService):
    """
    Stripe payment provider implementation.

    This class wraps existing services/payment_service.py functions
    to provide a clean interface that matches IPaymentService.

    All business logic remains in services/payment_service.py - this
    is purely an adapter for interface compatibility.
    """

    provider_name: str = "stripe"

    def __init__(self):
        """Initialize Stripe provider (no state needed)."""
        pass

    # ==========================================
    # Checkout & Sessions
    # ==========================================

    def create_checkout_session(
        self,
        user_id: str,
        plan_type: str,
        discount_percent: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        customer_id: Optional[str] = None,
    ) -> CheckoutSession:
        """
        Create a checkout session for payment or subscription.

        Wraps: services.payment_service.create_checkout_session()

        Args:
            customer_id: WS6 (#1) — Stripe Customer ID to bind session to existing customer
        """
        try:
            url = stripe_service.create_checkout_session(
                user_id=user_id,
                plan_type=plan_type,
                discount_percent=discount_percent,
                customer_id=customer_id,
            )

            if url:
                return CheckoutSession(
                    success=True,
                    url=url,
                    session_id=None,  # Existing service doesn't return session_id
                )
            else:
                return CheckoutSession(
                    success=False,
                    error="Failed to create checkout session"
                )

        except Exception as e:
            logger.error(f"[StripeProvider] Checkout session error: {e}")
            return CheckoutSession(
                success=False,
                error=str(e)
            )

    def create_portal_session(
        self,
        user_id: str,
        customer_id: str
    ) -> PortalSession:
        """
        Create a customer portal session for managing subscriptions.

        Wraps: services.payment_service.create_portal_session()
        """
        try:
            url = stripe_service.create_portal_session(
                user_id=user_id,
                customer_id=customer_id
            )

            if url:
                return PortalSession(success=True, url=url)
            else:
                return PortalSession(
                    success=False,
                    error="Failed to create portal session"
                )

        except Exception as e:
            logger.error(f"[StripeProvider] Portal session error: {e}")
            return PortalSession(success=False, error=str(e))

    # ==========================================
    # Subscriptions
    # ==========================================

    def get_subscription_status(
        self,
        customer_id: str
    ) -> Optional[SubscriptionInfo]:
        """
        Get active subscription status for a customer.

        Wraps: services.payment_service.get_subscription_status()
        """
        try:
            result = stripe_service.get_subscription_status(customer_id)

            if result is None:
                return None

            # Convert to SubscriptionInfo
            status_str = result.get("status", "inactive")
            try:
                status = SubscriptionStatus(status_str)
            except ValueError:
                status = SubscriptionStatus.INACTIVE

            return SubscriptionInfo(
                status=status,
                tier=result.get("tier", "t1"),
                current_period_end=result.get("current_period_end"),
                cancel_at_period_end=False  # Not provided by existing service
            )

        except Exception as e:
            logger.error(f"[StripeProvider] Get subscription error: {e}")
            return None

    def get_customer_subscriptions(
        self,
        customer_id: str,
        limit: int = 10
    ) -> List[Any]:
        """
        Get all subscriptions for a customer.

        Wraps: services.payment_service.get_customer_subscriptions()
        """
        try:
            return stripe_service.get_customer_subscriptions(customer_id)
        except Exception as e:
            logger.error(f"[StripeProvider] Get subscriptions error: {e}")
            return []

    def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.

        Wraps: services.payment_service.cancel_subscription()
        """
        try:
            return stripe_service.cancel_subscription(
                subscription_id=subscription_id,
                immediate=immediate
            )
        except Exception as e:
            logger.error(f"[StripeProvider] Cancel subscription error: {e}")
            return {
                "success": False,
                "subscription": None,
                "error": str(e)
            }

    # ==========================================
    # Payments & Refunds
    # ==========================================

    def get_customer_payments(
        self,
        customer_id: str,
        limit: int = 10
    ) -> List[PaymentIntent]:
        """
        Get successful payment history for a customer.

        Wraps: services.payment_service.get_customer_payments()
        """
        try:
            raw_payments = stripe_service.get_customer_payments(
                customer_id=customer_id,
                limit=limit
            )

            # Convert to PaymentIntent objects
            payments = []
            for pi in raw_payments:
                payments.append(PaymentIntent(
                    id=pi.id,
                    amount=pi.amount,
                    currency=pi.currency,
                    status=pi.status,
                    created=pi.created,
                    metadata=dict(pi.metadata) if pi.metadata else {}
                ))

            return payments

        except Exception as e:
            logger.error(f"[StripeProvider] Get payments error: {e}")
            return []

    def get_payment_intent_details(
        self,
        payment_intent_id: str
    ) -> Optional[Any]:
        """
        Get details of a specific payment intent.

        Wraps: services.payment_service.get_payment_intent_details()
        """
        try:
            return stripe_service.get_payment_intent_details(payment_intent_id)
        except Exception as e:
            logger.error(f"[StripeProvider] Get payment intent error: {e}")
            return None

    def create_refund(
        self,
        payment_intent_id: str,
        amount_cents: Optional[int] = None,
        reason: RefundReason = RefundReason.REQUESTED_BY_CUSTOMER
    ) -> RefundResult:
        """
        Create a refund for a payment.

        Wraps: services.payment_service.create_refund()
        """
        try:
            result = stripe_service.create_refund(
                payment_intent_id=payment_intent_id,
                amount_cents=amount_cents,
                reason=reason.value  # Convert enum to string
            )

            if result["success"]:
                return RefundResult(
                    success=True,
                    refund_id=result["refund"].id if result["refund"] else None,
                    amount=result["refund"].amount if result["refund"] else None
                )
            else:
                return RefundResult(
                    success=False,
                    error=result.get("error", "Unknown error")
                )

        except Exception as e:
            logger.error(f"[StripeProvider] Create refund error: {e}")
            return RefundResult(success=False, error=str(e))

    # ==========================================
    # Webhooks
    # ==========================================

    def construct_webhook_event(
        self,
        payload: bytes,
        signature_header: str
    ) -> WebhookEvent:
        """
        Verify and parse webhook event from Stripe.

        Wraps: services.payment_service.construct_event()
        """
        try:
            event = stripe_service.construct_event(payload, signature_header)

            return WebhookEvent(
                type=event.type,
                data=event.data.to_dict() if hasattr(event.data, 'to_dict') else dict(event.data),
                id=event.id
            )

        except Exception as e:
            logger.error(f"[StripeProvider] Webhook construction error: {e}")
            raise  # Re-raise for webhook validation failures

    # ==========================================
    # Utility
    # ==========================================

    def is_configured(self) -> bool:
        """
        Check if Stripe is properly configured.

        Returns True if STRIPE_SECRET_KEY is set.
        """
        import os
        return bool(os.environ.get("STRIPE_SECRET_KEY"))
