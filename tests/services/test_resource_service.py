"""
Resource Service Tests
资源服务测试

Coverage target: 90%+
Business logic tested:
- Resource type and category enums
- Tier-based access control for resources
- Resource CRUD operations
- Sticker, project, background retrieval
"""

import pytest
from unittest.mock import patch, MagicMock


class TestResourceTypeEnum:
    """Test ResourceType enum"""
    
    def test_resource_types_defined(self):
        """All resource types are defined"""
        from services.resource_service import ResourceType
        
        assert ResourceType.PROJECT == "project"
        assert ResourceType.STICKER == "sticker"
        assert ResourceType.IMAGE == "image"
        assert ResourceType.BACKGROUND == "background"
        assert ResourceType.FRAME == "frame"
        assert ResourceType.EMOJI == "emoji"
        assert ResourceType.FONT == "font"
        assert ResourceType.SHAPE == "shape"
        assert ResourceType.ICON == "icon"
        assert ResourceType.PATTERN == "pattern"


class TestResourceCategoryEnum:
    """Test ResourceCategory enum"""
    
    def test_project_categories(self):
        """Project-related categories are defined"""
        from services.resource_service import ResourceCategory
        
        assert ResourceCategory.STORY == "story"
        assert ResourceCategory.EDUCATIONAL == "educational"
        assert ResourceCategory.SEASONAL == "seasonal"
        assert ResourceCategory.BLANK == "blank"
    
    def test_sticker_categories(self):
        """Sticker-related categories are defined"""
        from services.resource_service import ResourceCategory
        
        assert ResourceCategory.ANIMALS == "animals"
        assert ResourceCategory.NATURE == "nature"
        assert ResourceCategory.PEOPLE == "people"
        assert ResourceCategory.FOOD == "food"
        assert ResourceCategory.OBJECTS == "objects"
        assert ResourceCategory.EMOTIONS == "emotions"
    
    def test_general_categories(self):
        """General categories are defined"""
        from services.resource_service import ResourceCategory
        
        assert ResourceCategory.POPULAR == "popular"
        assert ResourceCategory.NEW == "new"
        assert ResourceCategory.AI_GENERATED == "ai_generated"
        assert ResourceCategory.USER_UPLOAD == "user_upload"


class TestTypeCategoriesMapping:
    """Test TYPE_CATEGORIES mapping"""
    
    def test_project_categories(self):
        """Projects have correct categories"""
        from services.resource_service import TYPE_CATEGORIES, ResourceType, ResourceCategory
        
        project_cats = TYPE_CATEGORIES[ResourceType.PROJECT]
        
        assert ResourceCategory.STORY in project_cats
        assert ResourceCategory.EDUCATIONAL in project_cats
        assert ResourceCategory.SEASONAL in project_cats
        assert ResourceCategory.BLANK in project_cats
    
    def test_sticker_categories(self):
        """Stickers have correct categories"""
        from services.resource_service import TYPE_CATEGORIES, ResourceType, ResourceCategory
        
        sticker_cats = TYPE_CATEGORIES[ResourceType.STICKER]
        
        assert ResourceCategory.ANIMALS in sticker_cats
        assert ResourceCategory.NATURE in sticker_cats
        assert ResourceCategory.PEOPLE in sticker_cats
    
    def test_background_categories(self):
        """Backgrounds have correct categories"""
        from services.resource_service import TYPE_CATEGORIES, ResourceType, ResourceCategory
        
        bg_cats = TYPE_CATEGORIES[ResourceType.BACKGROUND]
        
        assert ResourceCategory.NATURE in bg_cats
        assert ResourceCategory.PATTERN in bg_cats


class TestResourceServiceInit:
    """Test ResourceService initialization"""
    
    def test_init_with_supabase(self):
        """Initializes with supabase client"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        service = ResourceService(mock_supabase)
        
        assert service.supabase is mock_supabase
        assert service.access_control is not None


class TestGetResources:
    """Test ResourceService.get_resources method"""
    
    def test_get_resources_basic(self):
        """Basic resource retrieval"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "1", "type": "sticker", "allowed_tiers": ["free"], "category": "animals"},
            {"id": "2", "type": "sticker", "allowed_tiers": ["starter"], "category": "people"},
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"id": "user_1", "tier": "free"}
        
        result = service.get_resources(user)
        
        assert "items" in result
        assert "total" in result
        assert "page" in result
    
    def test_get_resources_with_type_filter(self):
        """Filters by resource type"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "1", "type": "sticker", "allowed_tiers": ["free"]}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        
        result = service.get_resources(user, resource_type="sticker")
        
        # Verify eq was called for type filter
        mock_supabase.table.return_value.select.return_value.eq.assert_called_with("type", "sticker")
    
    def test_get_resources_with_category_filter(self):
        """Filters by category"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        
        result = service.get_resources(user, resource_type="sticker", category="animals")
        
        assert result is not None
    
    def test_get_resources_tier_filter(self):
        """Filters by allowed tiers"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.contains.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "starter"}
        
        result = service.get_resources(user, allowed_tiers_filter="free")
        
        mock_supabase.table.return_value.select.return_value.contains.assert_called_with("allowed_tiers", ["free"])
    
    def test_get_resources_accessibility(self):
        """Adds accessibility flags to resources"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "1", "type": "sticker", "allowed_tiers": ["free"]},
            {"id": "2", "type": "sticker", "allowed_tiers": ["pro"]},
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        
        result = service.get_resources(user)
        
        # Free resource should be accessible
        free_item = next(i for i in result["items"] if i["id"] == "1")
        assert free_item["is_accessible"] is True
        assert free_item["is_locked"] is False
        
        # Pro resource should not be accessible
        pro_item = next(i for i in result["items"] if i["id"] == "2")
        assert pro_item["is_accessible"] is False
        assert pro_item["is_locked"] is True
    
    def test_get_resources_project_pro_only(self):
        """PRD v3.2: Projects only accessible to Pro users"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "1", "type": "project", "allowed_tiers": ["free"]},  # Even with free tier, should be locked for non-pro
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        # Starter user cannot access projects
        starter_user = {"tier": "starter"}
        result = service.get_resources(starter_user)
        assert result["items"][0]["is_accessible"] is False
        
        # Pro user can access projects
        pro_user = {"tier": "pro"}
        result = service.get_resources(pro_user)
        assert result["items"][0]["is_accessible"] is True
    
    def test_get_resources_exclude_locked(self):
        """Can exclude locked resources"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "1", "type": "sticker", "allowed_tiers": ["free"]},
            {"id": "2", "type": "sticker", "allowed_tiers": ["pro"]},
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        
        result = service.get_resources(user, include_locked=False)
        
        # Should only return accessible resources
        assert len(result["items"]) == 1
        assert result["items"][0]["id"] == "1"
    
    def test_get_resources_pagination(self):
        """Pagination works correctly"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        
        result = service.get_resources(user, page=2, limit=20)
        
        # Offset should be (2-1) * 20 = 20
        mock_supabase.table.return_value.select.return_value.order.return_value.range.assert_called_with(20, 39)


class TestGetResourceById:
    """Test ResourceService.get_resource_by_id method"""
    
    def test_get_resource_by_id_found(self):
        """Returns resource when found"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {"id": "1", "type": "sticker", "allowed_tiers": ["free"]}
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        
        result = service.get_resource_by_id("1", user)
        
        assert result["id"] == "1"
        assert "is_accessible" in result
    
    def test_get_resource_by_id_not_found(self):
        """Returns None when not found"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        
        result = service.get_resource_by_id("nonexistent", user)
        
        assert result is None
    
    def test_get_resource_by_id_project_access(self):
        """Project access check for non-pro users"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {"id": "1", "type": "project", "allowed_tiers": ["free"]}
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        # Starter user
        starter_user = {"tier": "starter"}
        result = service.get_resource_by_id("1", starter_user)
        assert result["is_accessible"] is False


class TestGetStickers:
    """Test ResourceService.get_stickers convenience method"""
    
    def test_get_stickers(self):
        """Gets stickers with correct parameters"""
        from services.resource_service import ResourceService, ResourceType
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        
        result = service.get_stickers(user, category="animals", page=1, limit=100)
        
        assert "items" in result


class TestGetProjects:
    """Test ResourceService.get_projects convenience method"""
    
    def test_get_projects(self):
        """Gets projects with correct parameters"""
        from services.resource_service import ResourceService, ResourceType
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "pro"}
        
        result = service.get_projects(user, category="story", page=1, limit=20)
        
        assert "items" in result


class TestGetBackgrounds:
    """Test ResourceService.get_backgrounds convenience method"""
    
    def test_get_backgrounds(self):
        """Gets backgrounds with correct parameters"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "starter"}
        
        result = service.get_backgrounds(user, category="nature")
        
        assert "items" in result


class TestGetCategories:
    """Test ResourceService.get_categories method"""
    
    def test_get_categories_for_stickers(self):
        """Gets categories for sticker type"""
        from services.resource_service import ResourceService
        
        service = ResourceService(MagicMock())
        
        result = service.get_categories("sticker")
        
        assert len(result) > 0
        assert any(cat["id"] == "animals" for cat in result)
    
    def test_get_categories_for_projects(self):
        """Gets categories for project type"""
        from services.resource_service import ResourceService
        
        service = ResourceService(MagicMock())
        
        result = service.get_categories("project")
        
        assert len(result) > 0
        assert any(cat["id"] == "story" for cat in result)
    
    def test_get_categories_invalid_type(self):
        """Returns empty for invalid type"""
        from services.resource_service import ResourceService
        
        service = ResourceService(MagicMock())
        
        result = service.get_categories("invalid_type")
        
        assert result == []
    
    def test_get_categories_format(self):
        """Categories have correct format"""
        from services.resource_service import ResourceService
        
        service = ResourceService(MagicMock())
        
        result = service.get_categories("sticker")
        
        for cat in result:
            assert "id" in cat
            assert "name" in cat


class TestGetResourceStats:
    """Test ResourceService.get_resource_stats method"""
    
    def test_get_resource_stats(self):
        """Gets resource statistics"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"type": "sticker", "allowed_tiers": ["free"]},
            {"type": "sticker", "allowed_tiers": ["starter"]},
            {"type": "project", "allowed_tiers": ["pro"]},
        ]
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        result = service.get_resource_stats()
        
        assert result["total"] == 3
        assert "by_type" in result
        assert "by_tier" in result
        assert result["by_type"]["sticker"] == 2
        assert result["by_type"]["project"] == 1


class TestAdminCreateResource:
    """Test ResourceService.create_resource admin method"""
    
    def test_create_resource(self):
        """Creates new resource"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "new-123", "type": "sticker", "url": "https://example.com/img.png"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        result = service.create_resource(
            resource_type="sticker",
            url="https://example.com/img.png",
            category="animals",
            allowed_tiers=["free"]
        )
        
        assert result["id"] == "new-123"
    
    def test_create_resource_default_tiers(self):
        """Creates resource with default tiers"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        service.create_resource(
            resource_type="sticker",
            url="https://example.com/img.png"
        )
        
        # Verify default tiers
        insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
        assert insert_call["allowed_tiers"] == ["free"]


class TestAdminUpdateResource:
    """Test ResourceService.update_resource admin method"""
    
    def test_update_resource(self):
        """Updates existing resource"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "1", "category": "updated"}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        result = service.update_resource("1", {"category": "updated"})
        
        assert result["category"] == "updated"
    
    def test_update_resource_validates_tiers(self):
        """Validates allowed_tiers on update"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        service = ResourceService(mock_supabase)
        
        # Invalid tier should raise error
        with pytest.raises(ValueError):
            service.update_resource("1", {"allowed_tiers": ["invalid_tier"]})


class TestAdminDeleteResource:
    """Test ResourceService.delete_resource admin method"""
    
    def test_delete_resource_success(self):
        """Deletes resource successfully"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}]
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        result = service.delete_resource("1")
        
        assert result is True
    
    def test_delete_resource_not_found(self):
        """Returns False when resource not found"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        result = service.delete_resource("nonexistent")
        
        assert result is False


class TestBulkImportResources:
    """Test ResourceService.bulk_import_resources admin method"""
    
    def test_bulk_import_success(self):
        """Bulk import succeeds"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        resources = [
            {"type": "sticker", "url": "https://example.com/1.png"},
            {"type": "sticker", "url": "https://example.com/2.png"},
        ]
        
        result = service.bulk_import_resources(resources)
        
        assert result["total"] == 2
        assert result["success"] == 2
        assert result["errors"] == 0
    
    def test_bulk_import_partial_failure(self):
        """Handles partial failures in bulk import"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}]
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = [
            mock_result,
            Exception("DB error"),
        ]
        
        service = ResourceService(mock_supabase)
        
        resources = [
            {"type": "sticker", "url": "https://example.com/1.png"},
            {"type": "sticker", "url": "https://example.com/2.png"},
        ]
        
        result = service.bulk_import_resources(resources)
        
        assert result["success"] == 1
        assert result["errors"] == 1
        assert len(result["error_details"]) == 1


class TestUserAccessScenarios:
    """Test various user access scenarios"""
    
    def test_anonymous_user_access(self):
        """Anonymous user (empty dict) can only access free resources"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "1", "type": "sticker", "allowed_tiers": ["free"]},
            {"id": "2", "type": "sticker", "allowed_tiers": ["starter"]},
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        
        # Use empty dict for anonymous user (None causes issues)
        result = service.get_resources({})  # Anonymous user with no tier
        
        free_item = next(i for i in result["items"] if i["id"] == "1")
        starter_item = next(i for i in result["items"] if i["id"] == "2")
        
        assert free_item["is_accessible"] is True
        assert starter_item["is_accessible"] is False
    
    def test_free_tier_access(self):
        """Free tier user can only access free resources"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "1", "type": "sticker", "allowed_tiers": ["free"]},
            {"id": "2", "type": "sticker", "allowed_tiers": ["starter", "pro"]},
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        free_user = {"tier": "free"}
        
        result = service.get_resources(free_user)
        
        free_item = next(i for i in result["items"] if i["id"] == "1")
        paid_item = next(i for i in result["items"] if i["id"] == "2")
        
        assert free_item["is_accessible"] is True
        assert paid_item["is_accessible"] is False
    
    def test_pro_tier_access(self):
        """Pro tier user with active subscription can access stickers at all tiers"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "1", "type": "sticker", "allowed_tiers": ["free"]},
            {"id": "2", "type": "sticker", "allowed_tiers": ["starter", "pro"]},
            {"id": "3", "type": "sticker", "allowed_tiers": ["pro"]},
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        # Pro user needs active subscription to be considered a member
        pro_user = {"tier": "pro", "subscription_status": "active"}
        
        result = service.get_resources(pro_user)
        
        # Pro user can access all stickers
        for item in result["items"]:
            assert item["is_accessible"] is True
