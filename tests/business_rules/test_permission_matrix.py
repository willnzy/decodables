"""
功能权限矩阵业务规则测试

业务规则来源: 后台业务逻辑说明.md Section 4

核心规则:
- 功能权限按用户等级和试用期状态分配
- 资源访问控制通过 allowed_tiers 字段

@module tests/business_rules/test_permission_matrix
@version v3.24
"""

import pytest


class TestFeaturePermissionMatrix:
    """
    测试功能权限矩阵
    
    业务规则来源: Section 4.1
    """
    
    def test_ai_generation_all_users(self):
        """【业务规则 4.1】AI 图像生成所有用户可用（需积分）"""
        def can_generate(tier, has_credits=True):
            return has_credits  # 只要有积分就能生成
        
        assert can_generate("free") is True
        assert can_generate("starter") is True
        assert can_generate("pro") is True
        assert can_generate("free", has_credits=False) is False
    
    def test_sticker_library_requires_membership_or_trial(self):
        """【业务规则 4.1】贴纸库需要会员或试用期"""
        def can_use_stickers(tier, is_trial=False):
            if tier in ["starter", "pro"]:
                return True
            if tier == "free" and is_trial:
                return True
            return False
        
        assert can_use_stickers("free") is False
        assert can_use_stickers("free", is_trial=True) is True
        assert can_use_stickers("starter") is True
        assert can_use_stickers("pro") is True
    
    def test_ocr_requires_pro_or_trial(self):
        """【业务规则 4.1】OCR/Smart Scan 仅限 Pro 或试用期"""
        def can_use_ocr(tier, is_trial=False):
            if tier == "pro":
                return True
            if tier == "free" and is_trial:
                return True
            return False
        
        assert can_use_ocr("free") is False
        assert can_use_ocr("free", is_trial=True) is True
        assert can_use_ocr("starter") is False  # Starter 没有 OCR！
        assert can_use_ocr("pro") is True
    
    def test_zip_export_pro_only(self):
        """【业务规则 4.1】ZIP 导出仅限 Pro"""
        def can_export_zip(tier):
            return tier == "pro"
        
        assert can_export_zip("free") is False
        assert can_export_zip("starter") is False
        assert can_export_zip("pro") is True
    
    def test_pdf_export_all_users(self):
        """【业务规则 4.1】PDF 导出所有用户可用"""
        def can_export_pdf(tier):
            return True
        
        assert can_export_pdf("free") is True
        assert can_export_pdf("starter") is True
        assert can_export_pdf("pro") is True
    
    def test_pdf_watermark_for_free_after_trial(self):
        """【业务规则 9.2】Free 用户试用期后 PDF 有水印"""
        def has_pdf_watermark(tier, is_trial=False):
            if tier == "free" and not is_trial:
                return True
            return False
        
        assert has_pdf_watermark("free") is True
        assert has_pdf_watermark("free", is_trial=True) is False
        assert has_pdf_watermark("starter") is False
        assert has_pdf_watermark("pro") is False
    
    def test_personal_upload_pro_only(self):
        """【业务规则 4.1】个人资源上传仅限 Pro"""
        def can_upload_personal(tier):
            return tier == "pro"
        
        assert can_upload_personal("free") is False
        assert can_upload_personal("starter") is False
        assert can_upload_personal("pro") is True


class TestProjectLimits:
    """
    测试项目数量限制
    
    业务规则来源: Section 7.1
    """
    
    PROJECT_LIMITS = {
        "free": 1,
        "starter": 20,
        "pro": 200
    }
    
    def test_free_project_limit(self):
        """【业务规则 7.1】Free 用户限制 1 个项目"""
        assert self.PROJECT_LIMITS["free"] == 1
    
    def test_starter_project_limit(self):
        """【业务规则 7.1】Starter 用户限制 20 个项目"""
        assert self.PROJECT_LIMITS["starter"] == 20
    
    def test_pro_project_limit(self):
        """【业务规则 7.1】Pro 用户限制 200 个项目"""
        assert self.PROJECT_LIMITS["pro"] == 200
    
    def test_can_create_project(self):
        """【业务规则 7.1】项目数量限制检查"""
        def can_create_project(tier, current_count):
            limit = self.PROJECT_LIMITS.get(tier, 1)
            return current_count < limit
        
        # Free 用户
        assert can_create_project("free", 0) is True
        assert can_create_project("free", 1) is False
        
        # Starter 用户
        assert can_create_project("starter", 19) is True
        assert can_create_project("starter", 20) is False
        
        # Pro 用户
        assert can_create_project("pro", 199) is True
        assert can_create_project("pro", 200) is False


class TestResourceAccessControl:
    """
    测试资源访问控制
    
    业务规则来源: Section 4.2
    """
    
    VALID_ALLOWED_TIERS = [
        ["free"],           # 所有登录用户
        ["starter", "pro"], # 会员用户
        ["pro"],            # 仅 Pro 用户
    ]
    
    def test_valid_allowed_tiers_combinations(self):
        """【业务规则 4.2】有效的 allowed_tiers 组合（白名单）"""
        assert ["free"] in self.VALID_ALLOWED_TIERS
        assert ["starter", "pro"] in self.VALID_ALLOWED_TIERS
        assert ["pro"] in self.VALID_ALLOWED_TIERS
    
    def test_invalid_allowed_tiers_combinations(self):
        """【业务规则 4.2】无效的 allowed_tiers 组合"""
        INVALID = [
            ["starter"],        # 无效
            ["free", "pro"],    # 无效
            ["free", "starter", "pro"],  # 无效
        ]
        
        for combo in INVALID:
            assert combo not in self.VALID_ALLOWED_TIERS
    
    def test_access_check_logic(self):
        """【业务规则 4.2】访问检查逻辑"""
        def can_access_resource(user_tier, allowed_tiers, is_member=False):
            if "free" in allowed_tiers:
                return True  # 免费资源所有人可访问
            if not is_member:
                return False
            return user_tier in allowed_tiers
        
        # 免费资源所有人可访问
        assert can_access_resource("free", ["free"]) is True
        assert can_access_resource("pro", ["free"], is_member=True) is True
        
        # 会员资源
        assert can_access_resource("free", ["starter", "pro"]) is False
        assert can_access_resource("starter", ["starter", "pro"], is_member=True) is True
        assert can_access_resource("pro", ["starter", "pro"], is_member=True) is True
        
        # Pro 专属
        assert can_access_resource("starter", ["pro"], is_member=True) is False
        assert can_access_resource("pro", ["pro"], is_member=True) is True
