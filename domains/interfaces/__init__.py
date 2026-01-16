"""
Domain Repository Interfaces - Centralized Interface Registry.

@module domains.interfaces
@version 1.0.0

This module provides a centralized registry for all domain repository interfaces.
Following the Dependency Inversion Principle (DIP), high-level modules (Services)
depend on abstractions (Interfaces) rather than concrete implementations.

Architecture Decision:
    WHY centralized interfaces?
    1. Single import location for all repository interfaces
    2. Decouples domains from infrastructure implementations
    3. Enables easy mocking in tests
    4. Supports future database provider switches (Supabase -> others)

    HOW to use:
    - Domain Services: Import interfaces from here
    - Infrastructure: Import interfaces to implement them
    - Container: Wire implementations to interfaces

Usage:
    # In domain service
    from domains.interfaces import IUserRepository, ICreditRepository

    class MyService:
        def __init__(self, user_repo: IUserRepository):
            self._user_repo = user_repo

    # In infrastructure repository
    from domains.interfaces import IUserRepository
    from domains.identity.aggregates.user_profile import UserProfile

    class SupabaseUserRepository(IUserRepository):
        async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
            ...

    # In container
    from domains.interfaces import IUserRepository
    from infrastructure.repositories import SupabaseUserRepository

    container.register(IUserRepository, SupabaseUserRepository)

Interface Naming Convention:
    I{Domain}Repository - Preferred (e.g., IUserRepository, ICreditRepository)
    {Domain}Repository - Legacy (e.g., ThemesRepository, LoggingRepository)

    Note: Some interfaces use Protocol instead of ABC for structural typing.
    Both are valid - ABC for nominal typing, Protocol for structural typing.

Implementation Naming Convention:
    {Provider}{Domain}Repository - e.g., SupabaseUserRepository
"""

# =============================================================================
# Core Domain Interfaces (ABC-based, I-prefixed)
# =============================================================================

# Billing Domain - Credit and transaction management
from domains.billing.repository import ICreditRepository

# Identity Domain - User profile and authentication
from domains.identity.repository import IUserRepository

# Creation Domain - Project and page management
from domains.creation.repository import IProjectRepository

# Marketplace Domain - Listing and purchase management
from domains.marketplace.repository import IListingRepository

# Platform Domain - Feature flags, experiments, notifications
from domains.platform.repository import (
    IFeatureFlagRepository,
    IExperimentRepository,
    IAIModelConfigRepository,
    INotificationRepository,
)

# =============================================================================
# Supporting Domain Interfaces (Mixed naming for backward compatibility)
# =============================================================================

# Events Domain - Event tracking and analytics
from domains.events.repository import IEventsRepository

# Themes Domain - Holiday themes and campaigns (Protocol-based)
from domains.themes.repository import ThemesRepository

# Logging Domain - Error and audit logging (Protocol-based)
from domains.logging.repository import LoggingRepository

# Content Domain - System resources and categories
from domains.content.repository import ISystemResourceRepository, ICategoryRepository

# Analytics Domain - User analytics and metrics
from domains.analytics.repository import IAnalyticsRepository

# Articles Domain - Blog and documentation
from domains.articles.repository import ArticleRepository

# Static Pages Domain - Legal and info pages
from domains.static_pages.repository import StaticPageRepository

# Onboarding Domain - User onboarding flow (class-based, no ABC)
from domains.onboarding.repository import OnboardingRepository

# Referrals Domain - Referral program (class-based, no ABC)
from domains.referrals.repository import ReferralRepository

# Feature Flags Domain (legacy standalone, use platform.IFeatureFlagRepository instead)
from domains.feature_flags.repository import FeatureFlagRepository as LegacyFeatureFlagRepository

# Marketing Domain - Campaigns and promotions
from domains.marketing.repository import ICampaignRepository

# Tasks Domain - User task management (Protocol-based)
from domains.tasks.repository import TasksRepository

# =============================================================================
# Export All Interfaces
# =============================================================================

__all__ = [
    # Core Domains (I-prefixed ABC)
    'ICreditRepository',
    'IUserRepository',
    'IProjectRepository',
    'IListingRepository',
    'IFeatureFlagRepository',
    'IExperimentRepository',
    'IAIModelConfigRepository',
    'INotificationRepository',
    # Supporting Domains (Mixed naming)
    'IEventsRepository',
    'ThemesRepository',
    'LoggingRepository',
    'ISystemResourceRepository',
    'ICategoryRepository',
    'IAnalyticsRepository',
    'ArticleRepository',
    'StaticPageRepository',
    'OnboardingRepository',
    'ReferralRepository',
    'LegacyFeatureFlagRepository',
    'ICampaignRepository',
    'TasksRepository',
]
