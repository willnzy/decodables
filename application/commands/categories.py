"""
Category Command Handlers - CQRS Command Side.

@module application.commands.categories
@version 1.0.0
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from domains.content.category_service import CategoryService


# =============================================================================
# Command DTOs
# =============================================================================

@dataclass
class CreateCategoryCommand:
    """Command to create a new category."""
    slug: str
    name: str
    asset_type: str
    parent_slug: Optional[str] = None
    name_i18n: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    min_tier: str = "t1"
    is_visible: bool = True
    is_featured: bool = False
    display_order: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UpdateCategoryCommand:
    """Command to update category metadata."""
    category_id: str
    updates: Dict[str, Any]


@dataclass
class MoveCategoryCommand:
    """Command to move a category to a new parent."""
    category_slug: str
    new_parent_slug: Optional[str]


@dataclass
class DeleteCategoryCommand:
    """Command to delete a category."""
    category_id: str
    cascade: bool = False


@dataclass
class ReorderCategoriesCommand:
    """Command to reorder multiple categories."""
    category_orders: List[Dict[str, Any]]  # [{id: str, display_order: int}]


@dataclass
class UpdateAssetCountCommand:
    """Command to update asset count for a category."""
    category_id: str
    count: int


@dataclass
class IncrementUsageCommand:
    """Command to increment usage count for a category."""
    category_id: str


# =============================================================================
# Command Handlers
# =============================================================================

class CategoryCommandHandlers:
    """Handles category command operations."""

    def __init__(self, category_service: CategoryService):
        """
        Initialize handlers with service.

        Args:
            category_service: Category business logic service
        """
        self.service = category_service

    async def handle_create_category(
        self,
        command: CreateCategoryCommand
    ) -> Dict[str, Any]:
        """
        Handle create category command.

        Args:
            command: CreateCategoryCommand

        Returns:
            Created category dict

        Raises:
            ValueError: If validation fails
            Exception: If creation fails
        """
        return await self.service.create_category(
            slug=command.slug,
            name=command.name,
            asset_type=command.asset_type,
            parent_slug=command.parent_slug,
            name_i18n=command.name_i18n,
            description=command.description,
            icon=command.icon,
            min_tier=command.min_tier,
            is_visible=command.is_visible,
            is_featured=command.is_featured,
            display_order=command.display_order,
            metadata=command.metadata
        )

    async def handle_update_category(
        self,
        command: UpdateCategoryCommand
    ) -> Dict[str, Any]:
        """
        Handle update category command.

        Args:
            command: UpdateCategoryCommand

        Returns:
            Updated category dict

        Raises:
            ValueError: If trying to update protected fields
            Exception: If update fails
        """
        return await self.service.update_category(
            category_id=command.category_id,
            updates=command.updates
        )

    async def handle_move_category(
        self,
        command: MoveCategoryCommand
    ) -> Dict[str, Any]:
        """
        Handle move category command.

        Args:
            command: MoveCategoryCommand

        Returns:
            Updated category dict

        Raises:
            ValueError: If would create circular reference or exceed max level
            Exception: If move fails
        """
        return await self.service.move_category(
            category_slug=command.category_slug,
            new_parent_slug=command.new_parent_slug
        )

    async def handle_delete_category(
        self,
        command: DeleteCategoryCommand
    ) -> bool:
        """
        Handle delete category command.

        Args:
            command: DeleteCategoryCommand

        Returns:
            True if deleted

        Raises:
            ValueError: If cascade=False and category has children
            Exception: If deletion fails
        """
        return await self.service.delete_category(
            category_id=command.category_id,
            cascade=command.cascade
        )

    async def handle_reorder_categories(
        self,
        command: ReorderCategoriesCommand
    ) -> List[Dict[str, Any]]:
        """
        Handle reorder categories command.

        Args:
            command: ReorderCategoriesCommand

        Returns:
            List of updated categories

        Raises:
            ValueError: If invalid data
            Exception: If update fails
        """
        return await self.service.reorder_categories(
            category_orders=command.category_orders
        )

    async def handle_update_asset_count(
        self,
        command: UpdateAssetCountCommand
    ) -> bool:
        """
        Handle update asset count command.

        Args:
            command: UpdateAssetCountCommand

        Returns:
            True if updated
        """
        return await self.service.update_asset_count(
            category_id=command.category_id,
            count=command.count
        )

    async def handle_increment_usage(
        self,
        command: IncrementUsageCommand
    ) -> bool:
        """
        Handle increment usage command.

        Args:
            command: IncrementUsageCommand

        Returns:
            True if incremented
        """
        return await self.service.increment_usage(
            category_id=command.category_id
        )
