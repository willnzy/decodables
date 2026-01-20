"""
Platform Repository Interfaces - Abstract data access for platform domain.

@module domains.platform.repository
@version 1.1.0

Changes:
- v1.1.0: Added IAIModelConfigRepository and INotificationRepository interfaces

This defines the repository interfaces (ports) for platform operations.
Concrete implementations live in infrastructure/repositories/.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from .aggregates.feature_flag import FeatureFlag
from .aggregates.experiment import Experiment
from .value_objects import FlagStatus, ExperimentStatus


class IFeatureFlagRepository(ABC):
    """
    Repository interface for feature flag operations.
    """

    @abstractmethod
    async def get_by_key(self, key: str) -> Optional[FeatureFlag]:
        """
        Get feature flag by key.

        Args:
            key: Feature flag key

        Returns:
            FeatureFlag or None if not found
        """
        pass

    @abstractmethod
    async def save(self, flag: FeatureFlag) -> FeatureFlag:
        """
        Persist feature flag.

        Args:
            flag: FeatureFlag to save

        Returns:
            Saved FeatureFlag
        """
        pass

    @abstractmethod
    async def create(self, flag: FeatureFlag) -> FeatureFlag:
        """
        Create a new feature flag.

        Args:
            flag: FeatureFlag to create

        Returns:
            Created FeatureFlag
        """
        pass

    @abstractmethod
    async def update(self, flag: FeatureFlag) -> FeatureFlag:
        """
        Update existing feature flag.

        Args:
            flag: FeatureFlag to update

        Returns:
            Updated FeatureFlag
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a feature flag.

        Args:
            key: Flag key to delete

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        status: Optional[FlagStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[FeatureFlag]:
        """
        Get all feature flags.

        Args:
            status: Filter by status
            tags: Filter by tags

        Returns:
            List of FeatureFlags
        """
        pass

    @abstractmethod
    async def get_active(self) -> List[FeatureFlag]:
        """
        Get all active feature flags.

        Returns:
            List of active FeatureFlags
        """
        pass


class IExperimentRepository(ABC):
    """
    Repository interface for experiment operations.
    """

    @abstractmethod
    async def get_by_id(self, experiment_id: str) -> Optional[Experiment]:
        """
        Get experiment by ID.

        Args:
            experiment_id: Experiment ID

        Returns:
            Experiment or None if not found
        """
        pass

    @abstractmethod
    async def save(self, experiment: Experiment) -> Experiment:
        """
        Persist experiment.

        Args:
            experiment: Experiment to save

        Returns:
            Saved Experiment
        """
        pass

    @abstractmethod
    async def create(self, experiment: Experiment) -> Experiment:
        """
        Create a new experiment.

        Args:
            experiment: Experiment to create

        Returns:
            Created Experiment
        """
        pass

    @abstractmethod
    async def update(self, experiment: Experiment) -> Experiment:
        """
        Update existing experiment.

        Args:
            experiment: Experiment to update

        Returns:
            Updated Experiment
        """
        pass

    @abstractmethod
    async def delete(self, experiment_id: str) -> bool:
        """
        Delete an experiment.

        Args:
            experiment_id: Experiment ID to delete

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        status: Optional[ExperimentStatus] = None
    ) -> List[Experiment]:
        """
        Get all experiments.

        Args:
            status: Filter by status

        Returns:
            List of Experiments
        """
        pass

    @abstractmethod
    async def get_running(self) -> List[Experiment]:
        """
        Get all running experiments.

        Returns:
            List of running Experiments
        """
        pass

    @abstractmethod
    async def record_assignment(
        self,
        experiment_id: str,
        user_id: str,
        variant_id: str
    ) -> bool:
        """
        Record a user's variant assignment.

        Args:
            experiment_id: Experiment ID
            user_id: User ID
            variant_id: Assigned variant ID

        Returns:
            True if recorded
        """
        pass

    @abstractmethod
    async def get_user_assignment(
        self,
        experiment_id: str,
        user_id: str
    ) -> Optional[str]:
        """
        Get user's assigned variant.

        Args:
            experiment_id: Experiment ID
            user_id: User ID

        Returns:
            Variant ID or None
        """
        pass


class IAIModelConfigRepository(ABC):
    """
    Repository interface for AI model configuration operations.

    v1.1.0: Added for AI Models Config DDD migration
    """

    @abstractmethod
    async def get_config(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get AI model configuration by key.

        Args:
            key: Config key (e.g., 'ai_model.user.text_reasoning')

        Returns:
            Config dict or None if not found
        """
        pass

    @abstractmethod
    async def set_config(self, key: str, value: Dict[str, Any]) -> bool:
        """
        Set AI model configuration.

        Args:
            key: Config key
            value: Config value (JSON)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete_config(self, key: str) -> bool:
        """
        Delete AI model configuration.

        Args:
            key: Config key to delete

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def get_all_configs(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all configs, optionally filtered by prefix.

        Args:
            prefix: Key prefix filter (e.g., 'ai_model.')

        Returns:
            Dict of key-value pairs
        """
        pass


class INotificationRepository(ABC):
    """
    Repository interface for notification operations.

    v1.1.0: Added for Notifications DDD migration
    """

    @abstractmethod
    async def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        action_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a notification for a single user.

        Args:
            user_id: Target user ID
            title: Notification title
            message: Notification content
            notification_type: Type of notification
            action_url: Optional action URL

        Returns:
            Created notification dict or None
        """
        pass

    @abstractmethod
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get notifications for a user.

        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            limit: Max number to return

        Returns:
            List of notification dicts
        """
        pass

    @abstractmethod
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """
        Mark notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID (for security)

        Returns:
            True if marked as read
        """
        pass

    @abstractmethod
    async def mark_all_as_read(self, user_id: str) -> bool:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """
        Delete a notification.

        Args:
            notification_id: Notification ID
            user_id: User ID (for security)

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def get_all_notification_stats(self) -> Dict[str, Any]:
        """
        Get overall notification statistics.

        Returns:
            Stats dict with total, unread, read, by_type counts
        """
        pass

    @abstractmethod
    async def get_notification_history(
        self,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get paginated notification history.

        Args:
            offset: Pagination offset
            limit: Page size

        Returns:
            Dict with items, total, offset, limit
        """
        pass

    # ==========================================
    # Legacy Methods (Admin sending operations)
    # ==========================================

    @abstractmethod
    async def send_notification_to_user(
        self,
        user_id: str,
        title: str,
        content: str,
        notification_type: str = "system"
    ) -> Optional[Dict[str, Any]]:
        """
        Send notification to a single user.

        Args:
            user_id: Target user ID
            title: Notification title
            content: Notification content
            notification_type: Type of notification

        Returns:
            Created notification dict or None
        """
        pass

    @abstractmethod
    async def send_notification_to_users(
        self,
        user_ids: List[str],
        title: str,
        content: str,
        notification_type: str = "system"
    ) -> List[Dict[str, Any]]:
        """
        Send notification to multiple users.

        Args:
            user_ids: List of target user IDs
            title: Notification title
            content: Notification content
            notification_type: Type of notification

        Returns:
            List of created notification dicts
        """
        pass


class INotificationTemplateRepository(ABC):
    """
    Repository interface for admin notification template operations.

    v1.0.0: Added for Admin Notification Templates CRUD
    """

    @abstractmethod
    async def create(
        self,
        title: str,
        message: str,
        notification_type: str,
        channel: str,
        target_users: Optional[List[str]],
        target_tiers: Optional[List[str]],
        scheduled_at: Optional[str],
        created_by: str
    ) -> Dict[str, Any]:
        """
        Create a new notification template.

        Args:
            title: Notification title
            message: Notification content
            notification_type: Type (info/warning/error/success/announcement)
            channel: Delivery channel (in_app/email/push/all)
            target_users: List of specific user IDs
            target_tiers: List of tier codes
            scheduled_at: Optional scheduled send time (ISO string)
            created_by: Admin user ID

        Returns:
            Created notification template dict
        """
        pass

    @abstractmethod
    async def get_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get notification template by ID.

        Args:
            template_id: Template UUID

        Returns:
            Template dict or None if not found
        """
        pass

    @abstractmethod
    async def get_list(
        self,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get paginated list of notification templates.

        Args:
            status: Filter by status (draft/scheduled/sent/failed)
            offset: Pagination offset
            limit: Page size

        Returns:
            Dict with notifications list and total count
        """
        pass

    @abstractmethod
    async def update(
        self,
        template_id: str,
        title: Optional[str] = None,
        message: Optional[str] = None,
        notification_type: Optional[str] = None,
        channel: Optional[str] = None,
        target_users: Optional[List[str]] = None,
        target_tiers: Optional[List[str]] = None,
        scheduled_at: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing notification template.

        Args:
            template_id: Template UUID
            title: New title (optional)
            message: New message (optional)
            notification_type: New type (optional)
            channel: New channel (optional)
            target_users: New target users (optional)
            target_tiers: New target tiers (optional)
            scheduled_at: New scheduled time (optional)

        Returns:
            Updated template dict or None if not found
        """
        pass

    @abstractmethod
    async def delete(self, template_id: str) -> bool:
        """
        Delete a notification template.

        Args:
            template_id: Template UUID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def mark_as_sent(
        self,
        template_id: str,
        total_recipients: int,
        delivered: int = 0,
        failed: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Mark template as sent with statistics.

        Args:
            template_id: Template UUID
            total_recipients: Total number of recipients
            delivered: Number of successful deliveries
            failed: Number of failed deliveries

        Returns:
            Updated template dict or None if not found
        """
        pass

    @abstractmethod
    async def get_pending_scheduled(self) -> List[Dict[str, Any]]:
        """
        Get all scheduled notifications that are due to be sent.

        Returns:
            List of template dicts that need to be sent
        """
        pass
