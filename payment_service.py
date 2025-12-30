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

def create_checkout_session(user_id: str, plan_type: str, discount_percent: int = 0):
    """
    创建 Stripe Checkout Session
    
    Args:
        user_id: 用户 ID
        plan_type: 'credits_100', 'starter', 'pro'
        discount_percent: 折扣百分比 (0-100)
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
        
        # 如果有折扣，创建优惠券
        if discount_percent > 0 and discount_percent <= 100:
            # 创建一次性优惠券
            coupon = stripe.Coupon.create(
                percent_off=discount_percent,
                duration="once",
                name=f"Special Discount {discount_percent}%"
            )
            session_params["discounts"] = [{"coupon": coupon.id}]
        
        # 允许促销码
        if discount_percent == 0:
            session_params["allow_promotion_codes"] = True
        
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

def get_subscription_status(customer_id: str):
    """
    获取客户的订阅状态
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
            
            # 根据 price_id 判断 tier
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
        print(f"Get Subscription Error: {e}")
        return None


# ==========================================
# Admin 操作函数
# ==========================================

def get_customer_subscriptions(customer_id: str):
    """
    获取客户的所有订阅（包括活跃和已取消的）
    """
    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            limit=10
        )
        return subscriptions.data
    except Exception as e:
        print(f"Get Subscriptions Error: {e}")
        return []

def get_customer_payments(customer_id: str, limit: int = 10):
    """
    获取客户的付款历史（用于退款）
    Returns: List of PaymentIntent objects
    """
    try:
        # 获取 PaymentIntents
        payment_intents = stripe.PaymentIntent.list(
            customer=customer_id,
            limit=limit
        )
        
        # 过滤出成功的付款
        successful_payments = [
            pi for pi in payment_intents.data 
            if pi.status == 'succeeded'
        ]
        
        return successful_payments
    except Exception as e:
        print(f"Get Customer Payments Error: {e}")
        return []

def cancel_subscription(subscription_id: str, immediate: bool = False):
    """
    取消订阅
    
    Args:
        subscription_id: Stripe 订阅 ID
        immediate: True = 立即取消，False = 在当前计费周期结束时取消
    
    Returns:
        { success: bool, subscription: Subscription, error: str }
    """
    try:
        if immediate:
            # 立即取消
            subscription = stripe.Subscription.cancel(subscription_id)
        else:
            # 在计费周期结束时取消
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
        print(f"Cancel Subscription Error: {e}")
        return {
            "success": False,
            "subscription": None,
            "error": str(e)
        }

def create_refund(payment_intent_id: str, amount_cents: int = None, reason: str = "requested_by_customer"):
    """
    创建退款
    
    Args:
        payment_intent_id: Stripe PaymentIntent ID
        amount_cents: 退款金额（以分为单位），None 表示全额退款
        reason: 退款原因 ('duplicate', 'fraudulent', 'requested_by_customer')
    
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
        print(f"Create Refund Error: {e}")
        return {
            "success": False,
            "refund": None,
            "error": str(e)
        }

def get_payment_intent_details(payment_intent_id: str):
    """
    获取 PaymentIntent 详情
    """
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        print(f"Get PaymentIntent Error: {e}")
        return None
