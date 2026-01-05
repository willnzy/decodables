"""
CAPI Package - Server-side conversion tracking

@package services.capi
@version 3.24
"""

from .models import (
    CAPIEventType,
    CAPIUserData,
    CAPIEvent,
    sha256_hash,
    hash_email,
    hash_phone,
)
from .providers import (
    CAPIProvider,
    FacebookCAPIProvider,
    TikTokEventsAPIProvider,
)
from .service import (
    CAPIService,
    capi_service,
    track_purchase_conversion,
    track_signup_conversion,
)

__all__ = [
    # Models
    'CAPIEventType', 'CAPIUserData', 'CAPIEvent',
    'sha256_hash', 'hash_email', 'hash_phone',
    # Providers
    'CAPIProvider', 'FacebookCAPIProvider', 'TikTokEventsAPIProvider',
    # Service
    'CAPIService', 'capi_service',
    'track_purchase_conversion', 'track_signup_conversion',
]
