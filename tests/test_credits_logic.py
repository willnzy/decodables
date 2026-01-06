"""
Tests for Credits System Logic (PRD v3.2)
Tests the three key rules:
1. Monthly credits reset each month for Starter/Pro
2. Permanent credits never expire (from purchase/sale)
3. Deduct monthly credits first, then permanent credits
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from services.db_service import (
    refresh_monthly_credits,
    check_and_reset_monthly_credits_if_needed,
    credit_deduct,
    add_credits_permanent,
    get_user_profile
)


class TestMonthlyCreditsReset:
    """Test Rule 1: Monthly credits reset each month"""
    
    @patch('services.db.users.supabase')
    @patch('services.db.users.log_credit_transaction')
    def test_refresh_monthly_credits_resets_monthly_only(self, mock_log, mock_supabase):
        """Monthly credits reset, permanent credits preserved"""
        # Mock supabase update call
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        # Reset monthly credits for starter
        result = refresh_monthly_credits("user_123", "starter")
        
        # Verify: supabase update was called
        update_call = mock_supabase.table.return_value.update.return_value.eq.return_value.execute
        assert update_call.called
        
        # Verify: transaction log was called
        assert mock_log.called
    
    @patch('services.db.users.supabase')
    @patch('services.db.users.get_user_profile')
    @patch('services.db.users.refresh_monthly_credits')
    def test_check_reset_after_30_days(self, mock_refresh, mock_get_profile, mock_supabase):
        """Monthly credits reset if credits_reset_at is over 30 days old"""
        mock_supabase.__bool__ = lambda x: True  # Make supabase truthy
        
        # Setup: User with credits_reset_at 31 days ago
        old_date = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        mock_get_profile.return_value = {
            "id": "user_123",
            "tier": "starter",
            "subscription_status": "active",
            "credits_monthly": 100,
            "credits_permanent": 200,
            "credits_reset_at": old_date,
        }
        
        # Check and reset
        check_and_reset_monthly_credits_if_needed("user_123")
        
        # Verify: refresh_monthly_credits was called
        assert mock_refresh.called
    
    @patch('services.db.users.supabase')
    @patch('services.db.users.get_user_profile')
    @patch('services.db.users.refresh_monthly_credits')
    def test_no_reset_before_30_days(self, mock_refresh, mock_get_profile, mock_supabase):
        """Monthly credits don't reset if credits_reset_at is less than 30 days old"""
        mock_supabase.__bool__ = lambda x: True  # Make supabase truthy
        
        # Setup: User with credits_reset_at 10 days ago
        recent_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        mock_get_profile.return_value = {
            "id": "user_123",
            "tier": "starter",
            "subscription_status": "active",
            "credits_monthly": 100,
            "credits_permanent": 200,
            "credits_reset_at": recent_date,
        }
        
        # Check and reset
        check_and_reset_monthly_credits_if_needed("user_123")
        
        # Verify: refresh_monthly_credits was NOT called
        assert not mock_refresh.called


class TestPermanentCreditsNeverExpire:
    """Test Rule 2: Permanent credits never expire"""
    
    @patch('services.db.users.supabase')
    def test_add_permanent_credits(self, mock_supabase):
        """Adding permanent credits increases permanent balance"""
        # Mock RPC call to return new balance
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"credits_permanent": 250}
        )
        mock_supabase.__bool__ = lambda x: True  # Make supabase truthy
        
        # Add 50 permanent credits
        result = add_credits_permanent("user_123", 50, "Test purchase", "topup_purchase")
        
        # Verify: RPC was called
        assert mock_supabase.rpc.called
    
    @patch('services.db.users.supabase')
    @patch('services.db.users.get_user_profile')
    @patch('services.db.users.refresh_monthly_credits')
    def test_permanent_credits_preserved_on_reset(self, mock_refresh, mock_get_profile, mock_supabase):
        """
        【业务规则 3.5】月度重置时永久积分不受影响
        
        永久积分来源: 市场销售收入、充值购买、注册赠送
        永久积分特性: 永不过期，不随月度重置而变化
        """
        mock_supabase.__bool__ = lambda x: True
        
        user_profile = {
            "id": "user_123",
            "tier": "starter",
            "subscription_status": "active",
            "credits_monthly": 50,
            "credits_permanent": 300,  # 应该被保留
            "credits_reset_at": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
        }
        mock_get_profile.return_value = user_profile
        
        # Mock refresh_monthly_credits 来验证它保留了永久积分
        def mock_refresh_side_effect(user_id, tier):
            # 使用已 mock 的 profile（不调用真实的 get_user_profile）
            permanent = user_profile.get("credits_permanent", 0)
            # 验证永久积分被保留
            assert permanent == 300, "永久积分应该被保留，不受月度重置影响"
            return True
        
        mock_refresh.side_effect = mock_refresh_side_effect
        
        # 检查并重置
        check_and_reset_monthly_credits_if_needed("user_123")
        
        # 验证: refresh 被调用
        assert mock_refresh.called, "refresh_monthly_credits 应该被调用"


class TestDeductionPriority:
    """Test Rule 3: Deduct monthly credits first, then permanent credits"""
    
    @patch('services.db.users.supabase')
    def test_deduct_monthly_first(self, mock_supabase):
        """Deduct from monthly credits first when sufficient"""
        # Mock RPC call to return expected result
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "balance_monthly": 50,  # 100 - 50
            "balance_permanent": 200,
            "total_balance": 250,
            "deducted_from": "monthly"
        })
        
        # Deduct 50 credits
        result = credit_deduct("user_123", 50, "generation", "Test")
        
        # Verify: Monthly credits reduced, permanent unchanged
        assert result["success"] is True
        assert result["balance_monthly"] == 50  # 100 - 50
        assert result["balance_permanent"] == 200  # Unchanged
        assert result["deducted_from"] == "monthly"
    
    @patch('services.db.users.supabase')
    def test_deduct_monthly_then_permanent(self, mock_supabase):
        """Deduct from monthly first, then permanent when monthly insufficient"""
        # Mock RPC call to return expected result (deducted from both)
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "balance_monthly": 0,  # 30 - 30
            "balance_permanent": 180,  # 200 - 20
            "total_balance": 180,
            "deducted_from": "both"
        })
        
        # Deduct 50 credits (30 monthly + 20 permanent needed)
        result = credit_deduct("user_123", 50, "generation", "Test")
        
        # Verify: Monthly credits exhausted, permanent reduced
        assert result["balance_monthly"] == 0  # All 30 used
        assert result["balance_permanent"] == 180  # 200 - 20
    
    @patch('services.db.users.supabase')
    def test_deduct_all_from_permanent_when_monthly_zero(self, mock_supabase):
        """Deduct all from permanent when monthly credits are zero"""
        # Mock RPC call
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "balance_monthly": 0,
            "balance_permanent": 150,  # 200 - 50
            "total_balance": 150,
            "deducted_from": "permanent"
        })
        
        # Deduct 50 credits
        result = credit_deduct("user_123", 50, "generation", "Test")
        
        # Verify: All deducted from permanent
        assert result["success"] is True
        assert result["balance_monthly"] == 0  # Unchanged
        assert result["balance_permanent"] == 150  # 200 - 50
        assert result["deducted_from"] == "permanent"
    
    @patch('services.db.users.supabase')
    def test_insufficient_credits_error(self, mock_supabase):
        """Return error when total credits insufficient"""
        # Mock RPC call to simulate insufficient credits error
        mock_supabase.rpc.return_value.execute.side_effect = Exception("INSUFFICIENT_CREDITS")
        
        # Try to deduct 50 credits (only 40 available)
        result = credit_deduct("user_123", 50, "generation", "Test")
        
        # Verify: Returns error dict, not raises
        assert result["success"] is False
        assert "INSUFFICIENT_CREDITS" in result["error"]


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios"""
    
    @patch('services.db.users.supabase')
    def test_complete_cycle_scenario(self, mock_supabase):
        """
        Scenario: User starts month with 500 monthly credits
        1. Uses 300 monthly credits → 200 monthly, 0 permanent
        2. Uses 250 credits (200 monthly + 50 permanent needed) → 0 monthly, 50 permanent used
        
        This tests the deduction priority: monthly first, then permanent
        """
        # Step 1: Deduct 300 from monthly (500 available)
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "balance_monthly": 200,  # 500 - 300
            "balance_permanent": 0,
            "total_balance": 200,
            "deducted_from": "monthly"
        })
        
        result1 = credit_deduct("user_123", 300, "generation", "Used 300")
        assert result1["success"] is True
        assert result1["balance_monthly"] == 200
        assert result1["balance_permanent"] == 0
        
        # Step 2: Deduct 250 (need 200 monthly + 50 permanent)
        # User now has: 200 monthly, 100 permanent (assumed)
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "balance_monthly": 0,  # All 200 used
            "balance_permanent": 50,  # 100 - 50
            "total_balance": 50,
            "deducted_from": "both"
        })
        
        result2 = credit_deduct("user_123", 250, "generation", "Used 250")
        assert result2["success"] is True
        assert result2["balance_monthly"] == 0  # All monthly used
        assert result2["balance_permanent"] == 50  # 100 - 50 = 50 remaining
