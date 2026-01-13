"""
Analytics Value Objects - Immutable value objects for analytics domain.

@module domains.analytics.value_objects
@version 1.0.0

This module defines value objects like EventType, Source, EventLevel.
"""

from enum import Enum
from typing import Set


class EventSource(str, Enum):
    """Event source enumeration."""
    SERVER = "server"
    WEB = "web"
    MOBILE = "mobile"
    API = "api"


class EventLevel(str, Enum):
    """Event severity/importance level."""
    CRITICAL = "critical"
    IMPORTANT = "important"
    NORMAL = "normal"
    DEBUG = "debug"


class StandardEventTypes:
    """
    Standard event type constants.
    
    Provides a centralized registry of all event types used in the system.
    This helps maintain consistency and discoverability.
    """
    
    # Page Views
    PAGE_VIEW = "page_view"
    
    # User Actions
    BUTTON_CLICK = "button_click"
    FORM_SUBMIT = "form_submit"
    SEARCH = "search"
    
    # AI Generation
    AI_GENERATE_STARTED = "ai_generate_started"
    AI_GENERATE_SUCCESS = "ai_generate_success"
    AI_GENERATE_FAILURE = "ai_generate_failure"
    
    # Project Actions
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    PROJECT_SAVED = "project_saved"
    PROJECT_EXPORTED = "project_exported"
    PROJECT_PREVIEW = "project_preview"
    
    # Marketplace Actions
    MARKETPLACE_VIEW = "marketplace_view"
    MARKETPLACE_SEARCH = "marketplace_search"
    MARKETPLACE_PURCHASE = "marketplace_purchase"
    MARKETPLACE_PUBLISH = "marketplace_publish"
    
    # Payment Events
    CHECKOUT_STARTED = "checkout_started"
    CHECKOUT_COMPLETED = "checkout_completed"
    CHECKOUT_FAILED = "checkout_failed"
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    
    # User Lifecycle
    USER_SIGNUP = "signup"
    USER_LOGIN = "login"
    USER_LOGOUT = "logout"
    PROFILE_UPDATED = "profile_updated"
    
    # Asset Management
    ASSET_UPLOADED = "asset_uploaded"
    ASSET_DELETED = "asset_deleted"
    ASSET_PURCHASED = "asset_purchased"
    
    # Feature Usage
    FEATURE_USED = "feature_used"
    
    # Errors
    ERROR_OCCURRED = "error_occurred"
    API_CALL_FAILED = "api_call"
    
    @classmethod
    def all_types(cls) -> Set[str]:
        """Get all standard event types."""
        return {
            value for name, value in vars(cls).items()
            if not name.startswith('_') and isinstance(value, str)
        }
    
    @classmethod
    def is_valid_type(cls, event_type: str) -> bool:
        """Check if event type is in standard registry."""
        return event_type in cls.all_types()


class AnalyticsEventTypes:
    """
    Alias for StandardEventTypes for backward compatibility.
    
    Deprecated: Use StandardEventTypes instead.
    """
    # Re-export all constants from StandardEventTypes
    def __init__(self):
        for name, value in vars(StandardEventTypes).items():
            if not name.startswith('_') and isinstance(value, str):
                setattr(self, name, value)


# Create singleton instance for backward compatibility
AnalyticsEvents = AnalyticsEventTypes()


# Valid event types for user_events table (with database constraints)
USER_EVENT_TYPES = {
    'page_view',
    'button_click',
    'form_submit',
    'feature_used',
    'error_occurred',
    'api_call',
    'project_created',
    'project_updated',
    'project_deleted',
    'asset_uploaded',
    'asset_purchased',
    'payment_completed',
    'login',
    'logout',
    'signup',
    'profile_updated',
}


# Event types that should also log to activity_logs
ACTIVITY_LOG_EVENT_MAPPING = {
    "project_print": "print_project",
    "project_export_pdf": "download_pdf",
    "project_export_zip": "export_zip",
    "project_preview": "preview_pdf",
    "project_delete": "delete_project",
    "project_create_complete": "create_project",
    "project_created": "create_project",
    "project_updated": "update_project",
    "project_deleted": "delete_project",
}
