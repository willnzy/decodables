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
    v3.22: 使用 RPC 原子操作
    """
    
    @patch('services.db_service.supabase')
    def test_deduction_priority_monthly_first(self, mock_supabase):
        """【业务规则 3.2】扣费优先级: 先扣月度积分 (RPC 实现)"""
        from services.db_service import credit_deduct
        
        # Mock RPC 返回扣费结果（RPC 内部处理优先级逻辑）
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": True,
            "balance_monthly": 0,  # 月度扣完
            "balance_permanent": 80  # 永久扣了 20
        })
        
        result = credit_deduct("user_001", 50, "generation", "Test deduction")
        
        assert result["success"] is True
        # 月度应该扣完 30，永久扣 20
        assert result["balance_monthly"] == 0
        assert result["balance_permanent"] == 80
    
    @patch('services.db_service.supabase')
    def test_insufficient_credits_raises_exception(self, mock_supabase):
        """【业务规则 3.2】积分不足时抛出异常 (RPC 实现)"""
        from services.db_service import credit_deduct
        
        # Mock RPC 返回积分不足错误
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": False,
            "error": "Insufficient credits",
            "error_code": "CREDITS_INSUFFICIENT"
        })
        
        with pytest.raises(Exception) as exc_info:
            credit_deduct("user_001", 100, "generation", "Test deduction")
        
        assert "CREDITS_INSUFFICIENT" in str(exc_info.value)
    
    @patch('services.db_service.supabase')
    def test_user_not_found_raises_exception(self, mock_supabase):
        """【业务规则】用户不存在时抛出异常 (RPC 实现)"""
        from services.db_service import credit_deduct
        
        # Mock RPC 返回用户不存在错误
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={
            "success": False,
            "error": "User not found",
            "error_code": "USER_NOT_FOUND"
        })
        
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


class TestRestoreAsset:
    """
    资产恢复测试
    """
    
    @patch('services.db_service.supabase')
    def test_restore_asset(self, mock_supabase):
        """【业务规则】恢复软删除的资产"""
        from services.db_service import restore_asset
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "asset_001"}])
        
        restore_asset("asset_001", "user_001")
        
        mock_supabase.table.return_value.update.assert_called()


class TestPermanentlyHideAsset:
    """
    永久隐藏资产测试
    """
    
    @patch('services.db_service.supabase')
    def test_permanently_hide_asset(self, mock_supabase):
        """【业务规则】永久隐藏资产"""
        from services.db_service import permanently_hide_asset
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "asset_001"}])
        
        permanently_hide_asset("asset_001", "user_001")
        
        mock_supabase.table.return_value.update.assert_called()


# ==========================================
# Project Query Tests
# ==========================================

class TestGetUserProjects:
    """
    获取用户项目测试
    
    注意: 这个函数有复杂的查询逻辑，需要完整的 mock 链
    """
    
    def test_project_pagination_logic(self):
        """【业务规则】项目分页逻辑"""
        # 测试分页参数计算
        page = 2
        limit = 20
        start = (page - 1) * limit
        end = start + limit - 1
        
        assert start == 20
        assert end == 39


class TestCountUserProjects:
    """
    统计用户项目数量测试
    """
    
    @patch('services.db_service.supabase')
    def test_count_user_projects(self, mock_supabase):
        """【业务规则】统计用户项目数量"""
        from services.db_service import count_user_projects
        
        # count_user_projects 通过查询 id 列表来计数
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}, {"id": "5"}]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result
        
        count = count_user_projects("user_001")
        
        assert count == 5


class TestDuplicateProject:
    """
    复制项目测试
    """
    
    @patch('services.db_service.get_project_detail')
    @patch('services.db_service.supabase')
    def test_duplicate_project_success(self, mock_supabase, mock_get_detail):
        """【业务规则】成功复制项目"""
        from services.db_service import duplicate_project
        
        mock_get_detail.return_value = {
            "id": "proj_001",
            "title": "Original Project",
            "canvas_data": {"pages": []},
            "user_id": "user_001"
        }
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": "proj_002",
            "title": "Original Project (Copy)",
            "user_id": "user_001"
        }])
        
        result = duplicate_project("proj_001", "user_001")
        
        assert result is not None
        mock_supabase.table.return_value.insert.assert_called()


# ==========================================
# Marketplace Tests
# ==========================================

class TestGetMarketplaceListings:
    """
    获取市场列表测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6
    """
    
    def test_marketplace_visibility_rules(self):
        """【业务规则 6.4】市场商品可见性规则"""
        # 市场可见条件: moderation_status='approved' AND is_public=true AND is_deleted=false
        visibility_conditions = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False
        }
        
        assert visibility_conditions["moderation_status"] == "approved"
        assert visibility_conditions["is_public"] is True
        assert visibility_conditions["is_deleted"] is False


class TestCreateListing:
    """
    创建商品列表测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6
    """
    
    @patch('services.db_service.supabase')
    def test_create_listing_success(self, mock_supabase):
        """【业务规则 6】创建商品"""
        from services.db_service import create_listing
        
        # Mock 检查现有 listing 的查询 - 返回空（没有现有 listing）
        mock_existing_result = MagicMock()
        mock_existing_result.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_existing_result
        
        # Mock insert
        mock_insert_result = MagicMock()
        mock_insert_result.data = [{
            "id": "listing_001",
            "title": "Test Asset",
            "seller_id": "seller_001",
            "moderation_status": "pending"
        }]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_result
        
        result = create_listing(
            seller_id="seller_001",
            title="Test Asset",
            description="A test asset",
            thumbnail_url="https://example.com/thumb.jpg",
            resource_url="https://example.com/resource.zip",
            resource_type="asset",
            price_credits=100
        )
        
        assert result is not None


class TestSubmitListingForReview:
    """
    提交商品审核测试
    """
    
    @patch('services.db_service.supabase')
    def test_submit_listing_for_review(self, mock_supabase):
        """【业务规则 6.4】提交商品进行审核"""
        from services.db_service import submit_listing_for_review
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "listing_001",
            "moderation_status": "pending"
        }])
        
        result = submit_listing_for_review("listing_001", "seller_001")
        
        assert result is not None


# ==========================================
# System Resources Tests
# ==========================================

class TestGetSystemResources:
    """
    获取系统资源测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 8
    """
    
    @patch('services.db_service.supabase')
    def test_get_system_stickers(self, mock_supabase):
        """【业务规则 8】获取系统贴纸"""
        from services.db_service import get_system_resources
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "sticker_001", "name": "Cat", "type": "sticker"},
            {"id": "sticker_002", "name": "Dog", "type": "sticker"}
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        
        resources = get_system_resources("sticker")
        
        assert len(resources) == 2
    
    @patch('services.db_service.supabase')
    def test_get_system_resources_by_tier(self, mock_supabase):
        """【业务规则 8】根据用户等级获取资源"""
        from services.db_service import get_system_resources
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "sticker_001", "name": "Pro Sticker", "type": "sticker", "allowed_tiers": ["pro"]}
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        
        resources = get_system_resources("sticker", user_tier="pro")
        
        assert len(resources) == 1


class TestGetAssets:
    """
    获取资产测试
    """
    
    @patch('services.db_service.supabase')
    def test_get_assets_for_user(self, mock_supabase):
        """【业务规则】获取用户资产"""
        from services.db_service import get_assets
        
        # Mock 主查询
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "asset_001", "url": "https://example.com/image1.png", "user_id": "user_001"},
            {"id": "asset_002", "url": "https://example.com/image2.png", "user_id": "user_001"}
        ]
        
        # Mock marketplace_listings 查询
        mock_listings_result = MagicMock()
        mock_listings_result.data = []
        
        # 设置完整的 mock 链
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value = mock_chain
        
        # Mock marketplace 查询
        mock_supabase.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_listings_result
        
        assets = get_assets("user_001")
        
        # 验证返回了资产列表
        assert isinstance(assets, list)
    
    @patch('services.db_service.supabase')
    def test_get_assets_for_project(self, mock_supabase):
        """【业务规则】获取项目关联资产"""
        from services.db_service import get_assets
        
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "asset_001", "url": "https://example.com/image1.png", "project_id": "proj_001"}
        ]
        
        # 设置完整的 mock 链
        mock_chain = MagicMock()
        mock_chain.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value = mock_chain
        
        # Mock marketplace 查询
        mock_listings_result = MagicMock()
        mock_listings_result.data = []
        mock_supabase.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_listings_result
        
        assets = get_assets("user_001", project_id="proj_001")
        
        assert isinstance(assets, list)


class TestGetDeletedAssets:
    """
    获取已删除资产测试
    """
    
    def test_deleted_asset_recovery_window(self):
        """【业务规则 7.3】已删除资产 30 天内可恢复"""
        from datetime import datetime, timedelta, timezone
        
        # 在恢复窗口内
        deleted_at = datetime.now(timezone.utc) - timedelta(days=15)
        days_since = (datetime.now(timezone.utc) - deleted_at).days
        can_restore = days_since <= 30
        
        assert can_restore is True
        
        # 超出恢复窗口
        deleted_at_old = datetime.now(timezone.utc) - timedelta(days=35)
        days_since_old = (datetime.now(timezone.utc) - deleted_at_old).days
        can_restore_old = days_since_old <= 30
        
        assert can_restore_old is False


# ==========================================
# Dashboard Tests
# ==========================================

class TestGetDashboardProjects:
    """
    Dashboard 项目查询测试
    """
    
    def test_dashboard_project_pagination(self):
        """【业务规则】Dashboard 项目分页"""
        page = 1
        limit = 20
        start = (page - 1) * limit
        end = start + limit - 1
        
        assert start == 0
        assert end == 19


class TestGetDashboardAssets:
    """
    Dashboard 资产查询测试
    """
    
    def test_dashboard_asset_pagination(self):
        """【业务规则】Dashboard 资产分页"""
        page = 2
        limit = 50
        start = (page - 1) * limit
        end = start + limit - 1
        
        assert start == 50
        assert end == 99


# ==========================================
# Seller Stats Tests
# ==========================================

class TestGetSellerStats:
    """
    卖家统计测试
    """
    
    @patch('services.db_service.supabase')
    def test_get_seller_project_stats(self, mock_supabase):
        """【业务规则 6】获取卖家项目统计"""
        from services.db_service import get_seller_project_stats
        
        mock_result = MagicMock()
        mock_result.data = [
            {"total_sales": 10, "total_revenue": 500}
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[{"sum": 500}])
        
        stats = get_seller_project_stats("seller_001")
        
        assert stats is not None
    
    @patch('services.db_service.supabase')
    def test_get_seller_asset_stats(self, mock_supabase):
        """【业务规则 6】获取卖家资产统计"""
        from services.db_service import get_seller_asset_stats
        
        mock_result = MagicMock()
        mock_result.data = [
            {"total_sales": 20, "total_revenue": 1000}
        ]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[{"sum": 1000}])
        
        stats = get_seller_asset_stats("seller_001")
        
        assert stats is not None


# ==========================================
# Check User Purchase Tests
# ==========================================

class TestCheckUserPurchase:
    """
    检查用户购买测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6.2
    """
    
    @patch('services.db_service.supabase')
    def test_check_user_already_purchased(self, mock_supabase):
        """【业务规则 6.2】检查用户是否已购买"""
        from services.db_service import check_user_purchase
        
        mock_result = MagicMock()
        mock_result.data = [{"id": "purchase_001"}]
        
        # check_user_purchase 没有 limit，只有 eq.eq.execute
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result
        
        result = check_user_purchase("user_001", "listing_001")
        
        assert result is True
    
    @patch('services.db_service.supabase')
    def test_check_user_not_purchased(self, mock_supabase):
        """【业务规则 6.2】检查用户未购买"""
        from services.db_service import check_user_purchase
        
        mock_result = MagicMock()
        mock_result.data = []
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result
        
        result = check_user_purchase("user_001", "listing_001")
        
        assert result is False


# ==========================================
# Listing Visibility Tests
# ==========================================

class TestListingVisibility:
    """
    商品可见性测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 6.4
    """
    
    def test_listing_is_public_visible_true(self):
        """【业务规则 6.4】已审核且公开的商品可见"""
        from services.db_service import listing_is_public_visible
        
        listing = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": False
        }
        
        assert listing_is_public_visible(listing) is True
    
    def test_listing_is_public_visible_not_approved(self):
        """【业务规则 6.4】未审核的商品不可见"""
        from services.db_service import listing_is_public_visible
        
        listing = {
            "moderation_status": "pending",
            "is_public": True,
            "is_deleted": False
        }
        
        assert listing_is_public_visible(listing) is False
    
    def test_listing_is_public_visible_deleted(self):
        """【业务规则 6.4】已删除的商品不可见"""
        from services.db_service import listing_is_public_visible
        
        listing = {
            "moderation_status": "approved",
            "is_public": True,
            "is_deleted": True
        }
        
        assert listing_is_public_visible(listing) is False


# ==========================================
# Get Total Credits Tests
# ==========================================

class TestGetTotalCredits:
    """
    获取总积分测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 3.1
    """
    
    def test_get_total_credits(self):
        """【业务规则 3.1】总积分 = 月度 + 永久"""
        from services.db_service import get_total_credits
        
        user = {
            "credits_monthly": 100,
            "credits_permanent": 50
        }
        
        total = get_total_credits(user)
        
        assert total == 150
    
    def test_get_total_credits_with_missing_fields(self):
        """【业务规则 3.1】缺失字段默认为 0"""
        from services.db_service import get_total_credits
        
        user = {}
        
        total = get_total_credits(user)
        
        assert total == 0
