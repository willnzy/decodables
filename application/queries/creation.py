"""
Creation Queries - Project read operations.

@module application.queries.creation
@version 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from domains.creation import CreationService, Project, ProjectStatus
from domains.creation.repository import IProjectRepository


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
    exception: Optional[Exception] = None  # Original exception for type checking


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
                exception=e,
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

            # Get actual total count for pagination (not just current page count)
            total_count = await self._creation_service.count_user_projects(query.user_id)

            return GetUserProjectsResult(
                success=True,
                projects=projects,
                projects_list=[p.to_dict() for p in projects],
                total_count=total_count,
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


@dataclass
class GetDashboardProjectsQuery:
    """
    Query to get dashboard projects with view type filtering.

    P1-002 fix: Migrated from page-based to offset-based pagination (DDD compliant).
    Supports cross-domain data (marketplace listings).
    v3.45: Added workspace_id for data isolation.
    """
    user_id: str
    workspace_id: Optional[str] = None
    view_type: str = "all"  # "all", "bought", "selling"
    offset: int = 0
    limit: int = 20
    search: Optional[str] = None
    include_canvas_data: bool = True
    folder_id: Optional[str] = "NOT_SET"  # "NOT_SET" = no filter, None = root only, str = specific folder


@dataclass
class GetDashboardProjectsResult:
    """Result of dashboard projects query."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GetDashboardProjectsHandler:
    """
    Handler for GetDashboardProjectsQuery.

    Uses repository directly for cross-domain queries.
    """

    def __init__(self, repository: IProjectRepository):
        self._repository = repository

    async def handle(self, query: GetDashboardProjectsQuery) -> GetDashboardProjectsResult:
        """Execute dashboard projects query."""
        try:
            # Repository method handles cross-domain data (marketplace enrichment)
            result = await self._repository.get_dashboard_projects(
                user_id=query.user_id,
                workspace_id=query.workspace_id,
                view_type=query.view_type,
                offset=query.offset,
                limit=query.limit,
                search=query.search,
                include_canvas_data=query.include_canvas_data,
                folder_id=query.folder_id,
            )

            return GetDashboardProjectsResult(
                success=True,
                data=result,
            )

        except Exception as e:
            return GetDashboardProjectsResult(
                success=False,
                error=str(e),
            )
