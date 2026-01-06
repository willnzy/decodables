"""
Database Projects Service Tests
services/db/projects.py 模块测试

覆盖目标: 95%+
"""

import pytest
from unittest.mock import MagicMock, patch


class TestGetUserProjects:
    """测试 get_user_projects"""
    
    @patch('services.db.projects.supabase')
    def test_returns_user_projects(self, mock_supabase):
        """返回用户项目列表"""
        from services.db.projects import get_user_projects
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "p1", "title": "Project 1"},
            {"id": "p2", "title": "Project 2"}
        ]
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_user_projects("user_001")
        
        assert len(result) == 2
    
    @patch('services.db.projects.supabase', None)
    def test_returns_empty_when_supabase_not_available(self):
        """Supabase 不可用时返回空列表"""
        from services.db.projects import get_user_projects
        result = get_user_projects("user_001")
        assert result == []


class TestCountUserProjects:
    """测试 count_user_projects"""
    
    @patch('services.db.projects.supabase')
    def test_counts_user_projects(self, mock_supabase):
        """计数用户项目"""
        from services.db.projects import count_user_projects
        
        mock_result = MagicMock()
        mock_result.count = 3
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result
        
        count = count_user_projects("user_001")
        
        assert count == 3
    
    @patch('services.db.projects.supabase', None)
    def test_returns_zero_when_supabase_not_available(self):
        """Supabase 不可用时返回 0"""
        from services.db.projects import count_user_projects
        result = count_user_projects("user_001")
        assert result == 0


class TestGetProjectDetail:
    """测试 get_project_detail"""
    
    @patch('services.db.projects.supabase')
    def test_returns_project_when_owner(self, mock_supabase):
        """拥有者可以访问项目"""
        from services.db.projects import get_project_detail
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001", "title": "Test", "user_id": "user_001"}]
        )
        
        result = get_project_detail("proj_001", "user_001")
        
        assert result is not None
        assert result["id"] == "proj_001"
    
    @patch('services.db.projects.supabase')
    def test_returns_project_when_purchased(self, mock_supabase):
        """购买者可以访问项目"""
        from services.db.projects import get_project_detail
        
        # 项目不属于当前用户
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001", "user_id": "other_user"}]
        )
        
        # 但用户已购买
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "purchase_001"}]
        )
        
        result = get_project_detail("proj_001", "buyer_001")
        
        assert result is not None
    
    @patch('services.db.projects.supabase')
    def test_returns_none_when_not_found(self, mock_supabase):
        """项目不存在返回 None"""
        from services.db.projects import get_project_detail
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = get_project_detail("nonexistent", "user_001")
        
        assert result is None


class TestCreateProject:
    """测试 create_project"""
    
    @patch('services.db.projects.supabase')
    def test_creates_project(self, mock_supabase):
        """创建项目"""
        from services.db.projects import create_project
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new_proj", "title": "New Project"}]
        )
        
        result = create_project("user_001", "New Project")
        
        assert result is not None
        assert result["title"] == "New Project"


class TestDuplicateProject:
    """测试 duplicate_project"""
    
    @patch('services.db.projects.get_project_detail')
    @patch('services.db.projects.supabase')
    def test_duplicates_project(self, mock_supabase, mock_get_detail):
        """复制项目"""
        from services.db.projects import duplicate_project
        
        mock_get_detail.return_value = {"id": "orig", "title": "Original", "canvas_data": {}}
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "copy", "title": "Original (Copy)"}]
        )
        
        result = duplicate_project("orig", "user_001")
        
        assert result is not None


class TestSaveProject:
    """测试 save_project"""
    
    @patch('services.db.projects.supabase')
    def test_saves_project(self, mock_supabase):
        """保存项目"""
        from services.db.projects import save_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001", "title": "Updated"}]
        )
        
        result = save_project("proj_001", "user_001", canvas_data={"pages": []})
        
        assert result is not None


class TestSoftDeleteProject:
    """测试 soft_delete_project"""
    
    @patch('services.db.projects.supabase')
    def test_soft_deletes_project(self, mock_supabase):
        """软删除项目"""
        from services.db.projects import soft_delete_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001", "is_deleted": True}]
        )
        
        result = soft_delete_project("proj_001", "user_001")
        
        assert result is not None


class TestRestoreProject:
    """测试 restore_project"""
    
    @patch('services.db.projects.supabase')
    def test_restores_project(self, mock_supabase):
        """恢复项目"""
        from services.db.projects import restore_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001", "is_deleted": False}]
        )
        
        result = restore_project("proj_001")
        
        assert result is not None


class TestUserRestoreProject:
    """测试 user_restore_project"""
    
    @patch('services.db.projects.supabase')
    def test_user_restores_project(self, mock_supabase):
        """用户恢复自己的项目"""
        from services.db.projects import user_restore_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001", "is_deleted": False}]
        )
        
        result = user_restore_project("proj_001", "user_001")
        
        assert result is not None


class TestGetUserDeletedProjects:
    """测试 get_user_deleted_projects"""
    
    @patch('services.db.projects.supabase')
    def test_returns_deleted_projects(self, mock_supabase):
        """返回已删除项目"""
        from services.db.projects import get_user_deleted_projects
        
        mock_result = MagicMock()
        mock_result.data = [{"id": "p1", "title": "Deleted Project"}]
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_user_deleted_projects("user_001")
        
        assert len(result) == 1


class TestPermanentlyHideProject:
    """测试 permanently_hide_project"""
    
    @patch('services.db.projects.supabase')
    def test_permanently_hides_project(self, mock_supabase):
        """永久隐藏项目"""
        from services.db.projects import permanently_hide_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001", "is_permanently_deleted": True}]
        )
        
        result = permanently_hide_project("proj_001", "user_001")
        
        assert result is not None


class TestUpdateProjectHash:
    """测试 update_project_hash"""
    
    @patch('services.db.projects.supabase')
    def test_updates_project_hash(self, mock_supabase):
        """更新项目哈希"""
        from services.db.projects import update_project_hash
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        # 函数无返回值，验证不抛异常即可
        update_project_hash("proj_001", "new_hash_123")
        
        mock_supabase.table.return_value.update.assert_called()


class TestGetAllProjectsFeed:
    """测试 get_all_projects_feed"""
    
    @patch('services.db.projects.supabase')
    def test_returns_project_feed(self, mock_supabase):
        """返回项目 Feed"""
        from services.db.projects import get_all_projects_feed
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "p1", "title": "Project 1"},
            {"id": "p2", "title": "Project 2"}
        ]
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_all_projects_feed()
        
        assert len(result) == 2


class TestGetDashboardProjects:
    """测试 get_dashboard_projects"""
    
    @patch('services.db.projects.supabase')
    def test_returns_dashboard_projects(self, mock_supabase):
        """返回仪表板项目"""
        from services.db.projects import get_dashboard_projects
        
        # Mock 项目查询
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "p1", "title": "Project 1", "marketplace_listing_id": None},
        ]
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.range.return_value.order.return_value = mock_chain
        
        # Mock 计数查询
        mock_count_result = MagicMock()
        mock_count_result.count = 1
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_count_result
        
        # 正确的参数签名: view_type (不是 view)
        result = get_dashboard_projects("user_001", view_type="all")
        
        assert "items" in result
        assert result["view_type"] == "all"


class TestGetSellerProjectStats:
    """测试 get_seller_project_stats"""
    
    @patch('services.db.projects.supabase')
    def test_returns_seller_stats(self, mock_supabase):
        """返回卖家统计"""
        from services.db.projects import get_seller_project_stats
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "l1", "price": 100, "sales_count": 5},
                {"id": "l2", "price": 50, "sales_count": 10}
            ]
        )
        
        result = get_seller_project_stats("user_001")
        
        assert result["total_listings"] == 2
        assert result["total_sales"] == 15
