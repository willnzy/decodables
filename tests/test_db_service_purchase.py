"""
Tests for db_service purchase and project-related functions.
按功能设计测试用例，测试驱动开发。
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


class TestExecutePurchaseFull:
    """Test execute_purchase function - full flow"""
    
    def test_purchase_paid_item_success(self):
        """成功购买付费商品"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                with patch('services.db_service.can_access_resource') as mock_access:
                    with patch('services.db_service.check_user_purchase') as mock_check:
                        with patch('services.db_service.credit_deduct') as mock_deduct:
                            with patch('services.db_service.add_credits_permanent') as mock_add:
                                with patch('services.db_service._create_purchased_item_copy') as mock_copy:
                                    # Mock listing lookup - need to mock the chain properly
                                    mock_chain = MagicMock()
                                    mock_chain.eq.return_value = mock_chain
                                    mock_chain.single.return_value = mock_chain
                                    mock_chain.execute.return_value.data = {
                                        "id": "listing-1",
                                        "seller_id": "seller-123",
                                        "price_credits": 100,
                                        "allowed_tiers": ["free", "starter", "pro"],
                                        "title": "Test Item",
                                        "sales_count": 5
                                    }
                                    mock_supabase.table.return_value.select.return_value = mock_chain
                                    
                                    # Mock buyer profile
                                    mock_profile.return_value = {"id": "buyer-123", "tier": "pro"}
                                    mock_access.return_value = True
                                    mock_check.return_value = False  # Not purchased yet
                                    
                                    # Mock purchase record insert and sales update
                                    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
                                    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
                                    
                                    from services.db_service import execute_purchase
                                    result = execute_purchase(buyer_id="buyer-123", listing_id="listing-1")
                                    
                                    assert result["success"] is True
    
    def test_purchase_free_item(self):
        """领取免费商品"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                with patch('services.db_service.can_access_resource') as mock_access:
                    with patch('services.db_service.check_user_purchase') as mock_check:
                        with patch('services.db_service._create_purchased_item_copy') as mock_copy:
                            # Mock free listing
                            mock_chain = MagicMock()
                            mock_chain.eq.return_value = mock_chain
                            mock_chain.single.return_value = mock_chain
                            mock_chain.execute.return_value.data = {
                                "id": "listing-1",
                                "seller_id": "seller-123",
                                "price_credits": 0,  # Free
                                "allowed_tiers": ["free", "starter", "pro"],
                                "title": "Free Item"
                            }
                            mock_supabase.table.return_value.select.return_value = mock_chain
                            
                            mock_profile.return_value = {"id": "buyer-123", "tier": "free"}
                            mock_access.return_value = True
                            mock_check.return_value = False
                            
                            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
                            
                            from services.db_service import execute_purchase
                            result = execute_purchase("buyer-123", "listing-1")
                            
                            assert result["success"] is True
                            assert "Free item claimed" in result["message"]
    
    def test_purchase_already_purchased(self):
        """重复购买应返回已购买提示"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                with patch('services.db_service.can_access_resource') as mock_access:
                    with patch('services.db_service.check_user_purchase') as mock_check:
                        # Mock listing
                        mock_chain = MagicMock()
                        mock_chain.eq.return_value = mock_chain
                        mock_chain.single.return_value = mock_chain
                        mock_chain.execute.return_value.data = {
                            "id": "listing-1",
                            "price_credits": 50,
                            "allowed_tiers": ["free", "starter", "pro"]
                        }
                        mock_supabase.table.return_value.select.return_value = mock_chain
                        
                        mock_profile.return_value = {"id": "buyer-123", "tier": "pro"}
                        mock_access.return_value = True
                        mock_check.return_value = True  # Already purchased
                        
                        from services.db_service import execute_purchase
                        result = execute_purchase("buyer-123", "listing-1")
                        
                        assert result["success"] is True
                        assert "already" in result["message"].lower()
    
    def test_purchase_listing_not_found(self):
        """购买不存在或不可用的商品"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Mock listing not found (query returns None because is_public/is_deleted/status check fails)
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.single.return_value = mock_chain
            mock_chain.execute.return_value.data = None
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import execute_purchase
            result = execute_purchase("buyer-123", "nonexistent")
            
            assert result["success"] is False
            assert "not found" in result["message"].lower() or "not available" in result["message"].lower()
    
    def test_purchase_tier_not_allowed(self):
        """用户等级不符合购买要求"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                with patch('services.db_service.can_access_resource') as mock_access:
                    mock_chain = MagicMock()
                    mock_chain.eq.return_value = mock_chain
                    mock_chain.single.return_value = mock_chain
                    mock_chain.execute.return_value.data = {
                        "id": "listing-1",
                        "allowed_tiers": ["pro"],  # Only pro users
                        "price_credits": 50
                    }
                    mock_supabase.table.return_value.select.return_value = mock_chain
                    
                    mock_profile.return_value = {"id": "buyer-123", "tier": "free"}
                    mock_access.return_value = False  # Access denied
                    
                    from services.db_service import execute_purchase
                    result = execute_purchase("buyer-123", "listing-1")
                    
                    assert result["success"] is False
                    assert "upgrade" in result["message"].lower()
    
    def test_purchase_insufficient_credits(self):
        """积分不足"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                with patch('services.db_service.can_access_resource') as mock_access:
                    with patch('services.db_service.check_user_purchase') as mock_check:
                        with patch('services.db_service.credit_deduct') as mock_deduct:
                            mock_deduct.side_effect = Exception("INSUFFICIENT_CREDITS")
                            
                            mock_chain = MagicMock()
                            mock_chain.eq.return_value = mock_chain
                            mock_chain.single.return_value = mock_chain
                            mock_chain.execute.return_value.data = {
                                "id": "listing-1",
                                "seller_id": "seller-123",
                                "price_credits": 1000,
                                "allowed_tiers": ["free", "starter", "pro"],
                                "title": "Expensive Item"
                            }
                            mock_supabase.table.return_value.select.return_value = mock_chain
                            
                            mock_profile.return_value = {"id": "buyer-123", "tier": "pro"}
                            mock_access.return_value = True
                            mock_check.return_value = False
                            
                            from services.db_service import execute_purchase
                            result = execute_purchase("buyer-123", "listing-1")
                            
                            assert result["success"] is False
                            assert "insufficient" in result["message"].lower()
    
    def test_purchase_buyer_not_found(self):
        """买家不存在"""
        with patch('services.db_service.supabase') as mock_supabase:
            with patch('services.db_service.get_user_profile') as mock_profile:
                mock_chain = MagicMock()
                mock_chain.eq.return_value = mock_chain
                mock_chain.single.return_value = mock_chain
                mock_chain.execute.return_value.data = {
                    "id": "listing-1",
                    "price_credits": 50
                }
                mock_supabase.table.return_value.select.return_value = mock_chain
                
                mock_profile.return_value = None  # Buyer not found
                
                from services.db_service import execute_purchase
                result = execute_purchase("nonexistent-buyer", "listing-1")
                
                assert result["success"] is False
                assert "buyer" in result["message"].lower() or "not found" in result["message"].lower()
    
    def test_purchase_with_idempotency_key(self):
        """幂等性检查 - 重复请求"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Mock idempotency check - already processed
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.execute.return_value.data = [{"id": "purchase-1"}]
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import execute_purchase
            result = execute_purchase("buyer-123", "listing-1", idempotency_key="unique-key-123")
            
            assert result["success"] is True
            assert "already processed" in result["message"].lower()


class TestCreatePurchasedItemCopy:
    """Test _create_purchased_item_copy function"""
    
    def test_copy_project(self):
        """复制购买的项目到买家库"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Mock original project lookup
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "project-1",
                "title": "Original Project",
                "canvas_data": {"pages": []},
                "thumbnail_url": "https://example.com/thumb.jpg"
            }
            # Mock project insert
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            
            from services.db_service import _create_purchased_item_copy
            _create_purchased_item_copy(
                buyer_id="buyer-123",
                listing={
                    "resource_type": "project",
                    "resource_id": "project-1"
                },
                seller_id="seller-123",
                listing_id="listing-1"
            )
            
            # Verify project was inserted
            insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
            assert insert_call["user_id"] == "buyer-123"
            assert insert_call["is_purchased"] is True
            assert insert_call["source_listing_id"] == "listing-1"
    
    def test_copy_asset(self):
        """复制购买的素材到买家库"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Mock original asset lookup
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "asset-1",
                "url": "https://example.com/image.jpg",
                "type": "image",
                "prompt": "A beautiful sunset"
            }
            # Mock asset insert
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
            
            from services.db_service import _create_purchased_item_copy
            _create_purchased_item_copy(
                buyer_id="buyer-123",
                listing={
                    "resource_type": "asset",
                    "resource_id": "asset-1"
                },
                seller_id="seller-123",
                listing_id="listing-1"
            )
            
            # Verify asset was inserted
            insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
            assert insert_call["user_id"] == "buyer-123"
            assert insert_call["is_purchased"] is True


class TestGetUserProjectsMarketplace:
    """Test get_user_projects with marketplace listing info"""
    
    def test_projects_with_marketplace_listings(self):
        """项目包含市场列表信息"""
        with patch('services.db_service.supabase') as mock_supabase:
            # get_user_projects returns a list of items
            
            # First call: projects table query
            mock_projects_result = MagicMock()
            mock_projects_result.data = [
                {"id": "proj-1", "title": "Project 1", "user_id": "user-123"},
                {"id": "proj-2", "title": "Project 2", "user_id": "user-123"}
            ]
            
            # Second call: marketplace_listings query
            mock_listings_result = MagicMock()
            mock_listings_result.data = [
                {
                    "id": "listing-1",
                    "resource_id": "proj-1",
                    "moderation_status": "approved",
                    "is_public": True,
                    "allowed_tiers": ["free"],
                    "price_credits": 50,
                    "sales_count": 10
                }
            ]
            
            # Setup mock chain
            def table_side_effect(table_name):
                mock_table = MagicMock()
                if table_name == "projects":
                    mock_chain = MagicMock()
                    mock_chain.eq.return_value = mock_chain
                    mock_chain.ilike.return_value = mock_chain
                    mock_chain.order.return_value = mock_chain
                    mock_chain.range.return_value = mock_chain
                    mock_chain.execute.return_value = mock_projects_result
                    mock_table.select.return_value = mock_chain
                elif table_name == "marketplace_listings":
                    mock_chain = MagicMock()
                    mock_chain.eq.return_value = mock_chain
                    mock_chain.in_.return_value = mock_chain
                    mock_chain.execute.return_value = mock_listings_result
                    mock_table.select.return_value = mock_chain
                return mock_table
            
            mock_supabase.table.side_effect = table_side_effect
            
            from services.db_service import get_user_projects
            items = get_user_projects("user-123")
            
            # Returns a list
            assert isinstance(items, list)
            assert len(items) == 2
    
    def test_projects_returns_list(self):
        """get_user_projects 返回列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": "proj-1", "title": "Project"}]
            
            def table_side_effect(table_name):
                mock_table = MagicMock()
                mock_chain = MagicMock()
                mock_chain.eq.return_value = mock_chain
                mock_chain.ilike.return_value = mock_chain
                mock_chain.order.return_value = mock_chain
                mock_chain.range.return_value = mock_chain
                mock_chain.in_.return_value = mock_chain
                
                if table_name == "projects":
                    mock_chain.execute.return_value = mock_result
                else:
                    mock_chain.execute.return_value.data = []
                
                mock_table.select.return_value = mock_chain
                return mock_table
            
            mock_supabase.table.side_effect = table_side_effect
            
            from services.db_service import get_user_projects
            result = get_user_projects("user-123")
            
            # Should return a list
            assert isinstance(result, list)
            assert len(result) == 1


class TestCountUserProjectsSearch:
    """Test count_user_projects with search functionality"""
    
    def test_count_with_search(self):
        """带搜索条件的项目计数"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.ilike.return_value = mock_chain
            mock_chain.execute.return_value.data = [{"id": "p1"}, {"id": "p2"}]
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            from services.db_service import count_user_projects
            count = count_user_projects("user-123", search="magic")
            
            assert count == 2
            mock_chain.ilike.assert_called()
    
    def test_count_error_handling(self):
        """计数查询失败返回0"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.side_effect = Exception("DB error")
            
            from services.db_service import count_user_projects
            count = count_user_projects("user-123")
            
            assert count == 0


class TestDuplicateProjectError:
    """Test duplicate_project error handling"""
    
    def test_duplicate_not_found(self):
        """复制不存在的项目"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None
            
            from services.db_service import duplicate_project
            with pytest.raises(Exception, match="not found"):
                duplicate_project("nonexistent", "user-123")


class TestGetDashboardProjectsMarketplace:
    """Test get_dashboard_projects with marketplace info"""
    
    def test_dashboard_with_listings(self):
        """仪表板项目包含市场列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Mock projects
            mock_projects = MagicMock()
            mock_projects.data = [
                {"id": "proj-1", "title": "My Project", "thumbnail_url": "thumb.jpg"}
            ]
            mock_projects.count = 1
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.range.return_value = mock_chain
            mock_chain.execute.return_value = mock_projects
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            # Mock listings
            mock_listings = MagicMock()
            mock_listings.data = [
                {"resource_id": "proj-1", "moderation_status": "approved"}
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.eq.return_value.execute.return_value = mock_listings
            
            from services.db_service import get_dashboard_projects
            result = get_dashboard_projects("user-123", page=1, limit=20)
            
            assert "items" in result or isinstance(result, tuple)


class TestGetDashboardAssetsMarketplace:
    """Test get_dashboard_assets with marketplace info"""
    
    def test_dashboard_assets_with_listings(self):
        """仪表板素材包含市场列表"""
        with patch('services.db_service.supabase') as mock_supabase:
            # Mock assets
            mock_assets = MagicMock()
            mock_assets.data = [
                {"id": "asset-1", "url": "image.jpg", "type": "image"}
            ]
            mock_assets.count = 1
            
            mock_chain = MagicMock()
            mock_chain.eq.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.range.return_value = mock_chain
            mock_chain.execute.return_value = mock_assets
            mock_supabase.table.return_value.select.return_value = mock_chain
            
            # Mock listings
            mock_listings = MagicMock()
            mock_listings.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.eq.return_value.execute.return_value = mock_listings
            
            from services.db_service import get_dashboard_assets
            result = get_dashboard_assets("user-123", page=1, limit=20)
            
            assert "items" in result or isinstance(result, tuple)


class TestGetAssetsFilters:
    """Test get_assets with various filters"""
    
    def test_get_assets_by_project(self):
        """按项目获取素材"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                {"id": "a1", "project_id": "proj-1"}
            ]
            
            from services.db_service import get_assets
            result = get_assets("user-123", project_id="proj-1")
            
            assert len(result) == 1
    
    def test_get_assets_all_for_user(self):
        """获取用户所有素材"""
        with patch('services.db_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                {"id": "a1"}, {"id": "a2"}
            ]
            
            from services.db_service import get_assets
            result = get_assets("user-123")
            
            assert len(result) == 2
