"""
Database Projects - Project CRUD operations

@module services.db.projects
@version 3.24
"""

import logging
from datetime import datetime, timezone

from .core import supabase, retry_on_network_error

logger = logging.getLogger(__name__)


# ==========================================
# Project CRUD
# ==========================================

@retry_on_network_error()
def get_user_projects(user_id: str, page: int = 1, limit: int = 20, 
                      search: str = None, include_canvas_data: bool = True):
    """Get user's projects with pagination."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    fields = "*" if include_canvas_data else "id, title, thumbnail_url, created_at, updated_at"
    
    query = supabase.table("projects").select(fields)\
        .eq("user_id", user_id).eq("is_deleted", False)
    
    if search:
        query = query.ilike("title", f"%{search}%")
    
    result = query.order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
    return result.data or []


@retry_on_network_error()
def count_user_projects(user_id: str, search: str = None):
    """Count user's projects."""
    if not supabase:
        return 0
    
    query = supabase.table("projects").select("id", count="exact")\
        .eq("user_id", user_id).eq("is_deleted", False)
    
    if search:
        query = query.ilike("title", f"%{search}%")
    
    result = query.execute()
    return result.count or 0


@retry_on_network_error()
def get_project_detail(project_id: str, user_id: str):
    """Get project detail (must be owner or purchased)."""
    if not supabase:
        return None
    
    result = supabase.table("projects").select("*").eq("id", project_id).execute()
    if not result.data:
        return None
    
    project = result.data[0]
    
    # Owner access
    if project.get("user_id") == user_id:
        return project
    
    # Check if purchased
    purchase = supabase.table("marketplace_purchases").select("id")\
        .eq("buyer_id", user_id).eq("project_id", project_id).execute()
    
    if purchase.data:
        return project
    
    return None


@retry_on_network_error()
def create_project(user_id: str, title: str = None, canvas_data: dict = None, tz: str = "UTC"):
    """Create new project."""
    if not supabase:
        return None
    
    result = supabase.table("projects").insert({
        "user_id": user_id,
        "title": title or "Untitled Project",
        "canvas_data": canvas_data or {},
        "timezone": tz,
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def duplicate_project(project_id: str, user_id: str, tz: str = "UTC"):
    """Duplicate a project."""
    if not supabase:
        return None
    
    original = get_project_detail(project_id, user_id)
    if not original:
        return None
    
    new_title = f"{original.get('title', 'Project')} (Copy)"
    
    result = supabase.table("projects").insert({
        "user_id": user_id,
        "title": new_title,
        "canvas_data": original.get("canvas_data", {}),
        "timezone": tz,
    }).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def save_project(project_id: str, user_id: str, canvas_data: dict = None, 
                 thumbnail_url: str = None, title: str = None):
    """Save/update project."""
    if not supabase:
        return None
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if canvas_data is not None:
        update_data["canvas_data"] = canvas_data
    if thumbnail_url is not None:
        update_data["thumbnail_url"] = thumbnail_url
    if title is not None:
        update_data["title"] = title
    
    result = supabase.table("projects").update(update_data)\
        .eq("id", project_id).eq("user_id", user_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def soft_delete_project(project_id: str, user_id: str):
    """Soft delete project."""
    if not supabase:
        return None
    
    result = supabase.table("projects").update({
        "is_deleted": True,
        "deleted_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", project_id).eq("user_id", user_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def restore_project(project_id: str):
    """Restore soft-deleted project (admin)."""
    if not supabase:
        return None
    
    result = supabase.table("projects").update({
        "is_deleted": False,
        "deleted_at": None
    }).eq("id", project_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def user_restore_project(project_id: str, user_id: str):
    """Restore soft-deleted project (user)."""
    if not supabase:
        return None
    
    result = supabase.table("projects").update({
        "is_deleted": False,
        "deleted_at": None
    }).eq("id", project_id).eq("user_id", user_id).execute()
    
    return result.data[0] if result.data else None


@retry_on_network_error()
def get_user_deleted_projects(user_id: str, page: int = 1, limit: int = 20):
    """Get user's deleted projects."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    result = supabase.table("projects").select("id, title, thumbnail_url, deleted_at")\
        .eq("user_id", user_id).eq("is_deleted", True)\
        .order("deleted_at", desc=True).range(offset, offset + limit - 1).execute()
    
    return result.data or []


@retry_on_network_error()
def permanently_hide_project(project_id: str, user_id: str):
    """Permanently hide project (stage 2 delete)."""
    if not supabase:
        return None
    
    result = supabase.table("projects").update({
        "is_permanently_deleted": True
    }).eq("id", project_id).eq("user_id", user_id).eq("is_deleted", True).execute()
    
    return result.data[0] if result.data else None


def update_project_hash(project_id: str, new_hash: str):
    """Update project content hash."""
    if not supabase:
        return None
    supabase.table("projects").update({"content_hash": new_hash}).eq("id", project_id).execute()


@retry_on_network_error()
def get_all_projects_feed(page: int = 1, limit: int = 50):
    """Get site-wide project feed (admin)."""
    if not supabase:
        return []
    
    offset = (page - 1) * limit
    result = supabase.table("projects").select(
        "id, title, thumbnail_url, created_at, user_id, profiles(username, avatar_url)"
    ).eq("is_deleted", False).order("created_at", desc=True)\
    .range(offset, offset + limit - 1).execute()
    
    return result.data or []


# ==========================================
# Dashboard & Stats
# ==========================================

@retry_on_network_error()
def get_dashboard_projects(user_id: str, view: str = "all", page: int = 1, 
                           limit: int = 20, search: str = None, include_canvas: bool = True):
    """Get projects for dashboard with view filtering."""
    if not supabase:
        return {"items": [], "total": 0}
    
    offset = (page - 1) * limit
    
    if view == "all":
        fields = "*" if include_canvas else "id, title, thumbnail_url, created_at, updated_at"
        query = supabase.table("projects").select(fields, count="exact")\
            .eq("user_id", user_id).eq("is_deleted", False)
        if search:
            query = query.ilike("title", f"%{search}%")
        result = query.order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
        return {"items": result.data or [], "total": result.count or 0}
    
    elif view == "bought":
        result = supabase.table("marketplace_purchases").select(
            "id, purchased_at, project_id, projects(id, title, thumbnail_url, created_at)"
        ).eq("buyer_id", user_id).order("purchased_at", desc=True)\
        .range(offset, offset + limit - 1).execute()
        
        items = []
        for p in (result.data or []):
            proj = p.get("projects")
            if proj:
                proj["is_purchased"] = True
                proj["purchased_at"] = p.get("purchased_at")
                items.append(proj)
        return {"items": items, "total": len(items)}
    
    elif view == "selling":
        result = supabase.table("marketplace_listings").select(
            "id, title, price, sales_count, moderation_status, is_public, project_id"
        ).eq("user_id", user_id).eq("is_deleted", False)\
        .order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return {"items": result.data or [], "total": len(result.data or [])}
    
    return {"items": [], "total": 0}


@retry_on_network_error()
def get_seller_project_stats(user_id: str):
    """Get seller statistics for projects."""
    if not supabase:
        return {}
    
    listings = supabase.table("marketplace_listings").select("id, price, sales_count")\
        .eq("user_id", user_id).eq("resource_type", "project").execute()
    
    data = listings.data or []
    total_sales = sum(l.get("sales_count", 0) for l in data)
    total_revenue = sum(l.get("price", 0) * l.get("sales_count", 0) for l in data)
    
    return {
        "total_listings": len(data),
        "total_sales": total_sales,
        "total_revenue": total_revenue
    }
