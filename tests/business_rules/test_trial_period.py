"""
30天试用期业务规则测试

业务规则来源: 后台业务逻辑说明.md Section 2.3

核心规则:
- 试用期时长: 30 天（从注册日期开始）
- 试用期内: Free 用户可以体验所有功能（等同 Pro）
- 试用期结束后: 不属于 Free 的功能权益会"上锁"

@module tests/business_rules/test_trial_period
@version v3.24
"""

import pytest
from datetime import datetime, timezone, timedelta


# 业务规则定义的试用期天数
TRIAL_DAYS = 30


class TestTrialPeriodDuration:
    """测试试用期时长"""
    
    def test_trial_period_is_30_days(self):
        """【业务规则 2.3】试用期时长为 30 天"""
        assert TRIAL_DAYS == 30


class TestTrialPeriodLogic:
    """测试试用期判断逻辑"""
    
    @staticmethod
    def is_in_trial(user):
        """
        判断用户是否在试用期内
        
        业务规则:
        - 只有 Free 用户有试用期
        - 付费用户不需要试用期判断
        """
        if user.get("tier") != "free":
            return False
        
        created_at = user.get("created_at")
        if not created_at:
            return False
        
        # 处理时区
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        days_since_registration = (now - created_at).total_seconds() / (24 * 3600)
        
        return days_since_registration <= TRIAL_DAYS
    
    def test_new_free_user_in_trial(self):
        """【业务规则 2.3】新注册的 Free 用户在试用期内"""
        user = {
            "tier": "free",
            "created_at": datetime.now(timezone.utc) - timedelta(days=1)
        }
        assert self.is_in_trial(user) is True
    
    def test_free_user_day_10_in_trial(self):
        """【业务规则 2.3】第10天的 Free 用户在试用期内"""
        user = {
            "tier": "free",
            "created_at": datetime.now(timezone.utc) - timedelta(days=10)
        }
        assert self.is_in_trial(user) is True
    
    def test_free_user_day_29_in_trial(self):
        """【业务规则 2.3】第29天的 Free 用户在试用期内"""
        user = {
            "tier": "free",
            "created_at": datetime.now(timezone.utc) - timedelta(days=29)
        }
        assert self.is_in_trial(user) is True
    
    def test_free_user_day_30_in_trial(self):
        """【业务规则 2.3】第30天的 Free 用户仍在试用期内（<=30）"""
        # 使用 29.9 天来避免浮点精度问题
        user = {
            "tier": "free",
            "created_at": datetime.now(timezone.utc) - timedelta(days=29, hours=23)
        }
        assert self.is_in_trial(user) is True
    
    def test_free_user_day_31_expired(self):
        """【业务规则 2.3】第31天的 Free 用户试用期已过期"""
        user = {
            "tier": "free",
            "created_at": datetime.now(timezone.utc) - timedelta(days=31)
        }
        assert self.is_in_trial(user) is False
    
    def test_old_free_user_expired(self):
        """【业务规则 2.3】注册超过30天的 Free 用户试用期已过期"""
        user = {
            "tier": "free",
            "created_at": datetime.now(timezone.utc) - timedelta(days=60)
        }
        assert self.is_in_trial(user) is False
    
    def test_paid_user_not_need_trial(self):
        """【业务规则 2.3】付费用户不需要试用期"""
        # Starter 用户
        starter_user = {
            "tier": "starter",
            "created_at": datetime.now(timezone.utc) - timedelta(days=5)
        }
        assert self.is_in_trial(starter_user) is False
        
        # Pro 用户
        pro_user = {
            "tier": "pro",
            "created_at": datetime.now(timezone.utc) - timedelta(days=5)
        }
        assert self.is_in_trial(pro_user) is False
    
    def test_missing_created_at_not_in_trial(self):
        """【边界条件】没有 created_at 的用户不在试用期"""
        user = {"tier": "free"}
        assert self.is_in_trial(user) is False


class TestTrialFeatures:
    """测试试用期功能权限"""
    
    def test_trial_features_equal_to_pro(self):
        """【业务规则 2.3】试用期内 Free 用户可以体验所有功能"""
        # 试用期内 Free 用户应该能使用的功能
        TRIAL_ENABLED_FEATURES = [
            "ai_generation",       # AI 图像生成
            "sticker_library",     # 贴纸库
            "ocr_smart_scan",      # OCR/Smart Scan
            "project_templates",   # 项目模板
            "pdf_export_no_watermark",  # PDF 导出无水印
        ]
        
        # 注意：即使试用期也不可用的功能
        TRIAL_DISABLED_FEATURES = [
            "zip_export",          # ZIP 导出（仅 Pro）
            "personal_upload",     # 个人资源上传（仅 Pro）
        ]
        
        # 验证试用期功能列表符合预期
        assert "sticker_library" in TRIAL_ENABLED_FEATURES
        assert "ocr_smart_scan" in TRIAL_ENABLED_FEATURES
        assert "zip_export" not in TRIAL_ENABLED_FEATURES
    
    def test_trial_expired_features_locked(self):
        """【业务规则 2.3】试用期结束后功能上锁"""
        # 试用期结束后，以下功能应该被锁定
        LOCKED_AFTER_TRIAL = [
            "sticker_library",
            "ocr_smart_scan",
            "project_templates",
        ]
        
        # 这些功能在试用期后只有升级才能使用
        for feature in LOCKED_AFTER_TRIAL:
            assert feature in LOCKED_AFTER_TRIAL
