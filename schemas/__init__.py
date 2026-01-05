"""
Pydantic Schemas Package
Request/Response models organized by domain

@module schemas
@version 3.24
"""

# Base schemas
from .base import (
    ApiResponse,
    PaginatedResponse,
)

# User schemas
from .users import (
    UserProfile,
    CreditTransaction,
    TimezoneUpdateRequest,
)

# Project schemas
from .projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectSaveResult,
)

# Asset schemas  
from .assets import (
    CreateAssetFromUrlRequest,
)

# Generation schemas
from .generation import (
    StoryGenRequest,
    ImageGenRequest,
    PdfGenRequest,
    InspirationRequest,
    GenerationHistoryQuery,
    FavoriteRequest,
    AssetPromptTemplateCreate,
    AssetPromptTemplateUpdate,
    PagePromptTemplateCreate,
    # Backward compatibility
    TemplateCreate,
    TemplateUpdate,
    PageDesignTemplateCreate,
)

# Marketplace schemas
from .marketplace import (
    ListingCreate,
    ListingUpdate,
    ListingResponse,
    MarketplacePublishRequest,
    MarketplacePurchaseRequest,
    ListingUpdateRequest,
    PurchaseRequest,
    PurchaseResult,
    SellerStats,
    ReportRequest,
)

# Admin schemas
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

# Analytics schemas
from .analytics import (
    AnalyticsEvent,
    AnalyticsEventsRequest,
    UserEventsRequest,
)

# Log schemas
from .logs import (
    ErrorLogRequest,
    ErrorLogBatchRequest,
)

# Support schemas
from .support import (
    SupportTicketRequest,
    ChatImageData,
    ChatSupportRequest,
    ContactFormRequest,
    FeedbackWithImagesRequest,
)

# Checkout schemas
from .checkout import (
    CheckoutRequest,
)

__all__ = [
    # Base
    'ApiResponse',
    'PaginatedResponse',
    # Users
    'UserProfile',
    'CreditTransaction',
    'TimezoneUpdateRequest',
    # Projects
    'ProjectCreate',
    'ProjectUpdate', 
    'ProjectResponse',
    'ProjectSaveResult',
    # Assets
    'CreateAssetFromUrlRequest',
    # Generation
    'StoryGenRequest',
    'ImageGenRequest',
    'PdfGenRequest',
    'InspirationRequest',
    'GenerationHistoryQuery',
    'FavoriteRequest',
    'AssetPromptTemplateCreate',
    'AssetPromptTemplateUpdate',
    'PagePromptTemplateCreate',
    'TemplateCreate',
    'TemplateUpdate',
    'PageDesignTemplateCreate',
    # Marketplace
    'ListingCreate',
    'ListingUpdate',
    'ListingResponse',
    'MarketplacePublishRequest',
    'MarketplacePurchaseRequest',
    'ListingUpdateRequest',
    'PurchaseRequest',
    'PurchaseResult',
    'SellerStats',
    'ReportRequest',
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
    # Support
    'SupportTicketRequest',
    'ChatImageData',
    'ChatSupportRequest',
    'ContactFormRequest',
    'FeedbackWithImagesRequest',
    # Checkout
    'CheckoutRequest',
]
