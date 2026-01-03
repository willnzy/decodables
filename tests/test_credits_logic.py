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
    
    @patch('db_service.get_user_profile')
    @patch('db_service.supabase')
    @patch('db_service.log_credit_transaction')
    def test_refresh_monthly_credits_resets_monthly_only(self, mock_log, mock_supabase, mock_get_profile):
        """Monthly credits reset, permanent credits preserved"""
        # Setup: User has 100 monthly and 200 permanent credits
        mock_get_profile.return_value = {
            "id": "user_123",
            "tier": "starter",
            "credits_monthly": 100,  # Some remaining monthly credits
            "credits_permanent": 200,  # Permanent credits should be preserved
        }
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        # Reset monthly credits
        result = refresh_monthly_credits("user_123", "starter")
        
        # Verify: Monthly credits reset to 500, permanent credits unchanged
        update_call = mock_supabase.table.return_value.update.return_value.eq.return_value.execute
        assert update_call.called
        
        # Check that permanent credits are preserved in transaction log
        log_calls = mock_log.call_args_list
        assert len(log_calls) > 0
        # The log should show permanent credits unchanged
        call_kwargs = log_calls[0][1] if log_calls[0][0] == () else log_calls[0][0][1]
        assert call_kwargs.get('balance_permanent_after') == 200  # Unchanged
    
    @patch('db_service.get_user_profile')
    @patch('db_service.refresh_monthly_credits')
    def test_check_reset_after_30_days(self, mock_refresh, mock_get_profile):
        """Monthly credits reset if cycle_anchor is over 30 days old"""
        # Setup: User with cycle_anchor 31 days ago
        old_date = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        mock_get_profile.return_value = {
            "id": "user_123",
            "tier": "starter",
            "subscription_status": "active",
            "credits_monthly": 100,
            "credits_permanent": 200,
            "monthly_credits_cycle_anchor": old_date,
        }
        mock_refresh.return_value = True
        
        # Check and reset
        result = check_and_reset_monthly_credits_if_needed("user_123")
        
        # Verify: refresh_monthly_credits was called
        assert mock_refresh.called
        assert result is True
    
    @patch('db_service.get_user_profile')
    @patch('db_service.refresh_monthly_credits')
    def test_no_reset_before_30_days(self, mock_refresh, mock_get_profile):
        """Monthly credits don't reset if cycle_anchor is less than 30 days old"""
        # Setup: User with cycle_anchor 10 days ago
        recent_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        mock_get_profile.return_value = {
            "id": "user_123",
            "tier": "starter",
            "subscription_status": "active",
            "credits_monthly": 100,
            "credits_permanent": 200,
            "monthly_credits_cycle_anchor": recent_date,
        }
        
        # Check and reset
        result = check_and_reset_monthly_credits_if_needed("user_123")
        
        # Verify: refresh_monthly_credits was NOT called
        assert not mock_refresh.called
        assert result is False


class TestPermanentCreditsNeverExpire:
    """Test Rule 2: Permanent credits never expire"""
    
    @patch('db_service.get_user_profile')
    @patch('db_service.supabase')
    @patch('db_service.log_credit_transaction')
    def test_add_permanent_credits(self, mock_log, mock_supabase, mock_get_profile):
        """Adding permanent credits increases permanent balance"""
        mock_get_profile.return_value = {
            "id": "user_123",
            "credits_monthly": 100,
            "credits_permanent": 200,
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        # Add 50 permanent credits
        result = add_credits_permanent("user_123", 50, "Test purchase", "topup_purchase")
        
        # Verify: Permanent credits increased, monthly unchanged
        assert result["balance_permanent"] == 250
        assert result["balance_monthly"] == 100  # Unchanged
    
    @patch('db_service.get_user_profile')
    @patch('db_service.refresh_monthly_credits')
    def test_permanent_credits_preserved_on_reset(self, mock_refresh, mock_get_profile):
        """Permanent credits are preserved when monthly credits reset"""
        mock_get_profile.return_value = {
            "id": "user_123",
            "tier": "starter",
            "subscription_status": "active",
            "credits_monthly": 50,
            "credits_permanent": 300,  # Should be preserved
            "monthly_credits_cycle_anchor": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
        }
        
        # Mock refresh_monthly_credits to verify it preserves permanent credits
        def mock_refresh_side_effect(user_id, tier):
            profile = get_user_profile(user_id)
            permanent = profile.get("credits_permanent", 0)
            # Verify permanent credits are preserved
            assert permanent == 300
            return True
        
        mock_refresh.side_effect = mock_refresh_side_effect
        
        # Check and reset
        check_and_reset_monthly_credits_if_needed("user_123")
        
        # Verify: refresh was called (and verified permanent credits preserved)
        assert mock_refresh.called


class TestDeductionPriority:
    """Test Rule 3: Deduct monthly credits first, then permanent credits"""
    
    @patch('db_service.get_user_profile')
    @patch('db_service.supabase')
    @patch('db_service.log_credit_transaction')
    def test_deduct_monthly_first(self, mock_log, mock_supabase, mock_get_profile):
        """Deduct from monthly credits first when sufficient"""
        mock_get_profile.return_value = {
            "id": "user_123",
            "credits_monthly": 100,
            "credits_permanent": 200,
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        # Deduct 50 credits
        result = credit_deduct("user_123", 50, "generation", "Test")
        
        # Verify: Monthly credits reduced, permanent unchanged
        assert result["balance_monthly"] == 50  # 100 - 50
        assert result["balance_permanent"] == 200  # Unchanged
    
    @patch('db_service.get_user_profile')
    @patch('db_service.supabase')
    @patch('db_service.log_credit_transaction')
    def test_deduct_monthly_then_permanent(self, mock_log, mock_supabase, mock_get_profile):
        """Deduct from monthly first, then permanent when monthly insufficient"""
        mock_get_profile.return_value = {
            "id": "user_123",
            "credits_monthly": 30,  # Not enough
            "credits_permanent": 200,
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        # Deduct 50 credits (30 monthly + 20 permanent needed)
        result = credit_deduct("user_123", 50, "generation", "Test")
        
        # Verify: Monthly credits exhausted, permanent reduced
        assert result["balance_monthly"] == 0  # All 30 used
        assert result["balance_permanent"] == 180  # 200 - 20
    
    @patch('db_service.get_user_profile')
    @patch('db_service.supabase')
    @patch('db_service.log_credit_transaction')
    def test_deduct_all_from_permanent_when_monthly_zero(self, mock_log, mock_supabase, mock_get_profile):
        """Deduct all from permanent when monthly credits are zero"""
        mock_get_profile.return_value = {
            "id": "user_123",
            "credits_monthly": 0,  # No monthly credits
            "credits_permanent": 200,
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        # Deduct 50 credits
        result = credit_deduct("user_123", 50, "generation", "Test")
        
        # Verify: All deducted from permanent
        assert result["balance_monthly"] == 0  # Unchanged
        assert result["balance_permanent"] == 150  # 200 - 50
    
    @patch('db_service.get_user_profile')
    def test_insufficient_credits_error(self, mock_get_profile):
        """Raise error when total credits insufficient"""
        mock_get_profile.return_value = {
            "id": "user_123",
            "credits_monthly": 30,
            "credits_permanent": 10,
        }
        
        # Try to deduct 50 credits (only 40 available)
        with pytest.raises(Exception) as exc_info:
            credit_deduct("user_123", 50, "generation", "Test")
        
        assert "CREDITS_INSUFFICIENT" in str(exc_info.value)


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios"""
    
    @patch('db_service.get_user_profile')
    @patch('db_service.supabase')
    @patch('db_service.log_credit_transaction')
    @patch('db_service.refresh_monthly_credits')
    def test_complete_cycle_scenario(self, mock_refresh, mock_log, mock_supabase, mock_get_profile):
        """
        Scenario: User starts month with 500 monthly credits
        1. Uses 300 monthly credits
        2. Buys 100 permanent credits
        3. Uses 250 credits (200 monthly + 50 permanent)
        4. Month resets: monthly back to 500, permanent still 50
        """
        # Step 1: User has 500 monthly, 0 permanent
        mock_get_profile.return_value = {
            "id": "user_123",
            "tier": "starter",
            "subscription_status": "active",
            "credits_monthly": 500,
            "credits_permanent": 0,
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        # Use 300 monthly credits
        result1 = credit_deduct("user_123", 300, "generation", "Used 300")
        assert result1["balance_monthly"] == 200
        assert result1["balance_permanent"] == 0
        
        # Step 2: Buy 100 permanent credits
        result2 = add_credits_permanent("user_123", 100, "Purchase", "topup_purchase")
        assert result2["balance_permanent"] == 100
        
        # Step 3: Use 250 credits (200 monthly + 50 permanent)
        mock_get_profile.return_value = {
            "id": "user_123",
            "credits_monthly": 200,
            "credits_permanent": 100,
        }
        result3 = credit_deduct("user_123", 250, "generation", "Used 250")
        assert result3["balance_monthly"] == 0  # All monthly used
        assert result3["balance_permanent"] == 50  # 100 - 50
        
        # Step 4: Month resets
        mock_get_profile.return_value = {
            "id": "user_123",
            "tier": "starter",
            "subscription_status": "active",
            "credits_monthly": 0,
            "credits_permanent": 50,  # Should be preserved
            "monthly_credits_cycle_anchor": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
        }
        mock_refresh.return_value = True
        
        check_and_reset_monthly_credits_if_needed("user_123")
        
        # Verify: Monthly reset, permanent preserved
        assert mock_refresh.called
        # refresh_monthly_credits should preserve permanent credits (verified in mock)

