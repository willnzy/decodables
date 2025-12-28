"""
Base Repository
Common database operations

@module repositories/base
"""

from typing import Optional, List, Dict, Any


class BaseRepository:
    """
    Base repository with common database operations.
    
    Provides:
    - CRUD operations
    - Pagination
    - Filtering
    """
    
    def __init__(self, supabase, table_name: str):
        self.supabase = supabase
        self.table_name = table_name
    
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Find record by ID.
        
        Args:
            id: Record ID
        
        Returns:
            Record dict or None
        """
        result = self.supabase.table(self.table_name).select(
            "*"
        ).eq("id", id).single().execute()
        return result.data if result.data else None
    
    def find_all(
        self, 
        page: int = 1, 
        limit: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find all records with pagination.
        
        Args:
            page: Page number (1-based)
            limit: Items per page
            order_by: Column to order by
            order_desc: Descending order
        
        Returns:
            List of records
        """
        offset = (page - 1) * limit
        query = self.supabase.table(self.table_name).select("*")
        query = query.order(order_by, desc=order_desc)
        query = query.range(offset, offset + limit - 1)
        result = query.execute()
        return result.data or []
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new record.
        
        Args:
            data: Record data
        
        Returns:
            Created record
        """
        result = self.supabase.table(self.table_name).insert(data).execute()
        return result.data[0] if result.data else None
    
    def update(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update record by ID.
        
        Args:
            id: Record ID
            data: Update data
        
        Returns:
            Updated record
        """
        result = self.supabase.table(self.table_name).update(
            data
        ).eq("id", id).execute()
        return result.data[0] if result.data else None
    
    def delete(self, id: str) -> bool:
        """
        Delete record by ID.
        
        Args:
            id: Record ID
        
        Returns:
            True if deleted
        """
        result = self.supabase.table(self.table_name).delete().eq("id", id).execute()
        return len(result.data) > 0 if result.data else False
    
    def soft_delete(self, id: str) -> bool:
        """
        Soft delete record (set is_deleted=true).
        
        Args:
            id: Record ID
        
        Returns:
            True if updated
        """
        result = self.supabase.table(self.table_name).update({
            "is_deleted": True
        }).eq("id", id).execute()
        return len(result.data) > 0 if result.data else False
    
    def count(self, **filters) -> int:
        """
        Count records with optional filters.
        
        Args:
            **filters: Column filters
        
        Returns:
            Count
        """
        query = self.supabase.table(self.table_name).select("id", count="exact")
        for key, value in filters.items():
            query = query.eq(key, value)
        result = query.execute()
        return result.count or 0

