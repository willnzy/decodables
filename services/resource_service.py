"""
Resource Service
Unified resource management for templates, stickers, images, and other assets

@module services/resource_service
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from .access_control import AccessControl


class ResourceType(str, Enum):
    """Resource type enumeration"""
    TEMPLATE = "template"          # 项目模板
    STICKER = "sticker"            # 贴纸
    IMAGE = "image"                # 图片素材
    BACKGROUND = "background"      # 背景图
    FRAME = "frame"                # 边框/装饰框
    EMOJI = "emoji"                # 表情符号
    FONT = "font"                  # 字体
    SHAPE = "shape"                # 形状/图形
    ICON = "icon"                  # 图标
    PATTERN = "pattern"            # 图案/纹理


class ResourceCategory(str, Enum):
    """Resource category enumeration"""
    # Template categories
    STORY = "story"                # 故事模板
    EDUCATIONAL = "educational"    # 教育模板
    SEASONAL = "seasonal"          # 节日/季节
    BLANK = "blank"                # 空白模板
    
    # Sticker categories
    ANIMALS = "animals"            # 动物
    NATURE = "nature"              # 自然
    PEOPLE = "people"              # 人物
    FOOD = "food"                  # 食物
    OBJECTS = "objects"            # 物品
    EMOTIONS = "emotions"          # 表情/情绪
    EDUCATION = "education"        # 教育相关
    HOLIDAY = "holiday"            # 节日
    
    # General
    POPULAR = "popular"            # 热门
    NEW = "new"                    # 最新
    AI_GENERATED = "ai_generated"  # AI生成
    USER_UPLOAD = "user_upload"    # 用户上传


# Resource type to categories mapping
TYPE_CATEGORIES = {
    ResourceType.TEMPLATE: [
        ResourceCategory.STORY,
        ResourceCategory.EDUCATIONAL,
        ResourceCategory.SEASONAL,
        ResourceCategory.BLANK,
    ],
    ResourceType.STICKER: [
        ResourceCategory.ANIMALS,
        ResourceCategory.NATURE,
        ResourceCategory.PEOPLE,
        ResourceCategory.FOOD,
        ResourceCategory.OBJECTS,
        ResourceCategory.EMOTIONS,
        ResourceCategory.EDUCATION,
        ResourceCategory.HOLIDAY,
    ],
    ResourceType.IMAGE: [
        ResourceCategory.ANIMALS,
        ResourceCategory.NATURE,
        ResourceCategory.PEOPLE,
        ResourceCategory.OBJECTS,
    ],
    ResourceType.BACKGROUND: [
        ResourceCategory.NATURE,
        ResourceCategory.PATTERN,
        ResourceCategory.SEASONAL,
    ],
}


class ResourceService:
    """
    Service for managing system resources.
    
    Handles:
    - System templates and assets
    - Resource categorization
    - Tier-based access control
    - Resource search and filtering
    """
    
    def __init__(self, supabase):
        self.supabase = supabase
        self.access_control = AccessControl()
    
    def get_resources(
        self,
        user: dict,
        resource_type: str = None,
        category: str = None,
        allowed_tiers_filter: str = None,
        search: str = None,
        page: int = 1,
        limit: int = 50,
        include_locked: bool = True
    ) -> Dict[str, Any]:
        """
        Get system resources with filtering.
        
        Args:
            user: Current user profile
            resource_type: Filter by type (template, sticker, image, etc.)
            category: Filter by category
            allowed_tiers_filter: Filter by tier (free, starter, pro)
            search: Search in name/tags
            page: Page number
            limit: Items per page
            include_locked: Include resources user cannot access (with locked flag)
        
        Returns:
            Dict with items, total, and metadata
        """
        offset = (page - 1) * limit
        
        # Build query
        query = self.supabase.table("system_resources").select("*")
        
        if resource_type:
            query = query.eq("type", resource_type)
        
        if category:
            query = query.eq("category", category)
        
        if allowed_tiers_filter:
            if allowed_tiers_filter == "free":
                query = query.contains("allowed_tiers", ["free"])
            else:
                query = query.contains("allowed_tiers", [allowed_tiers_filter])
        
        # Execute query
        query = query.order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        items = result.data or []
        
        # Process items - add access info
        processed_items = []
        user_tier = user.get("tier", "free") if user else "free"
        
        for item in items:
            allowed_tiers = item.get("allowed_tiers", ["free"])
            item_type = item.get("type", "")
            
            # Base access check based on allowed_tiers
            is_accessible = self.access_control.can_access_resource(user, allowed_tiers)
            
            # PRD v3.2: Project Template is only accessible to Pro users
            # Even if allowed_tiers would grant access, Starter cannot use templates
            if item_type == "template" and user_tier != "pro":
                is_accessible = False
            
            # Skip locked items if not including them
            if not is_accessible and not include_locked:
                continue
            
            processed_items.append({
                **item,
                "is_accessible": is_accessible,
                "is_locked": not is_accessible,
            })
        
        return {
            "items": processed_items,
            "total": len(processed_items),
            "page": page,
            "limit": limit,
        }
    
    def get_resource_by_id(
        self,
        resource_id: str,
        user: dict
    ) -> Optional[Dict[str, Any]]:
        """
        Get single resource by ID.
        
        Args:
            resource_id: Resource ID
            user: Current user profile
        
        Returns:
            Resource with access info, or None
        """
        result = self.supabase.table("system_resources").select(
            "*"
        ).eq("id", resource_id).single().execute()
        
        if not result.data:
            return None
        
        item = result.data
        allowed_tiers = item.get("allowed_tiers", ["free"])
        item_type = item.get("type", "")
        user_tier = user.get("tier", "free") if user else "free"
        
        is_accessible = self.access_control.can_access_resource(user, allowed_tiers)
        
        # PRD v3.2: Project Template is only accessible to Pro users
        if item_type == "template" and user_tier != "pro":
            is_accessible = False
        
        return {
            **item,
            "is_accessible": is_accessible,
            "is_locked": not is_accessible,
        }
    
    def get_stickers(
        self,
        user: dict,
        category: str = None,
        page: int = 1,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get stickers for the editor.
        
        Args:
            user: Current user profile
            category: Filter by category
            page: Page number
            limit: Items per page
        
        Returns:
            Stickers with access info
        """
        return self.get_resources(
            user=user,
            resource_type=ResourceType.STICKER,
            category=category,
            page=page,
            limit=limit,
            include_locked=True  # Show locked stickers with lock icon
        )
    
    def get_templates(
        self,
        user: dict,
        category: str = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get project templates.
        
        Args:
            user: Current user profile
            category: Filter by category
            page: Page number
            limit: Items per page
        
        Returns:
            Templates with access info
        """
        return self.get_resources(
            user=user,
            resource_type=ResourceType.TEMPLATE,
            category=category,
            page=page,
            limit=limit,
            include_locked=True
        )
    
    def get_backgrounds(
        self,
        user: dict,
        category: str = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get background images.
        
        Args:
            user: Current user profile
            category: Filter by category
            page: Page number
            limit: Items per page
        
        Returns:
            Backgrounds with access info
        """
        return self.get_resources(
            user=user,
            resource_type=ResourceType.BACKGROUND,
            category=category,
            page=page,
            limit=limit,
            include_locked=True
        )
    
    def get_categories(
        self,
        resource_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get available categories for a resource type.
        
        Args:
            resource_type: Resource type
        
        Returns:
            List of category info
        """
        try:
            type_enum = ResourceType(resource_type)
            categories = TYPE_CATEGORIES.get(type_enum, [])
            
            return [
                {
                    "id": cat.value,
                    "name": cat.value.replace("_", " ").title(),
                }
                for cat in categories
            ]
        except ValueError:
            return []
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """
        Get resource statistics (for admin).
        
        Returns:
            Stats by type and tier
        """
        result = self.supabase.table("system_resources").select(
            "type, allowed_tiers"
        ).execute()
        
        items = result.data or []
        
        # Count by type
        type_counts = {}
        tier_counts = {"free": 0, "starter": 0, "pro": 0}
        
        for item in items:
            item_type = item.get("type", "unknown")
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            allowed_tiers = item.get("allowed_tiers", ["free"])
            if "free" in allowed_tiers:
                tier_counts["free"] += 1
            elif "starter" in allowed_tiers:
                tier_counts["starter"] += 1
            elif "pro" in allowed_tiers:
                tier_counts["pro"] += 1
        
        return {
            "total": len(items),
            "by_type": type_counts,
            "by_tier": tier_counts,
        }
    
    # ==========================================
    # Admin Methods
    # ==========================================
    
    def create_resource(
        self,
        resource_type: str,
        url: str,
        category: str = None,
        name: str = None,
        tags: List[str] = None,
        allowed_tiers: List[str] = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        Create a new system resource (admin only).
        
        Args:
            resource_type: Resource type
            url: Resource URL
            category: Category
            name: Display name
            tags: Search tags
            allowed_tiers: Access tiers
            metadata: Additional metadata (dimensions, etc.)
        
        Returns:
            Created resource
        """
        data = {
            "type": resource_type,
            "url": url,
            "category": category,
            "allowed_tiers": allowed_tiers or ["free"],
        }
        
        # Add optional fields to metadata or separate columns
        # depending on your schema
        
        result = self.supabase.table("system_resources").insert(data).execute()
        return result.data[0] if result.data else None
    
    def update_resource(
        self,
        resource_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a system resource (admin only).
        
        Args:
            resource_id: Resource ID
            updates: Fields to update
        
        Returns:
            Updated resource
        """
        # Validate allowed_tiers if provided
        if "allowed_tiers" in updates:
            if not self.access_control.validate_allowed_tiers(updates["allowed_tiers"]):
                raise ValueError("Invalid allowed_tiers")
        
        result = self.supabase.table("system_resources").update(
            updates
        ).eq("id", resource_id).execute()
        
        return result.data[0] if result.data else None
    
    def delete_resource(self, resource_id: str) -> bool:
        """
        Delete a system resource (admin only).
        
        Args:
            resource_id: Resource ID
        
        Returns:
            True if deleted
        """
        result = self.supabase.table("system_resources").delete().eq(
            "id", resource_id
        ).execute()
        
        return len(result.data) > 0 if result.data else False
    
    def bulk_import_resources(
        self,
        resources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Bulk import resources (admin only).
        
        Args:
            resources: List of resource data
        
        Returns:
            Import result with success/error counts
        """
        success_count = 0
        error_count = 0
        errors = []
        
        for resource in resources:
            try:
                self.create_resource(
                    resource_type=resource.get("type"),
                    url=resource.get("url"),
                    category=resource.get("category"),
                    name=resource.get("name"),
                    tags=resource.get("tags"),
                    allowed_tiers=resource.get("allowed_tiers"),
                    metadata=resource.get("metadata"),
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({
                    "resource": resource.get("url"),
                    "error": str(e)
                })
        
        return {
            "total": len(resources),
            "success": success_count,
            "errors": error_count,
            "error_details": errors[:10],  # Limit error details
        }

