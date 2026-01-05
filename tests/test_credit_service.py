"""
Credit Service Tests
积分服务测试

Coverage target: 90%+
"""

import pytest
from unittest.mock import patch, MagicMock


class TestCreditServiceGetBalance:
    """Test CreditService.get_balance"""
    
    def test_returns_balances(self):
        """Returns monthly and permanent balances"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        
        service = CreditService(mock_supabase)
        monthly, permanent = service.get_balance("user_123")
        
        assert monthly == 100
        assert permanent == 50
    
    def test_returns_zeros_when_no_data(self):
        """Returns (0, 0) when user not found"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )
        
        service = CreditService(mock_supabase)
        monthly, permanent = service.get_balance("user_123")
        
        assert monthly == 0
        assert permanent == 0
    
    def test_handles_missing_fields(self):
        """Handles missing fields with defaults"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={}  # No credits_monthly or credits_permanent
        )
        
        service = CreditService(mock_supabase)
        monthly, permanent = service.get_balance("user_123")
        
        assert monthly == 0
        assert permanent == 0


class TestCreditServiceGetTotal:
    """Test CreditService.get_total"""
    
    def test_returns_sum_of_balances(self):
        """Returns sum of monthly and permanent"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        
        service = CreditService(mock_supabase)
        total = service.get_total("user_123")
        
        assert total == 150


class TestCreditServiceHasEnough:
    """Test CreditService.has_enough"""
    
    def test_returns_true_when_enough(self):
        """Returns True when user has enough"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        
        service = CreditService(mock_supabase)
        
        assert service.has_enough("user_123", 100) is True
        assert service.has_enough("user_123", 150) is True
    
    def test_returns_false_when_not_enough(self):
        """Returns False when user doesn't have enough"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        
        service = CreditService(mock_supabase)
        
        assert service.has_enough("user_123", 200) is False


class TestCreditServiceDeduct:
    """Test CreditService.deduct"""
    
    def test_success_for_zero_amount(self):
        """Returns success for zero amount"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        service = CreditService(mock_supabase)
        
        success, message = service.deduct("user_123", 0, "generation")
        
        assert success is True
        assert "No credits needed" in message
    
    def test_fails_for_insufficient_credits(self):
        """Fails when insufficient credits"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 10, "credits_permanent": 5}
        )
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 50, "generation")
        
        assert success is False
        assert "Insufficient credits" in message
    
    def test_deducts_monthly_first(self):
        """Deducts from monthly balance first"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]  # Success
        )
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 30, "generation", "Test deduction")
        
        assert success is True
        assert "Deducted 30 credits" in message
        
        # Verify update was called with correct values
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["credits_monthly"] == 70  # 100 - 30
        assert update_call[0][0]["credits_permanent"] == 50  # Unchanged
    
    def test_deducts_from_both_buckets(self):
        """Deducts from both buckets when monthly insufficient"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 20, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]
        )
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 30, "generation")
        
        assert success is True
        
        # Verify: deduct 20 from monthly, 10 from permanent
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["credits_monthly"] == 0  # 20 - 20
        assert update_call[0][0]["credits_permanent"] == 40  # 50 - 10
    
    def test_fails_on_optimistic_lock(self):
        """Fails when balance changed during transaction"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]  # No rows updated (optimistic lock failed)
        )
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 30, "generation")
        
        assert success is False
        assert "retry" in message.lower()
    
    def test_handles_exception(self):
        """Handles database exception"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.side_effect = Exception("DB Error")
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 30, "generation")
        
        assert success is False
        assert "DB Error" in message
    
    def test_uses_permanent_bucket_when_monthly_zero(self):
        """Uses permanent bucket when monthly is zero"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 0, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]
        )
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        
        service = CreditService(mock_supabase)
        service.deduct("user_123", 10, "generation")
        
        # Verify transaction recorded with permanent bucket
        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call[0][0]["bucket"] == "permanent"


class TestCreditServiceAdd:
    """Test CreditService.add"""
    
    def test_fails_for_zero_amount(self):
        """Fails for zero or negative amount"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        service = CreditService(mock_supabase)
        
        success, message = service.add("user_123", 0, "monthly", "bonus")
        
        assert success is False
        assert "positive" in message.lower()
    
    def test_adds_to_monthly_bucket(self):
        """Adds credits to monthly bucket"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        
        service = CreditService(mock_supabase)
        success, message = service.add("user_123", 50, "monthly", "bonus")
        
        assert success is True
        assert "Added 50 credits to monthly" in message
        
        # Verify update
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["credits_monthly"] == 150  # 100 + 50
        assert update_call[0][0]["credits_permanent"] == 50  # Unchanged
    
    def test_adds_to_permanent_bucket(self):
        """Adds credits to permanent bucket"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        
        service = CreditService(mock_supabase)
        success, message = service.add("user_123", 100, "permanent", "purchase")
        
        assert success is True
        assert "permanent" in message
        
        # Verify update
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["credits_monthly"] == 100  # Unchanged
        assert update_call[0][0]["credits_permanent"] == 150  # 50 + 100
    
    def test_handles_exception(self):
        """Handles database exception"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("DB Error")
        
        service = CreditService(mock_supabase)
        success, message = service.add("user_123", 50, "monthly", "bonus")
        
        assert success is False
        assert "DB Error" in message


class TestCreditServiceResetMonthly:
    """Test CreditService.reset_monthly"""
    
    def test_resets_monthly_credits(self):
        """Resets monthly credits to new amount"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 30, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        
        service = CreditService(mock_supabase)
        success, message = service.reset_monthly("user_123", 500)
        
        assert success is True
        assert "500" in message
        
        # Verify transaction recorded with net change
        insert_call = mock_supabase.table.return_value.insert.call_args
        assert insert_call[0][0]["amount"] == 470  # 500 - 30
        assert insert_call[0][0]["type"] == "sub_grant"
    
    def test_handles_exception(self):
        """Handles database exception"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 30, "credits_permanent": 50}
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("DB Error")
        
        service = CreditService(mock_supabase)
        success, message = service.reset_monthly("user_123", 500)
        
        assert success is False


class TestCreditServiceIsFirstGeneration:
    """Test CreditService.is_first_generation"""
    
    def test_returns_true_for_new_user(self):
        """Returns True for user with no generation history"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        service = CreditService(mock_supabase)
        
        assert service.is_first_generation("user_123") is True
    
    def test_returns_false_for_existing_user(self):
        """Returns False for user with generation history"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]
        )
        
        service = CreditService(mock_supabase)
        
        assert service.is_first_generation("user_123") is False


class TestCreditServiceGetGenerationCost:
    """Test CreditService.get_generation_cost"""
    
    @patch('services.credit_service.CREDITS_PER_IMAGE', 5)
    def test_returns_zero_for_first_generation(self):
        """Returns 0 for first generation"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]  # No previous generations
        )
        
        service = CreditService(mock_supabase)
        cost = service.get_generation_cost("user_123")
        
        assert cost == 0
    
    @patch('services.credit_service.CREDITS_PER_IMAGE', 5)
    def test_returns_normal_cost(self):
        """Returns normal cost for subsequent generations"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]  # Has previous generations
        )
        
        service = CreditService(mock_supabase)
        cost = service.get_generation_cost("user_123")
        
        assert cost == 5


class TestCreditServiceGetOcrCost:
    """Test CreditService.get_ocr_cost"""
    
    @patch('services.credit_service.CREDITS_PER_OCR', 5)
    def test_returns_ocr_cost(self):
        """Returns OCR cost from config"""
        from services.credit_service import CreditService
        
        cost = CreditService.get_ocr_cost()
        
        assert cost == 5


class TestDefaultTimezone:
    """Test DEFAULT_TIMEZONE constant"""
    
    def test_default_timezone_is_utc(self):
        """Default timezone is UTC"""
        from services.credit_service import DEFAULT_TIMEZONE
        
        assert DEFAULT_TIMEZONE == "UTC"
