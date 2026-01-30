"""
Project Aggregate - Encapsulates project and canvas management.

@module domains.creation.aggregates.project
@version 1.0.0

This is the aggregate root for project management.
All project operations must go through this aggregate.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from ..value_objects import (
    ProjectId,
    ProjectStatus,
    CanvasSize,
    ProjectMetadata,
)
from ..exceptions import PageNotFoundException


@dataclass
class Page:
    """Represents a single page/canvas in a project."""
    page_id: str
    page_number: int
    canvas_data: Optional[Dict[str, Any]] = None
    thumbnail_url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Project:
    """
    Aggregate root for project management.

    Encapsulates:
    - Project metadata
    - Canvas configuration
    - Pages/canvas data
    - Sharing settings

    v1.1.0: Added idempotency_key for safe retry support.
    """
    project_id: str
    owner_id: str
    metadata: ProjectMetadata
    canvas_size: CanvasSize
    status: ProjectStatus = ProjectStatus.DRAFT
    pages: List[Page] = field(default_factory=list)
    collaborators: List[str] = field(default_factory=list)
    canvas_data: Optional[Dict[str, Any]] = None  # Direct canvas data from DB
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # v1.1.0: Idempotency support - client-generated key for safe retries
    idempotency_key: Optional[str] = None
    # Flag for locked elements (marketplace assets)
    contains_locked_elements: bool = False
    # v3.33 Phase 2.6: Folder organization and starring
    folder_id: Optional[str] = None
    is_starred: bool = False
    # Soft delete support
    deleted_at: Optional[datetime] = None
    recovery_expires_at: Optional[datetime] = None

    @classmethod
    def create_new(
        cls,
        owner_id: str,
        title: str,
        canvas_size: CanvasSize = None,
        description: Optional[str] = None
    ) -> "Project":
        """
        Factory method to create a new project.

        Args:
            owner_id: User ID of the project owner
            title: Project title
            canvas_size: Canvas dimensions
            description: Optional description

        Returns:
            New Project instance with initial page
        """
        project_id = ProjectId.generate()
        size = canvas_size or CanvasSize.instagram_square()

        project = cls(
            project_id=str(project_id),
            owner_id=owner_id,
            metadata=ProjectMetadata(title=title, description=description),
            canvas_size=size,
            status=ProjectStatus.DRAFT,
        )

        # Add initial page
        project.add_page()

        return project

    @property
    def title(self) -> str:
        """Get project title."""
        return self.metadata.title

    @property
    def is_editable(self) -> bool:
        """Check if project can be edited."""
        return self.status.is_editable

    @property
    def is_public(self) -> bool:
        """Check if project is publicly visible."""
        return self.metadata.is_public

    @property
    def page_count(self) -> int:
        """Get number of pages."""
        return len(self.pages)

    def can_access(self, user_id: str) -> bool:
        """Check if user can access this project."""
        if self.owner_id == user_id:
            return True
        if user_id in self.collaborators:
            return True
        if self.is_public:
            return True
        return False

    def can_edit(self, user_id: str) -> bool:
        """Check if user can edit this project."""
        if not self.is_editable:
            return False
        if self.owner_id == user_id:
            return True
        if user_id in self.collaborators:
            return True
        return False

    def update_metadata(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_public: Optional[bool] = None
    ):
        """Update project metadata (creates new immutable ProjectMetadata)."""
        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if tags is not None:
            updates["tags"] = tuple(tags)
        if is_public is not None:
            updates["is_public"] = is_public
        if updates:
            self.metadata = self.metadata.replace(**updates)
            self.updated_at = datetime.now(timezone.utc)

    def add_page(self, canvas_data: Optional[Dict[str, Any]] = None) -> Page:
        """
        Add a new page to the project.

        Args:
            canvas_data: Initial canvas data

        Returns:
            The newly created page
        """
        page_number = len(self.pages) + 1
        page = Page(
            page_id=str(ProjectId.generate()),
            page_number=page_number,
            canvas_data=canvas_data or {},
        )
        self.pages.append(page)
        self.updated_at = datetime.now(timezone.utc)
        return page

    def remove_page(self, page_id: str) -> bool:
        """
        Remove a page from the project.

        Args:
            page_id: ID of page to remove

        Returns:
            True if removed
        """
        if len(self.pages) <= 1:
            return False  # Must have at least one page

        for i, page in enumerate(self.pages):
            if page.page_id == page_id:
                self.pages.pop(i)
                # Renumber remaining pages
                for j, p in enumerate(self.pages):
                    p.page_number = j + 1
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False

    def update_page_canvas(self, page_id: str, canvas_data: Dict[str, Any]):
        """
        Update canvas data for a page.

        Args:
            page_id: Page ID
            canvas_data: New canvas data
        """
        for page in self.pages:
            if page.page_id == page_id:
                page.canvas_data = canvas_data
                page.updated_at = datetime.now(timezone.utc)
                self.updated_at = datetime.now(timezone.utc)
                return
        raise PageNotFoundException(page_id=page_id, project_id=self.project_id)

    def get_page(self, page_id: str) -> Optional[Page]:
        """Get a page by ID."""
        for page in self.pages:
            if page.page_id == page_id:
                return page
        return None

    def add_collaborator(self, user_id: str):
        """Add a collaborator to the project."""
        if user_id not in self.collaborators and user_id != self.owner_id:
            self.collaborators.append(user_id)
            self.updated_at = datetime.now(timezone.utc)

    def remove_collaborator(self, user_id: str):
        """Remove a collaborator from the project."""
        if user_id in self.collaborators:
            self.collaborators.remove(user_id)
            self.updated_at = datetime.now(timezone.utc)

    def archive(self):
        """Archive the project."""
        self.status = ProjectStatus.ARCHIVED
        self.updated_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore archived project."""
        if self.status == ProjectStatus.ARCHIVED:
            self.status = ProjectStatus.ACTIVE
            self.updated_at = datetime.now(timezone.utc)

    def mark_deleted(self):
        """Mark project as deleted (soft delete)."""
        self.status = ProjectStatus.DELETED
        self.updated_at = datetime.now(timezone.utc)

    def activate(self):
        """Activate a draft project."""
        if self.status == ProjectStatus.DRAFT:
            self.status = ProjectStatus.ACTIVE
            self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API responses.

        Note: Uses 'id' and 'user_id' for API compatibility with ProjectResponse model.
        """
        return {
            "id": self.project_id,  # API uses 'id' not 'project_id'
            "user_id": self.owner_id,  # API uses 'user_id' not 'owner_id'
            "title": self.metadata.title,
            "description": self.metadata.description,
            "tags": list(self.metadata.tags),
            "is_public": self.metadata.is_public,
            "thumbnail_url": self.metadata.thumbnail_url,
            "canvas_size": self.canvas_size.to_string(),
            "canvas_data": self.canvas_data,
            "status": self.status.value,
            "page_count": self.page_count,
            "collaborators": self.collaborators,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            # v3.33 Phase 2.6: Folder organization and starring
            "folder_id": self.folder_id,
            "is_starred": self.is_starred,
        }
