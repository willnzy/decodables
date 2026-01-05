"""
CAPI Models - Data classes and event types

@module services.capi.models
@version 3.24
"""

import hashlib
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class CAPIEventType(str, Enum):
    """Standard event types for CAPI."""
    USER_REGISTERED = "user_registered"
    USER_LOGGED_IN = "user_logged_in"
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_UPGRADED = "subscription_upgraded"
    CREDITS_PURCHASED = "credits_purchased"
    MARKETPLACE_PURCHASED = "marketplace_purchased"
    AI_GENERATION_STARTED = "ai_generation_started"
    AI_GENERATION_COMPLETED = "ai_generation_completed"
    PROJECT_CREATED = "project_created"
    PROJECT_EXPORTED = "project_exported"
    PAGE_VIEWED = "page_viewed"


@dataclass
class CAPIUserData:
    """User data for Advanced Matching (hashed)."""
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    external_id: Optional[str] = None
    client_ip_address: Optional[str] = None
    client_user_agent: Optional[str] = None
    fbc: Optional[str] = None
    fbp: Optional[str] = None


@dataclass
class CAPIEvent:
    """Platform-agnostic CAPI event structure."""
    event_name: CAPIEventType
    event_id: str
    event_time: int
    event_source_url: Optional[str] = None
    action_source: str = "website"
    user_data: Optional[CAPIUserData] = None
    custom_data: Optional[Dict[str, Any]] = None


# ==========================================
# Hashing Utilities
# ==========================================

def sha256_hash(value: str) -> Optional[str]:
    """SHA256 hash for Advanced Matching."""
    if not value:
        return None
    normalized = value.lower().strip()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def hash_email(email: str) -> Optional[str]:
    """Hash email for CAPI."""
    return sha256_hash(email)


def hash_phone(phone: str) -> Optional[str]:
    """Hash phone (E.164 format) for CAPI."""
    if not phone:
        return None
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
    return sha256_hash(cleaned)
