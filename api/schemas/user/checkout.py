"""
Checkout Schemas - Payment checkout models

@module schemas.checkout
"""

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    """Checkout request for Stripe."""
    plan_type: str  # 't2', 't3', 'credits_100', 'credits_500', 'credits_2000'
