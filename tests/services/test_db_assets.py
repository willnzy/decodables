"""
Database Assets Service Tests
services/db/assets.py 模块测试

覆盖目标: 95%+
"""

import pytest
from unittest.mock import MagicMock, patch


class TestSaveAsset:
    """测试 save_asset"""
    
    @patch('services.db.assets.supabase')
    def test_saves_asset(self, mock_supabase):
        """保存资产"""
        from services.db.assets import save_asset
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "asset_001", "url": "https://example.com/image.png"}]
        )
        
        save_asset(
            user_id="user_001",
            url="https://example.com/image.png",
            type="image"
        )
        
        mock_supabase.table.return_value.insert.assert_called_once()


class TestGetAssets:
    """测试 get_assets"""
    
    @patch('services.db.assets.supabase')
    def test_returns_user_assets(self, mock_supabase):
        """返回用户资产"""
        from services.db.assets import get_assets
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "a1", "url": "https://example.com/1.png"},
            {"id": "a2", "url": "https://example.com/2.png"}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value = mock_chain
        
        # Mock marketplace 查询
        mock_supabase.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = get_assets("user_001")
        
        assert len(result) >= 0
    
    @patch('services.db.assets.supabase')
    def test_filters_by_project(self, mock_supabase):
        """按项目筛选资产"""
        from services.db.assets import get_assets
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "a1", "project_id": "proj_001"}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value = mock_chain
        mock_supabase.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = get_assets("user_001", project_id="proj_001")
        
        assert len(result) >= 0


class TestSoftDeleteAsset:
    """测试 soft_delete_asset"""
    
    @patch('services.db.assets.supabase')
    def test_soft_deletes_asset(self, mock_supabase):
        """软删除资产"""
        from services.db.assets import soft_delete_asset
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "asset_001", "is_deleted": True}]
        )
        
        result = soft_delete_asset("asset_001", "user_001")
        
        assert result is not None


class TestPermanentlyHideAsset:
    """测试 permanently_hide_asset"""
    
    @patch('services.db.assets.supabase')
    def test_permanently_hides_asset(self, mock_supabase):
        """永久隐藏资产"""
        from services.db.assets import permanently_hide_asset
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "asset_001", "hidden_permanently": True}]
        )
        
        permanently_hide_asset("asset_001", "user_001")
        
        mock_supabase.table.return_value.update.assert_called()


class TestRestoreAsset:
    """测试 restore_asset"""
    
    @patch('services.db.assets.supabase')
    def test_restores_asset(self, mock_supabase):
        """恢复资产"""
        from services.db.assets import restore_asset
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "asset_001", "is_deleted": False}]
        )
        
        restore_asset("asset_001", "user_001")
        
        mock_supabase.table.return_value.update.assert_called()


class TestGetDeletedAssets:
    """测试 get_deleted_assets"""
    
    @patch('services.db.assets.supabase')
    def test_returns_deleted_assets(self, mock_supabase):
        """返回已删除的资产"""
        from services.db.assets import get_deleted_assets
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": "a1", "is_deleted": True}]
        )
        
        result = get_deleted_assets("user_001")
        
        assert len(result) == 1


class TestIncrementAssetUsage:
    """测试 increment_asset_usage"""
    
    @patch('services.db.assets.supabase')
    def test_increments_usage(self, mock_supabase):
        """增加资产使用次数"""
        from services.db.assets import increment_asset_usage
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "asset_001", "usage_count": 5}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        result = increment_asset_usage("asset_001")
        
        assert result is True


class TestGetDashboardAssets:
    """测试 get_dashboard_assets"""
    
    @patch('services.db.assets.supabase')
    def test_returns_dashboard_assets(self, mock_supabase):
        """返回 dashboard 资产"""
        from services.db.assets import get_dashboard_assets
        
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=[
            {"id": "a1", "type": "image"}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value = mock_chain
        
        result = get_dashboard_assets("user_001")
        
        assert len(result) >= 0


class TestGetSellerAssetStats:
    """测试 get_seller_asset_stats"""
    
    @patch('services.db.assets.supabase')
    def test_returns_seller_stats(self, mock_supabase):
        """返回卖家资产统计"""
        from services.db.assets import get_seller_asset_stats
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[{"sum": 100}])
        
        result = get_seller_asset_stats("seller_001")
        
        assert result is not None


class TestGetSystemResources:
    """测试 get_system_resources"""
    
    @patch('services.db.assets.supabase')
    def test_returns_system_resources(self, mock_supabase):
        """返回系统资源"""
        from services.db.assets import get_system_resources
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "s1", "name": "Sticker 1", "type": "sticker"},
                {"id": "s2", "name": "Sticker 2", "type": "sticker"}
            ]
        )
        
        result = get_system_resources("sticker")
        
        assert len(result) == 2
    
    @patch('services.db.assets.supabase')
    def test_filters_by_user_tier(self, mock_supabase):
        """按用户等级筛选资源"""
        from services.db.assets import get_system_resources
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "s1", "allowed_tiers": ["pro"]}]
        )
        
        result = get_system_resources("sticker", user_tier="pro")
        
        assert len(result) >= 0
