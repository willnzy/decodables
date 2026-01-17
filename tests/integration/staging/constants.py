"""
Constants for Staging API Tests

集中管理测试中使用的常量:
- API URLs
- 状态码
- 错误消息
- 测试数据

@module tests.integration.staging.constants
"""

import os

# ==========================================
# Environment Configuration
# ==========================================

STAGING_BASE_URL = os.getenv(
    "STAGING_BASE_URL",
    "https://decodables-staging.up.railway.app"
)

CLERK_API_BASE = "https://api.clerk.com/v1"

# API Version Prefix
API_V2 = "/api/v2"
API_V3 = "/api/v3"
API_ADMIN = "/api/admin"

# ==========================================
# API Endpoints
# ==========================================

class Endpoints:
    """API 端点路径"""

    # Health
    HEALTH = "/health"
    HEALTH_DETAILED = "/health/detailed"

    # User Profile
    PROFILE_ME = f"{API_V2}/user/profile/me"
    PROFILE_HISTORY = f"{API_V2}/user/profile/history"
    PROFILE_PURCHASES = f"{API_V2}/user/profile/purchases"
    PROFILE_NOTIFICATIONS = f"{API_V2}/user/profile/notifications"

    # Billing
    BILLING_CREDITS = f"{API_V2}/user/billing/credits"
    BILLING_TRANSACTIONS = f"{API_V2}/user/billing/transactions"
    BILLING_CAN_AFFORD = f"{API_V2}/user/billing/can-afford"

    # Payment
    PAYMENT_CHECKOUT = f"{API_V2}/user/payment/checkout"
    PAYMENT_PORTAL = f"{API_V2}/user/payment/portal"

    # Projects
    PROJECTS = f"{API_V2}/user/projects"
    PROJECTS_DASHBOARD = f"{API_V2}/user/projects/dashboard"
    PROJECTS_DELETED = f"{API_V2}/user/projects/deleted"

    @staticmethod
    def project(project_id: str) -> str:
        return f"{API_V2}/user/projects/{project_id}"

    @staticmethod
    def project_restore(project_id: str) -> str:
        return f"{API_V2}/user/projects/{project_id}/restore"

    @staticmethod
    def project_duplicate(project_id: str) -> str:
        return f"{API_V2}/user/projects/{project_id}/duplicate"

    # AI Generation
    GENERATE_IMAGES = f"{API_V2}/user/generate/images"
    GENERATE_IMAGES_ASYNC = f"{API_V2}/user/generate/images/async"
    GENERATE_STORY = f"{API_V2}/user/generate/story"
    GENERATE_INSPIRATION = f"{API_V2}/user/generate/inspiration"

    # Marketplace
    MARKETPLACE_LISTINGS = f"{API_V2}/user/marketplace/listings"
    MARKETPLACE_PURCHASE = f"{API_V2}/user/marketplace/purchase"
    MARKETPLACE_MY_LISTINGS = f"{API_V2}/user/marketplace/my-listings"
    MARKETPLACE_LEADERBOARD = f"{API_V2}/user/marketplace/leaderboard"

    @staticmethod
    def marketplace_listing(listing_id: str) -> str:
        return f"{API_V2}/user/marketplace/listings/{listing_id}"

    # Resources
    RESOURCES = f"{API_V2}/user/resources"
    RESOURCES_TYPES = f"{API_V2}/user/resources/types"

    # Assets (v3)
    ASSETS = f"{API_V3}/user/assets"
    ASSETS_DASHBOARD = f"{API_V3}/user/assets/dashboard"
    ASSETS_DELETED = f"{API_V3}/user/assets/deleted"

    # Config
    CONFIG = f"{API_V2}/user/config"

    @staticmethod
    def config_group(group_name: str) -> str:
        return f"{API_V2}/user/config/group/{group_name}"

    # Generations History
    GENERATIONS_HISTORY = f"{API_V2}/user/generations/history"

    @staticmethod
    def generation(generation_id: str) -> str:
        return f"{API_V2}/user/generations/{generation_id}"

    # Tasks
    @staticmethod
    def task(task_id: str) -> str:
        return f"{API_V2}/user/tasks/{task_id}"

    # Support
    SUPPORT_TICKET = f"{API_V2}/user/support/ticket"
    SUPPORT_CHAT = f"{API_V2}/user/support/chat"
    SUPPORT_CONTACT = f"{API_V2}/user/support/contact"
    SUPPORT_FEEDBACK = f"{API_V2}/user/support/feedback"

    # Onboarding
    ONBOARDING_STEPS = f"{API_V2}/user/onboarding/steps"
    ONBOARDING_STEPS_START = f"{API_V2}/user/onboarding/steps/start"
    ONBOARDING_STEPS_COMPLETE = f"{API_V2}/user/onboarding/steps/complete"
    ONBOARDING_STEPS_SKIP = f"{API_V2}/user/onboarding/steps/skip"
    ONBOARDING_CHECKLIST = f"{API_V2}/user/onboarding/checklist"

    # Referrals
    REFERRALS = f"{API_V2}/user/referrals"
    REFERRALS_STATS = f"{API_V2}/user/referrals/stats"

    @staticmethod
    def referral_by_code(code: str) -> str:
        return f"{API_V2}/user/referrals/code/{code}"

    @staticmethod
    def referral_complete(referral_id: str) -> str:
        return f"{API_V2}/user/referrals/{referral_id}/complete"

    # Seller
    SELLER_STATS = f"{API_V2}/user/seller/stats"

    # Templates
    TEMPLATES_ASSET = f"{API_V3}/user/templates/asset"
    TEMPLATES_PAGE = f"{API_V3}/user/templates/page"

    @staticmethod
    def template_asset(template_id: str) -> str:
        return f"{API_V3}/user/templates/asset/{template_id}"

    @staticmethod
    def template_asset_use(template_id: str) -> str:
        return f"{API_V3}/user/templates/asset/{template_id}/use"

    @staticmethod
    def template_page(template_id: str) -> str:
        return f"{API_V3}/user/templates/page/{template_id}"

    @staticmethod
    def template_page_use(template_id: str) -> str:
        return f"{API_V3}/user/templates/page/{template_id}/use"

    # Themes
    THEMES_CURRENT = f"{API_V2}/user/themes/current"

    # Tools
    TOOLS_PDF_PREVIEW = f"{API_V2}/user/tools/pdf-preview"
    TOOLS_OCR = f"{API_V2}/user/tools/ocr"

    # Tasks
    @staticmethod
    def task_cancel(task_id: str) -> str:
        return f"{API_V2}/user/tasks/{task_id}/cancel"

    # User Assets
    ASSETS_CHECK_URL = f"{API_V3}/user/assets/check-url"
    ASSETS_FROM_URL = f"{API_V3}/user/assets/from-url"

    @staticmethod
    def asset(asset_id: str) -> str:
        return f"{API_V3}/user/assets/{asset_id}"

    @staticmethod
    def asset_restore(asset_id: str) -> str:
        return f"{API_V3}/user/assets/{asset_id}/restore"

    @staticmethod
    def asset_increment_usage(asset_id: str) -> str:
        return f"{API_V3}/user/assets/{asset_id}/increment-usage"

    # Generation (Images, PDF, Story)
    GENERATE_PDF = f"{API_V2}/user/generate/pdf/pdf"
    GENERATE_STORY_STORY = f"{API_V2}/user/generate/story/story"
    GENERATE_STORY_INSPIRATION = f"{API_V2}/user/generate/story/inspiration"

    # Experiments (Feature Flags)
    EXPERIMENTS = f"{API_V2}/user/experiments"
    EXPERIMENTS_ALL_FLAGS = f"{API_V2}/user/experiments/all-flags"
    EXPERIMENTS_USER_TARGETING = f"{API_V2}/user/experiments/user-targeting"

    @staticmethod
    def experiment(flag_key: str) -> str:
        return f"{API_V2}/user/experiments/{flag_key}"

    # Analytics
    ANALYTICS_EVENTS = f"{API_V2}/user/analytics/events"

    # Articles (public)
    ARTICLES = f"{API_V2}/user/articles"
    ARTICLES_CATEGORIES = f"{API_V2}/user/articles/categories"
    ARTICLES_SEARCH = f"{API_V2}/user/articles/search"
    ARTICLES_FEATURED = f"{API_V2}/user/articles/featured"

    @staticmethod
    def article(slug: str) -> str:
        return f"{API_V2}/user/articles/{slug}"

    @staticmethod
    def article_related(slug: str) -> str:
        return f"{API_V2}/user/articles/{slug}/related"

    # Campaigns
    CAMPAIGNS_ACTIVE = f"{API_V2}/user/campaigns/active"

    @staticmethod
    def campaign_claim(campaign_id: str) -> str:
        return f"{API_V2}/user/campaigns/{campaign_id}/claim"

    @staticmethod
    def campaign_dismiss(campaign_id: str) -> str:
        return f"{API_V2}/user/campaigns/{campaign_id}/dismiss"

    # Config (public)
    @staticmethod
    def config_key(key: str) -> str:
        return f"{API_V2}/user/config/{key}"

    # Export
    @staticmethod
    def export_pdf(project_id: str) -> str:
        return f"{API_V2}/user/export/projects/{project_id}/pdf"

    @staticmethod
    def export_preview(project_id: str) -> str:
        return f"{API_V2}/user/export/projects/{project_id}/preview"

    @staticmethod
    def export_zip(project_id: str) -> str:
        return f"{API_V2}/user/export/projects/{project_id}/zip"

    @staticmethod
    def export_pdf_async(project_id: str) -> str:
        return f"{API_V2}/user/export/projects/{project_id}/pdf/async"

    @staticmethod
    def export_zip_async(project_id: str) -> str:
        return f"{API_V2}/user/export/projects/{project_id}/zip/async"

    # Logs (public - no auth required)
    LOGS_ERROR = f"{API_V2}/user/logs/error"
    LOGS_ERRORS_BATCH = f"{API_V2}/user/logs/errors"

    # Static Pages (public)
    STATIC_PAGES = f"{API_V2}/user/static-pages"

    @staticmethod
    def static_page(slug: str) -> str:
        return f"{API_V2}/user/static-pages/{slug}"

    # Admin Endpoints
    ADMIN_USERS = f"{API_ADMIN}/users"
    ADMIN_SUBSCRIPTIONS_REFUND = f"{API_ADMIN}/subscriptions/refund"
    ADMIN_SUBSCRIPTIONS_CANCEL = f"{API_ADMIN}/subscriptions/subscription/cancel"

    @staticmethod
    def admin_user(user_id: str) -> str:
        return f"{API_ADMIN}/users/{user_id}"

    @staticmethod
    def admin_user_credits(user_id: str) -> str:
        return f"{API_ADMIN}/users/{user_id}/credits"


# ==========================================
# HTTP Status Codes
# ==========================================

class StatusCodes:
    """HTTP 状态码常量"""

    # Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    GONE = 410
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429

    # Server Errors
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


# ==========================================
# Error Messages
# ==========================================

class ErrorMessages:
    """常见错误消息"""

    # Auth
    MISSING_TOKEN = "Missing authentication token"
    INVALID_TOKEN = "Invalid token"
    TOKEN_EXPIRED = "Token expired"
    UNAUTHORIZED_ORIGIN = "unauthorized origin"

    # Permission
    FORBIDDEN = "Forbidden"
    ADMIN_REQUIRED = "Admin required"
    MEMBER_REQUIRED = "Member required"

    # Validation
    REQUIRED_FIELD = "field required"
    INVALID_FORMAT = "invalid format"
    VALUE_TOO_LONG = "too long"
    VALUE_TOO_SHORT = "too short"

    # Business
    INSUFFICIENT_CREDITS = "Insufficient credits"
    PROJECT_LIMIT_EXCEEDED = "Project limit exceeded"
    ALREADY_PURCHASED = "Already purchased"
    NOT_AVAILABLE = "Not available"

    # Server
    INTERNAL_ERROR = "Internal server error"


# ==========================================
# Test User Tiers
# ==========================================

class Tiers:
    """用户 Tier 常量"""

    FREE = "t1"
    STARTER = "t2"
    PRO = "t3"
    ENTERPRISE = "t4"

    # Tier Limits
    PROJECT_LIMITS = {
        "t1": 1,
        "t2": 20,
        "t3": 200,
        "t4": 1000,
    }

    MONTHLY_CREDITS = {
        "t1": 0,
        "t2": 100,
        "t3": 200,
        "t4": 500,
    }


# ==========================================
# Test Data Constants
# ==========================================

class TestData:
    """测试数据常量"""

    # Valid test values
    VALID_EMAIL = "test@example.com"
    VALID_TITLE = "Test Project"
    VALID_UUID = "00000000-0000-0000-0000-000000000001"

    # Boundary values
    TITLE_MIN_LENGTH = 1
    TITLE_MAX_LENGTH = 200
    DESCRIPTION_MAX_LENGTH = 5000

    # Pagination defaults
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100
    DEFAULT_OFFSET = 0

    # Credit costs
    CREDIT_COST_IMAGE = 5
    CREDIT_COST_OCR = 5
    CREDIT_COST_PAGE = 5


# ==========================================
# Rate Limits (requests per minute)
# ==========================================

class RateLimits:
    """速率限制常量"""

    # Read operations
    GET_CREDITS = 60
    GET_TRANSACTIONS = 30
    GET_PROJECTS = 60

    # Write operations
    CREATE_PROJECT = 30
    GENERATE_IMAGE = 10
    CHECKOUT = 5

    # Admin operations
    ADMIN_DEFAULT = 10


# ==========================================
# Timeouts (seconds)
# ==========================================

class Timeouts:
    """超时常量"""

    DEFAULT = 30
    GENERATE_IMAGE = 60
    EXPORT_PDF = 120
    HEALTH_CHECK = 5


# ==========================================
# Response Schema Keys
# ==========================================

class ResponseKeys:
    """响应字段名常量"""

    # Common
    ID = "id"
    USER_ID = "user_id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

    # Billing
    MONTHLY_CREDITS = "monthly_credits"
    PERMANENT_CREDITS = "permanent_credits"
    TOTAL_CREDITS = "total_credits"
    TIER = "tier"

    # Pagination
    ITEMS = "items"
    TOTAL = "total"
    OFFSET = "offset"
    LIMIT = "limit"

    # Error
    CODE = "code"
    MESSAGE = "message"
    DETAIL = "detail"
    REQUEST_ID = "request_id"
