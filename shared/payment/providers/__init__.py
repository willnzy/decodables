"""
Payment Service Providers - Concrete implementations of IPaymentService.

@module shared.payment.providers
@version 1.0.0
"""

from .stripe_provider import StripePaymentProvider

__all__ = [
    "StripePaymentProvider",
]
