"""
Creation Queries - Project read operations.

@module application.queries.creation
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from domains.creation import CreationService, Project, ProjectStatus


@dataclass
class GetProjectQuery:
    """Query to get a project by ID."""
    project_id: str
    user_id: str  # For access control


@dataclass
class GetProjectResult:
    """Result of project query."""
    success: bool
    project: Optional[Project] = None
    project_dict: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GetProjectHandler:
    """Handler for GetProjectQuery."""

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, query: GetProjectQuery) -> GetProjectResult:
        """Execute project query."""
        try:
            project = await self._creation_service.get_project_with_access(
                project_id=query.project_id,
                user_id=query.user_id,
            )

            return GetProjectResult(
                success=True,
                project=project,
                project_dict=project.to_dict(),
            )

        except Exception as e:
            return GetProjectResult(
                success=False,
                error=str(e),
            )


@dataclass
class GetUserProjectsQuery:
    """Query to get user's projects."""
    user_id: str
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass
class GetUserProjectsResult:
    """Result of user projects query."""
    success: bool
    projects: List[Project] = None
    projects_list: List[Dict[str, Any]] = None
    total_count: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if self.projects is None:
            self.projects = []
        if self.projects_list is None:
            self.projects_list = []


class GetUserProjectsHandler:
    """Handler for GetUserProjectsQuery."""

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, query: GetUserProjectsQuery) -> GetUserProjectsResult:
        """Execute user projects query."""
        try:
            status = ProjectStatus(query.status) if query.status else None

            projects = await self._creation_service.get_user_projects(
                user_id=query.user_id,
                status=status,
                limit=query.limit,
                offset=query.offset,
            )

            return GetUserProjectsResult(
                success=True,
                projects=projects,
                projects_list=[p.to_dict() for p in projects],
                total_count=len(projects),
            )

        except Exception as e:
            return GetUserProjectsResult(
                success=False,
                error=str(e),
            )


@dataclass
class SearchProjectsQuery:
    """Query to search projects."""
    query: str
    user_id: Optional[str] = None
    include_public: bool = True
    limit: int = 50
    offset: int = 0


@dataclass
class SearchProjectsResult:
    """Result of project search."""
    success: bool
    projects: List[Project] = None
    projects_list: List[Dict[str, Any]] = None
    total_count: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if self.projects is None:
            self.projects = []
        if self.projects_list is None:
            self.projects_list = []


class SearchProjectsHandler:
    """Handler for SearchProjectsQuery."""

    def __init__(self, creation_service: CreationService):
        self._creation_service = creation_service

    async def handle(self, query: SearchProjectsQuery) -> SearchProjectsResult:
        """Execute project search."""
        try:
            projects = await self._creation_service.search_projects(
                query=query.query,
                user_id=query.user_id,
                include_public=query.include_public,
                limit=query.limit,
                offset=query.offset,
            )

            return SearchProjectsResult(
                success=True,
                projects=projects,
                projects_list=[p.to_dict() for p in projects],
                total_count=len(projects),
            )

        except Exception as e:
            return SearchProjectsResult(
                success=False,
                error=str(e),
            )
