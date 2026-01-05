"""
CAPI Providers - Platform-specific implementations

@module services.capi.providers
@version 3.24
"""

import os
import logging
from typing import Dict, Any, List
from abc import ABC, abstractmethod
import httpx

from .models import CAPIEvent, CAPIEventType

logger = logging.getLogger(__name__)


class CAPIProvider(ABC):
    """Abstract base class for CAPI integrations."""
    
    @abstractmethod
    async def send_event(self, event: CAPIEvent) -> bool:
        """Send a single event to the platform."""
        pass
    
    @abstractmethod
    async def send_batch(self, events: List[CAPIEvent]) -> bool:
        """Send multiple events in batch."""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass


class FacebookCAPIProvider(CAPIProvider):
    """Facebook Conversions API provider."""
    
    EVENT_MAPPING = {
        CAPIEventType.USER_REGISTERED: "CompleteRegistration",
        CAPIEventType.SUBSCRIPTION_STARTED: "Subscribe",
        CAPIEventType.CREDITS_PURCHASED: "Purchase",
        CAPIEventType.AI_GENERATION_COMPLETED: "Lead",
        CAPIEventType.PAGE_VIEWED: "PageView",
    }
    
    def __init__(self):
        self.pixel_id = os.environ.get("FACEBOOK_PIXEL_ID")
        self.access_token = os.environ.get("FACEBOOK_CAPI_TOKEN")
        self.api_version = "v18.0"
    
    def is_configured(self) -> bool:
        return bool(self.pixel_id and self.access_token)
    
    async def send_event(self, event: CAPIEvent) -> bool:
        if not self.is_configured():
            return False
        return await self.send_batch([event])
    
    async def send_batch(self, events: List[CAPIEvent]) -> bool:
        if not self.is_configured() or not events:
            return False
        
        fb_events = [self._transform_event(e) for e in events]
        url = f"https://graph.facebook.com/{self.api_version}/{self.pixel_id}/events"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    params={"access_token": self.access_token},
                    json={"data": fb_events},
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"[FB CAPI] Error: {e}")
            return False
    
    def _transform_event(self, event: CAPIEvent) -> Dict[str, Any]:
        fb_name = self.EVENT_MAPPING.get(event.event_name, "Lead")
        
        fb_event = {
            "event_name": fb_name,
            "event_time": event.event_time,
            "event_id": event.event_id,
            "action_source": event.action_source,
        }
        
        if event.event_source_url:
            fb_event["event_source_url"] = event.event_source_url
        
        if event.user_data:
            fb_event["user_data"] = {
                k: v for k, v in {
                    "em": event.user_data.email,
                    "ph": event.user_data.phone,
                    "fn": event.user_data.first_name,
                    "ln": event.user_data.last_name,
                    "external_id": event.user_data.external_id,
                    "client_ip_address": event.user_data.client_ip_address,
                    "client_user_agent": event.user_data.client_user_agent,
                    "fbc": event.user_data.fbc,
                    "fbp": event.user_data.fbp,
                }.items() if v
            }
        
        if event.custom_data:
            fb_event["custom_data"] = event.custom_data
        
        return fb_event


class TikTokEventsAPIProvider(CAPIProvider):
    """TikTok Events API provider."""
    
    EVENT_MAPPING = {
        CAPIEventType.USER_REGISTERED: "CompleteRegistration",
        CAPIEventType.SUBSCRIPTION_STARTED: "Subscribe",
        CAPIEventType.CREDITS_PURCHASED: "CompletePayment",
        CAPIEventType.PAGE_VIEWED: "PageView",
    }
    
    def __init__(self):
        self.pixel_code = os.environ.get("TIKTOK_PIXEL_CODE")
        self.access_token = os.environ.get("TIKTOK_EVENTS_TOKEN")
    
    def is_configured(self) -> bool:
        return bool(self.pixel_code and self.access_token)
    
    async def send_event(self, event: CAPIEvent) -> bool:
        if not self.is_configured():
            return False
        return await self.send_batch([event])
    
    async def send_batch(self, events: List[CAPIEvent]) -> bool:
        if not self.is_configured() or not events:
            return False
        
        url = "https://business-api.tiktok.com/open_api/v1.3/pixel/track/"
        
        try:
            async with httpx.AsyncClient() as client:
                for event in events:
                    payload = self._transform_event(event)
                    response = await client.post(
                        url,
                        headers={"Access-Token": self.access_token},
                        json=payload,
                        timeout=10.0
                    )
                    if response.status_code != 200:
                        return False
                return True
        except Exception as e:
            logger.error(f"[TikTok Events] Error: {e}")
            return False
    
    def _transform_event(self, event: CAPIEvent) -> Dict[str, Any]:
        return {
            "pixel_code": self.pixel_code,
            "event": self.EVENT_MAPPING.get(event.event_name, "SubmitForm"),
            "event_id": event.event_id,
            "timestamp": str(event.event_time),
        }
