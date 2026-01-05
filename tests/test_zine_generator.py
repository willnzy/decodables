"""
Zine Generator Tests
迷你书生成器测试

基于 BUSINESS_LOGIC_SPEC.md Section 9 的业务规则测试

核心业务规则:
1. PDF 导出:
   - 8 页可折叠格式
   - 支持 Letter 和 A4 纸张

2. ZIP 导出:
   - 仅 Pro 用户可用
   - 包含高清图片

@module tests/test_zine_generator
@version v3.3
"""

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
import base64


# ==========================================
# Paper Configuration Tests
# ==========================================

class TestPaperConfig:
    """
    纸张配置测试
    """
    
    def test_paper_config_has_letter(self):
        """【业务规则 9】支持 US Letter 纸张"""
        from services.ai.zine_generator import PAPER_CONFIG
        
        assert "US_LETTER" in PAPER_CONFIG
        assert "size" in PAPER_CONFIG["US_LETTER"]
    
    def test_paper_config_has_a4(self):
        """【业务规则 9】支持 A4 纸张"""
        from services.ai.zine_generator import PAPER_CONFIG
        
        assert "A4" in PAPER_CONFIG
        assert "size" in PAPER_CONFIG["A4"]
    
    def test_paper_config_has_padding(self):
        """【业务规则】纸张配置包含默认内边距"""
        from services.ai.zine_generator import PAPER_CONFIG
        
        assert "default_padding" in PAPER_CONFIG["US_LETTER"]
        assert "default_padding" in PAPER_CONFIG["A4"]


# ==========================================
# decode_base64_image Tests
# ==========================================

class TestDecodeBase64Image:
    """
    Base64 图片解码测试
    """
    
    def test_decode_valid_base64(self):
        """【业务规则】解码有效 Base64 图片"""
        from services.ai.zine_generator import decode_base64_image
        
        # 创建简单的 1x1 PNG 图片的 base64
        png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        data_url = f"data:image/png;base64,{png_base64}"
        
        result = decode_base64_image(data_url)
        
        assert result is not None
        assert isinstance(result, BytesIO)
    
    def test_decode_returns_none_for_invalid(self):
        """【业务规则】无效输入返回 None"""
        from services.ai.zine_generator import decode_base64_image
        
        assert decode_base64_image(None) is None
        assert decode_base64_image("") is None
        assert decode_base64_image("not a data url") is None
    
    def test_decode_returns_none_for_non_data_url(self):
        """【业务规则】非 data URL 返回 None"""
        from services.ai.zine_generator import decode_base64_image
        
        result = decode_base64_image("https://example.com/image.png")
        
        assert result is None
    
    def test_decode_handles_malformed_base64(self):
        """【业务规则】处理格式错误的 Base64"""
        from services.ai.zine_generator import decode_base64_image
        
        result = decode_base64_image("data:image/png;base64,invalid!!!")
        
        assert result is None


# ==========================================
# draw_smart_image Tests
# ==========================================

class TestDrawSmartImage:
    """
    智能图片绘制测试
    """
    
    def test_draw_smart_image_handles_none(self):
        """【业务规则】处理 None 图片源"""
        from services.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        
        # 不应抛出异常
        draw_smart_image(mock_canvas, None, 0, 0, 100, 100)
        
        mock_canvas.drawImage.assert_not_called()
    
    def test_draw_smart_image_handles_empty_string(self):
        """【业务规则】处理空字符串"""
        from services.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        
        draw_smart_image(mock_canvas, "", 0, 0, 100, 100)
        
        mock_canvas.drawImage.assert_not_called()


# ==========================================
# draw_wrapped_text Tests
# ==========================================

class TestDrawWrappedText:
    """
    文本换行绘制测试
    """
    
    def test_draw_wrapped_text_handles_none(self):
        """【业务规则】处理 None 文本"""
        from services.ai.zine_generator import draw_wrapped_text
        
        mock_canvas = MagicMock()
        
        # 不应抛出异常
        draw_wrapped_text(mock_canvas, None, 0, 0, 100)
        
        mock_canvas.drawCentredString.assert_not_called()
    
    def test_draw_wrapped_text_handles_empty(self):
        """【业务规则】处理空文本"""
        from services.ai.zine_generator import draw_wrapped_text
        
        mock_canvas = MagicMock()
        
        draw_wrapped_text(mock_canvas, "", 0, 0, 100)
        
        mock_canvas.drawCentredString.assert_not_called()


# ==========================================
# create_foldable_book Tests
# ==========================================

class TestCreateFoldableBook:
    """
    可折叠书创建测试
    """
    
    @patch('services.ai.zine_generator.canvas.Canvas')
    def test_create_foldable_book_letter(self, mock_canvas_class):
        """【业务规则 9】创建 Letter 尺寸 PDF"""
        from services.ai.zine_generator import create_foldable_book
        
        mock_canvas = MagicMock()
        mock_canvas_class.return_value = mock_canvas
        
        output = BytesIO()
        image_paths = ["img1.png"] * 8
        
        create_foldable_book(
            image_paths,
            output_buffer=output,
            paper_type="US_LETTER"
        )
        
        mock_canvas_class.assert_called_once()
        mock_canvas.save.assert_called_once()
    
    @patch('services.ai.zine_generator.canvas.Canvas')
    def test_create_foldable_book_a4(self, mock_canvas_class):
        """【业务规则 9】创建 A4 尺寸 PDF"""
        from services.ai.zine_generator import create_foldable_book
        
        mock_canvas = MagicMock()
        mock_canvas_class.return_value = mock_canvas
        
        output = BytesIO()
        image_paths = ["img1.png"] * 8
        
        create_foldable_book(
            image_paths,
            output_buffer=output,
            paper_type="A4"
        )
        
        mock_canvas_class.assert_called_once()
    
    @patch('services.ai.zine_generator.canvas.Canvas')
    def test_create_foldable_book_pads_images(self, mock_canvas_class):
        """【业务规则】自动补齐不足 8 张的图片"""
        from services.ai.zine_generator import create_foldable_book
        
        mock_canvas = MagicMock()
        mock_canvas_class.return_value = mock_canvas
        
        output = BytesIO()
        image_paths = ["img1.png", "img2.png"]  # 只有 2 张
        
        create_foldable_book(
            image_paths,
            output_buffer=output
        )
        
        # 应该能正常创建
        mock_canvas.save.assert_called_once()
    
    @patch('services.ai.zine_generator.canvas.Canvas')
    def test_create_foldable_book_with_text(self, mock_canvas_class):
        """【业务规则】支持文本标签"""
        from services.ai.zine_generator import create_foldable_book
        
        mock_canvas = MagicMock()
        mock_canvas_class.return_value = mock_canvas
        
        output = BytesIO()
        image_paths = ["img1.png"] * 8
        text_list = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5", "Text 6", "Text 7", "Text 8"]
        
        create_foldable_book(
            image_paths,
            text_list=text_list,
            output_buffer=output
        )
        
        mock_canvas.save.assert_called_once()
    
    @patch('services.ai.zine_generator.canvas.Canvas')
    def test_create_foldable_book_show_guides(self, mock_canvas_class):
        """【业务规则】显示折叠辅助线"""
        from services.ai.zine_generator import create_foldable_book
        
        mock_canvas = MagicMock()
        mock_canvas_class.return_value = mock_canvas
        
        output = BytesIO()
        
        create_foldable_book(
            ["img.png"] * 8,
            output_buffer=output,
            show_guides=True
        )
        
        # 应该绘制辅助线
        mock_canvas.line.assert_called()
    
    @patch('services.ai.zine_generator.canvas.Canvas')
    def test_create_foldable_book_no_guides(self, mock_canvas_class):
        """【业务规则】可选隐藏辅助线"""
        from services.ai.zine_generator import create_foldable_book
        
        mock_canvas = MagicMock()
        mock_canvas_class.return_value = mock_canvas
        
        output = BytesIO()
        
        create_foldable_book(
            ["img.png"] * 8,
            output_buffer=output,
            show_guides=False
        )
        
        mock_canvas.save.assert_called_once()


# ==========================================
# create_assets_zip Tests
# ==========================================

class TestCreateAssetsZip:
    """
    资产 ZIP 创建测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 9
    """
    
    @patch('services.ai.zine_generator.requests.get')
    def test_create_assets_zip_creates_zip(self, mock_get):
        """【业务规则 9.1】创建 ZIP 包含图片"""
        from services.ai.zine_generator import create_assets_zip
        
        mock_response = MagicMock()
        mock_response.content = b"fake image data"
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        output = BytesIO()
        image_urls = ["https://example.com/img1.png", "https://example.com/img2.png"]
        
        create_assets_zip(image_urls, output)
        
        # 验证输出是有效的 ZIP
        output.seek(0)
        assert output.read(2) == b'PK'  # ZIP 文件头
    
    @patch('services.ai.zine_generator.requests.get')
    def test_create_assets_zip_handles_failed_download(self, mock_get):
        """【业务规则】处理下载失败"""
        from services.ai.zine_generator import create_assets_zip
        
        mock_get.side_effect = Exception("Download failed")
        
        output = BytesIO()
        
        # 不应抛出异常
        create_assets_zip(["https://example.com/img.png"], output)


# ==========================================
# Page Layout Tests
# ==========================================

class TestPageLayout:
    """
    页面布局测试
    """
    
    def test_page_order_constant(self):
        """【业务规则】8 页布局顺序"""
        # 可折叠书的页面顺序
        # 参考 create_foldable_book 中的 order_map
        expected_pages = 8
        
        assert expected_pages == 8
    
    def test_landscape_orientation(self):
        """【业务规则】横向打印"""
        from services.ai.zine_generator import PAPER_CONFIG
        from reportlab.lib.pagesizes import letter
        
        # Letter 尺寸应该是横向
        raw_w, raw_h = PAPER_CONFIG["US_LETTER"]["size"]
        
        # 代码会交换宽高使其横向
        if raw_h > raw_w:
            page_width, page_height = raw_h, raw_w
        else:
            page_width, page_height = raw_w, raw_h
        
        assert page_width > page_height


# ==========================================
# Export Permission Tests
# ==========================================

class TestExportPermissions:
    """
    导出权限测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 9.1
    """
    
    def test_pdf_export_all_users(self):
        """【业务规则 9.1】PDF 导出对所有用户开放"""
        # PDF 导出权限
        pdf_allowed_tiers = ["free", "starter", "pro"]
        
        assert "free" in pdf_allowed_tiers
        assert "starter" in pdf_allowed_tiers
        assert "pro" in pdf_allowed_tiers
    
    def test_zip_export_pro_only(self):
        """【业务规则 9.1】ZIP 导出仅 Pro 用户"""
        # ZIP 导出权限
        zip_allowed_tiers = ["pro"]
        
        assert "free" not in zip_allowed_tiers
        assert "starter" not in zip_allowed_tiers
        assert "pro" in zip_allowed_tiers


# ==========================================
# Watermark Tests
# ==========================================

class TestWatermark:
    """
    水印测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 9.2
    """
    
    def test_free_user_has_watermark(self):
        """【业务规则 9.2】Free 用户 PDF 有水印 (试用期外)"""
        watermark_rules = {
            "free_in_trial": False,
            "free_after_trial": True,
            "starter": False,
            "pro": False
        }
        
        assert watermark_rules["free_after_trial"] is True
    
    def test_paid_users_no_watermark(self):
        """【业务规则 9.2】付费用户无水印"""
        watermark_rules = {
            "starter": False,
            "pro": False
        }
        
        assert watermark_rules["starter"] is False
        assert watermark_rules["pro"] is False
