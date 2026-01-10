"""
Identity Queries - User read operations.

@module application.queries.identity
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from domains.identity import IdentityService, UserProfile


@dataclass
class GetUserProfileQuery:
    """Query to get user profile."""
    user_id: str


@dataclass
class GetUserProfileResult:
    """Result of user profile query."""
    success: bool
    user: Optional[UserProfile] = None
    user_dict: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GetUserProfileHandler:
    """Handler for GetUserProfileQuery."""

    def __init__(self, identity_service: IdentityService):
        self._identity_service = identity_service

    async def handle(self, query: GetUserProfileQuery) -> GetUserProfileResult:
        """Execute user profile query."""
        try:
            user = await self._identity_service.get_user(query.user_id)

            if not user:
                return GetUserProfileResult(
                    success=False,
                    error="User not found",
                )

            return GetUserProfileResult(
                success=True,
                user=user,
                user_dict=user.to_dict(),
            )

        except Exception as e:
            return GetUserProfileResult(
                success=False,
                error=str(e),
            )


@dataclass
class CheckFeatureAccessQuery:
    """Query to check if user has access to a feature."""
    user_id: str
    feature: str


@dataclass
class CheckFeatureAccessResult:
    """Result of feature access check."""
    success: bool
    has_access: bool = False
    user_tier: str = "t1"
    error: Optional[str] = None


class CheckFeatureAccessHandler:
    """Handler for CheckFeatureAccessQuery."""

    def __init__(self, identity_service: IdentityService):
        self._identity_service = identity_service

    async def handle(self, query: CheckFeatureAccessQuery) -> CheckFeatureAccessResult:
        """Execute feature access check."""
        try:
            has_access = await self._identity_service.check_feature_access(
                query.user_id,
                query.feature
            )

            user = await self._identity_service.get_user(query.user_id)
            tier = user.tier.value if user else "t1"

            return CheckFeatureAccessResult(
                success=True,
                has_access=has_access,
                user_tier=tier,
            )

        except Exception as e:
            return CheckFeatureAccessResult(
                success=False,
                error=str(e),
            )


@dataclass
class GetUserByEmailQuery:
    """Query to get user by email."""
    email: str


class GetUserByEmailHandler:
    """Handler for GetUserByEmailQuery."""

    def __init__(self, identity_service: IdentityService):
        self._identity_service = identity_service

    async def handle(self, query: GetUserByEmailQuery) -> GetUserProfileResult:
        """Execute user by email query."""
        try:
            # Access repository directly through service
            user = await self._identity_service._repository.get_by_email(query.email)

            if not user:
                return GetUserProfileResult(
                    success=False,
                    error="User not found",
                )

            return GetUserProfileResult(
                success=True,
                user=user,
                user_dict=user.to_dict(),
            )

        except Exception as e:
            return GetUserProfileResult(
                success=False,
                error=str(e),
            )
