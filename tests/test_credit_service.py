"""
Credit Service Tests
积分服务测试

v3.22: Updated tests for atomic RPC-based operations

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
    """
    Test CreditService.deduct
    
    v3.22: Updated to test RPC-based atomic deduction
    """
    
    def test_success_for_zero_amount(self):
        """Returns success for zero amount"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        service = CreditService(mock_supabase)
        
        success, message = service.deduct("user_123", 0, "generation")
        
        assert success is True
        assert "No credits needed" in message
    
    def test_deduct_via_rpc_success(self):
        """Deducts credits via RPC call"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        # Mock RPC response for successful deduction
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "deducted": 30,
                "balance_monthly": 70,
                "balance_permanent": 50,
                "bucket": "monthly"
            }
        )
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 30, "generation", "Test deduction")
        
        assert success is True
        assert "Deducted 30 credits" in message
        
        # Verify RPC was called with correct params
        mock_supabase.rpc.assert_called_once_with("deduct_credits_atomic", {
            "p_user_id": "user_123",
            "p_amount": 30,
            "p_tx_type": "generation",
            "p_description": "Test deduction",
            "p_timezone": "UTC",
            "p_idempotency_key": None
        })
    
    def test_fails_for_insufficient_credits(self):
        """Fails when insufficient credits"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        # Mock RPC response for insufficient credits
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": False,
                "error": "Insufficient credits",
                "error_code": "CREDITS_INSUFFICIENT",
                "available": 15,
                "required": 50
            }
        )
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 50, "generation")
        
        assert success is False
        assert "Insufficient credits" in message
    
    def test_fails_for_user_not_found(self):
        """Fails when user not found"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": False,
                "error": "User not found",
                "error_code": "USER_NOT_FOUND"
            }
        )
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 30, "generation")
        
        assert success is False
        assert "User not found" in message
    
    def test_handles_idempotent_response(self):
        """Handles idempotent response (already processed)"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "idempotent": True,
                "message": "Already processed",
                "balance_monthly": 70,
                "balance_permanent": 50
            }
        )
        
        service = CreditService(mock_supabase)
        success, message = service.deduct(
            "user_123", 30, "generation", 
            idempotency_key="unique-key-123"
        )
        
        assert success is True
        assert "Deducted 30 credits" in message
    
    def test_handles_rpc_exception(self):
        """Handles RPC exception"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.side_effect = Exception("RPC Error")
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 30, "generation")
        
        assert success is False
        assert "RPC Error" in message
    
    def test_handles_empty_rpc_response(self):
        """Handles empty RPC response"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=None)
        
        service = CreditService(mock_supabase)
        success, message = service.deduct("user_123", 30, "generation")
        
        assert success is False
        assert "no response" in message.lower()


class TestCreditServiceDeductWithDetails:
    """Test CreditService.deduct_with_details"""
    
    def test_returns_detailed_result(self):
        """Returns detailed result including balances"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "deducted": 30,
                "balance_monthly": 70,
                "balance_permanent": 50,
                "bucket": "monthly"
            }
        )
        
        service = CreditService(mock_supabase)
        result = service.deduct_with_details("user_123", 30, "generation")
        
        assert result["success"] is True
        assert result["balance_monthly"] == 70
        assert result["balance_permanent"] == 50
        assert result["deducted"] == 30
        assert result["bucket"] == "monthly"
    
    def test_returns_current_balance_for_zero_amount(self):
        """Returns current balance for zero amount"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"credits_monthly": 100, "credits_permanent": 50}
        )
        
        service = CreditService(mock_supabase)
        result = service.deduct_with_details("user_123", 0, "generation")
        
        assert result["success"] is True
        assert result["balance_monthly"] == 100
        assert result["balance_permanent"] == 50


class TestCreditServiceAdd:
    """
    Test CreditService.add
    
    v3.22: Updated to test RPC-based atomic addition
    """
    
    def test_fails_for_zero_amount(self):
        """Fails for zero or negative amount"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        service = CreditService(mock_supabase)
        
        success, message = service.add("user_123", 0, "monthly", "bonus")
        
        assert success is False
        assert "positive" in message.lower()
    
    def test_add_via_rpc_success(self):
        """Adds credits via RPC call"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "added": 50,
                "bucket": "monthly",
                "balance_monthly": 150,
                "balance_permanent": 50
            }
        )
        
        service = CreditService(mock_supabase)
        success, message = service.add("user_123", 50, "monthly", "bonus")
        
        assert success is True
        assert "Added 50 credits to monthly" in message
        
        # Verify RPC was called
        mock_supabase.rpc.assert_called_once_with("add_credits_atomic", {
            "p_user_id": "user_123",
            "p_amount": 50,
            "p_bucket": "monthly",
            "p_tx_type": "bonus",
            "p_description": None,
            "p_timezone": "UTC",
            "p_idempotency_key": None
        })
    
    def test_adds_to_permanent_bucket(self):
        """Adds credits to permanent bucket"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "added": 100,
                "bucket": "permanent",
                "balance_monthly": 100,
                "balance_permanent": 150
            }
        )
        
        service = CreditService(mock_supabase)
        success, message = service.add("user_123", 100, "permanent", "purchase")
        
        assert success is True
        assert "permanent" in message
    
    def test_handles_rpc_exception(self):
        """Handles RPC exception"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.side_effect = Exception("RPC Error")
        
        service = CreditService(mock_supabase)
        success, message = service.add("user_123", 50, "monthly", "bonus")
        
        assert success is False
        assert "RPC Error" in message
    
    def test_handles_idempotent_response(self):
        """Handles idempotent response"""
        from services.credit_service import CreditService
        
        mock_supabase = MagicMock()
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "idempotent": True,
                "message": "Already processed"
            }
        )
        
        service = CreditService(mock_supabase)
        success, message = service.add(
            "user_123", 50, "monthly", "bonus",
            idempotency_key="unique-key-456"
        )
        
        assert success is True


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


class TestCreditServiceGetGenerationCost:
    """
    Test CreditService.get_generation_cost
    
    【业务规则 - Business Spec v3.3 Section 3.3】
    - AI 图像生成: 5 积分/张
    - 无特殊规则（已移除首次免费）
    """
    
    @patch('services.credit_service.CREDITS_PER_IMAGE', 5)
    def test_generation_cost_is_always_5_credits(self):
        """【业务规则】每次 AI 图像生成固定消耗 5 积分"""
        from services.credit_service import CreditService
        
        # 静态方法，无需实例化或传入 user_id
        cost = CreditService.get_generation_cost()
        assert cost == 5
    
    @patch('services.credit_service.CREDITS_PER_IMAGE', 5)
    def test_generation_cost_no_first_free(self):
        """【业务规则验证】不存在"首次免费"，任何用户都是 5 积分"""
        from services.credit_service import CreditService
        
        # 业务规则 v3.3: AI 图像生成固定 5 积分/张，无首次免费
        # get_generation_cost 现在是静态方法，与用户无关
        cost = CreditService.get_generation_cost()
        
        assert cost == 5, f"业务规则: AI 图像生成固定 5 积分/张。当前返回 {cost}"
    
    @patch('services.credit_service.CREDITS_PER_IMAGE', 10)
    def test_generation_cost_uses_config(self):
        """【实现细节】成本从配置常量读取"""
        from services.credit_service import CreditService
        
        # 验证成本来自 CREDITS_PER_IMAGE 配置
        cost = CreditService.get_generation_cost()
        assert cost == 10


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
