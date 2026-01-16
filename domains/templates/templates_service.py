"""
Templates Service - Business logic for user prompt templates.

@module domains.templates.templates_service
@version 1.1.0 (DDD Exception Compliance)

Changes:
- v1.1.0: DDD-compliant exceptions
  - Removed all HTTPException (replaced with domain exceptions)
  - API layer now responsible for HTTP status code mapping
- v1.0.0: Initial implementation

Purpose:
- Template CRUD business logic
- Template count limit enforcement (MAX_TEMPLATES_PER_USER = 20)
- Use count tracking
"""

from typing import Dict, Any, List
from datetime import datetime, timezone

from infrastructure.repositories.templates_repository import SupabaseTemplatesRepository
from domains.templates.exceptions import (
    TemplateNotFoundException,
    TemplateLimitExceededException,
)

# Maximum templates per user
MAX_TEMPLATES_PER_USER = 20


class TemplatesService:
    """
    Domain service for Templates management.

    Handles all business logic for user prompt templates.
    """

    def __init__(self, repository: SupabaseTemplatesRepository):
        """
        Initialize service.

        Args:
            repository: Data access repository
        """
        self.repository = repository

    # ==========================================
    # Asset Prompt Templates (5W1H)
    # ==========================================

    async def list_asset_templates(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all asset templates for a user.

        Args:
            user_id: User ID

        Returns:
            List of templates ordered by use_count (desc)
        """
        return await self.repository.list_asset_templates(user_id)

    async def create_asset_template(
        self,
        user_id: str,
        template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create asset template with limit check.

        Business logic:
        1. Check template count limit
        2. Create template

        Args:
            user_id: User ID
            template_data: Template data

        Returns:
            Created template dict

        Raises:
            TemplateLimitExceededException: If limit exceeded
        """
        # 1. Check template count limit
        count = await self.repository.count_asset_templates(user_id)
        if count >= MAX_TEMPLATES_PER_USER:
            raise TemplateLimitExceededException(max_templates=MAX_TEMPLATES_PER_USER)

        # 2. Add user_id to data
        data = {
            "user_id": user_id,
            **template_data
        }

        # 3. Create template
        return await self.repository.create_asset_template(data)

    async def update_asset_template(
        self,
        template_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update asset template.

        Args:
            template_id: Template UUID
            user_id: User ID
            updates: Fields to update

        Returns:
            Updated template dict

        Raises:
            TemplateNotFoundException: If template not found
        """
        result = await self.repository.update_asset_template(
            template_id,
            user_id,
            updates
        )

        if not result:
            raise TemplateNotFoundException()

        return result

    async def delete_asset_template(
        self,
        template_id: str,
        user_id: str
    ) -> bool:
        """
        Delete asset template.

        Args:
            template_id: Template UUID
            user_id: User ID

        Returns:
            True if deleted
        """
        return await self.repository.delete_asset_template(template_id, user_id)

    async def use_asset_template(
        self,
        template_id: str,
        user_id: str
    ) -> int:
        """
        Mark asset template as used (increment use_count).

        Business logic:
        1. Get current use_count
        2. Update use_count + 1 and last_used_at
        3. Return new count

        Args:
            template_id: Template UUID
            user_id: User ID

        Returns:
            New use_count

        Raises:
            TemplateNotFoundException: If template not found
        """
        # 1. Get current template
        template = await self.repository.get_asset_template(template_id, user_id)
        if not template:
            raise TemplateNotFoundException()

        # 2. Increment use_count
        current_count = template.get("use_count", 0)
        new_count = current_count + 1

        # 3. Update
        await self.repository.update_asset_template(
            template_id,
            user_id,
            {
                "use_count": new_count,
                "last_used_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        return new_count

    # ==========================================
    # Page Prompt Templates
    # ==========================================

    async def list_page_templates(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all page templates for a user.

        Args:
            user_id: User ID

        Returns:
            List of templates ordered by use_count (desc)
        """
        return await self.repository.list_page_templates(user_id)

    async def create_page_template(
        self,
        user_id: str,
        template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create page template with limit check.

        Business logic:
        1. Check template count limit
        2. Create template

        Args:
            user_id: User ID
            template_data: Template data

        Returns:
            Created template dict

        Raises:
            TemplateLimitExceededException: If limit exceeded
        """
        # 1. Check template count limit
        count = await self.repository.count_page_templates(user_id)
        if count >= MAX_TEMPLATES_PER_USER:
            raise TemplateLimitExceededException(max_templates=MAX_TEMPLATES_PER_USER)

        # 2. Add user_id to data
        data = {
            "user_id": user_id,
            **template_data
        }

        # 3. Create template
        return await self.repository.create_page_template(data)

    async def update_page_template(
        self,
        template_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update page template.

        Args:
            template_id: Template UUID
            user_id: User ID
            updates: Fields to update

        Returns:
            Updated template dict

        Raises:
            TemplateNotFoundException: If template not found
        """
        result = await self.repository.update_page_template(
            template_id,
            user_id,
            updates
        )

        if not result:
            raise TemplateNotFoundException()

        return result

    async def delete_page_template(
        self,
        template_id: str,
        user_id: str
    ) -> bool:
        """
        Delete page template.

        Args:
            template_id: Template UUID
            user_id: User ID

        Returns:
            True if deleted
        """
        return await self.repository.delete_page_template(template_id, user_id)

    async def use_page_template(
        self,
        template_id: str,
        user_id: str
    ) -> int:
        """
        Mark page template as used (increment use_count).

        Business logic:
        1. Get current use_count
        2. Update use_count + 1 and last_used_at
        3. Return new count

        Args:
            template_id: Template UUID
            user_id: User ID

        Returns:
            New use_count

        Raises:
            TemplateNotFoundException: If template not found
        """
        # 1. Get current template
        template = await self.repository.get_page_template(template_id, user_id)
        if not template:
            raise TemplateNotFoundException()

        # 2. Increment use_count
        current_count = template.get("use_count", 0)
        new_count = current_count + 1

        # 3. Update
        await self.repository.update_page_template(
            template_id,
            user_id,
            {
                "use_count": new_count,
                "last_used_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        return new_count
