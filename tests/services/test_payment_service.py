"""
Payment Service Tests
基于 BUSINESS_LOGIC_SPEC.md Section 13 的业务规则测试

测试目的: 验证支付服务业务逻辑是否符合规格要求

核心业务规则:
1. Stripe Price Map (Section 13.2):
   - starter: 订阅
   - pro: 订阅
   - credits_100: 一次性支付

2. 订阅取消规则 (Section 13.4):
   - 不退费取消: 当月继续有效
   - 立即取消+退费: 立即降级

@module tests/test_payment_service
@version v3.3
@last_updated 2026-01-05
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import sys

# Mock stripe module before importing payment_service
stripe_mock = MagicMock()
stripe_mock.error = MagicMock()
stripe_mock.error.StripeError = type('StripeError', (Exception,), {})
sys.modules['stripe'] = stripe_mock

# Now import payment_service
from domains.billing import payment_service


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def reset_stripe_mock():
    """Reset stripe mock between tests"""
    stripe_mock.reset_mock()
    stripe_mock.checkout.Session.create.reset_mock()
    stripe_mock.billing_portal.Session.create.reset_mock()
    stripe_mock.Subscription.list.reset_mock()
    stripe_mock.Subscription.cancel.reset_mock()
    stripe_mock.Subscription.modify.reset_mock()
    stripe_mock.Coupon.create.reset_mock()
    stripe_mock.Refund.create.reset_mock()
    stripe_mock.PaymentIntent.list.reset_mock()
    stripe_mock.PaymentIntent.retrieve.reset_mock()
    stripe_mock.Webhook.construct_event.reset_mock()
    yield


# ==========================================
# Checkout Session 测试
# ==========================================

class TestCreateCheckoutSession:
    """
    测试 Checkout Session 创建
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 13.2
    """
    
    def test_invalid_plan_type_raises_exception(self, reset_stripe_mock):
        """【业务规则】无效的 plan_type 抛出异常"""
        with pytest.raises(Exception) as exc_info:
            payment_service.create_checkout_session("user_001", "invalid_plan")
        
        assert "Invalid plan type" in str(exc_info.value)
    
    def test_subscription_mode_for_starter(self, reset_stripe_mock):
        """【业务规则 13.2】Starter 计划使用 subscription 模式"""
        # Setup
        payment_service.PRICE_MAP["starter"] = "price_starter_123"
        stripe_mock.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/...")
        
        result = payment_service.create_checkout_session("user_001", "starter")
        
        # Verify subscription mode
        call_kwargs = stripe_mock.checkout.Session.create.call_args[1]
        assert call_kwargs["mode"] == "subscription"
    
    def test_subscription_mode_for_pro(self, reset_stripe_mock):
        """【业务规则 13.2】Pro 计划使用 subscription 模式"""
        # Setup
        payment_service.PRICE_MAP["pro"] = "price_pro_456"
        stripe_mock.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/...")
        
        result = payment_service.create_checkout_session("user_001", "pro")
        
        # Verify subscription mode
        call_kwargs = stripe_mock.checkout.Session.create.call_args[1]
        assert call_kwargs["mode"] == "subscription"
    
    def test_payment_mode_for_credits(self, reset_stripe_mock):
        """【业务规则 13.2】积分购买使用 payment 模式"""
        # Setup
        payment_service.PRICE_MAP["credits_100"] = "price_credits_789"
        stripe_mock.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/...")
        
        result = payment_service.create_checkout_session("user_001", "credits_100")
        
        # Verify payment mode
        call_kwargs = stripe_mock.checkout.Session.create.call_args[1]
        assert call_kwargs["mode"] == "payment"
    
    def test_discount_coupon_created_when_percent_provided(self, reset_stripe_mock):
        """【业务规则】提供折扣百分比时创建优惠券"""
        # Setup
        payment_service.PRICE_MAP["credits_100"] = "price_credits_789"
        stripe_mock.Coupon.create.return_value = MagicMock(id="coupon_123")
        stripe_mock.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/...")
        
        result = payment_service.create_checkout_session("user_001", "credits_100", discount_percent=20)
        
        # Verify coupon was created
        stripe_mock.Coupon.create.assert_called_once()
        coupon_call_kwargs = stripe_mock.Coupon.create.call_args[1]
        assert coupon_call_kwargs["percent_off"] == 20
        
        # Verify discount applied to session
        session_call_kwargs = stripe_mock.checkout.Session.create.call_args[1]
        assert "discounts" in session_call_kwargs
    
    def test_promotion_codes_allowed_when_no_discount(self, reset_stripe_mock):
        """【业务规则】无折扣时允许促销码"""
        # Setup
        payment_service.PRICE_MAP["credits_100"] = "price_credits_789"
        stripe_mock.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/...")
        
        result = payment_service.create_checkout_session("user_001", "credits_100", discount_percent=0)
        
        # Verify allow_promotion_codes
        call_kwargs = stripe_mock.checkout.Session.create.call_args[1]
        assert call_kwargs.get("allow_promotion_codes") is True
    
    def test_metadata_contains_user_id_and_plan(self, reset_stripe_mock):
        """【业务规则】元数据包含 user_id 和 plan_type"""
        # Setup
        payment_service.PRICE_MAP["starter"] = "price_starter_123"
        stripe_mock.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/...")
        
        result = payment_service.create_checkout_session("user_001", "starter")
        
        # Verify metadata
        call_kwargs = stripe_mock.checkout.Session.create.call_args[1]
        assert call_kwargs["metadata"]["user_id"] == "user_001"
        assert call_kwargs["metadata"]["plan_type"] == "starter"
    
    def test_stripe_error_returns_none(self, reset_stripe_mock):
        """【业务规则】Stripe 错误返回 None"""
        # Setup
        payment_service.PRICE_MAP["starter"] = "price_starter_123"
        stripe_mock.checkout.Session.create.side_effect = Exception("Stripe error")
        
        result = payment_service.create_checkout_session("user_001", "starter")
        
        assert result is None


# ==========================================
# Portal Session 测试
# ==========================================

class TestCreatePortalSession:
    """
    测试 Billing Portal Session 创建
    """
    
    def test_no_customer_id_raises_exception(self, reset_stripe_mock):
        """【业务规则】无 customer_id 抛出异常"""
        with pytest.raises(Exception) as exc_info:
            payment_service.create_portal_session("user_001", None)
        
        assert "No Stripe Customer ID" in str(exc_info.value)
    
    def test_portal_session_created_successfully(self, reset_stripe_mock):
        """【业务规则】成功创建 Portal Session"""
        stripe_mock.billing_portal.Session.create.return_value = MagicMock(url="https://billing.stripe.com/...")
        
        result = payment_service.create_portal_session("user_001", "cus_123")
        
        assert result == "https://billing.stripe.com/..."
        stripe_mock.billing_portal.Session.create.assert_called_once_with(
            customer="cus_123",
            return_url=f'{payment_service.FRONTEND_URL}/dashboard'
        )
    
    def test_portal_error_returns_none(self, reset_stripe_mock):
        """【业务规则】Portal 错误返回 None"""
        stripe_mock.billing_portal.Session.create.side_effect = Exception("Portal error")
        
        result = payment_service.create_portal_session("user_001", "cus_123")
        
        assert result is None


# ==========================================
# 订阅状态测试
# ==========================================

class TestGetSubscriptionStatus:
    """
    测试订阅状态查询
    """
    
    def test_active_starter_subscription(self, reset_stripe_mock):
        """【业务规则】正确识别 Starter 订阅"""
        payment_service.PRICE_MAP["starter"] = "price_starter_123"
        
        mock_sub = MagicMock()
        mock_sub.status = "active"
        mock_sub.current_period_end = 1704067200
        mock_sub.__getitem__ = lambda self, key: {
            "items": {"data": [{"price": {"id": "price_starter_123"}}]}
        }[key]
        
        stripe_mock.Subscription.list.return_value = MagicMock(data=[mock_sub])
        
        result = payment_service.get_subscription_status("cus_123")
        
        assert result["status"] == "active"
        assert result["tier"] == "starter"
    
    def test_active_pro_subscription(self, reset_stripe_mock):
        """【业务规则】正确识别 Pro 订阅"""
        payment_service.PRICE_MAP["pro"] = "price_pro_456"
        
        mock_sub = MagicMock()
        mock_sub.status = "active"
        mock_sub.current_period_end = 1704067200
        mock_sub.__getitem__ = lambda self, key: {
            "items": {"data": [{"price": {"id": "price_pro_456"}}]}
        }[key]
        
        stripe_mock.Subscription.list.return_value = MagicMock(data=[mock_sub])
        
        result = payment_service.get_subscription_status("cus_123")
        
        assert result["status"] == "active"
        assert result["tier"] == "pro"
    
    def test_no_subscription_returns_free(self, reset_stripe_mock):
        """【业务规则】无订阅返回 free"""
        stripe_mock.Subscription.list.return_value = MagicMock(data=[])
        
        result = payment_service.get_subscription_status("cus_123")
        
        assert result["status"] == "inactive"
        assert result["tier"] == "free"
    
    def test_subscription_error_returns_none(self, reset_stripe_mock):
        """【业务规则】查询错误返回 None"""
        stripe_mock.Subscription.list.side_effect = Exception("Stripe error")
        
        result = payment_service.get_subscription_status("cus_123")
        
        assert result is None


# ==========================================
# 订阅取消测试 (Section 13.4)
# ==========================================

class TestCancelSubscription:
    """
    测试订阅取消
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 13.4
    """
    
    def test_cancel_at_period_end(self, reset_stripe_mock):
        """【业务规则 13.4】不退费取消: 设置 cancel_at_period_end=True"""
        mock_subscription = MagicMock()
        stripe_mock.Subscription.modify.return_value = mock_subscription
        
        result = payment_service.cancel_subscription("sub_123", immediate=False)
        
        assert result["success"] is True
        stripe_mock.Subscription.modify.assert_called_once_with(
            "sub_123",
            cancel_at_period_end=True
        )
        stripe_mock.Subscription.cancel.assert_not_called()
    
    def test_cancel_immediately(self, reset_stripe_mock):
        """【业务规则 13.4】立即取消: 调用 Subscription.cancel"""
        mock_subscription = MagicMock()
        stripe_mock.Subscription.cancel.return_value = mock_subscription
        
        result = payment_service.cancel_subscription("sub_123", immediate=True)
        
        assert result["success"] is True
        stripe_mock.Subscription.cancel.assert_called_once_with("sub_123")
        stripe_mock.Subscription.modify.assert_not_called()
    
    def test_cancel_error_returns_failure(self, reset_stripe_mock):
        """【业务规则】取消错误返回失败"""
        stripe_mock.Subscription.modify.side_effect = stripe_mock.error.StripeError("Error")
        
        result = payment_service.cancel_subscription("sub_123", immediate=False)
        
        assert result["success"] is False
        assert result["error"] is not None


# ==========================================
# 退款测试
# ==========================================

class TestCreateRefund:
    """
    测试退款功能
    """
    
    def test_full_refund(self, reset_stripe_mock):
        """【业务规则】全额退款"""
        mock_refund = MagicMock()
        stripe_mock.Refund.create.return_value = mock_refund
        
        result = payment_service.create_refund("pi_123")
        
        assert result["success"] is True
        call_kwargs = stripe_mock.Refund.create.call_args[1]
        assert call_kwargs["payment_intent"] == "pi_123"
        assert "amount" not in call_kwargs  # 全额退款不指定金额
    
    def test_partial_refund(self, reset_stripe_mock):
        """【业务规则】部分退款"""
        mock_refund = MagicMock()
        stripe_mock.Refund.create.return_value = mock_refund
        
        result = payment_service.create_refund("pi_123", amount_cents=500)
        
        assert result["success"] is True
        call_kwargs = stripe_mock.Refund.create.call_args[1]
        assert call_kwargs["amount"] == 500
    
    def test_refund_with_reason(self, reset_stripe_mock):
        """【业务规则】带原因的退款"""
        mock_refund = MagicMock()
        stripe_mock.Refund.create.return_value = mock_refund
        
        result = payment_service.create_refund("pi_123", reason="duplicate")
        
        call_kwargs = stripe_mock.Refund.create.call_args[1]
        assert call_kwargs["reason"] == "duplicate"
    
    def test_refund_error_returns_failure(self, reset_stripe_mock):
        """【业务规则】退款错误返回失败"""
        stripe_mock.Refund.create.side_effect = stripe_mock.error.StripeError("Error")
        
        result = payment_service.create_refund("pi_123")
        
        assert result["success"] is False
        assert result["error"] is not None


# ==========================================
# Webhook 验证测试
# ==========================================

class TestConstructEvent:
    """
    测试 Webhook 事件验证
    """
    
    def test_valid_webhook_event(self, reset_stripe_mock):
        """【业务规则】有效的 webhook 事件被正确解析"""
        mock_event = MagicMock()
        stripe_mock.Webhook.construct_event.return_value = mock_event
        
        result = payment_service.construct_event(b"payload", "sig_header")
        
        assert result == mock_event
    
    def test_invalid_signature_raises_exception(self, reset_stripe_mock):
        """【业务规则】无效签名抛出异常"""
        stripe_mock.Webhook.construct_event.side_effect = Exception("Invalid signature")
        
        with pytest.raises(Exception) as exc_info:
            payment_service.construct_event(b"payload", "invalid_sig")
        
        assert "Webhook Error" in str(exc_info.value)


# ==========================================
# Admin 功能测试
# ==========================================

class TestAdminFunctions:
    """
    测试管理员功能
    """
    
    def test_get_customer_subscriptions(self, reset_stripe_mock):
        """【业务规则】获取用户所有订阅"""
        mock_subs = [MagicMock(), MagicMock()]
        
        with patch('services.payment_service.stripe.Subscription.list') as mock_list:
            mock_list.return_value = MagicMock(data=mock_subs)
            
            result = payment_service.get_customer_subscriptions("cus_123")
            
            assert result == mock_subs
            mock_list.assert_called_once_with(
                customer="cus_123",
                limit=10
            )
    
    def test_get_customer_subscriptions_error_returns_empty(self, reset_stripe_mock):
        """【业务规则】订阅查询错误返回空列表"""
        stripe_mock.Subscription.list.side_effect = Exception("Error")
        
        result = payment_service.get_customer_subscriptions("cus_123")
        
        assert result == []
    
    def test_get_customer_payments(self, reset_stripe_mock):
        """【业务规则】只返回成功的支付"""
        mock_succeeded = MagicMock(status='succeeded')
        mock_pending = MagicMock(status='requires_payment_method')
        stripe_mock.PaymentIntent.list.return_value = MagicMock(data=[mock_succeeded, mock_pending])
        
        result = payment_service.get_customer_payments("cus_123")
        
        assert len(result) == 1
        assert result[0].status == 'succeeded'
    
    def test_get_payment_intent_details(self, reset_stripe_mock):
        """【业务规则】获取支付详情"""
        mock_pi = MagicMock(id="pi_123")
        stripe_mock.PaymentIntent.retrieve.return_value = mock_pi
        
        result = payment_service.get_payment_intent_details("pi_123")
        
        assert result.id == "pi_123"
    
    def test_get_payment_intent_error_returns_none(self, reset_stripe_mock):
        """【业务规则】支付详情查询错误返回 None"""
        stripe_mock.PaymentIntent.retrieve.side_effect = stripe_mock.error.StripeError("Error")
        
        result = payment_service.get_payment_intent_details("pi_123")
        
        assert result is None
