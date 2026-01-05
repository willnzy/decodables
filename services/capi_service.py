"""
Conversions API (CAPI) Service - Server-Side Event Tracking

This service provides architecture for server-side event tracking integrations:
- Facebook Conversions API (CAPI)
- TikTok Events API
- Google Server-Side GTM

Purpose:
- Improve conversion attribution accuracy
- Bypass browser tracking restrictions (ITP, ad blockers)
- Enable Event Deduplication with browser-side tracking
- Support Advanced Matching with hashed user data

Architecture:
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Frontend      │    │     Backend      │    │   Ad Platforms   │
│   (Browser)     │    │   (This File)    │    │                  │
├─────────────────┤    ├──────────────────┤    ├──────────────────┤
│ dataLayer.push  │───▶│ Store event_id   │    │                  │
│ (GTM → GA4/FB)  │    │ + user data      │    │                  │
│                 │    │        │         │    │                  │
│                 │    │        ▼         │    │                  │
│                 │    │ capi_service.py  │───▶│ Facebook CAPI    │
│                 │    │ (server-side)    │    │ TikTok Events API│
│                 │    │                  │    │ Server-Side GTM  │
└─────────────────┘    └──────────────────┘    └──────────────────┘

event_id ensures deduplication: Same event sent from both browser & server
will be counted only once by the ad platform.

@module services/capi_service
"""

import os
import hashlib
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ==========================================
# Event Types (Platform-Agnostic)
# ==========================================

class CAPIEventType(str, Enum):
    """
    Standard event types for CAPI.
    Maps to platform-specific events (FB: Purchase, TikTok: CompletePayment, etc.)
    """
    # User lifecycle
    USER_REGISTERED = "user_registered"
    USER_LOGGED_IN = "user_logged_in"
    
    # Monetization
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_UPGRADED = "subscription_upgraded"
    CREDITS_PURCHASED = "credits_purchased"
    MARKETPLACE_PURCHASED = "marketplace_purchased"
    
    # Engagement
    AI_GENERATION_STARTED = "ai_generation_started"
    AI_GENERATION_COMPLETED = "ai_generation_completed"
    PROJECT_CREATED = "project_created"
    PROJECT_EXPORTED = "project_exported"
    
    # Page views
    PAGE_VIEWED = "page_viewed"


# ==========================================
# Data Classes
# ==========================================

@dataclass
class CAPIUserData:
    """
    User data for Advanced Matching.
    All fields should be hashed (SHA256) before sending to CAPI.
    """
    email: Optional[str] = None  # SHA256 hashed
    phone: Optional[str] = None  # SHA256 hashed, E.164 format
    first_name: Optional[str] = None  # SHA256 hashed, lowercase
    last_name: Optional[str] = None  # SHA256 hashed, lowercase
    external_id: Optional[str] = None  # SHA256 hashed (user_id or user_code)
    client_ip_address: Optional[str] = None  # Not hashed
    client_user_agent: Optional[str] = None  # Not hashed
    fbc: Optional[str] = None  # Facebook click ID (_fbc cookie)
    fbp: Optional[str] = None  # Facebook browser ID (_fbp cookie)


@dataclass
class CAPIEvent:
    """
    Platform-agnostic CAPI event structure.
    """
    event_name: CAPIEventType
    event_id: str  # UUID for deduplication
    event_time: int  # Unix timestamp
    event_source_url: Optional[str] = None
    action_source: str = "website"  # website, app, email, etc.
    
    # User data for matching
    user_data: Optional[CAPIUserData] = None
    
    # Custom data (platform-specific payload)
    custom_data: Optional[Dict[str, Any]] = None


# ==========================================
# Hashing Utilities
# ==========================================

def sha256_hash(value: str) -> str:
    """
    SHA256 hash a string for Advanced Matching.
    Normalizes to lowercase and strips whitespace before hashing.
    """
    if not value:
        return None
    normalized = value.lower().strip()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def hash_email(email: str) -> Optional[str]:
    """Hash email for CAPI Advanced Matching."""
    return sha256_hash(email)


def hash_phone(phone: str) -> Optional[str]:
    """
    Hash phone for CAPI Advanced Matching.
    Phone should be in E.164 format (e.g., +14155551234).
    """
    if not phone:
        return None
    # Remove non-numeric characters except leading +
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
    return sha256_hash(cleaned)


# ==========================================
# Base CAPI Provider (Abstract)
# ==========================================

class CAPIProvider(ABC):
    """
    Abstract base class for CAPI integrations.
    Implement for each platform: Facebook, TikTok, Google sGTM.
    """
    
    @abstractmethod
    async def send_event(self, event: CAPIEvent) -> bool:
        """
        Send a single event to the platform.
        Returns True if successful.
        """
        pass
    
    @abstractmethod
    async def send_events_batch(self, events: List[CAPIEvent]) -> Dict[str, Any]:
        """
        Send multiple events in a batch.
        Returns summary of results.
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass


# ==========================================
# Facebook CAPI Provider (Stub)
# ==========================================

class FacebookCAPIProvider(CAPIProvider):
    """
    Facebook Conversions API integration.
    
    Required env vars:
    - FB_PIXEL_ID: Your Facebook Pixel ID
    - FB_ACCESS_TOKEN: Access token for CAPI
    - FB_TEST_EVENT_CODE: (Optional) For testing events
    
    Docs: https://developers.facebook.com/docs/marketing-api/conversions-api/
    """
    
    EVENT_MAP = {
        CAPIEventType.USER_REGISTERED: "CompleteRegistration",
        CAPIEventType.USER_LOGGED_IN: "Login",
        CAPIEventType.SUBSCRIPTION_STARTED: "Subscribe",
        CAPIEventType.SUBSCRIPTION_UPGRADED: "Subscribe",
        CAPIEventType.CREDITS_PURCHASED: "Purchase",
        CAPIEventType.MARKETPLACE_PURCHASED: "Purchase",
        CAPIEventType.AI_GENERATION_STARTED: "InitiateCheckout",
        CAPIEventType.AI_GENERATION_COMPLETED: "ViewContent",
        CAPIEventType.PROJECT_CREATED: "AddToCart",
        CAPIEventType.PROJECT_EXPORTED: "Lead",
        CAPIEventType.PAGE_VIEWED: "PageView",
    }
    
    def __init__(self):
        self.pixel_id = os.getenv("FB_PIXEL_ID")
        self.access_token = os.getenv("FB_ACCESS_TOKEN")
        self.test_event_code = os.getenv("FB_TEST_EVENT_CODE")
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    def is_configured(self) -> bool:
        return bool(self.pixel_id and self.access_token)
    
    async def send_event(self, event: CAPIEvent) -> bool:
        """
        Send event to Facebook CAPI.
        
        TODO: Implement actual API call when ready to enable.
        """
        if not self.is_configured():
            logger.debug("[FB CAPI] Not configured, skipping event")
            return False
        
        # Map event to Facebook event name
        fb_event_name = self.EVENT_MAP.get(event.event_name)
        if not fb_event_name:
            logger.warning(f"[FB CAPI] Unknown event type: {event.event_name}")
            return False
        
        # Build payload (stub)
        payload = {
            "data": [{
                "event_name": fb_event_name,
                "event_time": event.event_time,
                "event_id": event.event_id,  # For deduplication
                "event_source_url": event.event_source_url,
                "action_source": event.action_source,
                "user_data": self._build_user_data(event.user_data),
                "custom_data": event.custom_data or {},
            }],
        }
        
        if self.test_event_code:
            payload["test_event_code"] = self.test_event_code
        
        # TODO: Make actual HTTP request when enabling CAPI
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.base_url}/{self.pixel_id}/events",
        #         params={"access_token": self.access_token},
        #         json=payload
        #     )
        #     return response.status_code == 200
        
        logger.info(f"[FB CAPI] Would send event: {fb_event_name} (event_id: {event.event_id})")
        return True
    
    async def send_events_batch(self, events: List[CAPIEvent]) -> Dict[str, Any]:
        """Send batch of events. Currently sends one by one."""
        results = {"sent": 0, "failed": 0}
        for event in events:
            if await self.send_event(event):
                results["sent"] += 1
            else:
                results["failed"] += 1
        return results
    
    def _build_user_data(self, user_data: Optional[CAPIUserData]) -> Dict[str, Any]:
        """Build user_data object for Facebook CAPI."""
        if not user_data:
            return {}
        
        data = {}
        if user_data.email:
            data["em"] = [user_data.email]  # Already hashed
        if user_data.phone:
            data["ph"] = [user_data.phone]  # Already hashed
        if user_data.first_name:
            data["fn"] = [user_data.first_name]  # Already hashed
        if user_data.last_name:
            data["ln"] = [user_data.last_name]  # Already hashed
        if user_data.external_id:
            data["external_id"] = [user_data.external_id]
        if user_data.client_ip_address:
            data["client_ip_address"] = user_data.client_ip_address
        if user_data.client_user_agent:
            data["client_user_agent"] = user_data.client_user_agent
        if user_data.fbc:
            data["fbc"] = user_data.fbc
        if user_data.fbp:
            data["fbp"] = user_data.fbp
        
        return data


# ==========================================
# TikTok Events API Provider (Stub)
# ==========================================

class TikTokEventsAPIProvider(CAPIProvider):
    """
    TikTok Events API integration.
    
    Required env vars:
    - TIKTOK_PIXEL_ID: Your TikTok Pixel ID
    - TIKTOK_ACCESS_TOKEN: Access token for Events API
    - TIKTOK_TEST_EVENT_CODE: (Optional) For testing events
    
    Docs: https://ads.tiktok.com/marketing_api/docs?id=1739584860883969
    """
    
    EVENT_MAP = {
        CAPIEventType.USER_REGISTERED: "CompleteRegistration",
        CAPIEventType.USER_LOGGED_IN: "Login",
        CAPIEventType.SUBSCRIPTION_STARTED: "Subscribe",
        CAPIEventType.SUBSCRIPTION_UPGRADED: "Subscribe",
        CAPIEventType.CREDITS_PURCHASED: "CompletePayment",
        CAPIEventType.MARKETPLACE_PURCHASED: "CompletePayment",
        CAPIEventType.AI_GENERATION_STARTED: "InitiateCheckout",
        CAPIEventType.AI_GENERATION_COMPLETED: "ViewContent",
        CAPIEventType.PROJECT_CREATED: "AddToCart",
        CAPIEventType.PROJECT_EXPORTED: "SubmitForm",
        CAPIEventType.PAGE_VIEWED: "PageView",
    }
    
    def __init__(self):
        self.pixel_id = os.getenv("TIKTOK_PIXEL_ID")
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
        self.test_event_code = os.getenv("TIKTOK_TEST_EVENT_CODE")
    
    def is_configured(self) -> bool:
        return bool(self.pixel_id and self.access_token)
    
    async def send_event(self, event: CAPIEvent) -> bool:
        """Send event to TikTok Events API. (Stub)"""
        if not self.is_configured():
            logger.debug("[TikTok Events API] Not configured, skipping event")
            return False
        
        tt_event_name = self.EVENT_MAP.get(event.event_name)
        if not tt_event_name:
            logger.warning(f"[TikTok Events API] Unknown event type: {event.event_name}")
            return False
        
        # TODO: Implement actual API call
        logger.info(f"[TikTok Events API] Would send event: {tt_event_name} (event_id: {event.event_id})")
        return True
    
    async def send_events_batch(self, events: List[CAPIEvent]) -> Dict[str, Any]:
        """Send batch of events."""
        results = {"sent": 0, "failed": 0}
        for event in events:
            if await self.send_event(event):
                results["sent"] += 1
            else:
                results["failed"] += 1
        return results


# ==========================================
# Server-Side GTM Provider (Stub)
# ==========================================

class ServerSideGTMProvider(CAPIProvider):
    """
    Google Server-Side GTM integration.
    
    Required env vars:
    - SGTM_SERVER_URL: Your Server-Side GTM server URL
    - SGTM_API_SECRET: (Optional) API secret for authentication
    
    Docs: https://developers.google.com/tag-platform/tag-manager/server-side
    """
    
    def __init__(self):
        self.server_url = os.getenv("SGTM_SERVER_URL")
        self.api_secret = os.getenv("SGTM_API_SECRET")
    
    def is_configured(self) -> bool:
        return bool(self.server_url)
    
    async def send_event(self, event: CAPIEvent) -> bool:
        """Send event to Server-Side GTM. (Stub)"""
        if not self.is_configured():
            logger.debug("[sGTM] Not configured, skipping event")
            return False
        
        # TODO: Implement actual HTTP call to sGTM server
        logger.info(f"[sGTM] Would send event: {event.event_name} (event_id: {event.event_id})")
        return True
    
    async def send_events_batch(self, events: List[CAPIEvent]) -> Dict[str, Any]:
        """Send batch of events."""
        results = {"sent": 0, "failed": 0}
        for event in events:
            if await self.send_event(event):
                results["sent"] += 1
            else:
                results["failed"] += 1
        return results


# ==========================================
# CAPI Service (Main Interface)
# ==========================================

class CAPIService:
    """
    Main service for server-side event tracking.
    
    Usage:
        capi = CAPIService()
        await capi.track_conversion(
            event_type=CAPIEventType.CREDITS_PURCHASED,
            event_id="abc-123-def",  # Same as browser-side event_id
            event_time=int(time.time()),
            user_data=CAPIUserData(
                email=hash_email("user@example.com"),
                external_id=sha256_hash("user_123"),
            ),
            custom_data={
                "currency": "USD",
                "value": 9.99,
            }
        )
    """
    
    def __init__(self):
        self.providers: List[CAPIProvider] = []
        self._init_providers()
    
    def _init_providers(self):
        """Initialize all configured CAPI providers."""
        # Facebook CAPI
        fb_provider = FacebookCAPIProvider()
        if fb_provider.is_configured():
            self.providers.append(fb_provider)
            logger.info("[CAPI] Facebook CAPI provider enabled")
        
        # TikTok Events API
        tt_provider = TikTokEventsAPIProvider()
        if tt_provider.is_configured():
            self.providers.append(tt_provider)
            logger.info("[CAPI] TikTok Events API provider enabled")
        
        # Server-Side GTM
        sgtm_provider = ServerSideGTMProvider()
        if sgtm_provider.is_configured():
            self.providers.append(sgtm_provider)
            logger.info("[CAPI] Server-Side GTM provider enabled")
        
        if not self.providers:
            logger.debug("[CAPI] No CAPI providers configured")
    
    def is_enabled(self) -> bool:
        """Check if any CAPI provider is configured."""
        return len(self.providers) > 0
    
    async def track_conversion(
        self,
        event_type: CAPIEventType,
        event_id: str,
        event_time: int,
        user_data: Optional[CAPIUserData] = None,
        custom_data: Optional[Dict[str, Any]] = None,
        event_source_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Track a conversion event across all configured CAPI providers.
        
        Args:
            event_type: The type of conversion event
            event_id: Unique event ID (for deduplication with browser-side tracking)
            event_time: Unix timestamp when the event occurred
            user_data: User data for Advanced Matching (should be pre-hashed)
            custom_data: Custom data specific to the event (value, currency, etc.)
            event_source_url: The URL where the event occurred
            
        Returns:
            Summary of results from all providers
        """
        if not self.is_enabled():
            return {"status": "skipped", "reason": "no_providers_configured"}
        
        event = CAPIEvent(
            event_name=event_type,
            event_id=event_id,
            event_time=event_time,
            event_source_url=event_source_url,
            user_data=user_data,
            custom_data=custom_data,
        )
        
        results = {}
        for provider in self.providers:
            provider_name = provider.__class__.__name__
            try:
                success = await provider.send_event(event)
                results[provider_name] = "success" if success else "failed"
            except Exception as e:
                logger.error(f"[CAPI] Error sending to {provider_name}: {e}")
                results[provider_name] = f"error: {str(e)}"
        
        return results


# ==========================================
# Singleton Instance
# ==========================================

# Create singleton instance for easy import
capi_service = CAPIService()


# ==========================================
# Convenience Functions
# ==========================================

async def track_purchase_conversion(
    event_id: str,
    event_time: int,
    value: float,
    currency: str,
    user_email: Optional[str] = None,
    user_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    event_source_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Track a purchase conversion (subscription or credits).
    
    Example:
        await track_purchase_conversion(
            event_id=event.event_id,
            event_time=int(time.time()),
            value=9.99,
            currency="USD",
            user_email="user@example.com",
            user_id="user_123",
            transaction_id="txn_abc123",
        )
    """
    user_data = CAPIUserData(
        email=hash_email(user_email) if user_email else None,
        external_id=sha256_hash(user_id) if user_id else None,
    )
    
    custom_data = {
        "value": value,
        "currency": currency,
    }
    if transaction_id:
        custom_data["transaction_id"] = transaction_id
    
    return await capi_service.track_conversion(
        event_type=CAPIEventType.CREDITS_PURCHASED,
        event_id=event_id,
        event_time=event_time,
        user_data=user_data,
        custom_data=custom_data,
        event_source_url=event_source_url,
    )


async def track_signup_conversion(
    event_id: str,
    event_time: int,
    user_email: Optional[str] = None,
    user_id: Optional[str] = None,
    signup_method: str = "email",
    event_source_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Track a user registration conversion.
    """
    user_data = CAPIUserData(
        email=hash_email(user_email) if user_email else None,
        external_id=sha256_hash(user_id) if user_id else None,
    )
    
    custom_data = {
        "signup_method": signup_method,
    }
    
    return await capi_service.track_conversion(
        event_type=CAPIEventType.USER_REGISTERED,
        event_id=event_id,
        event_time=event_time,
        user_data=user_data,
        custom_data=custom_data,
        event_source_url=event_source_url,
    )
