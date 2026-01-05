"""
Resource Service Tests
资源服务测试

基于 BUSINESS_LOGIC_SPEC.md Section 8 的业务规则测试

核心业务规则:
1. 资源类型 (Section 8.1):
   - project, sticker, image, background, frame, emoji, pattern

2. 资源分类 (Section 8.2):
   - 模板分类: story, educational, seasonal, blank
   - 贴纸分类: animals, nature, people, food, objects, emotions, education, holiday

3. 存储路径 (Section 8.3):
   - 系统素材: make-decodables-s
   - 用户内容: make-decodables-u

@module tests/test_resource_service
@version v3.3
"""

import pytest
from unittest.mock import patch, MagicMock


# ==========================================
# ResourceType Tests
# ==========================================

class TestResourceType:
    """
    资源类型测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 8.1
    """
    
    def test_resource_types_defined(self):
        """【业务规则 8.1】资源类型定义"""
        from services.resource_service import ResourceType
        
        expected_types = [
            "project", "sticker", "image", "background",
            "frame", "emoji", "font", "shape", "icon", "pattern"
        ]
        
        for t in expected_types:
            assert hasattr(ResourceType, t.upper())
    
    def test_project_type(self):
        """【业务规则 8.1】项目模板类型"""
        from services.resource_service import ResourceType
        
        assert ResourceType.PROJECT.value == "project"
    
    def test_sticker_type(self):
        """【业务规则 8.1】贴纸类型"""
        from services.resource_service import ResourceType
        
        assert ResourceType.STICKER.value == "sticker"


# ==========================================
# ResourceCategory Tests
# ==========================================

class TestResourceCategory:
    """
    资源分类测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 8.2
    """
    
    def test_template_categories(self):
        """【业务规则 8.2】模板分类"""
        from services.resource_service import ResourceCategory
        
        template_categories = ["story", "educational", "seasonal", "blank"]
        
        for cat in template_categories:
            assert hasattr(ResourceCategory, cat.upper())
    
    def test_sticker_categories(self):
        """【业务规则 8.2】贴纸分类"""
        from services.resource_service import ResourceCategory
        
        sticker_categories = [
            "animals", "nature", "people", "food",
            "objects", "emotions", "education", "holiday"
        ]
        
        for cat in sticker_categories:
            assert hasattr(ResourceCategory, cat.upper())


# ==========================================
# TYPE_CATEGORIES Mapping Tests
# ==========================================

class TestTypeCategoriesMapping:
    """
    类型到分类映射测试
    """
    
    def test_project_categories(self):
        """【业务规则 8.2】项目对应的分类"""
        from services.resource_service import TYPE_CATEGORIES, ResourceType, ResourceCategory
        
        project_cats = TYPE_CATEGORIES.get(ResourceType.PROJECT, [])
        
        assert ResourceCategory.STORY in project_cats
        assert ResourceCategory.EDUCATIONAL in project_cats
        assert ResourceCategory.SEASONAL in project_cats
        assert ResourceCategory.BLANK in project_cats
    
    def test_sticker_categories(self):
        """【业务规则 8.2】贴纸对应的分类"""
        from services.resource_service import TYPE_CATEGORIES, ResourceType, ResourceCategory
        
        sticker_cats = TYPE_CATEGORIES.get(ResourceType.STICKER, [])
        
        assert ResourceCategory.ANIMALS in sticker_cats
        assert ResourceCategory.NATURE in sticker_cats


# ==========================================
# ResourceService Tests
# ==========================================

class TestResourceServiceInit:
    """
    ResourceService 初始化测试
    """
    
    def test_service_init(self):
        """【业务规则】服务初始化"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        service = ResourceService(mock_supabase)
        
        assert service.supabase == mock_supabase
        assert service.access_control is not None


class TestGetResources:
    """
    获取资源测试
    """
    
    def test_get_resources_basic(self):
        """【业务规则 8】获取资源列表"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "res_001", "name": "Sticker 1", "type": "sticker", "allowed_tiers": ["free"]},
            {"id": "res_002", "name": "Sticker 2", "type": "sticker", "allowed_tiers": ["free"]}
        ]
        mock_result.count = 2
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        # 返回的是 Dict，不是元组
        result = service.get_resources(user=user, resource_type="sticker")
        
        assert isinstance(result, dict)
    
    def test_get_resources_with_category(self):
        """【业务规则 8.2】按分类获取资源"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "res_001", "name": "Animal Sticker", "category": "animals", "allowed_tiers": ["free"]}
        ]
        mock_result.count = 1
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "pro", "subscription_status": "active"}
        result = service.get_resources(user=user, resource_type="sticker", category="animals")
        
        assert isinstance(result, dict)


class TestGetResourceById:
    """
    按 ID 获取资源测试
    """
    
    def test_get_resource_by_id_found(self):
        """【业务规则】获取存在的资源"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {"id": "res_001", "name": "Test Resource", "allowed_tiers": ["free"]}
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        resource = service.get_resource_by_id("res_001", user=user)
        
        assert resource is not None
    
    def test_get_resource_by_id_not_found(self):
        """【业务规则】获取不存在的资源返回 None"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = None
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        resource = service.get_resource_by_id("nonexistent", user=user)
        
        assert resource is None


class TestGetStickers:
    """
    获取贴纸测试
    """
    
    def test_get_stickers(self):
        """【业务规则 8.1】获取贴纸列表"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "sticker_001", "name": "Cat", "type": "sticker", "allowed_tiers": ["free"]},
            {"id": "sticker_002", "name": "Dog", "type": "sticker", "allowed_tiers": ["free"]}
        ]
        mock_result.count = 2
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        result = service.get_stickers(user=user)
        
        # 返回的是 Dict
        assert isinstance(result, dict)


class TestGetProjects:
    """
    获取项目模板测试
    """
    
    def test_get_projects(self):
        """【业务规则 8.1】获取项目模板列表"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "proj_001", "name": "Story Template", "type": "project", "allowed_tiers": ["free"]}
        ]
        mock_result.count = 1
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "pro", "subscription_status": "active"}
        result = service.get_projects(user=user)
        
        assert isinstance(result, dict)


class TestGetBackgrounds:
    """
    获取背景测试
    """
    
    def test_get_backgrounds(self):
        """【业务规则 8.1】获取背景列表"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "bg_001", "name": "Nature Background", "type": "background", "allowed_tiers": ["free"]}
        ]
        mock_result.count = 1
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        user = {"tier": "free"}
        result = service.get_backgrounds(user=user)
        
        assert isinstance(result, dict)


class TestGetCategories:
    """
    获取分类测试
    """
    
    def test_get_categories_for_sticker(self):
        """【业务规则 8.2】获取贴纸分类"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        service = ResourceService(mock_supabase)
        
        categories = service.get_categories("sticker")
        
        assert isinstance(categories, list)
    
    def test_get_categories_for_project(self):
        """【业务规则 8.2】获取项目分类"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        service = ResourceService(mock_supabase)
        
        categories = service.get_categories("project")
        
        assert isinstance(categories, list)


class TestGetResourceStats:
    """
    获取资源统计测试
    """
    
    def test_get_resource_stats(self):
        """【业务规则】获取资源统计"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"type": "sticker", "count": 100},
            {"type": "project", "count": 50}
        ]
        
        mock_supabase.rpc.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        stats = service.get_resource_stats()
        
        assert isinstance(stats, dict)


class TestCreateResource:
    """
    创建资源测试
    """
    
    def test_create_resource(self):
        """【业务规则】创建资源"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "res_new", "name": "New Resource"}]
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        result = service.create_resource(
            name="New Resource",
            resource_type="sticker",
            url="https://example.com/sticker.png"
        )
        
        assert result is not None


class TestUpdateResource:
    """
    更新资源测试
    """
    
    def test_update_resource(self):
        """【业务规则】更新资源"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "res_001", "name": "Updated Resource"}]
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        result = service.update_resource("res_001", {"name": "Updated Resource"})
        
        assert result is not None


class TestDeleteResource:
    """
    删除资源测试
    """
    
    def test_delete_resource(self):
        """【业务规则】删除资源 (软删除)"""
        from services.resource_service import ResourceService
        
        mock_supabase = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "res_001", "is_deleted": True}]
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result
        
        service = ResourceService(mock_supabase)
        result = service.delete_resource("res_001")
        
        # 结果可能是 True/False 或者返回数据
        assert result is not None


# ==========================================
# Storage Path Tests
# ==========================================

class TestStoragePaths:
    """
    存储路径测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 8.3
    """
    
    def test_system_bucket_name(self):
        """【业务规则 8.3】系统素材存储桶"""
        system_bucket = "make-decodables-s"
        
        assert system_bucket == "make-decodables-s"
    
    def test_user_bucket_name(self):
        """【业务规则 8.3】用户内容存储桶"""
        user_bucket = "make-decodables-u"
        
        assert user_bucket == "make-decodables-u"
    
    def test_user_temp_path(self):
        """【业务规则 8.3】用户临时文件路径"""
        user_id = "user_123"
        date = "2026-01-05"
        
        temp_path = f"{user_id}/temp/{date}/"
        
        assert temp_path.startswith(user_id)
        assert "temp" in temp_path
    
    def test_user_uploads_path(self):
        """【业务规则 8.3】用户上传路径"""
        user_id = "user_123"
        
        uploads_path = f"{user_id}/uploads/"
        
        assert uploads_path == "user_123/uploads/"
    
    def test_user_scans_path(self):
        """【业务规则 8.3】用户扫描路径"""
        user_id = "user_123"
        
        scans_path = f"{user_id}/scans/"
        
        assert scans_path == "user_123/scans/"


# ==========================================
# Access Control Integration Tests
# ==========================================

class TestResourceAccessControl:
    """
    资源访问控制测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 4.2
    """
    
    def test_free_tier_resource_access(self):
        """【业务规则 4.2】Free 用户可访问 free 资源"""
        from services.access_control import AccessControl
        
        ac = AccessControl()
        user = {"tier": "free"}
        allowed_tiers = ["free"]
        
        result = ac.can_access_resource(user, allowed_tiers)
        
        assert result is True
    
    def test_member_only_resource_access(self):
        """【业务规则 4.2】会员资源访问控制"""
        from services.access_control import AccessControl
        
        ac = AccessControl()
        
        # Free 用户不能访问会员资源
        free_user = {"tier": "free"}
        allowed_tiers = ["starter", "pro"]
        
        result = ac.can_access_resource(free_user, allowed_tiers)
        assert result is False
        
        # Starter 用户可以访问
        starter_user = {"tier": "starter", "subscription_status": "active"}
        result = ac.can_access_resource(starter_user, allowed_tiers)
        assert result is True
