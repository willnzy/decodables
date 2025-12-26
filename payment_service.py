# payment_service.py
import stripe
import os

# -------- Debug Start: 看看变量到底读到没 --------
print("DEBUG: Checking Price IDs...")
print(f"Credits 100 ID: {os.environ.get('STRIPE_PRICE_CREDITS_100')}")
print(f"Starter ID: {os.environ.get('STRIPE_PRICE_SUB_STARTER')}")
# -----------------------------------------------

# 从环境变量读取配置
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# 前端成功/失败跳转页面 (部署后需改为真实域名)
# 如果还没前端域名，先填 http://localhost:3000
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000") 

# 价格映射表 (Key 是前端传的 plan_name, Value 是 Stripe Price ID)
PRICE_MAP = {
    "credits_100": os.environ.get("STRIPE_PRICE_CREDITS_100"), # 您刚才创建的 100 积分包
    "starter": os.environ.get("STRIPE_PRICE_SUB_STARTER"),
    "pro": os.environ.get("STRIPE_PRICE_SUB_PRO")
}

def create_checkout_session(user_id: str, plan_type: str):
    """创建支付跳转链接"""
    price_id = PRICE_MAP.get(plan_type)
    if not price_id:
        raise Exception("Invalid plan type")

    # 判断是 订阅模式 还是 一次性购买
    mode = "subscription" if plan_type in ["starter", "pro"] else "payment"

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode=mode,
            success_url=f'{FRONTEND_URL}/dashboard?success=true',
            cancel_url=f'{FRONTEND_URL}/dashboard?canceled=true',
            # 关键：把 user_id 塞进 metadata，这样回调时才知道是谁付的钱
            metadata={
                "user_id": user_id,
                "plan_type": plan_type
            },
            # 如果是订阅，允许自动扣款
            subscription_data={} if mode == "subscription" else None
        )
        return checkout_session.url
    except Exception as e:
        print(f"Stripe Error: {e}")
        return None

def construct_event(payload, sig_header):
    """验证 Webhook 签名"""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
        return event
    except ValueError as e:
        raise Exception("Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise Exception("Invalid signature")