"""
Dependency Injection Container - Centralized service instantiation.

@module container
@version 2.0.0 - AsyncClient Migration

This module provides a dependency injection container that:
- Creates and caches service instances
- Manages repository and service dependencies
- Supports async initialization with AsyncClient
- Lazy initialization with async context

BREAKING CHANGES in v2.0:
- All repository properties are now async methods
- Repositories require AsyncClient parameter
- Container must be initialized with async context

Migration Guide:
    # OLD:
    container = get_container()
    repo = container.user_repository  # Sync property

    # NEW:
    container = get_container()
    repo = await container.get_user_repository()  # Async method
"""

from typing import Optional, TypeVar, Type
from functools import lru_cache
import logging

# Core Database
from core.database import get_async_db_client

# Infrastructure - Repositories
from infrastructure.repositories import (
    SupabaseCreditRepository,
    SupabaseUserRepository,
    SupabaseProjectRepository,
    SupabaseListingRepository,
    SupabaseFeatureFlagRepository,
    SupabaseExperimentRepository,
)

# Domains - Services
from domains.billing import BillingService, ICreditRepository
from domains.identity import IdentityService, IUserRepository
from domains.creation import CreationService, IProjectRepository
from domains.marketplace import MarketplaceService, IListingRepository
from domains.platform import (
    PlatformService,
    IFeatureFlagRepository,
    IExperimentRepository,
)
from domains.support import SupportService  # v3.0.0

# Application - Command Handlers
from application.commands.billing import (
    DeductCreditsHandler,
    AddCreditsHandler,
    GrantSignupBonusHandler,
)
from application.commands.identity import (
    CreateUserHandler,
    UpdateUserProfileHandler,
    UpdateUserTierHandler,
)
from application.commands.creation import (
    CreateProjectHandler,
    UpdateProjectHandler,
    DeleteProjectHandler,
    RestoreProjectHandler,
)
from application.commands.marketplace import (
    CreateListingHandler,
    UpdateListingHandler,
    UnpublishListingHandler,
    PurchaseListingHandler,
    CreateReportHandler,  # v3.0.0
)
from application.commands.platform import (
    CreateFeatureFlagHandler,
    CreateExperimentHandler,
)

# Application - Query Handlers
from application.queries.billing import (
    GetUserCreditsHandler,
    GetTransactionHistoryHandler,
)
from application.queries.identity import GetUserProfileHandler
from application.queries.creation import (
    GetProjectHandler,
    GetUserProjectsHandler,
    GetDashboardProjectsHandler,
)
from application.queries.marketplace import (
    GetListingHandler,
    SearchListingsHandler,
    GetMyListingsHandler,  # v3.0.0
    GetSellerStatsHandler,  # v3.0.0
    GetLeaderboardHandler,  # v3.0.0
    GetMyReportsHandler,  # v3.0.0
)
from application.queries.platform import (
    EvaluateFeatureFlagHandler,
    GetExperimentVariantHandler,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Container:
    """
    Dependency Injection Container (v2.0 - Async).

    Provides centralized service instantiation with async initialization.
    All repository getters are now async methods that require AsyncClient.

    CRITICAL CHANGES in v2.0:
    - Repositories require AsyncClient (mandatory parameter)
    - All repository getters are async methods (not properties)
    - Services are created lazily with async repositories
    - Handlers are created lazily with async services
    """

    _instance: Optional['Container'] = None
    _repositories: dict = {}
    _services: dict = {}
    _handlers: dict = {}

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize container (only once)."""
        if self._initialized:
            return
        self._repositories = {}
        self._services = {}
        self._handlers = {}
        self._initialized = True
        logger.info("[Container v2.0] Async dependency injection container initialized")

    # ========== Repositories (v2.0 - Async Methods) ==========

    async def get_credit_repository(self) -> ICreditRepository:
        """Get credit repository instance (async)."""
        if 'credit' not in self._repositories:
            db = await get_async_db_client()
            self._repositories['credit'] = SupabaseCreditRepository(db)
        return self._repositories['credit']

    async def get_user_repository(self) -> IUserRepository:
        """Get user repository instance (async)."""
        if 'user' not in self._repositories:
            db = await get_async_db_client()
            self._repositories['user'] = SupabaseUserRepository(db)
        return self._repositories['user']

    async def get_project_repository(self) -> IProjectRepository:
        """Get project repository instance (async)."""
        if 'project' not in self._repositories:
            db = await get_async_db_client()
            self._repositories['project'] = SupabaseProjectRepository(db)
        return self._repositories['project']

    async def get_listing_repository(self) -> IListingRepository:
        """Get listing repository instance (async)."""
        if 'listing' not in self._repositories:
            db = await get_async_db_client()
            self._repositories['listing'] = SupabaseListingRepository(db)
        return self._repositories['listing']

    async def get_feature_flag_repository(self) -> IFeatureFlagRepository:
        """Get feature flag repository instance (async)."""
        if 'feature_flag' not in self._repositories:
            db = await get_async_db_client()
            self._repositories['feature_flag'] = SupabaseFeatureFlagRepository(db)
        return self._repositories['feature_flag']

    async def get_experiment_repository(self) -> IExperimentRepository:
        """Get experiment repository instance (async)."""
        if 'experiment' not in self._repositories:
            db = await get_async_db_client()
            self._repositories['experiment'] = SupabaseExperimentRepository(db)
        return self._repositories['experiment']

    # ========== Domain Services (v2.0 - Async Methods) ==========

    async def get_billing_service(self) -> BillingService:
        """Get billing service instance (async)."""
        if 'billing' not in self._services:
            credit_repo = await self.get_credit_repository()
            self._services['billing'] = BillingService(credit_repo)
        return self._services['billing']

    async def get_identity_service(self) -> IdentityService:
        """Get identity service instance (async)."""
        if 'identity' not in self._services:
            user_repo = await self.get_user_repository()
            self._services['identity'] = IdentityService(user_repo)
        return self._services['identity']

    async def get_creation_service(self) -> CreationService:
        """Get creation service instance (async)."""
        if 'creation' not in self._services:
            project_repo = await self.get_project_repository()
            self._services['creation'] = CreationService(project_repo)
        return self._services['creation']

    async def get_marketplace_service(self) -> MarketplaceService:
        """Get marketplace service instance (async)."""
        if 'marketplace' not in self._services:
            listing_repo = await self.get_listing_repository()
            self._services['marketplace'] = MarketplaceService(listing_repo)
        return self._services['marketplace']

    async def get_platform_service(self) -> PlatformService:
        """Get platform service instance (async)."""
        if 'platform' not in self._services:
            flag_repo = await self.get_feature_flag_repository()
            experiment_repo = await self.get_experiment_repository()
            self._services['platform'] = PlatformService(
                flag_repository=flag_repo,
                experiment_repository=experiment_repo,
            )
        return self._services['platform']

    async def get_support_service(self) -> SupportService:
        """Get support service instance (v3.0.0, async)."""
        if 'support' not in self._services:
            db = await get_async_db_client()
            self._services['support'] = SupportService(db)
        return self._services['support']

    async def get_user_profile_service(self):
        """
        Get user profile service instance (v2.3.0, async).

        WHY separate from IdentityService?
        - UserProfileService handles cross-domain operations (user + credits + listings + notifications)
        - IdentityService handles core identity operations (CRUD, tier management)
        - Separation of concerns: profile aggregation vs identity management

        Returns:
            UserProfileService with all required repositories injected
        """
        from domains.identity.user_profile_service import UserProfileService
        from infrastructure.repositories import (
            SupabaseUserRepository,
            SupabaseCreditRepository,
            SupabaseListingRepository,
            SupabaseNotificationRepository,
        )

        if 'user_profile' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            # Create all required repositories
            user_repo = SupabaseUserRepository(db)
            credit_repo = SupabaseCreditRepository(db)
            listing_repo = SupabaseListingRepository(db)
            notif_repo = SupabaseNotificationRepository(db)

            # Create service with dependencies
            self._services['user_profile'] = UserProfileService(
                user_repo=user_repo,
                credit_repo=credit_repo,
                listing_repo=listing_repo,
                notif_repo=notif_repo,
            )
        return self._services['user_profile']

    async def get_article_service(self):
        """Get article service instance (v3.31, async)."""
        from domains.articles.service import ArticleService
        from infrastructure.repositories.article_repository import SupabaseArticleRepository
        if 'article' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")
            repository = SupabaseArticleRepository(db)
            self._services['article'] = ArticleService(repository)
        return self._services['article']

    async def get_static_page_service(self):
        """
        Get static page service instance (v3.32, async).

        v2.1.0: Now injects TierService and ConfigRepository for dynamic
        template variable replacement from database instead of hardcoded values.
        """
        from domains.static_pages.service import StaticPageService
        from infrastructure.repositories.static_page_repository import SupabaseStaticPageRepository
        from infrastructure.repositories.config_repository import SupabaseConfigRepository
        from domains.identity.tier_service import TierService

        if 'static_page' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            # Create repositories
            repository = SupabaseStaticPageRepository(db)
            config_repo = SupabaseConfigRepository(db)

            # Create TierService for tier-related configs
            tier_service = TierService(config_repo)

            # Create service with all dependencies
            self._services['static_page'] = StaticPageService(
                repository=repository,
                tier_service=tier_service,
                config_repo=config_repo,
            )
        return self._services['static_page']

    async def get_logging_service(self):
        """Get logging service instance (v3.0.0, async)."""
        from domains.logging import LoggingService
        if 'logging' not in self._services:
            db = await get_async_db_client()
            self._services['logging'] = LoggingService(db)
        return self._services['logging']

    async def get_themes_service(self):
        """Get themes service instance (v3.0.0, async)."""
        from domains.themes import ThemesService
        if 'themes' not in self._services:
            db = await get_async_db_client()
            self._services['themes'] = ThemesService(db)
        return self._services['themes']

    async def get_user_tasks_service(self):
        """Get user tasks service instance (v3.0.0, async)."""
        from domains.tasks import TasksService
        from infrastructure.repositories.tasks_repository import SupabaseUserTasksRepository
        if 'user_tasks' not in self._services:
            db = await get_async_db_client()
            tasks_repo = SupabaseUserTasksRepository(db)
            credit_repo = await self.get_credit_repository()
            self._services['user_tasks'] = TasksService(tasks_repo, credit_repo)
        return self._services['user_tasks']

    async def get_tools_service(self):
        """Get tools service instance (v3.0.0, async)."""
        from domains.tools import ToolsService
        from infrastructure.repositories.asset_repository import SupabaseAssetRepository
        from shared.ai.ocr_service import process_ocr
        from domains.shared.access_control import AccessControl
        if 'tools' not in self._services:
            db = await get_async_db_client()
            credit_repo = await self.get_credit_repository()
            asset_repo = SupabaseAssetRepository(db)
            # Note: AsyncClient also has storage methods
            self._services['tools'] = ToolsService(
                credit_repo,
                asset_repo,
                db,  # AsyncClient for storage
                process_ocr,  # OCR processor function
                AccessControl,  # Access control class
            )
        return self._services['tools']

    async def get_system_resources_admin_service(self):
        """Get system resources admin service instance (v3.0.0, async)."""
        from domains.content.system_resources_service import SystemResourcesService
        from infrastructure.repositories.system_resources_admin_repository import (
            SupabaseSystemResourcesAdminRepository
        )
        if 'system_resources_admin' not in self._services:
            db = await get_async_db_client()
            repository = SupabaseSystemResourcesAdminRepository(db)
            self._services['system_resources_admin'] = SystemResourcesService(
                repository=repository,
                storage_client=db,  # AsyncClient for storage
            )
        return self._services['system_resources_admin']

    async def get_templates_service(self):
        """Get templates service instance (v3.0.0, async)."""
        from domains.templates.templates_service import TemplatesService
        from infrastructure.repositories.templates_repository import SupabaseTemplatesRepository
        if 'templates' not in self._services:
            db = await get_async_db_client()
            repository = SupabaseTemplatesRepository(db)
            self._services['templates'] = TemplatesService(repository)
        return self._services['templates']

    async def get_subscription_service(self):
        """
        Get subscription service instance (v3.28, async).

        WHY separate from BillingService?
        - SubscriptionService handles Stripe subscription lifecycle (cancel, downgrade, refund)
        - BillingService handles credits and internal transactions
        - Different external dependencies (Stripe vs internal DB)
        """
        from domains.subscriptions import SubscriptionService
        from infrastructure.repositories import (
            SupabaseUserRepository,
            SupabasePaymentRepository,
            SupabaseAdminUsersRepository,
        )

        if 'subscription' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            users_repo = SupabaseUserRepository(db)
            payment_repo = SupabasePaymentRepository(db)
            admin_repo = SupabaseAdminUsersRepository(db)

            self._services['subscription'] = SubscriptionService(
                users_repo=users_repo,
                payment_repo=payment_repo,
                admin_repo=admin_repo,
            )
        return self._services['subscription']

    async def get_admin_users_service(self):
        """
        Get admin users service instance (v3.28, async).

        WHY AdminUsersService?
        - Encapsulates admin-specific user operations (audit, credit adjust, tier change)
        - Separates admin operations from regular user operations (IdentityService)
        - Provides audit logging for all admin actions
        """
        from domains.admin.admin_users_service import AdminUsersService
        from infrastructure.repositories import (
            SupabaseUserRepository,
            SupabaseAdminUsersRepository,
            SupabaseProjectRepository,
            SupabaseAssetRepository,
            SupabaseAnalyticsRepository,
        )

        if 'admin_users' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            user_repo = SupabaseUserRepository(db)
            admin_repo = SupabaseAdminUsersRepository(db)
            project_repo = SupabaseProjectRepository(db)
            asset_repo = SupabaseAssetRepository(db)
            analytics_repo = SupabaseAnalyticsRepository(db)

            self._services['admin_users'] = AdminUsersService(
                user_repo=user_repo,
                admin_repo=admin_repo,
                project_repo=project_repo,
                asset_repo=asset_repo,
                analytics_repo=analytics_repo,
            )
        return self._services['admin_users']

    async def get_admin_logs_service(self):
        """
        Get admin logs service instance (v3.29, async).

        WHY AdminLogsService?
        - Encapsulates admin-specific log query operations
        - Separates log reads (AdminLogsService) from log writes (LoggingService)
        - Combines ErrorLogs + OperationLogs under unified interface
        """
        from domains.admin.admin_logs_service import AdminLogsService
        from infrastructure.repositories import (
            SupabaseAdminUsersRepository,
            SupabaseErrorLogsRepository,
        )

        if 'admin_logs' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            error_logs_repo = SupabaseErrorLogsRepository(db)
            admin_repo = SupabaseAdminUsersRepository(db)

            self._services['admin_logs'] = AdminLogsService(
                error_logs_repo=error_logs_repo,
                admin_repo=admin_repo,
            )
        return self._services['admin_logs']

    async def get_admin_metrics_service(self):
        """
        Get admin metrics service instance (v3.29, async).

        WHY AdminMetricsService?
        - Encapsulates metrics calculation and aggregation logic
        - Decouples API layer from repository implementations
        - Provides unified interface for all metrics operations
        """
        from domains.admin.admin_metrics_service import AdminMetricsService
        from infrastructure.repositories import SupabaseMetricsRepository

        if 'admin_metrics' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            metrics_repo = SupabaseMetricsRepository(db)

            self._services['admin_metrics'] = AdminMetricsService(
                metrics_repo=metrics_repo,
            )
        return self._services['admin_metrics']

    async def get_admin_tasks_service(self):
        """
        Get admin tasks service instance (v3.29, async).

        WHY AdminTasksService?
        - Encapsulates task management operations (status, logs, health, run)
        - Decouples API layer from repository and scheduler
        - Provides unified interface for task monitoring
        """
        from domains.admin.admin_tasks_service import AdminTasksService
        from infrastructure.repositories import SupabaseTasksRepository

        if 'admin_tasks' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            tasks_repo = SupabaseTasksRepository(db)

            self._services['admin_tasks'] = AdminTasksService(
                tasks_repo=tasks_repo,
            )
        return self._services['admin_tasks']

    async def get_webhook_retry_service(self):
        """
        Get webhook retry service instance (v3.29, async).

        WHY in Container?
        - Centralizes complex service construction (requires 4 repositories + 2 services)
        - Enables testing with mock services
        - Follows DIP - API layer doesn't know about concrete implementations
        """
        from domains.webhooks import ClerkWebhookService, StripeWebhookService
        from domains.webhooks.webhook_retry_service import WebhookRetryService
        from infrastructure.repositories import (
            SupabaseWebhookRepository,
            SupabaseUserRepository,
            SupabaseCreditRepository,
            SupabasePaymentRepository,
        )

        if 'webhook_retry' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            # Repositories
            webhook_repo = SupabaseWebhookRepository(db)
            user_repo = SupabaseUserRepository(db)
            credit_repo = SupabaseCreditRepository(db)
            payment_repo = SupabasePaymentRepository(db)

            # Webhook Services
            clerk_service = ClerkWebhookService(user_repo, credit_repo)
            stripe_service = StripeWebhookService(user_repo, credit_repo, payment_repo)

            self._services['webhook_retry'] = WebhookRetryService(
                webhook_repo, clerk_service, stripe_service
            )
        return self._services['webhook_retry']

    async def get_events_service(self):
        """
        Get events service instance (v3.29, async).

        WHY in Container?
        - Centralizes service construction
        - Enables testing with mock services
        - Follows DIP - API layer doesn't know about concrete implementations
        """
        from application.services.events_service import EventsService
        from infrastructure.repositories.events_repository import SupabaseEventsRepository

        if 'events' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            repository = SupabaseEventsRepository(db)
            self._services['events'] = EventsService(repository)
        return self._services['events']

    async def get_feature_flag_service(self):
        """
        Get feature flag service instance (v3.29, async).

        WHY in Container?
        - Centralizes service construction
        - Enables testing with mock services
        - Follows DIP - API layer doesn't know about concrete implementations
        """
        from domains.feature_flags import FeatureFlagService, FeatureFlagRepository

        if 'feature_flag_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            repository = FeatureFlagRepository(db)
            self._services['feature_flag_service'] = FeatureFlagService(repository)
        return self._services['feature_flag_service']

    async def get_experiment_service(self):
        """
        Get experiment service instance (v3.29, async).

        WHY in Container?
        - Centralizes service construction
        - Enables testing with mock services
        - Follows DIP - API layer doesn't know about concrete implementations
        """
        from domains.platform.experiments.service import ExperimentService
        from infrastructure.repositories.experiment_repository import SupabaseExperimentRepository

        if 'experiment_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            repository = SupabaseExperimentRepository(db)
            self._services['experiment_service'] = ExperimentService(repository)
        return self._services['experiment_service']

    async def get_config_service(self):
        """
        Get config service instance (v3.29, async).

        WHY in Container?
        - Centralizes service construction
        - Enables testing with mock services
        - Follows DIP - API layer doesn't know about concrete implementations
        """
        from domains.platform.config_service import ConfigService
        from infrastructure.repositories.config_repository import SupabaseConfigRepository

        if 'config_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            config_repo = SupabaseConfigRepository(db)
            self._services['config_service'] = ConfigService(config_repo)
        return self._services['config_service']

    async def get_admin_audit_service(self):
        """
        Get admin audit service for logging admin operations (v3.29, async).

        WHY separate service?
        - Centralizes audit logging for admin operations
        - Avoids duplicate get_async_db_client() calls in API layer
        - Enables consistent audit trail across all admin endpoints
        """
        from infrastructure.repositories import SupabaseAdminUsersRepository

        if 'admin_audit' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            self._services['admin_audit'] = SupabaseAdminUsersRepository(db)
        return self._services['admin_audit']

    async def get_category_service(self):
        """
        Get category service instance (v3.29, async).

        WHY in Container?
        - Centralizes service construction
        - Enables testing with mock services
        - Follows DIP - API layer doesn't know about concrete implementations
        """
        from domains.content.category_service import CategoryService
        from infrastructure.repositories.category_repository import SupabaseCategoryRepository

        if 'category_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            repository = SupabaseCategoryRepository(db)
            self._services['category_service'] = CategoryService(repository)
        return self._services['category_service']

    async def get_webhook_repository(self):
        """
        Get webhook repository instance (v3.29, async).

        WHY separate from get_webhook_retry_service?
        - This is used for read-only queries (list failed webhooks)
        - Avoids overhead of constructing full retry service with Clerk/Stripe
        """
        from infrastructure.repositories import SupabaseWebhookRepository

        if 'webhook_repository' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            self._services['webhook_repository'] = SupabaseWebhookRepository(db)
        return self._services['webhook_repository']

    async def get_system_resource_repository(self):
        """
        Get system resource repository instance (v3.29, async).

        WHY in Container?
        - Centralizes repository construction
        - Enables testing with mock repositories
        - Used by admin asset category resources endpoint
        """
        from infrastructure.repositories.system_resource_repository import (
            SupabaseSystemResourceRepository
        )

        if 'system_resource_repository' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            self._services['system_resource_repository'] = SupabaseSystemResourceRepository(db)
        return self._services['system_resource_repository']

    async def get_generation_history_service(self):
        """
        Get generation history service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction
        - Enables testing with mock services
        - Used by user generations API for history management
        """
        from domains.generation import GenerationHistoryService

        if 'generation_history_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            self._services['generation_history_service'] = GenerationHistoryService(db_client=db)
        return self._services['generation_history_service']

    async def get_generation_service(self):
        """
        Get generation service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction with all dependencies
        - GenerationService requires BillingService, AssetRepository, TierService
        - Enables testing with mock services
        - Used by user generate images API
        """
        from domains.generation import GenerationService
        from infrastructure.repositories.asset_repository import SupabaseAssetRepository
        from domains.identity.tier_service import TierService

        if 'generation_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            billing_service = await self.get_billing_service()
            asset_repository = SupabaseAssetRepository(db)
            tier_service = TierService()

            self._services['generation_service'] = GenerationService(
                billing_service=billing_service,
                asset_repository=asset_repository,
                tier_service=tier_service,
                db_client=db,
            )
        return self._services['generation_service']

    async def get_analytics_service(self):
        """
        Get analytics service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction
        - Used by user analytics API for event tracking
        """
        from domains.analytics import AnalyticsService
        from infrastructure.repositories.analytics_events_repository import SupabaseAnalyticsEventsRepository

        if 'analytics_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            analytics_repo = SupabaseAnalyticsEventsRepository(db)
            self._services['analytics_service'] = AnalyticsService(analytics_repo)
        return self._services['analytics_service']

    async def get_campaign_service(self):
        """
        Get campaign service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction
        - Used by user campaigns API for marketing campaigns
        """
        from domains.marketing import CampaignService
        from infrastructure.repositories.campaign_repository import SupabaseCampaignRepository

        if 'campaign_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            campaign_repo = SupabaseCampaignRepository(db)
            self._services['campaign_service'] = CampaignService(campaign_repo)
        return self._services['campaign_service']

    async def get_export_service(self):
        """
        Get export service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction
        - Used by user export API for PDF/ZIP generation
        """
        from domains.export import ExportService
        from infrastructure.repositories.project_repository import SupabaseProjectRepository

        if 'export_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            project_repo = SupabaseProjectRepository(db)
            self._services['export_service'] = ExportService(project_repository=project_repo)
        return self._services['export_service']

    async def get_thumbnail_service(self):
        """
        Get thumbnail service instance (v2.3.0, async).

        WHY in Container?
        - Centralizes service construction with all dependencies
        - ThumbnailService requires ExportService, ProjectRepository, and storage client
        - Used by UpdateProjectHandler for background thumbnail generation
        """
        from domains.creation.thumbnail_service import ThumbnailService
        from infrastructure.repositories.project_repository import SupabaseProjectRepository

        if 'thumbnail_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            export_service = await self.get_export_service()
            project_repo = SupabaseProjectRepository(db)

            self._services['thumbnail_service'] = ThumbnailService(
                export_service=export_service,
                project_repository=project_repo,
                storage_client=db,  # AsyncClient has storage methods
            )
        return self._services['thumbnail_service']

    async def get_pdf_generation_service(self):
        """
        Get PDF generation service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction
        - Used by user PDF generation API
        """
        from domains.generation import PdfGenerationService
        from infrastructure.repositories.project_repository import SupabaseProjectRepository

        if 'pdf_generation_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            project_repo = SupabaseProjectRepository(db)
            self._services['pdf_generation_service'] = PdfGenerationService(project_repository=project_repo)
        return self._services['pdf_generation_service']

    async def get_story_generation_service(self):
        """
        Get story generation service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction with all dependencies
        - StoryGenerationService requires BillingService
        - Used by user story generation API
        """
        from domains.generation import StoryGenerationService

        if 'story_generation_service' not in self._services:
            billing_service = await self.get_billing_service()
            self._services['story_generation_service'] = StoryGenerationService(billing_service=billing_service)
        return self._services['story_generation_service']

    async def get_onboarding_service(self):
        """
        Get onboarding service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction
        - Used by user onboarding API
        """
        from domains.onboarding import OnboardingService, OnboardingRepository

        if 'onboarding_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            repository = OnboardingRepository(db)
            self._services['onboarding_service'] = OnboardingService(repository)
        return self._services['onboarding_service']

    async def get_referral_service(self):
        """
        Get referral service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction
        - Used by user referrals API
        """
        from domains.referrals import ReferralService, ReferralRepository

        if 'referral_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            repository = ReferralRepository(db)
            self._services['referral_service'] = ReferralService(repository)
        return self._services['referral_service']

    async def get_clerk_webhook_service(self):
        """
        Get Clerk webhook service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction with all dependencies
        - ClerkWebhookService requires UserRepository and CreditRepository
        - Used by webhooks API for Clerk events
        """
        from domains.webhooks import ClerkWebhookService
        from infrastructure.repositories import SupabaseUserRepository, SupabaseCreditRepository

        if 'clerk_webhook_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            user_repo = SupabaseUserRepository(db)
            credit_repo = SupabaseCreditRepository(db)
            self._services['clerk_webhook_service'] = ClerkWebhookService(user_repo, credit_repo)
        return self._services['clerk_webhook_service']

    async def get_stripe_webhook_service(self):
        """
        Get Stripe webhook service instance (v1.2.0, async).

        WHY in Container?
        - Centralizes service construction with all dependencies
        - StripeWebhookService requires UserRepository, CreditRepository, PaymentRepository
        - Used by webhooks API for Stripe events
        """
        from domains.webhooks import StripeWebhookService
        from infrastructure.repositories import (
            SupabaseUserRepository,
            SupabaseCreditRepository,
            SupabasePaymentRepository,
        )

        if 'stripe_webhook_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            user_repo = SupabaseUserRepository(db)
            credit_repo = SupabaseCreditRepository(db)
            payment_repo = SupabasePaymentRepository(db)
            self._services['stripe_webhook_service'] = StripeWebhookService(
                user_repo, credit_repo, payment_repo
            )
        return self._services['stripe_webhook_service']

    async def get_assets_service(self):
        """Get assets service instance (v3.0.0, async)."""
        from domains.assets.assets_service import AssetsService
        from infrastructure.repositories.asset_repository import SupabaseAssetRepository
        if 'assets' not in self._services:
            db = await get_async_db_client()
            repository = SupabaseAssetRepository(db)
            self._services['assets'] = AssetsService(repository, db)  # AsyncClient for storage
        return self._services['assets']

    # ========== Workspace & Tag Services (v3.33) ==========

    async def get_workspace_service(self):
        """
        Get workspace service instance (v3.33, async).

        WHY in Container?
        - Centralizes service construction
        - Used by Tag API and Clerk webhook for automatic workspace creation
        - Phase 1: Only manages default personal workspaces
        """
        from domains.workspace import WorkspaceService
        from infrastructure.repositories.workspace_repository import SupabaseWorkspaceRepository

        if 'workspace_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            repository = SupabaseWorkspaceRepository(db)
            self._services['workspace_service'] = WorkspaceService(repository)
        return self._services['workspace_service']

    async def get_tag_service(self):
        """
        Get tag service instance (v3.33, async).

        WHY in Container?
        - Centralizes service construction
        - Used by Tag API for tag CRUD operations
        - Phase 1: Full tag management functionality
        """
        from domains.tag import TagService
        from infrastructure.repositories.tag_repository import SupabaseTagRepository

        if 'tag_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            repository = SupabaseTagRepository(db)
            config_service = await self.get_config_service()
            self._services['tag_service'] = TagService(repository, config_service)
        return self._services['tag_service']

    async def get_project_tag_service(self):
        """
        Get project tag service instance (v3.33, async).

        WHY in Container?
        - Centralizes service construction
        - Used by Project Tag API for project-tag associations
        """
        from domains.tag import ProjectTagService
        from infrastructure.repositories.tag_repository import (
            SupabaseTagRepository,
            SupabaseProjectTagRepository,
        )

        if 'project_tag_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            tag_repo = SupabaseTagRepository(db)
            project_tag_repo = SupabaseProjectTagRepository(db)
            config_service = await self.get_config_service()
            self._services['project_tag_service'] = ProjectTagService(
                project_tag_repository=project_tag_repo,
                tag_repository=tag_repo,
                config_service=config_service,
            )
        return self._services['project_tag_service']

    async def get_asset_tag_service(self):
        """
        Get asset tag service instance (v3.33, async).

        WHY in Container?
        - Centralizes service construction
        - Used by Asset Tag API for asset-tag associations
        """
        from domains.tag import AssetTagService
        from infrastructure.repositories.tag_repository import (
            SupabaseTagRepository,
            SupabaseAssetTagRepository,
        )

        if 'asset_tag_service' not in self._services:
            db = await get_async_db_client()
            if db is None:
                raise RuntimeError("Database client not available")

            tag_repo = SupabaseTagRepository(db)
            asset_tag_repo = SupabaseAssetTagRepository(db)
            config_service = await self.get_config_service()
            self._services['asset_tag_service'] = AssetTagService(
                asset_tag_repository=asset_tag_repo,
                tag_repository=tag_repo,
                config_service=config_service,
            )
        return self._services['asset_tag_service']

    # ========== Command Handlers (v2.0 - Async Methods) ==========

    async def get_deduct_credits_handler(self) -> DeductCreditsHandler:
        """Get deduct credits handler (async)."""
        if 'deduct_credits' not in self._handlers:
            billing_service = await self.get_billing_service()
            self._handlers['deduct_credits'] = DeductCreditsHandler(billing_service)
        return self._handlers['deduct_credits']

    async def get_add_credits_handler(self) -> AddCreditsHandler:
        """Get add credits handler (async)."""
        if 'add_credits' not in self._handlers:
            billing_service = await self.get_billing_service()
            self._handlers['add_credits'] = AddCreditsHandler(billing_service)
        return self._handlers['add_credits']

    async def get_grant_signup_bonus_handler(self) -> GrantSignupBonusHandler:
        """Get grant signup bonus handler (async)."""
        if 'grant_signup_bonus' not in self._handlers:
            billing_service = await self.get_billing_service()
            self._handlers['grant_signup_bonus'] = GrantSignupBonusHandler(billing_service)
        return self._handlers['grant_signup_bonus']

    async def get_create_user_handler(self) -> CreateUserHandler:
        """Get create user handler (async)."""
        if 'create_user' not in self._handlers:
            identity_service = await self.get_identity_service()
            self._handlers['create_user'] = CreateUserHandler(identity_service)
        return self._handlers['create_user']

    async def get_update_user_profile_handler(self) -> UpdateUserProfileHandler:
        """Get update user profile handler (async)."""
        if 'update_user_profile' not in self._handlers:
            identity_service = await self.get_identity_service()
            self._handlers['update_user_profile'] = UpdateUserProfileHandler(identity_service)
        return self._handlers['update_user_profile']

    async def get_update_user_tier_handler(self) -> UpdateUserTierHandler:
        """Get update user tier handler (async)."""
        if 'update_user_tier' not in self._handlers:
            identity_service = await self.get_identity_service()
            self._handlers['update_user_tier'] = UpdateUserTierHandler(identity_service)
        return self._handlers['update_user_tier']

    async def get_create_project_handler(self) -> CreateProjectHandler:
        """Get create project handler (async)."""
        if 'create_project' not in self._handlers:
            creation_service = await self.get_creation_service()
            self._handlers['create_project'] = CreateProjectHandler(creation_service)
        return self._handlers['create_project']

    async def get_update_project_handler(self) -> UpdateProjectHandler:
        """
        Get update project handler (async).

        P1-013: includes listing_repository for locked elements check
        v2.3.0: includes thumbnail_service for background thumbnail generation
        """
        if 'update_project' not in self._handlers:
            creation_service = await self.get_creation_service()
            listing_repo = await self.get_listing_repository()
            thumbnail_service = await self.get_thumbnail_service()
            self._handlers['update_project'] = UpdateProjectHandler(
                creation_service,
                listing_repo,  # P1-013: For locked elements check
                thumbnail_service,  # v2.3.0: For background thumbnail generation
            )
        return self._handlers['update_project']

    async def get_delete_project_handler(self) -> DeleteProjectHandler:
        """Get delete project handler (async)."""
        if 'delete_project' not in self._handlers:
            creation_service = await self.get_creation_service()
            self._handlers['delete_project'] = DeleteProjectHandler(creation_service)
        return self._handlers['delete_project']

    async def get_restore_project_handler(self) -> RestoreProjectHandler:
        """Get restore project handler (async)."""
        if 'restore_project' not in self._handlers:
            creation_service = await self.get_creation_service()
            self._handlers['restore_project'] = RestoreProjectHandler(creation_service)
        return self._handlers['restore_project']

    async def get_create_listing_handler(self) -> CreateListingHandler:
        """Get create listing handler (async)."""
        if 'create_listing' not in self._handlers:
            marketplace_service = await self.get_marketplace_service()
            db = await get_async_db_client()
            self._handlers['create_listing'] = CreateListingHandler(
                marketplace_service, db
            )
        return self._handlers['create_listing']

    async def get_update_listing_handler(self) -> UpdateListingHandler:
        """Get update listing handler (async)."""
        if 'update_listing' not in self._handlers:
            marketplace_service = await self.get_marketplace_service()
            db = await get_async_db_client()
            self._handlers['update_listing'] = UpdateListingHandler(
                marketplace_service, db
            )
        return self._handlers['update_listing']

    async def get_unpublish_listing_handler(self) -> UnpublishListingHandler:
        """Get unpublish listing handler (async)."""
        if 'unpublish_listing' not in self._handlers:
            marketplace_service = await self.get_marketplace_service()
            db = await get_async_db_client()
            self._handlers['unpublish_listing'] = UnpublishListingHandler(
                marketplace_service, db
            )
        return self._handlers['unpublish_listing']

    async def get_purchase_listing_handler(self) -> PurchaseListingHandler:
        """Get purchase listing handler (async, cross-domain)."""
        if 'purchase_listing' not in self._handlers:
            marketplace_service = await self.get_marketplace_service()
            billing_service = await self.get_billing_service()
            self._handlers['purchase_listing'] = PurchaseListingHandler(
                marketplace_service=marketplace_service,
                billing_service=billing_service,
            )
        return self._handlers['purchase_listing']

    async def get_create_feature_flag_handler(self) -> CreateFeatureFlagHandler:
        """Get create feature flag handler (async)."""
        if 'create_feature_flag' not in self._handlers:
            platform_service = await self.get_platform_service()
            self._handlers['create_feature_flag'] = CreateFeatureFlagHandler(platform_service)
        return self._handlers['create_feature_flag']

    async def get_create_experiment_handler(self) -> CreateExperimentHandler:
        """Get create experiment handler (async)."""
        if 'create_experiment' not in self._handlers:
            platform_service = await self.get_platform_service()
            self._handlers['create_experiment'] = CreateExperimentHandler(platform_service)
        return self._handlers['create_experiment']

    async def get_create_report_handler(self) -> CreateReportHandler:
        """Get create report handler (v3.0.0, async)."""
        if 'create_report' not in self._handlers:
            support_service = await self.get_support_service()
            self._handlers['create_report'] = CreateReportHandler(support_service)
        return self._handlers['create_report']

    async def get_create_support_ticket_handler(self):
        """Get create support ticket handler (v3.1.0, async)."""
        from application.commands.support import CreateSupportTicketHandler
        if 'create_support_ticket' not in self._handlers:
            support_service = await self.get_support_service()
            self._handlers['create_support_ticket'] = CreateSupportTicketHandler(support_service)
        return self._handlers['create_support_ticket']

    async def get_ai_chat_support_handler(self):
        """Get AI chat support handler (v3.1.0, async)."""
        from application.commands.support import AiChatSupportHandler
        if 'ai_chat_support' not in self._handlers:
            support_service = await self.get_support_service()
            self._handlers['ai_chat_support'] = AiChatSupportHandler(support_service)
        return self._handlers['ai_chat_support']

    async def get_send_contact_message_handler(self):
        """Get send contact message handler (v3.1.0, async)."""
        from application.commands.support import SendContactMessageHandler
        if 'send_contact_message' not in self._handlers:
            support_service = await self.get_support_service()
            self._handlers['send_contact_message'] = SendContactMessageHandler(support_service)
        return self._handlers['send_contact_message']

    async def get_submit_feedback_handler(self):
        """Get submit feedback handler (v3.1.0, async)."""
        from application.commands.support import SubmitFeedbackHandler
        if 'submit_feedback' not in self._handlers:
            support_service = await self.get_support_service()
            self._handlers['submit_feedback'] = SubmitFeedbackHandler(support_service)
        return self._handlers['submit_feedback']

    async def get_create_error_log_handler(self):
        """Get create error log handler (v3.0.0, async)."""
        from application.commands.logging import CreateErrorLogHandler
        if 'create_error_log' not in self._handlers:
            logging_service = await self.get_logging_service()
            self._handlers['create_error_log'] = CreateErrorLogHandler(logging_service)
        return self._handlers['create_error_log']

    async def get_create_error_log_batch_handler(self):
        """Get create error log batch handler (v3.0.0, async)."""
        from application.commands.logging import CreateErrorLogBatchHandler
        if 'create_error_log_batch' not in self._handlers:
            logging_service = await self.get_logging_service()
            self._handlers['create_error_log_batch'] = CreateErrorLogBatchHandler(logging_service)
        return self._handlers['create_error_log_batch']

    # System Resources Command Handlers (v3.0.0, async)
    async def get_create_system_resource_handler(self):
        """Get create system resource handler (v3.0.0, async)."""
        from application.commands.system_resources import CreateSystemResourceHandler
        if 'create_system_resource' not in self._handlers:
            service = await self.get_system_resources_admin_service()
            self._handlers['create_system_resource'] = CreateSystemResourceHandler(service)
        return self._handlers['create_system_resource']

    async def get_update_system_resource_handler(self):
        """Get update system resource handler (v3.0.0, async)."""
        from application.commands.system_resources import UpdateSystemResourceHandler
        if 'update_system_resource' not in self._handlers:
            service = await self.get_system_resources_admin_service()
            self._handlers['update_system_resource'] = UpdateSystemResourceHandler(service)
        return self._handlers['update_system_resource']

    async def get_replace_resource_file_handler(self):
        """Get replace resource file handler (v3.0.0, async)."""
        from application.commands.system_resources import ReplaceResourceFileHandler
        if 'replace_resource_file' not in self._handlers:
            service = await self.get_system_resources_admin_service()
            self._handlers['replace_resource_file'] = ReplaceResourceFileHandler(service)
        return self._handlers['replace_resource_file']

    async def get_delete_system_resource_handler(self):
        """Get delete system resource handler (v3.0.0, async)."""
        from application.commands.system_resources import DeleteSystemResourceHandler
        if 'delete_system_resource' not in self._handlers:
            service = await self.get_system_resources_admin_service()
            self._handlers['delete_system_resource'] = DeleteSystemResourceHandler(service)
        return self._handlers['delete_system_resource']

    async def get_batch_operation_handler(self):
        """Get batch operation handler (v3.0.0, async)."""
        from application.commands.system_resources import BatchOperationHandler
        if 'batch_operation' not in self._handlers:
            service = await self.get_system_resources_admin_service()
            self._handlers['batch_operation'] = BatchOperationHandler(service)
        return self._handlers['batch_operation']

    # ========== Query Handlers (v2.0 - Async Methods) ==========

    async def get_user_credits_handler(self) -> GetUserCreditsHandler:
        """Get user credits query handler (async)."""
        if 'get_user_credits' not in self._handlers:
            billing_service = await self.get_billing_service()
            self._handlers['get_user_credits'] = GetUserCreditsHandler(billing_service)
        return self._handlers['get_user_credits']

    async def get_transaction_history_handler(self) -> GetTransactionHistoryHandler:
        """Get transaction history query handler (async)."""
        if 'get_transaction_history' not in self._handlers:
            billing_service = await self.get_billing_service()
            self._handlers['get_transaction_history'] = GetTransactionHistoryHandler(billing_service)
        return self._handlers['get_transaction_history']

    async def get_user_profile_handler(self) -> GetUserProfileHandler:
        """Get user profile query handler (async)."""
        if 'get_user_profile' not in self._handlers:
            identity_service = await self.get_identity_service()
            self._handlers['get_user_profile'] = GetUserProfileHandler(identity_service)
        return self._handlers['get_user_profile']

    async def get_project_handler(self) -> GetProjectHandler:
        """Get project query handler (async)."""
        if 'get_project' not in self._handlers:
            creation_service = await self.get_creation_service()
            self._handlers['get_project'] = GetProjectHandler(creation_service)
        return self._handlers['get_project']

    async def get_current_theme_handler(self):
        """Get current theme query handler (v3.0.0, async)."""
        from application.queries.themes import GetCurrentThemeHandler
        if 'get_current_theme' not in self._handlers:
            themes_service = await self.get_themes_service()
            self._handlers['get_current_theme'] = GetCurrentThemeHandler(themes_service)
        return self._handlers['get_current_theme']

    async def get_task_status_handler(self):
        """Get task status query handler (v3.0.0, async)."""
        from application.queries.tasks import GetTaskStatusHandler
        if 'get_task_status' not in self._handlers:
            user_tasks_service = await self.get_user_tasks_service()
            self._handlers['get_task_status'] = GetTaskStatusHandler(user_tasks_service)
        return self._handlers['get_task_status']

    async def get_cancel_task_handler(self):
        """Cancel task command handler (v3.0.0, async)."""
        from application.queries.tasks import CancelTaskHandler
        if 'cancel_task' not in self._handlers:
            user_tasks_service = await self.get_user_tasks_service()
            self._handlers['cancel_task'] = CancelTaskHandler(user_tasks_service)
        return self._handlers['cancel_task']

    async def get_pdf_preview_handler(self):
        """PDF preview command handler (v3.0.0, async)."""
        from application.commands.tools import PdfPreviewHandler
        if 'pdf_preview' not in self._handlers:
            tools_service = await self.get_tools_service()
            self._handlers['pdf_preview'] = PdfPreviewHandler(tools_service)
        return self._handlers['pdf_preview']

    async def get_ocr_handler(self):
        """OCR command handler (v3.0.0, async)."""
        from application.commands.tools import OcrHandler
        if 'ocr' not in self._handlers:
            tools_service = await self.get_tools_service()
            self._handlers['ocr'] = OcrHandler(tools_service)
        return self._handlers['ocr']

    async def get_user_projects_handler(self) -> GetUserProjectsHandler:
        """Get user projects query handler (async)."""
        if 'get_user_projects' not in self._handlers:
            creation_service = await self.get_creation_service()
            self._handlers['get_user_projects'] = GetUserProjectsHandler(creation_service)
        return self._handlers['get_user_projects']

    async def get_dashboard_projects_handler(self) -> GetDashboardProjectsHandler:
        """Get dashboard projects query handler (async)."""
        if 'get_dashboard_projects' not in self._handlers:
            project_repo = await self.get_project_repository()
            self._handlers['get_dashboard_projects'] = GetDashboardProjectsHandler(project_repo)
        return self._handlers['get_dashboard_projects']

    async def get_listing_handler(self) -> GetListingHandler:
        """Get listing query handler (async)."""
        if 'get_listing' not in self._handlers:
            marketplace_service = await self.get_marketplace_service()
            self._handlers['get_listing'] = GetListingHandler(marketplace_service)
        return self._handlers['get_listing']

    async def get_search_listings_handler(self) -> SearchListingsHandler:
        """Get search listings query handler (async)."""
        if 'search_listings' not in self._handlers:
            marketplace_service = await self.get_marketplace_service()
            self._handlers['search_listings'] = SearchListingsHandler(marketplace_service)
        return self._handlers['search_listings']

    async def get_evaluate_feature_flag_handler(self) -> EvaluateFeatureFlagHandler:
        """Get evaluate feature flag query handler (async)."""
        if 'evaluate_feature_flag' not in self._handlers:
            platform_service = await self.get_platform_service()
            self._handlers['evaluate_feature_flag'] = EvaluateFeatureFlagHandler(platform_service)
        return self._handlers['evaluate_feature_flag']

    async def get_experiment_variant_handler(self) -> GetExperimentVariantHandler:
        """Get experiment variant query handler (async)."""
        if 'get_experiment_variant' not in self._handlers:
            platform_service = await self.get_platform_service()
            self._handlers['get_experiment_variant'] = GetExperimentVariantHandler(platform_service)
        return self._handlers['get_experiment_variant']

    async def get_my_listings_handler(self) -> GetMyListingsHandler:
        """Get my listings query handler (v3.0.0, async)."""
        if 'get_my_listings' not in self._handlers:
            marketplace_service = await self.get_marketplace_service()
            self._handlers['get_my_listings'] = GetMyListingsHandler(marketplace_service)
        return self._handlers['get_my_listings']

    async def get_seller_stats_handler(self) -> GetSellerStatsHandler:
        """Get seller stats query handler (v3.0.0, async)."""
        if 'get_seller_stats' not in self._handlers:
            marketplace_service = await self.get_marketplace_service()
            self._handlers['get_seller_stats'] = GetSellerStatsHandler(marketplace_service)
        return self._handlers['get_seller_stats']

    async def get_leaderboard_handler(self) -> GetLeaderboardHandler:
        """Get leaderboard query handler (v3.0.0, async)."""
        if 'get_leaderboard' not in self._handlers:
            marketplace_service = await self.get_marketplace_service()
            self._handlers['get_leaderboard'] = GetLeaderboardHandler(marketplace_service)
        return self._handlers['get_leaderboard']

    async def get_my_reports_handler(self) -> GetMyReportsHandler:
        """Get my reports query handler (v3.0.0, async)."""
        if 'get_my_reports' not in self._handlers:
            support_service = await self.get_support_service()
            self._handlers['get_my_reports'] = GetMyReportsHandler(support_service)
        return self._handlers['get_my_reports']

    # ========== Content/Resources Handlers (v3.0.0, async) ==========

    async def get_content_service(self):
        """Get content service instance (v3.0.0, async)."""
        from domains.content.service import ContentService
        from infrastructure.repositories.content_repository import SupabaseContentRepository
        if 'content' not in self._services:
            db = await get_async_db_client()
            repository = SupabaseContentRepository(db)
            self._services['content'] = ContentService(repository)
        return self._services['content']

    async def get_resources_handler(self):
        """Get resources query handler (v3.0.0, async)."""
        from application.queries.content import GetResourcesHandler
        if 'get_resources' not in self._handlers:
            content_service = await self.get_content_service()
            self._handlers['get_resources'] = GetResourcesHandler(content_service)
        return self._handlers['get_resources']

    async def get_resource_by_id_handler(self):
        """Get resource by ID query handler (v3.0.0, async)."""
        from application.queries.content import GetResourceByIdHandler
        if 'get_resource_by_id' not in self._handlers:
            content_service = await self.get_content_service()
            self._handlers['get_resource_by_id'] = GetResourceByIdHandler(content_service)
        return self._handlers['get_resource_by_id']

    async def get_stickers_handler(self):
        """Get stickers query handler (v3.0.0, async)."""
        from application.queries.content import GetStickersHandler
        if 'get_stickers' not in self._handlers:
            content_service = await self.get_content_service()
            self._handlers['get_stickers'] = GetStickersHandler(content_service)
        return self._handlers['get_stickers']

    async def get_backgrounds_handler(self):
        """Get backgrounds query handler (v3.0.0, async)."""
        from application.queries.content import GetBackgroundsHandler
        if 'get_backgrounds' not in self._handlers:
            content_service = await self.get_content_service()
            self._handlers['get_backgrounds'] = GetBackgroundsHandler(content_service)
        return self._handlers['get_backgrounds']

    async def get_project_templates_handler(self):
        """Get project templates query handler (v3.0.0, async)."""
        from application.queries.content import GetProjectTemplatesHandler
        if 'get_project_templates' not in self._handlers:
            content_service = await self.get_content_service()
            self._handlers['get_project_templates'] = GetProjectTemplatesHandler(content_service)
        return self._handlers['get_project_templates']

    async def get_categories_handler(self):
        """Get categories query handler (v3.0.0, async)."""
        from application.queries.content import GetCategoriesHandler
        if 'get_categories' not in self._handlers:
            content_service = await self.get_content_service()
            self._handlers['get_categories'] = GetCategoriesHandler(content_service)
        return self._handlers['get_categories']

    async def get_resource_stats_handler(self):
        """Get resource stats query handler (v3.0.0, async)."""
        from application.queries.content import GetResourceStatsHandler
        if 'get_resource_stats' not in self._handlers:
            content_service = await self.get_content_service()
            self._handlers['get_resource_stats'] = GetResourceStatsHandler(content_service)
        return self._handlers['get_resource_stats']

    # System Resources Query Handlers (v3.0.0, async)
    async def get_list_system_resources_handler(self):
        """Get list system resources handler (v3.0.0, async)."""
        from application.queries.system_resources import ListSystemResourcesHandler
        if 'list_system_resources' not in self._handlers:
            service = await self.get_system_resources_admin_service()
            self._handlers['list_system_resources'] = ListSystemResourcesHandler(service)
        return self._handlers['list_system_resources']

    async def get_system_resource_handler(self):
        """Get system resource by ID handler (v3.0.0, async)."""
        from application.queries.system_resources import GetSystemResourceHandler
        if 'get_system_resource' not in self._handlers:
            service = await self.get_system_resources_admin_service()
            self._handlers['get_system_resource'] = GetSystemResourceHandler(service)
        return self._handlers['get_system_resource']

    async def get_system_resource_stats_handler(self):
        """Get system resource stats handler (v3.0.0, async)."""
        from application.queries.system_resources import GetResourceStatsHandler
        if 'get_system_resource_stats' not in self._handlers:
            service = await self.get_system_resources_admin_service()
            self._handlers['get_system_resource_stats'] = GetResourceStatsHandler(service)
        return self._handlers['get_system_resource_stats']

    async def get_audit_log_handler(self):
        """Get audit log handler (v3.0.0, async)."""
        from application.queries.system_resources import GetAuditLogHandler
        if 'get_audit_log' not in self._handlers:
            service = await self.get_system_resources_admin_service()
            self._handlers['get_audit_log'] = GetAuditLogHandler(service)
        return self._handlers['get_audit_log']

    # Templates Query Handlers (v3.0.0, async)
    async def get_list_asset_templates_handler(self):
        """Get list asset templates handler (v3.0.0, async)."""
        from application.queries.templates import ListAssetTemplatesHandler
        if 'list_asset_templates' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['list_asset_templates'] = ListAssetTemplatesHandler(templates_service)
        return self._handlers['list_asset_templates']

    async def get_list_page_templates_handler(self):
        """Get list page templates handler (v3.0.0, async)."""
        from application.queries.templates import ListPageTemplatesHandler
        if 'list_page_templates' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['list_page_templates'] = ListPageTemplatesHandler(templates_service)
        return self._handlers['list_page_templates']

    # Templates Command Handlers (v3.0.0, async)
    async def get_create_asset_template_handler(self):
        """Get create asset template handler (v3.0.0, async)."""
        from application.commands.templates import CreateAssetTemplateHandler
        if 'create_asset_template' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['create_asset_template'] = CreateAssetTemplateHandler(templates_service)
        return self._handlers['create_asset_template']

    async def get_update_asset_template_handler(self):
        """Get update asset template handler (v3.0.0, async)."""
        from application.commands.templates import UpdateAssetTemplateHandler
        if 'update_asset_template' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['update_asset_template'] = UpdateAssetTemplateHandler(templates_service)
        return self._handlers['update_asset_template']

    async def get_delete_asset_template_handler(self):
        """Get delete asset template handler (v3.0.0, async)."""
        from application.commands.templates import DeleteAssetTemplateHandler
        if 'delete_asset_template' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['delete_asset_template'] = DeleteAssetTemplateHandler(templates_service)
        return self._handlers['delete_asset_template']

    async def get_use_asset_template_handler(self):
        """Get use asset template handler (v3.0.0, async)."""
        from application.commands.templates import UseAssetTemplateHandler
        if 'use_asset_template' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['use_asset_template'] = UseAssetTemplateHandler(templates_service)
        return self._handlers['use_asset_template']

    async def get_create_page_template_handler(self):
        """Get create page template handler (v3.0.0, async)."""
        from application.commands.templates import CreatePageTemplateHandler
        if 'create_page_template' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['create_page_template'] = CreatePageTemplateHandler(templates_service)
        return self._handlers['create_page_template']

    async def get_update_page_template_handler(self):
        """Get update page template handler (v3.0.0, async)."""
        from application.commands.templates import UpdatePageTemplateHandler
        if 'update_page_template' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['update_page_template'] = UpdatePageTemplateHandler(templates_service)
        return self._handlers['update_page_template']

    async def get_delete_page_template_handler(self):
        """Get delete page template handler (v3.0.0, async)."""
        from application.commands.templates import DeletePageTemplateHandler
        if 'delete_page_template' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['delete_page_template'] = DeletePageTemplateHandler(templates_service)
        return self._handlers['delete_page_template']

    async def get_use_page_template_handler(self):
        """Get use page template handler (v3.0.0, async)."""
        from application.commands.templates import UsePageTemplateHandler
        if 'use_page_template' not in self._handlers:
            templates_service = await self.get_templates_service()
            self._handlers['use_page_template'] = UsePageTemplateHandler(templates_service)
        return self._handlers['use_page_template']

    # Assets Query Handlers (v3.0.0, async)
    async def get_user_assets_handler(self):
        """Get user assets handler (v3.0.0, async)."""
        from application.queries.assets import GetUserAssetsHandler
        if 'get_user_assets' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['get_user_assets'] = GetUserAssetsHandler(assets_service)
        return self._handlers['get_user_assets']

    async def get_check_url_handler(self):
        """Get check URL handler (v3.0.0, async)."""
        from application.queries.assets import CheckURLHandler
        if 'check_url' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['check_url'] = CheckURLHandler(assets_service)
        return self._handlers['check_url']

    async def get_dashboard_stats_handler(self):
        """Get dashboard stats handler (v3.0.0, async)."""
        from application.queries.assets import GetDashboardStatsHandler
        if 'get_dashboard_stats' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['get_dashboard_stats'] = GetDashboardStatsHandler(assets_service)
        return self._handlers['get_dashboard_stats']

    async def get_assets_seller_stats_handler(self):
        """Get seller stats handler (v3.0.0, async)."""
        from application.queries.assets import GetSellerStatsHandler
        if 'get_assets_seller_stats' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['get_assets_seller_stats'] = GetSellerStatsHandler(assets_service)
        return self._handlers['get_assets_seller_stats']

    async def get_deleted_assets_handler(self):
        """Get deleted assets handler (v3.0.0, async)."""
        from application.queries.assets import GetDeletedAssetsHandler
        if 'get_deleted_assets' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['get_deleted_assets'] = GetDeletedAssetsHandler(assets_service)
        return self._handlers['get_deleted_assets']

    async def get_dashboard_assets_handler(self):
        """Get dashboard assets handler (v1.1.0, async)."""
        from application.queries.assets import GetDashboardAssetsHandler
        from infrastructure.repositories.asset_repository import SupabaseAssetRepository
        if 'get_dashboard_assets' not in self._handlers:
            db = await get_async_db_client()
            repository = SupabaseAssetRepository(db)
            self._handlers['get_dashboard_assets'] = GetDashboardAssetsHandler(repository)
        return self._handlers['get_dashboard_assets']

    # Assets Command Handlers (v3.0.0, async)
    async def get_upload_asset_handler(self):
        """Get upload asset handler (v3.0.0, async)."""
        from application.commands.assets import UploadAssetHandler
        if 'upload_asset' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['upload_asset'] = UploadAssetHandler(assets_service)
        return self._handlers['upload_asset']

    async def get_add_asset_from_url_handler(self):
        """Get add asset from URL handler (v3.0.0, async)."""
        from application.commands.assets import AddAssetFromURLHandler
        if 'add_asset_from_url' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['add_asset_from_url'] = AddAssetFromURLHandler(assets_service)
        return self._handlers['add_asset_from_url']

    async def get_delete_asset_handler(self):
        """Get delete asset handler (v3.0.0, async)."""
        from application.commands.assets import DeleteAssetHandler
        if 'delete_asset' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['delete_asset'] = DeleteAssetHandler(assets_service)
        return self._handlers['delete_asset']

    async def get_increment_asset_usage_handler(self):
        """Get increment asset usage handler (v3.0.0, async)."""
        from application.commands.assets import IncrementAssetUsageHandler
        if 'increment_asset_usage' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['increment_asset_usage'] = IncrementAssetUsageHandler(assets_service)
        return self._handlers['increment_asset_usage']

    async def get_restore_asset_handler(self):
        """Get restore asset handler (v3.0.0, async)."""
        from application.commands.assets import RestoreAssetHandler
        if 'restore_asset' not in self._handlers:
            assets_service = await self.get_assets_service()
            self._handlers['restore_asset'] = RestoreAssetHandler(assets_service)
        return self._handlers['restore_asset']

    # ========== Utility Methods ==========

    def reset(self):
        """Reset all cached instances (for testing)."""
        self._repositories.clear()
        self._services.clear()
        self._handlers.clear()
        logger.info("[Container v2.0] All instances reset")


# Module-level singleton accessor
@lru_cache(maxsize=1)
def get_container() -> Container:
    """Get the singleton container instance."""
    return Container()


# ========== FastAPI Dependency Injection (v2.0 - Async) ==========
# WARNING: These are convenience wrappers but should NOT be used directly
# in production code. Use FastAPI Depends(get_async_db) pattern instead.

async def get_billing_service() -> BillingService:
    """FastAPI dependency for billing service (async)."""
    container = get_container()
    return await container.get_billing_service()


async def get_identity_service() -> IdentityService:
    """FastAPI dependency for identity service (async)."""
    container = get_container()
    return await container.get_identity_service()


async def get_creation_service() -> CreationService:
    """FastAPI dependency for creation service (async)."""
    container = get_container()
    return await container.get_creation_service()


async def get_marketplace_service() -> MarketplaceService:
    """FastAPI dependency for marketplace service (async)."""
    container = get_container()
    return await container.get_marketplace_service()


async def get_platform_service() -> PlatformService:
    """FastAPI dependency for platform service (async)."""
    container = get_container()
    return await container.get_platform_service()
