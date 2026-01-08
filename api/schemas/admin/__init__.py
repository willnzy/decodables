"""
Admin API Schemas
Request/Response models for admin-facing APIs

@module api.schemas.admin
"""

from .admin import (
    CreditAdjustRequest,
    TierUpdateRequest,
    DiscountCreateRequest,
    BroadcastRequest,
    ModerationAction,
    AdminAdjustRequest,
    AdminTierRequest,
    AdminDowngradeRequest,
    AdminDiscountRequest,
    AdminBroadcastRequest,
    AdminModerationRejectRequest,
    AdminRefundRequest,
    AdminCancelSubscriptionRequest,
    AdminSendNotificationRequest,
    AdminBatchNotificationRequest,
    ReportResponseRequest,
    ConfigUpdateRequest,
    BatchConfigUpdateRequest,
    RateLimitPresetRequest,
)

from .analytics import (
    AnalyticsEvent,
    AnalyticsEventsRequest,
    UserEventsRequest,
)

from .logs import (
    ErrorLogRequest,
    ErrorLogBatchRequest,
)

from .system_resources import (
    ResourceCreate,
    ResourceUpdate,
    ResourceBatchAction,
)

__all__ = [
    # Admin
    'CreditAdjustRequest',
    'TierUpdateRequest',
    'DiscountCreateRequest',
    'BroadcastRequest',
    'ModerationAction',
    'AdminAdjustRequest',
    'AdminTierRequest',
    'AdminDowngradeRequest',
    'AdminDiscountRequest',
    'AdminBroadcastRequest',
    'AdminModerationRejectRequest',
    'AdminRefundRequest',
    'AdminCancelSubscriptionRequest',
    'AdminSendNotificationRequest',
    'AdminBatchNotificationRequest',
    'ReportResponseRequest',
    'ConfigUpdateRequest',
    'BatchConfigUpdateRequest',
    'RateLimitPresetRequest',
    # Analytics
    'AnalyticsEvent',
    'AnalyticsEventsRequest',
    'UserEventsRequest',
    # Logs
    'ErrorLogRequest',
    'ErrorLogBatchRequest',
    # System Resources
    'ResourceCreate',
    'ResourceUpdate',
    'ResourceBatchAction',
]
