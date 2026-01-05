"""
Payment Service
Stripe 支付服务

v3.22: Replaced print statements with structured logging
"""

import stripe
import os
import logging

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000") 

PRICE_MAP = {
    "credits_100": os.environ.get("STRIPE_PRICE_CREDITS_100"),
    "starter": os.environ.get("STRIPE_PRICE_SUB_STARTER"),
    "pro": os.environ.get("STRIPE_PRICE_SUB_PRO")
}

def create_checkout_session(user_id: str, plan_type: str, discount_percent: int = 0):
    """
     Stripe Checkout Session
    
    Args:
        user_id:  ID
        plan_type: 'credits_100', 'starter', 'pro'
        discount_percent:  (0-100)
    """
    price_id = PRICE_MAP.get(plan_type)
    if not price_id:
        raise Exception("Invalid plan type")

    mode = "subscription" if plan_type in ["starter", "pro"] else "payment"

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
        
        # ，
        if discount_percent > 0 and discount_percent <= 100:
            # 
            coupon = stripe.Coupon.create(
                percent_off=discount_percent,
                duration="once",
                name=f"Special Discount {discount_percent}%"
            )
            session_params["discounts"] = [{"coupon": coupon.id}]
        
        # 
        if discount_percent == 0:
            session_params["allow_promotion_codes"] = True
        
        checkout_session = stripe.checkout.Session.create(**session_params)
        return checkout_session.url
    except Exception as e:
        logger.error(f"[Stripe] Checkout session error for user {user_id}: {e}")
        return None

def create_portal_session(user_id: str, customer_id: str):
    """ (/)"""
    if not customer_id:
        raise Exception("No Stripe Customer ID found")
    try:
        portal = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f'{FRONTEND_URL}/dashboard',
        )
        return portal.url
    except Exception as e:
        logger.error(f"[Stripe] Portal session error for customer {customer_id}: {e}")
        return None

def construct_event(payload, sig_header):
    try:
        return stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception as e:
        raise Exception(f"Webhook Error: {str(e)}")

def get_subscription_status(customer_id: str):
    """
    
    Returns: { status: str, tier: str, current_period_end: datetime }
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
            
            #  price_id  tier
            tier = 'free'
            if price_id == PRICE_MAP.get('starter'):
                tier = 'starter'
            elif price_id == PRICE_MAP.get('pro'):
                tier = 'pro'
            
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
    except Exception as e:
        logger.error(f"[Stripe] Get subscription error for customer {customer_id}: {e}")
        return None


# ==========================================
# Admin 
# ==========================================

def get_customer_subscriptions(customer_id: str):
    """
    （）
    """
    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            limit=10
        )
        return subscriptions.data
    except Exception as e:
        logger.error(f"[Stripe] Get subscriptions error for customer {customer_id}: {e}")
        return []

def get_customer_payments(customer_id: str, limit: int = 10):
    """
    （）
    Returns: List of PaymentIntent objects
    """
    try:
        #  PaymentIntents
        payment_intents = stripe.PaymentIntent.list(
            customer=customer_id,
            limit=limit
        )
        
        # 
        successful_payments = [
            pi for pi in payment_intents.data 
            if pi.status == 'succeeded'
        ]
        
        return successful_payments
    except Exception as e:
        logger.error(f"[Stripe] Get payments error for customer {customer_id}: {e}")
        return []

def cancel_subscription(subscription_id: str, immediate: bool = False):
    """
    
    
    Args:
        subscription_id: Stripe  ID
        immediate: True = ，False = 
    
    Returns:
        { success: bool, subscription: Subscription, error: str }
    """
    try:
        if immediate:
            # 
            subscription = stripe.Subscription.cancel(subscription_id)
        else:
            # 
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

def create_refund(payment_intent_id: str, amount_cents: int = None, reason: str = "requested_by_customer"):
    """
    
    
    Args:
        payment_intent_id: Stripe PaymentIntent ID
        amount_cents: （），None 
        reason:  ('duplicate', 'fraudulent', 'requested_by_customer')
    
    Returns:
        { success: bool, refund: Refund, error: str }
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

def get_payment_intent_details(payment_intent_id: str):
    """
     PaymentIntent 
    """
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        logger.error(f"[Stripe] Get payment intent error for {payment_intent_id}: {e}")
        return None
