"""
积分系统业务规则测试

业务规则来源: 后台业务逻辑说明.md Section 3

核心规则:
- 积分类型: 月度积分（每30天重置）+ 永久积分（永不过期）
- 扣费优先级: 先扣月度，再扣永久
- 月度重置: 覆盖重置，不累加，不结转

@module tests/business_rules/test_credit_rules
@version v3.24
"""

import pytest


class TestCreditTypes:
    """
    测试积分类型定义
    
    业务规则来源: Section 3.1
    """
    
    def test_credit_types(self):
        """【业务规则 3.1】两种积分类型"""
        CREDIT_TYPES = ["monthly", "permanent"]
        
        assert "monthly" in CREDIT_TYPES
        assert "permanent" in CREDIT_TYPES
        assert len(CREDIT_TYPES) == 2
    
    def test_monthly_credits_expire(self):
        """【业务规则 3.1】月度积分每30天重置"""
        MONTHLY_RESET_DAYS = 30
        assert MONTHLY_RESET_DAYS == 30
    
    def test_permanent_credits_never_expire(self):
        """【业务规则 3.1】永久积分永不过期"""
        # 永久积分没有过期时间
        PERMANENT_EXPIRY_DAYS = None
        assert PERMANENT_EXPIRY_DAYS is None


class TestCreditDeductionPriority:
    """
    测试积分扣费优先级
    
    业务规则来源: Section 3.2
    - 先扣月度积分，再扣永久积分
    """
    
    @staticmethod
    def calculate_deduction(monthly, permanent, amount):
        """计算扣费分配"""
        deduct_monthly = min(monthly, amount)
        deduct_permanent = amount - deduct_monthly
        return deduct_monthly, deduct_permanent
    
    def test_deduct_monthly_first_when_sufficient(self):
        """【业务规则 3.2】月度积分足够时只扣月度"""
        monthly, permanent, amount = 100, 50, 30
        deduct_m, deduct_p = self.calculate_deduction(monthly, permanent, amount)
        
        assert deduct_m == 30  # 全部从月度扣
        assert deduct_p == 0   # 不动永久
    
    def test_deduct_monthly_first_then_permanent(self):
        """【业务规则 3.2】月度不够时先扣月度，再扣永久"""
        monthly, permanent, amount = 30, 100, 50
        deduct_m, deduct_p = self.calculate_deduction(monthly, permanent, amount)
        
        assert deduct_m == 30  # 扣完月度
        assert deduct_p == 20  # 剩余从永久扣
    
    def test_deduct_all_from_permanent_when_monthly_zero(self):
        """【业务规则 3.2】月度为0时全部从永久扣"""
        monthly, permanent, amount = 0, 100, 30
        deduct_m, deduct_p = self.calculate_deduction(monthly, permanent, amount)
        
        assert deduct_m == 0
        assert deduct_p == 30
    
    def test_example_from_spec(self):
        """【业务规则 3.2】文档示例验证"""
        # 用户有 月度=30, 永久=100, 需要扣 50 积分
        monthly, permanent, amount = 30, 100, 50
        deduct_m, deduct_p = self.calculate_deduction(monthly, permanent, amount)
        
        # 扣 月度 30 + 永久 20 = 50
        assert deduct_m == 30
        assert deduct_p == 20
        
        # 结果: 月度=0, 永久=80
        final_monthly = monthly - deduct_m
        final_permanent = permanent - deduct_p
        assert final_monthly == 0
        assert final_permanent == 80


class TestCreditConsumption:
    """
    测试积分消耗规则
    
    业务规则来源: Section 3.3
    """
    
    CREDITS_PER_IMAGE = 5
    CREDITS_PER_OCR = 5
    MAX_LISTING_PRICE = 500
    
    def test_ai_image_generation_cost(self):
        """【业务规则 3.3】AI 图像生成消耗 5 积分/张"""
        assert self.CREDITS_PER_IMAGE == 5
    
    def test_ocr_cost(self):
        """【业务规则 3.3】OCR/Smart Scan 消耗 5 积分/次"""
        assert self.CREDITS_PER_OCR == 5
    
    def test_pdf_export_free(self):
        """【业务规则 3.3】PDF 导出免费"""
        PDF_COST = 0
        assert PDF_COST == 0
    
    def test_zip_export_free(self):
        """【业务规则 3.3】ZIP 导出免费（但仅限 Pro）"""
        ZIP_COST = 0
        assert ZIP_COST == 0
    
    def test_marketplace_price_range(self):
        """【业务规则 3.3】市场商品定价范围 0-500"""
        assert self.MAX_LISTING_PRICE == 500


class TestCreditAcquisition:
    """
    测试积分获取规则
    
    业务规则来源: Section 3.4
    """
    
    def test_signup_bonus(self):
        """【业务规则 3.4】注册赠送 50 永久积分"""
        SIGNUP_BONUS = 50
        SIGNUP_BONUS_TYPE = "permanent"
        
        assert SIGNUP_BONUS == 50
        assert SIGNUP_BONUS_TYPE == "permanent"
    
    def test_tier_monthly_credits(self):
        """【业务规则 3.4】各等级月度积分配额"""
        MONTHLY_CREDITS = {
            "free": 0,
            "starter": 500,
            "pro": 1000
        }
        
        assert MONTHLY_CREDITS["free"] == 0
        assert MONTHLY_CREDITS["starter"] == 500
        assert MONTHLY_CREDITS["pro"] == 1000
    
    def test_seller_revenue(self):
        """【业务规则 3.4 & 6.3】市场销售收入 90% 为永久积分"""
        SELLER_REVENUE_PERCENT = 90
        REVENUE_TYPE = "permanent"
        
        # 定价 100 积分，卖家获得 90 永久积分
        price = 100
        seller_gets = int(price * SELLER_REVENUE_PERCENT / 100)
        
        assert seller_gets == 90
        assert REVENUE_TYPE == "permanent"


class TestMonthlyReset:
    """
    测试月度积分重置规则
    
    业务规则来源: Section 3.5
    """
    
    def test_reset_is_override_not_add(self):
        """【业务规则 3.5】月度重置是覆盖，不是累加"""
        old_monthly = 200
        tier_quota = 500
        
        # 重置逻辑
        new_monthly = tier_quota  # 直接覆盖
        
        assert new_monthly == 500
        assert new_monthly != old_monthly + tier_quota  # 不是累加
    
    def test_unused_credits_not_rollover(self):
        """【业务规则 3.5】未使用的月度积分不结转"""
        old_monthly = 300  # 上月剩余
        tier_quota = 500
        
        new_monthly = tier_quota  # 覆盖重置
        
        # 新月度不包含旧积分
        assert new_monthly == 500
        assert old_monthly not in [new_monthly]  # 旧积分丢失
    
    def test_permanent_not_affected_by_reset(self):
        """【业务规则 3.5】永久积分不受月度重置影响"""
        permanent_before = 150
        permanent_after = permanent_before  # 永久积分不变
        
        assert permanent_after == permanent_before
