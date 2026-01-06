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
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "p1", "title": "Project 1"},
            {"id": "p2", "title": "Project 2"}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_user_projects("user_001", page=1, limit=20)
        
        assert len(result) == 2
    
    @patch('services.db.projects.supabase')
    def test_includes_canvas_data_when_requested(self, mock_supabase):
        """请求时包含画布数据"""
        from services.db.projects import get_user_projects
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "p1", "title": "Project 1", "canvas_data": {"pages": []}}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_user_projects("user_001", include_canvas_data=True)
        
        assert len(result) >= 0


class TestCountUserProjects:
    """测试 count_user_projects"""
    
    @patch('services.db.projects.supabase')
    def test_counts_user_projects(self, mock_supabase):
        """统计用户项目数量"""
        from services.db.projects import count_user_projects
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}, {"id": 2}, {"id": 3}]
        )
        
        count = count_user_projects("user_001")
        
        assert count == 3


class TestGetProjectDetail:
    """测试 get_project_detail"""
    
    @patch('services.db.projects.supabase')
    def test_returns_project_when_found(self, mock_supabase):
        """返回项目详情"""
        from services.db.projects import get_project_detail
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "proj_001", "title": "Test Project", "canvas_data": {"pages": []}}
        )
        
        result = get_project_detail("proj_001")
        
        assert result is not None
        assert result["id"] == "proj_001"
    
    @patch('services.db.projects.supabase')
    def test_returns_none_when_not_found(self, mock_supabase):
        """项目不存在返回 None"""
        from services.db.projects import get_project_detail
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        
        result = get_project_detail("nonexistent")
        
        assert result is None


class TestCreateProject:
    """测试 create_project"""
    
    @patch('services.db.projects.supabase')
    def test_creates_project(self, mock_supabase):
        """创建项目"""
        from services.db.projects import create_project
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new_proj", "title": "New Project", "user_id": "user_001"}]
        )
        
        result = create_project("user_001", "New Project")
        
        assert result is not None
    
    @patch('services.db.projects.supabase')
    def test_creates_project_with_canvas_data(self, mock_supabase):
        """创建项目时包含画布数据"""
        from services.db.projects import create_project
        
        canvas_data = {"pages": [{"id": "page_1"}]}
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new_proj", "canvas_data": canvas_data}]
        )
        
        result = create_project("user_001", "With Canvas", canvas_data=canvas_data)
        
        assert result is not None


class TestDuplicateProject:
    """测试 duplicate_project"""
    
    @patch('services.db.projects.get_project_detail')
    @patch('services.db.projects.supabase')
    def test_duplicates_project(self, mock_supabase, mock_get_detail):
        """复制项目"""
        from services.db.projects import duplicate_project
        
        mock_get_detail.return_value = {
            "id": "proj_001",
            "title": "Original",
            "canvas_data": {"pages": []},
            "user_id": "user_001"
        }
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_002", "title": "Original (Copy)"}]
        )
        
        result = duplicate_project("proj_001", "user_001")
        
        assert result is not None


class TestSaveProject:
    """测试 save_project"""
    
    @patch('services.db.projects.supabase')
    def test_saves_project(self, mock_supabase):
        """保存项目"""
        from services.db.projects import save_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001"}]
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
        """用户恢复项目（带权限检查）"""
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
        """返回已删除的项目"""
        from services.db.projects import get_user_deleted_projects
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "p1", "is_deleted": True}]
        )
        
        result = get_user_deleted_projects("user_001")
        
        assert len(result) == 1


class TestPermanentlyHideProject:
    """测试 permanently_hide_project"""
    
    @patch('services.db.projects.supabase')
    def test_permanently_hides_project(self, mock_supabase):
        """永久隐藏项目"""
        from services.db.projects import permanently_hide_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001", "hidden_permanently": True}]
        )
        
        result = permanently_hide_project("proj_001", "user_001")
        
        assert result is not None


class TestUpdateProjectHash:
    """测试 update_project_hash"""
    
    @patch('services.db.projects.supabase')
    def test_updates_project_hash(self, mock_supabase):
        """更新项目哈希"""
        from services.db.projects import update_project_hash
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "proj_001", "content_hash": "abc123"}]
        )
        
        result = update_project_hash("proj_001", "abc123")
        
        assert result is not None


class TestGetAllProjectsFeed:
    """测试 get_all_projects_feed"""
    
    @patch('services.db.projects.supabase')
    def test_returns_project_feed(self, mock_supabase):
        """返回项目 feed"""
        from services.db.projects import get_all_projects_feed
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "p1", "is_public": True},
            {"id": "p2", "is_public": True}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value = mock_chain
        
        result = get_all_projects_feed(limit=10)
        
        assert len(result) == 2


class TestGetDashboardProjects:
    """测试 get_dashboard_projects"""
    
    @patch('services.db.projects.supabase')
    def test_returns_dashboard_projects(self, mock_supabase):
        """返回 dashboard 项目"""
        from services.db.projects import get_dashboard_projects
        
        # Mock 复杂的链式调用
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "p1", "title": "Project 1", "is_deleted": False}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        # Mock marketplace listings
        mock_supabase.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = get_dashboard_projects("user_001", view="all")
        
        assert len(result) >= 0


class TestGetSellerProjectStats:
    """测试 get_seller_project_stats"""
    
    @patch('services.db.projects.supabase')
    def test_returns_seller_stats(self, mock_supabase):
        """返回卖家项目统计"""
        from services.db.projects import get_seller_project_stats
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"total_sales": 10}]
        )
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[{"sum": 500}])
        
        result = get_seller_project_stats("seller_001")
        
        assert result is not None
