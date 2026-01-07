"""
Project Repository Interface - Abstract data access for creation domain.

@module domains.creation.repository
@version 1.0.0

This defines the repository interface (port) for project operations.
Concrete implementations live in infrastructure/repositories/.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from .aggregates.project import Project, Page
from .value_objects import ProjectStatus


class IProjectRepository(ABC):
    """
    Repository interface for project operations.

    Follows the Repository pattern from DDD.
    Infrastructure layer provides the concrete implementation.
    """

    @abstractmethod
    async def get_by_id(self, project_id: str) -> Optional[Project]:
        """
        Get project by ID.

        Args:
            project_id: Project unique identifier

        Returns:
            Project aggregate or None if not found
        """
        pass

    @abstractmethod
    async def save(self, project: Project) -> Project:
        """
        Persist project.

        Creates new if not exists, updates if exists.

        Args:
            project: Project aggregate to save

        Returns:
            Saved Project aggregate
        """
        pass

    @abstractmethod
    async def create(self, project: Project) -> Project:
        """
        Create a new project.

        Args:
            project: Project to create

        Returns:
            Created Project
        """
        pass

    @abstractmethod
    async def update(self, project: Project) -> Project:
        """
        Update existing project.

        Args:
            project: Project to update

        Returns:
            Updated Project
        """
        pass

    @abstractmethod
    async def delete(self, project_id: str) -> bool:
        """
        Hard delete a project.

        Args:
            project_id: Project ID to delete

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def soft_delete(self, project_id: str) -> bool:
        """
        Soft delete a project (mark as deleted).

        Args:
            project_id: Project ID

        Returns:
            True if marked deleted
        """
        pass

    @abstractmethod
    async def get_by_owner(
        self,
        owner_id: str,
        status: Optional[ProjectStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """
        Get projects owned by a user.

        Args:
            owner_id: User ID of owner
            status: Filter by status
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of Projects
        """
        pass

    @abstractmethod
    async def get_shared_with_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """
        Get projects shared with a user.

        Args:
            user_id: User ID
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of Projects
        """
        pass

    @abstractmethod
    async def get_public_projects(
        self,
        limit: int = 50,
        offset: int = 0,
        tags: Optional[List[str]] = None
    ) -> List[Project]:
        """
        Get public projects.

        Args:
            limit: Maximum results
            offset: Results to skip
            tags: Filter by tags

        Returns:
            List of Projects
        """
        pass

    @abstractmethod
    async def count_by_owner(
        self,
        owner_id: str,
        status: Optional[ProjectStatus] = None
    ) -> int:
        """
        Count projects owned by user.

        Args:
            owner_id: User ID
            status: Filter by status

        Returns:
            Project count
        """
        pass

    @abstractmethod
    async def save_page(self, project_id: str, page: Page) -> Page:
        """
        Save a single page.

        Args:
            project_id: Parent project ID
            page: Page to save

        Returns:
            Saved Page
        """
        pass

    @abstractmethod
    async def get_page(self, project_id: str, page_id: str) -> Optional[Page]:
        """
        Get a specific page.

        Args:
            project_id: Parent project ID
            page_id: Page ID

        Returns:
            Page or None
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        owner_id: Optional[str] = None,
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """
        Search projects by title/description.

        Args:
            query: Search query
            owner_id: Filter by owner
            include_public: Include public projects
            limit: Maximum results
            offset: Results to skip

        Returns:
            List of matching Projects
        """
        pass
