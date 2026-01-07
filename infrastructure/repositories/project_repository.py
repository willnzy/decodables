"""
Project Repository Implementation - Supabase data access for creation domain.

@module infrastructure.repositories.project_repository
@version 1.0.0

Implements IProjectRepository using Supabase PostgreSQL.
"""

from typing import Optional, List
from datetime import datetime
import logging
import json

from domains.creation.repository import IProjectRepository
from domains.creation.aggregates.project import Project, Page
from domains.creation.value_objects import (
    ProjectStatus,
    CanvasSize,
    ProjectMetadata,
)
from domains.creation.exceptions import ProjectNotFoundException
from core.database import get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseProjectRepository(IProjectRepository):
    """
    Supabase implementation of project repository.
    """

    def __init__(self, client=None):
        """Initialize repository with Supabase client."""
        self._client = client

    @property
    def client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def get_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        try:
            result = self.client.table("projects").select("*").eq(
                "project_id", project_id
            ).single().execute()

            if not result.data:
                return None

            project = self._map_to_project(result.data)

            # Load pages
            pages_result = self.client.table("project_pages").select("*").eq(
                "project_id", project_id
            ).order("page_number").execute()

            project.pages = [self._map_to_page(row) for row in pages_result.data]

            return project

        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None

    async def save(self, project: Project) -> Project:
        """Persist project (upsert)."""
        try:
            data = self._map_to_row(project)
            self.client.table("projects").upsert(
                data, on_conflict="project_id"
            ).execute()

            # Save pages
            for page in project.pages:
                await self.save_page(project.project_id, page)

            return project

        except Exception as e:
            logger.error(f"Failed to save project {project.project_id}: {e}")
            raise

    async def create(self, project: Project) -> Project:
        """Create a new project."""
        try:
            data = self._map_to_row(project)
            self.client.table("projects").insert(data).execute()

            # Create initial pages
            for page in project.pages:
                await self.save_page(project.project_id, page)

            return project

        except Exception as e:
            logger.error(f"Failed to create project {project.project_id}: {e}")
            raise

    async def update(self, project: Project) -> Project:
        """Update existing project."""
        try:
            data = self._map_to_row(project)
            data["updated_at"] = datetime.utcnow().isoformat()

            result = self.client.table("projects").update(data).eq(
                "project_id", project.project_id
            ).select("*").single().execute()

            if not result.data:
                raise ProjectNotFoundException(project.project_id)

            return project

        except ProjectNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to update project {project.project_id}: {e}")
            raise

    async def delete(self, project_id: str) -> bool:
        """Hard delete a project."""
        try:
            # Delete pages first
            self.client.table("project_pages").delete().eq(
                "project_id", project_id
            ).execute()

            # Delete project
            result = self.client.table("projects").delete().eq(
                "project_id", project_id
            ).execute()

            return len(result.data) > 0 if result.data else False

        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            return False

    async def soft_delete(self, project_id: str) -> bool:
        """Soft delete a project."""
        try:
            self.client.table("projects").update({
                "status": ProjectStatus.DELETED.value,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("project_id", project_id).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to soft delete project {project_id}: {e}")
            return False

    async def get_by_owner(
        self,
        owner_id: str,
        status: Optional[ProjectStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """Get projects owned by a user."""
        try:
            query = self.client.table("projects").select("*").eq(
                "owner_id", owner_id
            ).neq("status", ProjectStatus.DELETED.value).order(
                "updated_at", desc=True
            ).range(offset, offset + limit - 1)

            if status:
                query = query.eq("status", status.value)

            result = query.execute()

            return [self._map_to_project(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get projects for owner {owner_id}: {e}")
            return []

    async def get_shared_with_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """Get projects shared with a user."""
        try:
            result = self.client.table("projects").select("*").contains(
                "collaborators", [user_id]
            ).neq("status", ProjectStatus.DELETED.value).order(
                "updated_at", desc=True
            ).range(offset, offset + limit - 1).execute()

            return [self._map_to_project(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get shared projects for user {user_id}: {e}")
            return []

    async def get_public_projects(
        self,
        limit: int = 50,
        offset: int = 0,
        tags: Optional[List[str]] = None
    ) -> List[Project]:
        """Get public projects."""
        try:
            query = self.client.table("projects").select("*").eq(
                "is_public", True
            ).eq("status", ProjectStatus.ACTIVE.value).order(
                "updated_at", desc=True
            ).range(offset, offset + limit - 1)

            if tags:
                query = query.contains("tags", tags)

            result = query.execute()

            return [self._map_to_project(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get public projects: {e}")
            return []

    async def count_by_owner(
        self,
        owner_id: str,
        status: Optional[ProjectStatus] = None
    ) -> int:
        """Count projects owned by user."""
        try:
            query = self.client.table("projects").select(
                "project_id", count="exact"
            ).eq("owner_id", owner_id).neq("status", ProjectStatus.DELETED.value)

            if status:
                query = query.eq("status", status.value)

            result = query.execute()

            return result.count if result.count else 0

        except Exception as e:
            logger.error(f"Failed to count projects for owner {owner_id}: {e}")
            return 0

    async def save_page(self, project_id: str, page: Page) -> Page:
        """Save a single page."""
        try:
            data = {
                "page_id": page.page_id,
                "project_id": project_id,
                "page_number": page.page_number,
                "canvas_data": json.dumps(page.canvas_data) if page.canvas_data else None,
                "thumbnail_url": page.thumbnail_url,
                "updated_at": datetime.utcnow().isoformat(),
            }

            self.client.table("project_pages").upsert(
                data, on_conflict="page_id"
            ).execute()

            return page

        except Exception as e:
            logger.error(f"Failed to save page {page.page_id}: {e}")
            raise

    async def get_page(self, project_id: str, page_id: str) -> Optional[Page]:
        """Get a specific page."""
        try:
            result = self.client.table("project_pages").select("*").eq(
                "project_id", project_id
            ).eq("page_id", page_id).single().execute()

            if not result.data:
                return None

            return self._map_to_page(result.data)

        except Exception as e:
            logger.error(f"Failed to get page {page_id}: {e}")
            return None

    async def search(
        self,
        query: str,
        owner_id: Optional[str] = None,
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[Project]:
        """Search projects by title/description."""
        try:
            # Build search query
            db_query = self.client.table("projects").select("*").neq(
                "status", ProjectStatus.DELETED.value
            ).or_(f"title.ilike.%{query}%,description.ilike.%{query}%").order(
                "updated_at", desc=True
            ).range(offset, offset + limit - 1)

            if owner_id and not include_public:
                db_query = db_query.eq("owner_id", owner_id)
            elif owner_id and include_public:
                db_query = db_query.or_(f"owner_id.eq.{owner_id},is_public.eq.true")
            elif include_public:
                db_query = db_query.eq("is_public", True)

            result = db_query.execute()

            return [self._map_to_project(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to search projects: {e}")
            return []

    def _map_to_project(self, row: dict) -> Project:
        """Map database row to Project."""
        metadata = ProjectMetadata(
            title=row.get("title", "Untitled"),
            description=row.get("description"),
            tags=row.get("tags", []),
            thumbnail_url=row.get("thumbnail_url"),
            is_public=row.get("is_public", False),
            is_template=row.get("is_template", False),
            template_category=row.get("template_category"),
            view_count=row.get("view_count", 0),
            like_count=row.get("like_count", 0),
        )

        canvas_size = CanvasSize.from_string(row.get("canvas_size", "1080x1080"))

        return Project(
            project_id=row["project_id"],
            owner_id=row["owner_id"],
            metadata=metadata,
            canvas_size=canvas_size,
            status=ProjectStatus(row.get("status", "draft")),
            pages=[],  # Loaded separately
            collaborators=row.get("collaborators", []),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.utcnow(),
        )

    def _map_to_page(self, row: dict) -> Page:
        """Map database row to Page."""
        canvas_data = row.get("canvas_data")
        if isinstance(canvas_data, str):
            canvas_data = json.loads(canvas_data)

        return Page(
            page_id=row["page_id"],
            page_number=row["page_number"],
            canvas_data=canvas_data,
            thumbnail_url=row.get("thumbnail_url"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                if row.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                if row.get("updated_at") else datetime.utcnow(),
        )

    def _map_to_row(self, project: Project) -> dict:
        """Map Project to database row."""
        return {
            "project_id": project.project_id,
            "owner_id": project.owner_id,
            "title": project.metadata.title,
            "description": project.metadata.description,
            "tags": project.metadata.tags,
            "thumbnail_url": project.metadata.thumbnail_url,
            "is_public": project.metadata.is_public,
            "is_template": project.metadata.is_template,
            "template_category": project.metadata.template_category,
            "canvas_size": project.canvas_size.to_string(),
            "status": project.status.value,
            "collaborators": project.collaborators,
        }
