"""
Application Layer - Use case orchestration and coordination.

This layer contains:
- Commands: Write operations that change state
- Queries: Read operations that return data
- Use cases that coordinate multiple domains

@package application
@version 1.0.0

Design Principles:
- Orchestrates domain services
- Handles cross-domain coordination
- No business logic - delegates to domains
- Thin layer for request/response handling
"""

from .commands import (
    # Billing commands
    DeductCreditsCommand,
    AddCreditsCommand,
    GrantSignupBonusCommand,
    # Identity commands
    CreateUserCommand,
    UpdateUserProfileCommand,
    UpdateUserTierCommand,
    # Creation commands
    CreateProjectCommand,
    UpdateProjectCommand,
    DeleteProjectCommand,
    # Marketplace commands
    CreateListingCommand,
    PurchaseListingCommand,
    # Platform commands
    CreateFeatureFlagCommand,
    CreateExperimentCommand,
)

from .queries import (
    # Billing queries
    GetUserCreditsQuery,
    GetTransactionHistoryQuery,
    # Identity queries
    GetUserProfileQuery,
    # Creation queries
    GetProjectQuery,
    GetUserProjectsQuery,
    # Marketplace queries
    GetListingQuery,
    SearchListingsQuery,
    # Platform queries
    EvaluateFeatureFlagQuery,
    GetExperimentVariantQuery,
)

__all__ = [
    # Commands
    'DeductCreditsCommand',
    'AddCreditsCommand',
    'GrantSignupBonusCommand',
    'CreateUserCommand',
    'UpdateUserProfileCommand',
    'UpdateUserTierCommand',
    'CreateProjectCommand',
    'UpdateProjectCommand',
    'DeleteProjectCommand',
    'CreateListingCommand',
    'PurchaseListingCommand',
    'CreateFeatureFlagCommand',
    'CreateExperimentCommand',
    # Queries
    'GetUserCreditsQuery',
    'GetTransactionHistoryQuery',
    'GetUserProfileQuery',
    'GetProjectQuery',
    'GetUserProjectsQuery',
    'GetListingQuery',
    'SearchListingsQuery',
    'EvaluateFeatureFlagQuery',
    'GetExperimentVariantQuery',
]
