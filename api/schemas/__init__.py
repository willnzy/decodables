"""
API Schemas Package
Request/Response models organized by domain (DDD compliant)

@module api.schemas
@version 3.24
"""

# Base schemas (v2.0.0)
from .base import (
    PaginatedResponse,
    DataResponse,
    OperationResponse,
    ErrorDetail,
    ErrorResponse,
)

# User schemas (from user subpackage)
from .user.users import (
    UserProfile,
    CreditTransaction,
    TimezoneUpdateRequest,
)

from .user.projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectSaveResult,
)

from .user.assets import (
    CreateAssetFromUrlRequest,
)

from .user.generation import (
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

from .user.marketplace import (
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

from .user.support import (
    SupportTicketRequest,
    ChatImageData,
    ChatSupportRequest,
    ContactFormRequest,
    FeedbackWithImagesRequest,
)

from .user.checkout import (
    CheckoutRequest,
)

# Admin schemas (from admin subpackage)
from .admin.admin import (
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

from .admin.analytics import (
    AnalyticsEvent,
    AnalyticsEventsRequest,
    UserEventsRequest,
)

from .admin.logs import (
    ErrorLogRequest,
    ErrorLogBatchRequest,
)

from .admin.system_resources import (
    ResourceCreate,
    ResourceUpdate,
    ResourceBatchAction,
)

__all__ = [
    # Base (v2.0.0)
    'PaginatedResponse',
    'DataResponse',
    'OperationResponse',
    'ErrorDetail',
    'ErrorResponse',
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
    # System Resources
    'ResourceCreate',
    'ResourceUpdate',
    'ResourceBatchAction',
]
