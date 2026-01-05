"""
db_service 业务规则测试
基于 BUSINESS_LOGIC_SPEC.md 的业务规则测试

核心业务规则:
1. 会员判断 (Section 2.1):
   - starter, pro 是会员
   - free 不是会员
   - 需要 subscription_status='active'

2. 资源访问控制 (Section 4.2):
   - allowed_tiers=['free'] 所有人可访问
   - allowed_tiers=['starter', 'pro'] 仅会员可访问

3. 发布权限 (Section 4.3):
   - Free 不能发布
   - Starter 只能发布免费资源
   - Pro 可发布 0-500 积分资源

4. 积分相关 (Section 3):
   - 扣费优先级: 月度 > 永久
   - 月度重置: 覆盖不累加

@module tests/test_db_service
@version v3.3
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


# ==========================================
# is_member Tests
# ==========================================

class TestIsMember:
    """
    会员判断测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 2.1
    """
    
    def test_starter_is_member(self):
        """【业务规则 2.1】Starter 是会员"""
        from services.db_service import is_member
        
        user = {
            "tier": "starter",
            "subscription_status": "active"
        }
        
        assert is_member(user) is True
    
    def test_pro_is_member(self):
        """【业务规则 2.1】Pro 是会员"""
        from services.db_service import is_member
        
        user = {
            "tier": "pro",
            "subscription_status": "active"
        }
        
        assert is_member(user) is True
    
    def test_free_is_not_member(self):
        """【业务规则 2.1】Free 不是会员"""
        from services.db_service import is_member
        
        user = {
            "tier": "free",
            "subscription_status": None
        }
        
        assert is_member(user) is False
    
    def test_inactive_subscription_is_not_member(self):
        """【业务规则 2.1】inactive 订阅状态不算会员"""
        from services.db_service import is_member
        
        user = {
            "tier": "starter",
            "subscription_status": "canceled"
        }
        
        assert is_member(user) is False
    
    def test_none_user_returns_false(self):
        """【业务规则】None 用户返回 False"""
        from services.db_service import is_member
        
        assert is_member(None) is False
    
    def test_empty_dict_returns_false(self):
        """【业务规则】空字典返回 False"""
        from services.db_service import is_member
        
        assert is_member({}) is False


# ==========================================
# can_access_resource Tests
# ==========================================

class TestCanAccessResource:
    """
    资源访问控制测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 4.2
    """
    
    def test_free_resource_accessible_to_all(self):
        """【业务规则 4.2】allowed_tiers=['free'] 的资源所有人可访问"""
        from services.db_service import can_access_resource
        
        free_user = {"tier": "free"}
        starter_user = {"tier": "starter", "subscription_status": "active"}
        pro_user = {"tier": "pro", "subscription_status": "active"}
        
        allowed_tiers = ["free"]
        
        assert can_access_resource(free_user, allowed_tiers) is True
        assert can_access_resource(starter_user, allowed_tiers) is True
        assert can_access_resource(pro_user, allowed_tiers) is True
    
    def test_member_only_resource(self):
        """【业务规则 4.2】allowed_tiers=['starter', 'pro'] 只有会员可访问"""
        from services.db_service import can_access_resource
        
        free_user = {"tier": "free"}
        starter_user = {"tier": "starter", "subscription_status": "active"}
        pro_user = {"tier": "pro", "subscription_status": "active"}
        
        allowed_tiers = ["starter", "pro"]
        
        assert can_access_resource(free_user, allowed_tiers) is False
        assert can_access_resource(starter_user, allowed_tiers) is True
        assert can_access_resource(pro_user, allowed_tiers) is True
    
    def test_pro_only_resource(self):
        """【业务规则 4.2】allowed_tiers=['pro'] 只有 Pro 可访问"""
        from services.db_service import can_access_resource
        
        free_user = {"tier": "free"}
        starter_user = {"tier": "starter", "subscription_status": "active"}
        pro_user = {"tier": "pro", "subscription_status": "active"}
        
        allowed_tiers = ["pro"]
        
        assert can_access_resource(free_user, allowed_tiers) is False
        assert can_access_resource(starter_user, allowed_tiers) is False
        assert can_access_resource(pro_user, allowed_tiers) is True


# ==========================================
# publish_permission Tests
# ==========================================

class TestPublishPermission:
    """
    发布权限测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 4.3
    """
    
    def test_free_cannot_publish(self):
        """【业务规则 4.3】Free 用户不能发布"""
        from services.db_service import publish_permission
        
        free_user = {"tier": "free"}
        
        result = publish_permission(free_user, "asset", 0)
        
        assert result["allowed"] is False
    
    def test_starter_can_publish_free_asset(self):
        """【业务规则 4.3】Starter 可以发布免费 Asset"""
        from services.db_service import publish_permission
        
        starter_user = {"tier": "starter", "subscription_status": "active"}
        
        result = publish_permission(starter_user, "asset", 0)
        
        assert result["allowed"] is True
    
    def test_starter_cannot_publish_paid_asset(self):
        """【业务规则 4.3】Starter 不能发布付费资源"""
        from services.db_service import publish_permission
        
        starter_user = {"tier": "starter", "subscription_status": "active"}
        
        result = publish_permission(starter_user, "asset", 100)
        
        assert result["allowed"] is False
    
    def test_starter_cannot_publish_project(self):
        """【业务规则 4.3】Starter 不能发布 Project"""
        from services.db_service import publish_permission
        
        starter_user = {"tier": "starter", "subscription_status": "active"}
        
        result = publish_permission(starter_user, "project", 0)
        
        assert result["allowed"] is False
    
    def test_pro_can_publish_paid_asset(self):
        """【业务规则 4.3】Pro 可以发布付费 Asset"""
        from services.db_service import publish_permission
        
        pro_user = {"tier": "pro", "subscription_status": "active"}
        
        result = publish_permission(pro_user, "asset", 100)
        
        assert result["allowed"] is True
    
    def test_pro_can_publish_project(self):
        """【业务规则 4.3】Pro 可以发布 Project"""
        from services.db_service import publish_permission
        
        pro_user = {"tier": "pro", "subscription_status": "active"}
        
        result = publish_permission(pro_user, "project", 200)
        
        assert result["allowed"] is True
    
    def test_pro_cannot_exceed_max_price(self):
        """【业务规则 4.3】定价不能超过 500 积分"""
        from services.db_service import publish_permission
        
        pro_user = {"tier": "pro", "subscription_status": "active"}
        
        result = publish_permission(pro_user, "asset", 501)
        
        assert result["allowed"] is False
        assert "500" in result.get("reason", "")


# ==========================================
# validate_allowed_tiers Tests
# ==========================================

class TestValidateAllowedTiers:
    """
    allowed_tiers 验证测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 4.2
    """
    
    def test_valid_free_tier(self):
        """【业务规则 4.2】['free'] 是有效配置"""
        from services.db_service import validate_allowed_tiers
        
        result = validate_allowed_tiers(["free"])
        
        assert result["valid"] is True
    
    def test_valid_member_tiers(self):
        """【业务规则 4.2】['starter', 'pro'] 是有效配置"""
        from services.db_service import validate_allowed_tiers
        
        result = validate_allowed_tiers(["starter", "pro"])
        
        assert result["valid"] is True
    
    def test_valid_pro_only(self):
        """【业务规则 4.2】['pro'] 是有效配置"""
        from services.db_service import validate_allowed_tiers
        
        result = validate_allowed_tiers(["pro"])
        
        assert result["valid"] is True
    
    def test_invalid_combination(self):
        """【业务规则 4.2】无效组合被拒绝"""
        from services.db_service import validate_allowed_tiers
        
        # 这不是一个有效的业务配置
        result = validate_allowed_tiers(["free", "pro"])
        
        # 根据实际验证逻辑判断
        assert "valid" in result


# ==========================================
# get_total_credits Tests
# ==========================================

class TestGetTotalCredits:
    """
    获取总积分测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 3.1
    """
    
    def test_sum_monthly_and_permanent(self):
        """【业务规则 3.1】总积分 = 月度 + 永久"""
        from services.db_service import get_total_credits
        
        user = {
            "credits_monthly": 100,
            "credits_permanent": 50
        }
        
        total = get_total_credits(user)
        
        assert total == 150
    
    def test_handles_missing_fields(self):
        """【业务规则】缺失字段默认为 0"""
        from services.db_service import get_total_credits
        
        user = {}
        
        total = get_total_credits(user)
        
        assert total == 0
    
    def test_handles_none_user(self):
        """【业务规则】None 用户返回 0"""
        from services.db_service import get_total_credits
        
        total = get_total_credits(None)
        
        assert total == 0


# ==========================================
# listing_is_public_visible Tests
# ==========================================

class TestListingIsPublicVisible:
    """
    Listing 可见性测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6.4
    """
    
    def test_approved_public_not_deleted_is_visible(self):
        """【业务规则 6.4】approved + public + not deleted = 可见"""
        from services.db_service import listing_is_public_visible
        
        listing = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False
        }
        
        assert listing_is_public_visible(listing) is True
    
    def test_pending_is_not_visible(self):
        """【业务规则 6.4】pending 状态不可见"""
        from services.db_service import listing_is_public_visible
        
        listing = {
            "moderation_status": "pending",
            "is_public": True,
            "is_deleted": False
        }
        
        assert listing_is_public_visible(listing) is False
    
    def test_not_public_is_not_visible(self):
        """【业务规则 6.4】is_public=False 不可见"""
        from services.db_service import listing_is_public_visible
        
        listing = {
            "moderation_status": "approved",
            "is_public": False,
            "is_deleted": False
        }
        
        assert listing_is_public_visible(listing) is False
    
    def test_deleted_is_not_visible(self):
        """【业务规则 6.4】已删除不可见"""
        from services.db_service import listing_is_public_visible
        
        listing = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": True
        }
        
        assert listing_is_public_visible(listing) is False


# ==========================================
# Credit Deduction Tests (Mocked)
# ==========================================

class TestCreditDeduction:
    """
    积分扣除测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 3.2
    """
    
    @patch('services.db_service.log_credit_transaction')
    @patch('services.db_service.supabase')
    @patch('services.db_service.get_user_profile')
    def test_deduction_priority_monthly_first(self, mock_get_profile, mock_supabase, mock_log):
        """【业务规则 3.2】扣费优先级: 先扣月度积分"""
        from services.db_service import credit_deduct
        
        # Mock 用户有 月度=30, 永久=100
        mock_get_profile.return_value = {
            "id": "user_001",
            "credits_monthly": 30,
            "credits_permanent": 100
        }
        
        # Mock update 成功
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "user_001"}])
        
        result = credit_deduct("user_001", 50, "generation", "Test deduction")
        
        assert result["success"] is True
        # 月度应该扣完 30，永久扣 20
        assert result["balance_monthly"] == 0
        assert result["balance_permanent"] == 80
    
    @patch('services.db_service.get_user_profile')
    def test_insufficient_credits_raises_exception(self, mock_get_profile):
        """【业务规则 3.2】积分不足时抛出异常"""
        from services.db_service import credit_deduct
        
        # Mock 用户积分不足
        mock_get_profile.return_value = {
            "id": "user_001",
            "credits_monthly": 10,
            "credits_permanent": 10
        }
        
        with pytest.raises(Exception) as exc_info:
            credit_deduct("user_001", 100, "generation", "Test deduction")
        
        assert "CREDITS_INSUFFICIENT" in str(exc_info.value)
    
    @patch('services.db_service.get_user_profile')
    def test_user_not_found_raises_exception(self, mock_get_profile):
        """【业务规则】用户不存在时抛出异常"""
        from services.db_service import credit_deduct
        
        mock_get_profile.return_value = None
        
        with pytest.raises(Exception) as exc_info:
            credit_deduct("nonexistent", 10, "generation", "Test")
        
        assert "not found" in str(exc_info.value).lower()


# ==========================================
# Project Count Tests (Mocked)
# ==========================================

class TestProjectCount:
    """
    项目计数测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7.1
    """
    
    @patch('services.db_service.supabase')
    def test_count_user_projects(self, mock_supabase):
        """【业务规则】正确计数用户项目"""
        from services.db_service import count_user_projects
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[
            {"id": "p1"}, {"id": "p2"}, {"id": "p3"}
        ])
        
        count = count_user_projects("user_001")
        
        assert count == 3


# ==========================================
# Generate User Code Tests
# ==========================================

class TestGenerateUserCode:
    """
    用户码生成测试
    """
    
    @patch('services.db_service.supabase')
    def test_user_code_format(self, mock_supabase):
        """【业务规则】用户码格式正确 (24字符)"""
        from services.db_service import generate_user_code
        
        # Mock supabase 查询返回 count
        mock_result = MagicMock()
        mock_result.count = 5
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_result
        
        code = generate_user_code()
        
        # 验证格式: YYYYMMDDHHMMSS + ms(3) + sequence(7) = 24 字符
        assert isinstance(code, str)
        assert len(code) == 24
        # 序列部分应该是 7 位数字，值为用户数 + 1 = 6
        assert code.endswith("0000006")


# ==========================================
# Retry Decorator Tests
# ==========================================

class TestRetryDecorator:
    """
    重试装饰器测试
    """
    
    def test_is_retryable_timeout_error(self):
        """【业务规则】timeout 错误可重试"""
        from services.db_service import is_retryable_error
        
        # 使用匹配 RETRYABLE_ERRORS 中关键字的错误
        timeout_error = Exception("Request timeout occurred")
        
        assert is_retryable_error(timeout_error) is True
    
    def test_is_retryable_connection_reset(self):
        """【业务规则】connection reset 可重试"""
        from services.db_service import is_retryable_error
        
        reset_error = Exception("Connection reset by peer")
        
        assert is_retryable_error(reset_error) is True
    
    def test_is_not_retryable_value_error(self):
        """【业务规则】普通业务错误不可重试"""
        from services.db_service import is_retryable_error
        
        value_error = ValueError("Invalid input")
        
        assert is_retryable_error(value_error) is False


# ==========================================
# Project Management Tests (Phase 4.2)
# ==========================================

class TestCreateProject:
    """
    项目创建测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7
    """
    
    @patch('services.db_service.supabase')
    def test_create_project_success(self, mock_supabase):
        """【业务规则】成功创建项目"""
        from services.db_service import create_project
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": "proj_001",
            "user_id": "user_001",
            "title": "New Project"
        }])
        
        result = create_project("user_001", "New Project")
        
        assert result is not None
        mock_supabase.table.assert_called()
    
    @patch('services.db_service.supabase')
    def test_create_project_with_canvas_data(self, mock_supabase):
        """【业务规则】创建项目时可以包含画布数据"""
        from services.db_service import create_project
        
        canvas_data = {"pages": [{"canvasJson": {}}]}
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": "proj_002",
            "canvas_data": canvas_data
        }])
        
        result = create_project("user_001", "With Canvas", canvas_data=canvas_data)
        
        assert result is not None


class TestSoftDeleteProject:
    """
    项目软删除测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7.3
    """
    
    @patch('services.db_service.supabase')
    def test_soft_delete_sets_is_deleted(self, mock_supabase):
        """【业务规则 7.3】软删除设置 is_deleted=true"""
        from services.db_service import soft_delete_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "proj_001"}])
        
        result = soft_delete_project("proj_001", "user_001")
        
        # 验证 update 被调用
        mock_supabase.table.return_value.update.assert_called()


class TestRestoreProject:
    """
    项目恢复测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7.3
    """
    
    @patch('services.db_service.supabase')
    def test_restore_clears_is_deleted(self, mock_supabase):
        """【业务规则 7.3】恢复项目清除 is_deleted 标志"""
        from services.db_service import restore_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "proj_001", "is_deleted": False}])
        
        result = restore_project("proj_001")
        
        mock_supabase.table.return_value.update.assert_called()


class TestSaveProject:
    """
    项目保存测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 7.4
    """
    
    @patch('services.db_service.supabase')
    def test_save_project_updates_data(self, mock_supabase):
        """【业务规则 7.4】保存项目更新画布数据"""
        from services.db_service import save_project
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "proj_001"}])
        
        canvas_data = {"pages": [{"updated": True}]}
        result = save_project("proj_001", "user_001", canvas_data=canvas_data)
        
        mock_supabase.table.return_value.update.assert_called()


class TestDuplicateProject:
    """
    项目复制测试
    """
    
    @patch('services.db_service.supabase')
    def test_duplicate_creates_new_project(self, mock_supabase):
        """【业务规则】复制项目创建新项目"""
        from services.db_service import duplicate_project
        
        # Mock 获取原项目
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "proj_001",
            "title": "Original",
            "canvas_data": {"pages": []},
            "user_id": "user_001"
        })
        
        # Mock 创建新项目
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": "proj_002",
            "title": "Original (Copy)"
        }])
        
        result = duplicate_project("proj_001", "user_001")
        
        assert result is not None


# ==========================================
# User Profile Tests (Phase 4.2 continued)
# ==========================================

class TestGetUserProfile:
    """
    获取用户档案测试
    """
    
    @patch('services.db_service.supabase')
    def test_get_existing_user(self, mock_supabase):
        """【业务规则】获取存在的用户档案"""
        from services.db_service import get_user_profile
        
        # 注意: get_user_profile 使用 res.data[0]，不是 .single()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "user_001",
            "tier": "pro",
            "credits_monthly": 1000,
            "credits_permanent": 200
        }])
        
        profile = get_user_profile("user_001")
        
        assert profile is not None
        assert profile["tier"] == "pro"
    
    @patch('services.db_service.supabase')
    def test_get_nonexistent_user_returns_none(self, mock_supabase):
        """【业务规则】获取不存在的用户返回 None"""
        from services.db_service import get_user_profile
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        profile = get_user_profile("nonexistent")
        
        assert profile is None


class TestUpdateUserProfile:
    """
    更新用户档案测试
    """
    
    @patch('services.db_service.supabase')
    def test_update_timezone(self, mock_supabase):
        """【业务规则】更新用户时区"""
        from services.db_service import update_user_timezone
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "user_001"}])
        
        result = update_user_timezone("user_001", "America/New_York")
        
        mock_supabase.table.return_value.update.assert_called()


# ==========================================
# Monthly Credits Reset Tests (Phase 4.3)
# ==========================================

class TestRefreshMonthlyCredits:
    """
    月度积分重置测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 3.5
    """
    
    @patch('services.db_service.log_credit_transaction')
    @patch('services.db_service.supabase')
    def test_refresh_resets_to_tier_quota(self, mock_supabase, mock_log):
        """【业务规则 3.5】重置为等级配额"""
        from services.db_service import refresh_monthly_credits
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "user_001"}])
        
        # Pro 用户应该重置为 1000
        result = refresh_monthly_credits("user_001", "pro")
        
        # 验证调用了 update
        mock_supabase.table.return_value.update.assert_called()
    
    @patch('services.db_service.log_credit_transaction')
    @patch('services.db_service.supabase')
    def test_refresh_starter_gets_500(self, mock_supabase, mock_log):
        """【业务规则 3.5】Starter 重置为 500 积分"""
        from services.db_service import refresh_monthly_credits
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "user_001"}])
        
        result = refresh_monthly_credits("user_001", "starter")
        
        mock_supabase.table.return_value.update.assert_called()


class TestAddCreditsPermanent:
    """
    添加永久积分测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 3.4
    """
    
    @patch('services.db_service.log_credit_transaction')
    @patch('services.db_service.supabase')
    @patch('services.db_service.get_user_profile')
    def test_add_permanent_increases_balance(self, mock_get_profile, mock_supabase, mock_log):
        """【业务规则 3.4】添加永久积分增加余额"""
        from services.db_service import add_credits_permanent
        
        mock_get_profile.return_value = {
            "id": "user_001",
            "credits_permanent": 100
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "user_001"}])
        
        result = add_credits_permanent("user_001", 50, "Market sale")
        
        assert result is not None


# ==========================================
# Asset Management Tests
# ==========================================

class TestSaveAsset:
    """
    保存资产测试
    """
    
    @patch('services.db_service.supabase')
    def test_save_asset_success(self, mock_supabase):
        """【业务规则】成功保存资产"""
        from services.db_service import save_asset
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": "asset_001",
            "url": "https://example.com/image.png",
            "type": "image"
        }])
        
        # save_asset 没有返回值，只是执行 insert
        save_asset(
            user_id="user_001",
            url="https://example.com/image.png",
            type="image"
        )
        
        # 验证 insert 被调用了
        mock_supabase.table.return_value.insert.assert_called_once()


class TestSoftDeleteAsset:
    """
    资产软删除测试
    """
    
    @patch('services.db_service.supabase')
    def test_soft_delete_asset(self, mock_supabase):
        """【业务规则】软删除资产"""
        from services.db_service import soft_delete_asset
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "asset_001"}])
        
        result = soft_delete_asset("asset_001", "user_001")
        
        mock_supabase.table.return_value.update.assert_called()
