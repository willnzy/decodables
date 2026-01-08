"""
Checkout Schemas - Payment checkout models

@module schemas.checkout
"""

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    """Checkout request for Stripe."""
    plan_type: str  # 'credits_100', 'starter', or 'pro'
