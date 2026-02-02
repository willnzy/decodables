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

# API Version Prefix
API_V2 = "/api/v2"
API_V3 = "/api/v3"
API_ADMIN = "/api/v2/admin"

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

    @staticmethod
    def project_move(project_id: str) -> str:
        """Move project to folder (v3.33 Phase 2.6)"""
        return f"{API_V2}/user/projects/{project_id}/move"

    @staticmethod
    def project_star(project_id: str) -> str:
        """Toggle project star status (v3.33 Phase 2.6)"""
        return f"{API_V2}/user/projects/{project_id}/star"

    # Project by folder / starred (v3.33 Phase 2.6)
    PROJECTS_STARRED = f"{API_V2}/user/projects/starred"

    @staticmethod
    def projects_by_folder(folder_id: str) -> str:
        """List projects in a folder (v3.33 Phase 2.6)"""
        return f"{API_V2}/user/projects/folder/{folder_id}"

    # AI Generation (router prefix is /generate/images, endpoint is /images)
    GENERATE_IMAGES = f"{API_V2}/user/generate/images/images"
    GENERATE_IMAGES_ASYNC = f"{API_V2}/user/generate/images/images/async"
    GENERATE_STORY = f"{API_V2}/user/generate/story/story"
    GENERATE_INSPIRATION = f"{API_V2}/user/generate/story/inspiration"

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

    # Assets (all user APIs are under v2)
    ASSETS = f"{API_V2}/user/assets"
    ASSETS_DASHBOARD = f"{API_V2}/user/assets/dashboard"
    ASSETS_DELETED = f"{API_V2}/user/assets/deleted"

    # Folders (v3.33 Phase 2.6)
    FOLDERS = f"{API_V2}/user/folders"
    FOLDERS_REORDER = f"{API_V2}/user/folders/reorder"

    @staticmethod
    def folder(folder_id: str) -> str:
        return f"{API_V2}/user/folders/{folder_id}"

    # Config
    CONFIG = f"{API_V2}/user/config"

    @staticmethod
    def config_group(group_name: str) -> str:
        return f"{API_V2}/user/config/group/{group_name}"

    # Workspaces (v3.33 Phase 2)
    WORKSPACES = f"{API_V2}/user/workspaces"
    WORKSPACES_CURRENT = f"{API_V2}/user/workspaces/current"

    @staticmethod
    def workspace(workspace_id: str) -> str:
        """Get/Update/Delete workspace by ID"""
        return f"{API_V2}/user/workspaces/{workspace_id}"

    @staticmethod
    def workspace_stats(workspace_id: str) -> str:
        """Get workspace statistics"""
        return f"{API_V2}/user/workspaces/{workspace_id}/stats"

    # Tags (v3.33 Phase 2)
    TAGS = f"{API_V2}/user/tags"
    TAGS_BY_GROUP = f"{API_V2}/user/tags/by-group"
    TAGS_PRESETS = f"{API_V2}/user/tags/presets"

    @staticmethod
    def tag(tag_id: str) -> str:
        """Update/Delete tag by ID"""
        return f"{API_V2}/user/tags/{tag_id}"

    # Project Tags (v3.33 Phase 2)
    @staticmethod
    def project_tags(project_id: str) -> str:
        """Get/Add/Set project tags"""
        return f"{API_V2}/user/projects/{project_id}/tags"

    @staticmethod
    def project_tag(project_id: str, tag_id: str) -> str:
        """Remove tag from project"""
        return f"{API_V2}/user/projects/{project_id}/tags/{tag_id}"

    # Asset Tags (v3.33 Phase 2)
    @staticmethod
    def asset_tags(asset_id: str) -> str:
        """Get/Add/Set asset tags"""
        return f"{API_V2}/user/assets/{asset_id}/tags"

    @staticmethod
    def asset_tag(asset_id: str, tag_id: str) -> str:
        """Remove tag from asset"""
        return f"{API_V2}/user/assets/{asset_id}/tags/{tag_id}"

    # System Resources (Admin)
    SYSTEM_RESOURCES = f"{API_V2}/user/system-resources"
    SYSTEM_RESOURCES_STATS = f"{API_V2}/user/system-resources/stats"
    SYSTEM_RESOURCES_BATCH = f"{API_V2}/user/system-resources/batch"

    @staticmethod
    def system_resource(resource_id: str) -> str:
        """Get/Update/Delete system resource"""
        return f"{API_V2}/user/system-resources/{resource_id}"

    @staticmethod
    def system_resource_replace(resource_id: str) -> str:
        """Replace system resource file"""
        return f"{API_V2}/user/system-resources/{resource_id}/replace"

    @staticmethod
    def system_resource_audit(resource_id: str) -> str:
        """Get system resource audit log"""
        return f"{API_V2}/user/system-resources/{resource_id}/audit-log"

    # Webhooks
    WEBHOOKS_STRIPE = f"{API_V2}/user/webhooks/stripe"

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

    # Templates (all user APIs are under v2)
    TEMPLATES_ASSET = f"{API_V2}/user/templates/asset"
    TEMPLATES_PAGE = f"{API_V2}/user/templates/page"

    @staticmethod
    def template_asset(template_id: str) -> str:
        return f"{API_V2}/user/templates/asset/{template_id}"

    @staticmethod
    def template_asset_use(template_id: str) -> str:
        return f"{API_V2}/user/templates/asset/{template_id}/use"

    @staticmethod
    def template_page(template_id: str) -> str:
        return f"{API_V2}/user/templates/page/{template_id}"

    @staticmethod
    def template_page_use(template_id: str) -> str:
        return f"{API_V2}/user/templates/page/{template_id}/use"

    # Themes
    THEMES_CURRENT = f"{API_V2}/user/themes/current"

    # Tools
    TOOLS_PDF_PREVIEW = f"{API_V2}/user/tools/pdf-preview"
    TOOLS_OCR = f"{API_V2}/user/tools/ocr"

    # Tasks
    @staticmethod
    def task_cancel(task_id: str) -> str:
        return f"{API_V2}/user/tasks/{task_id}/cancel"

    # User Assets (all user APIs are under v2)
    ASSETS_CHECK_URL = f"{API_V2}/user/assets/check-url"
    ASSETS_FROM_URL = f"{API_V2}/user/assets/from-url"

    @staticmethod
    def asset(asset_id: str) -> str:
        return f"{API_V2}/user/assets/{asset_id}"

    @staticmethod
    def asset_restore(asset_id: str) -> str:
        return f"{API_V2}/user/assets/{asset_id}/restore"

    @staticmethod
    def asset_move(asset_id: str) -> str:
        """Move asset to folder (v3.33 Phase 2.6)"""
        return f"{API_V2}/user/assets/{asset_id}/move"

    @staticmethod
    def asset_star(asset_id: str) -> str:
        """Toggle asset star status (v3.33 Phase 2.6)"""
        return f"{API_V2}/user/assets/{asset_id}/star"

    # Asset by folder / starred (v3.33 Phase 2.6)
    ASSETS_STARRED = f"{API_V2}/user/assets/starred"

    @staticmethod
    def assets_by_folder(folder_id: str) -> str:
        """List assets in a folder (v3.33 Phase 2.6)"""
        return f"{API_V2}/user/assets/folder/{folder_id}"

    @staticmethod
    def asset_increment_usage(asset_id: str) -> str:
        return f"{API_V2}/user/assets/{asset_id}/increment-usage"

    # Generation (Images, PDF, Story)
    GENERATE_PDF = f"{API_V2}/user/generate/pdf/pdf"
    GENERATE_STORY_STORY = f"{API_V2}/user/generate/story/story"
    GENERATE_STORY_INSPIRATION = f"{API_V2}/user/generate/story/inspiration"

    # Experiments (actual endpoints: assign, exposure, conversion, user/{identifier})
    EXPERIMENTS = f"{API_V2}/user/experiments"

    @staticmethod
    def experiment_assign(experiment_key: str) -> str:
        return f"{API_V2}/user/experiments/{experiment_key}/assign"

    @staticmethod
    def experiment_exposure(experiment_key: str) -> str:
        return f"{API_V2}/user/experiments/{experiment_key}/exposure"

    @staticmethod
    def experiment_conversion(experiment_key: str) -> str:
        return f"{API_V2}/user/experiments/{experiment_key}/conversion"

    @staticmethod
    def experiment_user(user_identifier: str) -> str:
        return f"{API_V2}/user/experiments/user/{user_identifier}"

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

    # ==========================================
    # Admin Endpoints
    # ==========================================

    # Admin Users
    ADMIN_USERS = f"{API_ADMIN}/users"

    @staticmethod
    def admin_user(user_id: str) -> str:
        return f"{API_ADMIN}/users/{user_id}"

    @staticmethod
    def admin_user_ban(user_id: str) -> str:
        return f"{API_ADMIN}/users/{user_id}/ban"

    @staticmethod
    def admin_user_unban(user_id: str) -> str:
        return f"{API_ADMIN}/users/{user_id}/unban"

    # Admin Subscriptions
    ADMIN_SUBSCRIPTIONS_REFUND = f"{API_ADMIN}/subscriptions/refund"
    ADMIN_SUBSCRIPTIONS_CANCEL = f"{API_ADMIN}/subscriptions/subscription/cancel"
    ADMIN_SUBSCRIPTIONS_GIFT_CREDITS = f"{API_ADMIN}/subscriptions/gift-credits"

    @staticmethod
    def admin_user_subscription(user_id: str) -> str:
        return f"{API_ADMIN}/subscriptions/user/{user_id}"

    # Admin Config
    ADMIN_CONFIG = f"{API_ADMIN}/config"

    @staticmethod
    def admin_config_key(key: str) -> str:
        return f"{API_ADMIN}/config/{key}"

    # Admin Themes
    ADMIN_THEMES = f"{API_ADMIN}/themes"
    ADMIN_THEMES_BATCH_GENERATE = f"{API_ADMIN}/themes/batch-generate"
    ADMIN_THEMES_GENERATION_STATUS = f"{API_ADMIN}/themes/generation-status"
    ADMIN_THEMES_CALENDAR = f"{API_ADMIN}/themes/calendar"
    ADMIN_THEMES_BATCH_APPROVE = f"{API_ADMIN}/themes/review/batch-approve"

    @staticmethod
    def admin_theme(theme_id: str) -> str:
        return f"{API_ADMIN}/themes/{theme_id}"

    @staticmethod
    def admin_theme_review(theme_id: str) -> str:
        return f"{API_ADMIN}/themes/{theme_id}/review"

    @staticmethod
    def admin_theme_regenerate(theme_id: str) -> str:
        return f"{API_ADMIN}/themes/{theme_id}/regenerate"

    @staticmethod
    def admin_theme_history(theme_id: str) -> str:
        return f"{API_ADMIN}/themes/{theme_id}/history"

    # Admin Campaigns
    ADMIN_CAMPAIGNS = f"{API_ADMIN}/campaigns"

    @staticmethod
    def admin_campaign(campaign_id: str) -> str:
        return f"{API_ADMIN}/campaigns/{campaign_id}"

    @staticmethod
    def admin_campaign_activate(campaign_id: str) -> str:
        return f"{API_ADMIN}/campaigns/{campaign_id}/activate"

    @staticmethod
    def admin_campaign_pause(campaign_id: str) -> str:
        return f"{API_ADMIN}/campaigns/{campaign_id}/pause"

    @staticmethod
    def admin_campaign_stats(campaign_id: str) -> str:
        return f"{API_ADMIN}/campaigns/{campaign_id}/stats"

    # Admin Feature Flags
    ADMIN_FEATURE_FLAGS = f"{API_ADMIN}/feature-flags"
    ADMIN_FEATURE_FLAGS_TEST = f"{API_ADMIN}/feature-flags/test-evaluation"
    ADMIN_FEATURE_FLAGS_CLIENT = f"{API_ADMIN}/feature-flags/client/flags"

    @staticmethod
    def admin_feature_flag(key: str) -> str:
        return f"{API_ADMIN}/feature-flags/{key}"

    @staticmethod
    def admin_feature_flag_toggle(key: str) -> str:
        return f"{API_ADMIN}/feature-flags/{key}/toggle"

    @staticmethod
    def admin_feature_flag_audit(key: str) -> str:
        return f"{API_ADMIN}/feature-flags/{key}/audit"

    # Admin Stats (Dashboard)
    ADMIN_STATS_DASHBOARD = f"{API_ADMIN}/stats/dashboard"
    ADMIN_STATS_USER_GROWTH = f"{API_ADMIN}/stats/user-growth"
    ADMIN_STATS_REVENUE = f"{API_ADMIN}/stats/revenue"
    ADMIN_STATS_PROJECTS = f"{API_ADMIN}/stats/projects"
    ADMIN_STATS_CREDITS = f"{API_ADMIN}/stats/credits"
    ADMIN_STATS_TIER_DISTRIBUTION = f"{API_ADMIN}/stats/tier-distribution"
    ADMIN_STATS_CONVERSION_FUNNEL = f"{API_ADMIN}/stats/conversion-funnel"
    ADMIN_STATS_EXPORTS = f"{API_ADMIN}/stats/exports"
    ADMIN_STATS_ASSETS = f"{API_ADMIN}/stats/assets"
    ADMIN_STATS_TIER_ACTIVITY = f"{API_ADMIN}/stats/tier-activity"
    ADMIN_STATS_SUBSCRIPTION_EVENTS = f"{API_ADMIN}/stats/subscription-events"
    ADMIN_STATS_PAGE_VIEWS = f"{API_ADMIN}/stats/page-views"
    ADMIN_STATS_PROJECT_DETAILS = f"{API_ADMIN}/stats/project-details"
    ADMIN_STATS_RETURNING_USERS = f"{API_ADMIN}/stats/returning-users"
    ADMIN_STATS_TIER_TREND = f"{API_ADMIN}/stats/tier-trend"
    ADMIN_STATS_TIER_CONVERSION = f"{API_ADMIN}/stats/tier-conversion"
    ADMIN_STATS_PERFORMANCE = f"{API_ADMIN}/stats/performance"
    ADMIN_STATS_USER_DISTRIBUTION = f"{API_ADMIN}/stats/user-distribution"

    # Admin Moderation
    ADMIN_MODERATION_LIST = f"{API_ADMIN}/moderation/marketplace/moderation/list"
    ADMIN_MODERATION_REPORTS = f"{API_ADMIN}/moderation/reports"
    ADMIN_MODERATION_REPORTS_STATS = f"{API_ADMIN}/moderation/reports/stats"

    @staticmethod
    def admin_moderation_listing(listing_id: str) -> str:
        return f"{API_ADMIN}/moderation/marketplace/moderation/{listing_id}"

    @staticmethod
    def admin_moderation_approve(listing_id: str) -> str:
        return f"{API_ADMIN}/moderation/marketplace/moderation/{listing_id}/approve"

    @staticmethod
    def admin_moderation_reject(listing_id: str) -> str:
        return f"{API_ADMIN}/moderation/marketplace/moderation/{listing_id}/reject"

    @staticmethod
    def admin_moderation_delete(listing_id: str) -> str:
        return f"{API_ADMIN}/moderation/marketplace/moderation/{listing_id}/delete"

    @staticmethod
    def admin_moderation_unpublish(listing_id: str) -> str:
        return f"{API_ADMIN}/moderation/marketplace/moderation/{listing_id}/unpublish"

    @staticmethod
    def admin_report(report_id: str) -> str:
        return f"{API_ADMIN}/moderation/reports/{report_id}"

    @staticmethod
    def admin_report_respond(report_id: str) -> str:
        return f"{API_ADMIN}/moderation/reports/{report_id}/respond"

    # Admin Logs
    ADMIN_LOGS_ERRORS = f"{API_ADMIN}/logs/errors"
    ADMIN_LOGS_ERRORS_STATS = f"{API_ADMIN}/logs/errors/stats"
    ADMIN_LOGS_OPERATIONS = f"{API_ADMIN}/logs/operations"
    ADMIN_LOGS_OPERATIONS_EXPORT = f"{API_ADMIN}/logs/operations/export"
    ADMIN_LOGS_AUDIT = f"{API_ADMIN}/logs/audit"

    # Admin Metrics
    ADMIN_METRICS_DAILY = f"{API_ADMIN}/metrics/daily"
    ADMIN_METRICS_MONTHLY = f"{API_ADMIN}/metrics/monthly"
    ADMIN_METRICS_RETENTION = f"{API_ADMIN}/metrics/retention"
    ADMIN_METRICS_FUNNEL = f"{API_ADMIN}/metrics/funnel"
    ADMIN_METRICS_ERRORS = f"{API_ADMIN}/metrics/errors"
    ADMIN_METRICS_DAU_TREND = f"{API_ADMIN}/metrics/dau-trend"
    ADMIN_METRICS_REFRESH = f"{API_ADMIN}/metrics/refresh"


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
