"""
CAPI Service - Main service for server-side tracking

@module services.capi.service
@version 3.24
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from .models import CAPIEvent, CAPIEventType, CAPIUserData, hash_email, sha256_hash
from .providers import FacebookCAPIProvider, TikTokEventsAPIProvider

logger = logging.getLogger(__name__)


class CAPIService:
    """
    Unified CAPI service for server-side conversion tracking.
    Sends events to all configured platforms.
    """
    
    def __init__(self):
        self.providers = []
        self._init_providers()
    
    def _init_providers(self):
        """Initialize configured providers."""
        fb = FacebookCAPIProvider()
        if fb.is_configured():
            self.providers.append(fb)
            logger.info("[CAPI] Facebook provider initialized")
        
        tt = TikTokEventsAPIProvider()
        if tt.is_configured():
            self.providers.append(tt)
            logger.info("[CAPI] TikTok provider initialized")
    
    def is_configured(self) -> bool:
        """Check if any provider is configured."""
        return len(self.providers) > 0
    
    def create_user_data(
        self,
        email: str = None,
        phone: str = None,
        user_id: str = None,
        first_name: str = None,
        last_name: str = None,
        ip_address: str = None,
        user_agent: str = None,
        fbc: str = None,
        fbp: str = None,
    ) -> CAPIUserData:
        """Create hashed user data for Advanced Matching."""
        return CAPIUserData(
            email=hash_email(email) if email else None,
            phone=sha256_hash(phone) if phone else None,
            first_name=sha256_hash(first_name) if first_name else None,
            last_name=sha256_hash(last_name) if last_name else None,
            external_id=sha256_hash(user_id) if user_id else None,
            client_ip_address=ip_address,
            client_user_agent=user_agent,
            fbc=fbc,
            fbp=fbp,
        )
    
    async def track_event(
        self,
        event_type: CAPIEventType,
        user_data: CAPIUserData = None,
        event_id: str = None,
        event_source_url: str = None,
        custom_data: Dict[str, Any] = None,
    ) -> bool:
        """Track a conversion event."""
        if not self.providers:
            return False
        
        event = CAPIEvent(
            event_name=event_type,
            event_id=event_id or str(uuid.uuid4()),
            event_time=int(datetime.now(timezone.utc).timestamp()),
            event_source_url=event_source_url,
            user_data=user_data,
            custom_data=custom_data,
        )
        
        success = True
        for provider in self.providers:
            try:
                result = await provider.send_event(event)
                if not result:
                    success = False
            except Exception as e:
                logger.error(f"[CAPI] Provider error: {e}")
                success = False
        
        return success


# Singleton instance
capi_service = CAPIService()


# ==========================================
# Convenience Functions
# ==========================================

async def track_purchase_conversion(
    user_id: str,
    email: str,
    amount: float,
    currency: str = "USD",
    transaction_id: str = None,
    ip_address: str = None,
    user_agent: str = None,
    event_id: str = None,
) -> bool:
    """Track purchase conversion."""
    user_data = capi_service.create_user_data(
        email=email,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return await capi_service.track_event(
        event_type=CAPIEventType.CREDITS_PURCHASED,
        user_data=user_data,
        event_id=event_id,
        custom_data={
            "currency": currency,
            "value": amount,
            "transaction_id": transaction_id,
        },
    )


async def track_signup_conversion(
    user_id: str,
    email: str,
    ip_address: str = None,
    user_agent: str = None,
    event_id: str = None,
) -> bool:
    """Track signup conversion."""
    user_data = capi_service.create_user_data(
        email=email,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return await capi_service.track_event(
        event_type=CAPIEventType.USER_REGISTERED,
        user_data=user_data,
        event_id=event_id,
    )
