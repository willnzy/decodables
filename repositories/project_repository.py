"""
Project Repository
Database operations for projects

@module repositories/project_repository
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class ProjectRepository(BaseRepository):
    """
    Repository for project operations.
    """
    
    def __init__(self, supabase):
        super().__init__(supabase, "projects")
    
    def find_by_user(
        self, 
        user_id: str, 
        page: int = 1, 
        limit: int = 20,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find projects by user.
        
        Args:
            user_id: User ID
            page: Page number
            limit: Items per page
            include_deleted: Include soft-deleted projects
        
        Returns:
            List of projects
        """
        offset = (page - 1) * limit
        query = self.supabase.table(self.table_name).select(
            "*"
        ).eq("user_id", user_id)
        
        if not include_deleted:
            query = query.eq("is_deleted", False)
        
        query = query.order("updated_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        return result.data or []
    
    def find_by_id_and_user(
        self, 
        project_id: str, 
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find project by ID and user (ownership check).
        
        Args:
            project_id: Project ID
            user_id: User ID
        
        Returns:
            Project dict or None
        """
        result = self.supabase.table(self.table_name).select(
            "*"
        ).eq("id", project_id).eq("user_id", user_id).eq(
            "is_deleted", False
        ).single().execute()
        return result.data if result.data else None
    
    def create_for_user(
        self, 
        user_id: str, 
        title: str = None,
        canvas_data: Dict = None
    ) -> Dict[str, Any]:
        """
        Create new project for user.
        
        Args:
            user_id: User ID
            title: Project title
            canvas_data: Initial canvas data
        
        Returns:
            Created project
        """
        data = {
            "user_id": user_id,
            "title": title or "My Magic Story",
            "canvas_data": canvas_data or {}
        }
        return self.create(data)
    
    def save(
        self, 
        project_id: str, 
        user_id: str,
        canvas_data: Dict = None,
        thumbnail_url: str = None,
        title: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Save project (update canvas_data, thumbnail, title).
        
        Args:
            project_id: Project ID
            user_id: User ID (for ownership check)
            canvas_data: Updated canvas data
            thumbnail_url: Updated thumbnail URL
            title: Updated title
        
        Returns:
            Updated project or None
        """
        update_data = {"updated_at": "now()"}
        
        if canvas_data is not None:
            update_data["canvas_data"] = canvas_data
        if thumbnail_url is not None:
            update_data["thumbnail_url"] = thumbnail_url
        if title is not None:
            update_data["title"] = title
        
        result = self.supabase.table(self.table_name).update(
            update_data
        ).eq("id", project_id).eq("user_id", user_id).execute()
        
        return result.data[0] if result.data else None
    
    def soft_delete_for_user(
        self, 
        project_id: str, 
        user_id: str
    ) -> bool:
        """
        Soft delete project (user ownership check).
        
        Args:
            project_id: Project ID
            user_id: User ID
        
        Returns:
            True if deleted
        """
        result = self.supabase.table(self.table_name).update({
            "is_deleted": True
        }).eq("id", project_id).eq("user_id", user_id).execute()
        return len(result.data) > 0 if result.data else False
    
    def restore(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore soft-deleted project.
        
        Args:
            project_id: Project ID
        
        Returns:
            Restored project or None
        """
        result = self.supabase.table(self.table_name).update({
            "is_deleted": False
        }).eq("id", project_id).execute()
        return result.data[0] if result.data else None
    
    def get_all_feed(
        self, 
        page: int = 1, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all projects feed (admin).
        
        Args:
            page: Page number
            limit: Items per page
        
        Returns:
            List of projects with user info
        """
        offset = (page - 1) * limit
        result = self.supabase.table(self.table_name).select(
            "*, profiles(id, email, username, avatar_url)"
        ).order("updated_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()
        return result.data or []
    
    def get_assets(
        self, 
        user_id: str, 
        project_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's assets.
        
        Args:
            user_id: User ID
            project_id: Optional project filter
        
        Returns:
            List of assets
        """
        query = self.supabase.table("assets").select(
            "*"
        ).eq("user_id", user_id).eq("is_deleted", False)
        
        if project_id:
            query = query.eq("project_id", project_id)
        
        result = query.order("created_at", desc=True).execute()
        return result.data or []

