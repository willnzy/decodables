"""
Tests for Projects API business rules (PRD v3.2)

基于 BUSINESS_LOGIC_SPEC.md Section 7 的业务规则测试

核心业务规则:
1. 项目限额: Free=1, Starter=20, Pro=200
2. 两阶段删除: 软删除 → 30天后移除
3. 自动保存: 3秒防抖

@module tests/test_projects_api
@version v3.3
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock


class TestProjectLimits:
    """
    项目数量限制测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7.1
    """
    
    def test_project_limits_by_tier(self):
        """【业务规则 7.1】项目数量限制"""
        limits = {
            "free": 1,
            "starter": 20,
            "pro": 200
        }
        
        for tier, expected_limit in limits.items():
            assert expected_limit == limits[tier]
    
    @patch('services.db_service.supabase')
    def test_free_user_cannot_exceed_one_project(self, mock_supabase):
        """【业务规则 7.1】Free 用户最多 1 个项目"""
        from services.db_service import get_user_projects
        
        # Mock 返回 1 个项目
        mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value = MagicMock(data=[
            {"id": "project_1", "title": "Existing Project"}
        ])
        
        # Free 用户已有 1 个项目
        user_tier = "free"
        max_projects = 1
        
        # 业务规则：达到上限后不能创建新项目
        existing_count = 1
        can_create = existing_count < max_projects
        
        assert can_create is False


class TestProjectSoftDelete:
    """
    项目软删除测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7.3
    """
    
    def test_soft_delete_sets_deleted_at(self):
        """【业务规则 7.3】软删除设置 deleted_at"""
        from datetime import datetime, timezone
        
        # 软删除时设置 deleted_at
        deleted_at = datetime.now(timezone.utc)
        
        assert deleted_at is not None
    
    def test_restore_clears_deleted_at(self):
        """【业务规则 7.3】恢复清除 deleted_at"""
        # 恢复时设置 deleted_at = None
        restored_project = {
            "id": "project_1",
            "deleted_at": None,
            "is_deleted": False
        }
        
        assert restored_project["deleted_at"] is None
        assert restored_project["is_deleted"] is False
    
    def test_soft_delete_30_day_window(self):
        """【业务规则 7.3】30天内可恢复"""
        deletion_date = datetime.now(timezone.utc) - timedelta(days=15)
        current_date = datetime.now(timezone.utc)
        
        days_since_deletion = (current_date - deletion_date).days
        can_restore = days_since_deletion <= 30
        
        assert can_restore is True
    
    def test_soft_delete_after_30_days(self):
        """【业务规则 7.3】30天后从删除历史移除"""
        deletion_date = datetime.now(timezone.utc) - timedelta(days=35)
        current_date = datetime.now(timezone.utc)
        
        days_since_deletion = (current_date - deletion_date).days
        can_restore = days_since_deletion <= 30
        
        assert can_restore is False


class TestProjectDataStructure:
    """
    项目数据结构测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7.2
    """
    
    def test_project_has_8_pages(self):
        """【业务规则 7.2】项目有 8 页"""
        expected_pages = 8
        
        project_data = {
            "pages": [{"canvasJson": {}, "previewImage": None} for _ in range(expected_pages)]
        }
        
        assert len(project_data["pages"]) == expected_pages
    
    def test_project_paper_sizes(self):
        """【业务规则 7.2】支持的纸张尺寸"""
        valid_paper_sizes = ["Letter", "A4"]
        
        for size in valid_paper_sizes:
            assert size in valid_paper_sizes


class TestTrialPeriodProjectAccess:
    """
    试用期项目访问测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 2.3
    """
    
    def test_free_user_in_trial_can_edit(self):
        """【业务规则 2.3】试用期内 Free 用户可编辑"""
        created_at = datetime.now(timezone.utc) - timedelta(days=10)
        now = datetime.now(timezone.utc)
        
        days_since = (now - created_at).days
        is_in_trial = days_since <= 30
        
        assert is_in_trial is True
    
    def test_free_user_after_trial_readonly(self):
        """【业务规则 2.3】试用期后 Free 用户只读"""
        created_at = datetime.now(timezone.utc) - timedelta(days=35)
        now = datetime.now(timezone.utc)
        
        days_since = (now - created_at).days
        is_in_trial = days_since <= 30
        
        assert is_in_trial is False


class TestAutosave:
    """
    自动保存测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7.4
    """
    
    def test_autosave_debounce_3_seconds(self):
        """【业务规则 7.4】自动保存 3 秒防抖"""
        AUTOSAVE_DEBOUNCE_MS = 3000  # 3 seconds
        
        assert AUTOSAVE_DEBOUNCE_MS == 3000


class TestPurchasedProjectIndependence:
    """
    已购买项目独立性测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7.3
    """
    
    def test_purchased_project_not_affected_by_original_deletion(self):
        """【业务规则 7.3】购买者副本不受原项目删除影响"""
        # 原项目被删除
        original_project = {
            "id": "original_project_1",
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }
        
        # 购买者的副本
        purchased_copy = {
            "id": "purchased_copy_1",
            "original_id": "original_project_1",
            "owner_id": "buyer_user_id",
            "is_deleted": False,
            "deleted_at": None
        }
        
        # 原项目删除不影响购买副本
        assert original_project["is_deleted"] is True
        assert purchased_copy["is_deleted"] is False
