"""
User API Schemas
Request/Response models for user-facing APIs

@module api.schemas.user
"""

from .users import (
    UserProfile,
    CreditTransaction,
    TimezoneUpdateRequest,
)

from .projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectSaveResult,
)

from .assets import (
    CreateAssetFromUrlRequest,
)

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
    TemplateCreate,
    TemplateUpdate,
    PageDesignTemplateCreate,
)

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

from .support import (
    SupportTicketRequest,
    ChatImageData,
    ChatSupportRequest,
    ContactFormRequest,
    FeedbackWithImagesRequest,
)

from .checkout import (
    CheckoutRequest,
)

__all__ = [
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
    # Support
    'SupportTicketRequest',
    'ChatImageData',
    'ChatSupportRequest',
    'ContactFormRequest',
    'FeedbackWithImagesRequest',
    # Checkout
    'CheckoutRequest',
]
