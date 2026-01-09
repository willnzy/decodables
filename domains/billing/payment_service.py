"""
Payment Service
Stripe 支付服务

@version 3.24

Changes in v3.24:
- P1: Added validate_config() for startup price ID validation
- P2: Implemented coupon caching to avoid resource leak (get_or_create_coupon)
- P3: Added idempotency_key support to create_checkout_session
- P4: Added retry logic with exponential backoff for transient Stripe errors

v3.23: Added get_tier_from_price_id() for config-based tier mapping
v3.22: Replaced print statements with structured logging
"""

import stripe
import os
import logging
import time
import hashlib
from functools import wraps
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

PRICE_MAP = {
    "credits_100": os.environ.get("STRIPE_PRICE_CREDITS_100"),
    "credits_500": os.environ.get("STRIPE_PRICE_CREDITS_500"),
    "credits_2000": os.environ.get("STRIPE_PRICE_CREDITS_2000"),
    "starter": os.environ.get("STRIPE_PRICE_SUB_STARTER"),
    "pro": os.environ.get("STRIPE_PRICE_SUB_PRO")
}

# Credit amounts for each plan
CREDITS_AMOUNT_MAP = {
    "credits_100": 100,
    "credits_500": 500,
    "credits_2000": 2000,
}

# Coupon cache: discount_percent -> coupon_id
_coupon_cache: Dict[int, str] = {}


# ==========================================
# Retry Decorator for Stripe API
# ==========================================

def retry_on_stripe_error(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    retryable_errors: tuple = (
        stripe.error.APIConnectionError,
        stripe.error.RateLimitError,
    )
) -> Callable:
    """
    Decorator for retrying Stripe API calls on transient errors.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for exponential backoff
        retryable_errors: Tuple of Stripe error types to retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_errors as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"[Stripe] {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"[Stripe] {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                except stripe.error.StripeError as e:
                    # Non-retryable Stripe errors
                    logger.error(f"[Stripe] {func.__name__} failed (non-retryable): {e}")
                    raise

            raise last_exception

        return wrapper
    return decorator


# ==========================================
# Configuration Validation
# ==========================================

def validate_config() -> Dict[str, Any]:
    """
    Validate Stripe configuration at startup.

    Call this function during application startup to ensure all required
    environment variables are set.

    Returns:
        Dict with validation status and missing keys

    Raises:
        ValueError: If critical configuration is missing (in strict mode)
    """
    missing_keys = []
    warnings = []

    # Check Stripe API key
    if not stripe.api_key:
        missing_keys.append("STRIPE_SECRET_KEY")

    # Check webhook secret
    if not WEBHOOK_SECRET:
        warnings.append("STRIPE_WEBHOOK_SECRET (webhooks will fail)")

    # Check price IDs
    required_prices = ["credits_100", "starter", "pro"]
    optional_prices = ["credits_500", "credits_2000"]

    for plan in required_prices:
        if not PRICE_MAP.get(plan):
            missing_keys.append(f"STRIPE_PRICE_{plan.upper()}" if plan.startswith("credits") else f"STRIPE_PRICE_SUB_{plan.upper()}")

    for plan in optional_prices:
        if not PRICE_MAP.get(plan):
            warnings.append(f"STRIPE_PRICE_{plan.upper()} (optional)")

    # Log results
    if missing_keys:
        logger.error(f"[Stripe] Missing required config: {', '.join(missing_keys)}")
    if warnings:
        logger.warning(f"[Stripe] Missing optional config: {', '.join(warnings)}")

    is_valid = len(missing_keys) == 0

    if is_valid:
        logger.info("[Stripe] Configuration validated successfully")

    return {
        "valid": is_valid,
        "missing_required": missing_keys,
        "missing_optional": [w.split(" ")[0] for w in warnings],
    }


def is_configured() -> bool:
    """Check if Stripe is properly configured."""
    return bool(stripe.api_key) and bool(PRICE_MAP.get("starter")) and bool(PRICE_MAP.get("pro"))


# ==========================================
# Coupon Management
# ==========================================

def get_or_create_coupon(discount_percent: int) -> Optional[str]:
    """
    Get existing coupon ID or create a new one.

    Caches coupons to avoid creating duplicate Stripe coupon objects.

    Args:
        discount_percent: Discount percentage (1-100)

    Returns:
        Coupon ID or None if creation fails
    """
    if discount_percent <= 0 or discount_percent > 100:
        return None

    # Check cache first
    if discount_percent in _coupon_cache:
        coupon_id = _coupon_cache[discount_percent]
        # Verify coupon still exists in Stripe
        try:
            stripe.Coupon.retrieve(coupon_id)
            return coupon_id
        except stripe.error.InvalidRequestError:
            # Coupon was deleted, remove from cache
            del _coupon_cache[discount_percent]

    # Create new coupon with deterministic ID
    coupon_id = f"DISCOUNT_{discount_percent}_PERCENT"

    try:
        # Try to retrieve existing coupon first
        try:
            coupon = stripe.Coupon.retrieve(coupon_id)
            _coupon_cache[discount_percent] = coupon.id
            return coupon.id
        except stripe.error.InvalidRequestError:
            pass  # Coupon doesn't exist, create it

        # Create new coupon
        coupon = stripe.Coupon.create(
            id=coupon_id,
            percent_off=discount_percent,
            duration="once",
            name=f"{discount_percent}% Discount"
        )
        _coupon_cache[discount_percent] = coupon.id
        logger.info(f"[Stripe] Created coupon: {coupon_id}")
        return coupon.id

    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Failed to get/create coupon {discount_percent}%: {e}")
        return None


# ==========================================
# Tier Mapping
# ==========================================

def get_tier_from_price_id(price_id: str) -> str:
    """
    Get tier name from Stripe price ID.

    Uses PRICE_MAP for config-based lookup instead of fragile string matching.

    Args:
        price_id: Stripe price ID

    Returns:
        Tier name ('starter', 'pro') or 'free' if not found
    """
    if not price_id:
        return 'free'

    # Build reverse map and lookup
    for tier, configured_price_id in PRICE_MAP.items():
        if configured_price_id and price_id == configured_price_id:
            # credits plans return 'free' (they don't change tier)
            return tier if tier in ['starter', 'pro'] else 'free'

    # Fallback: log warning and return free
    logger.warning(f"[Payment] Unknown price_id: {price_id}, defaulting to 'free'")
    return 'free'


def get_credits_amount(plan_type: str) -> int:
    """
    Get credits amount for a plan type.

    Args:
        plan_type: Plan type (credits_100, credits_500, credits_2000)

    Returns:
        Number of credits or 0 if not a credit plan
    """
    return CREDITS_AMOUNT_MAP.get(plan_type, 0)


# ==========================================
# Checkout Session
# ==========================================

@retry_on_stripe_error()
def create_checkout_session(
    user_id: str,
    plan_type: str,
    discount_percent: int = 0,
    idempotency_key: Optional[str] = None
) -> Optional[str]:
    """
    Create Stripe Checkout Session.

    Args:
        user_id: User ID
        plan_type: 'credits_100', 'credits_500', 'credits_2000', 'starter', 'pro'
        discount_percent: Discount percentage (0-100)
        idempotency_key: Optional key to prevent duplicate sessions

    Returns:
        Checkout session URL or None on failure
    """
    price_id = PRICE_MAP.get(plan_type)
    if not price_id:
        logger.error(f"[Stripe] Invalid plan type: {plan_type}")
        raise ValueError(f"Invalid plan type: {plan_type}")

    mode = "subscription" if plan_type in ["starter", "pro"] else "payment"

    # Generate idempotency key if not provided
    if not idempotency_key:
        # Create deterministic key based on user, plan, and approximate time (1-minute window)
        time_bucket = int(time.time() / 60)  # 1-minute window
        key_base = f"{user_id}:{plan_type}:{time_bucket}"
        idempotency_key = hashlib.sha256(key_base.encode()).hexdigest()[:32]

    try:
        # Build session params
        session_params = {
            "payment_method_types": ['card'],
            "line_items": [{'price': price_id, 'quantity': 1}],
            "mode": mode,
            "success_url": f'{FRONTEND_URL}/dashboard?success=true&plan={plan_type}',
            "cancel_url": f'{FRONTEND_URL}/dashboard?canceled=true',
            "metadata": {"user_id": user_id, "plan_type": plan_type},
        }

        # Apply discount coupon (using cached coupon)
        if discount_percent > 0 and discount_percent <= 100:
            coupon_id = get_or_create_coupon(discount_percent)
            if coupon_id:
                session_params["discounts"] = [{"coupon": coupon_id}]
            else:
                logger.warning(f"[Stripe] Could not apply {discount_percent}% discount for user {user_id}")

        # Allow promotion codes if no discount applied
        if discount_percent == 0:
            session_params["allow_promotion_codes"] = True

        # Create checkout session with idempotency key
        checkout_session = stripe.checkout.Session.create(
            **session_params,
            idempotency_key=idempotency_key
        )
        return checkout_session.url

    except stripe.error.IdempotencyError as e:
        # Same idempotency key was used with different params
        logger.warning(f"[Stripe] Idempotency conflict for user {user_id}: {e}")
        return None
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Checkout session error for user {user_id}: {e}")
        return None


@retry_on_stripe_error()
def create_portal_session(user_id: str, customer_id: str) -> Optional[str]:
    """
    Create Stripe billing portal session.

    Args:
        user_id: User ID (for logging)
        customer_id: Stripe customer ID

    Returns:
        Portal session URL or None on failure
    """
    if not customer_id:
        raise ValueError("No Stripe Customer ID found")

    try:
        portal = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f'{FRONTEND_URL}/dashboard',
        )
        return portal.url
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Portal session error for customer {customer_id}: {e}")
        return None


def construct_event(payload: bytes, sig_header: str) -> Dict:
    """
    Construct and verify Stripe webhook event.

    Args:
        payload: Raw request body
        sig_header: Stripe-Signature header value

    Returns:
        Verified event dict

    Raises:
        Exception: If signature verification fails
    """
    try:
        return stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"[Stripe] Webhook signature verification failed: {e}")
        raise Exception(f"Webhook signature verification failed: {str(e)}")
    except Exception as e:
        raise Exception(f"Webhook Error: {str(e)}")


# ==========================================
# Subscription Management
# ==========================================

@retry_on_stripe_error()
def get_subscription_status(customer_id: str) -> Optional[Dict]:
    """
    Get customer subscription status.

    Args:
        customer_id: Stripe customer ID

    Returns:
        Dict with status, tier, and current_period_end
    """
    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status='active',
            limit=1
        )

        if subscriptions.data:
            sub = subscriptions.data[0]
            price_id = sub['items']['data'][0]['price']['id']
            tier = get_tier_from_price_id(price_id)

            return {
                "status": sub.status,
                "tier": tier,
                "current_period_end": sub.current_period_end
            }

        return {
            "status": "inactive",
            "tier": "free",
            "current_period_end": None
        }
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Get subscription error for customer {customer_id}: {e}")
        return None


# ==========================================
# Admin Functions
# ==========================================

@retry_on_stripe_error()
def get_customer_subscriptions(customer_id: str) -> list:
    """Get all subscriptions for a customer."""
    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            limit=10
        )
        return subscriptions.data
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Get subscriptions error for customer {customer_id}: {e}")
        return []


@retry_on_stripe_error()
def get_customer_payments(customer_id: str, limit: int = 10, timeout: int = 30) -> list:
    """
    Get successful payments for a customer.

    Args:
        customer_id: Stripe customer ID
        limit: Maximum number of payment intents to retrieve
        timeout: Request timeout in seconds (default: 30, fixes USER-HIGH-3)

    Returns:
        List of successful payment intents

    v3.26 (USER-HIGH-3): Added timeout parameter to prevent hanging
    """
    try:
        payment_intents = stripe.PaymentIntent.list(
            customer=customer_id,
            limit=limit,
            timeout=timeout  # v3.26: Added timeout to prevent hanging
        )

        successful_payments = [
            pi for pi in payment_intents.data
            if pi.status == 'succeeded'
        ]

        return successful_payments
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Get payments error for customer {customer_id}: {e}")
        return []


def cancel_subscription(subscription_id: str, immediate: bool = False) -> Dict:
    """
    Cancel a subscription.

    Args:
        subscription_id: Stripe subscription ID
        immediate: If True, cancel immediately. If False, cancel at period end.

    Returns:
        Dict with success, subscription, and error
    """
    try:
        if immediate:
            subscription = stripe.Subscription.cancel(subscription_id)
        else:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )

        return {
            "success": True,
            "subscription": subscription,
            "error": None
        }
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Cancel subscription error for {subscription_id}: {e}")
        return {
            "success": False,
            "subscription": None,
            "error": str(e)
        }


def create_refund(
    payment_intent_id: str,
    amount_cents: Optional[int] = None,
    reason: str = "requested_by_customer"
) -> Dict:
    """
    Create a refund for a payment.

    Args:
        payment_intent_id: Stripe PaymentIntent ID
        amount_cents: Amount to refund in cents (None for full refund)
        reason: Refund reason ('duplicate', 'fraudulent', 'requested_by_customer')

    Returns:
        Dict with success, refund, and error
    """
    try:
        refund_params = {
            "payment_intent": payment_intent_id,
            "reason": reason
        }

        if amount_cents is not None:
            refund_params["amount"] = amount_cents

        refund = stripe.Refund.create(**refund_params)

        return {
            "success": True,
            "refund": refund,
            "error": None
        }
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Create refund error for {payment_intent_id}: {e}")
        return {
            "success": False,
            "refund": None,
            "error": str(e)
        }


@retry_on_stripe_error()
def get_payment_intent_details(payment_intent_id: str):
    """Get PaymentIntent details."""
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Get payment intent error for {payment_intent_id}: {e}")
        return None
