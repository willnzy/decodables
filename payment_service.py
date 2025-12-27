import stripe
import os

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000") 

PRICE_MAP = {
    "credits_100": os.environ.get("STRIPE_PRICE_CREDITS_100"),
    "starter": os.environ.get("STRIPE_PRICE_SUB_STARTER"),
    "pro": os.environ.get("STRIPE_PRICE_SUB_PRO")
}

def create_checkout_session(user_id: str, plan_type: str):
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
            "success_url": f'{FRONTEND_URL}/dashboard?success=true',
            "cancel_url": f'{FRONTEND_URL}/dashboard?canceled=true',
            "metadata": {"user_id": user_id, "plan_type": plan_type},
        }
        
        checkout_session = stripe.checkout.Session.create(**session_params)
        return checkout_session.url
    except Exception as e:
        print(f"Stripe Checkout Error: {e}")
        return None

def create_portal_session(user_id: str, customer_id: str):
    """创建客户门户链接 (用于取消订阅/换卡)"""
    if not customer_id:
        raise Exception("No Stripe Customer ID found")
    try:
        portal = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f'{FRONTEND_URL}/dashboard',
        )
        return portal.url
    except Exception as e:
        print(f"Portal Error: {e}")
        return None

def construct_event(payload, sig_header):
    try:
        return stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception as e:
        raise Exception(f"Webhook Error: {str(e)}")