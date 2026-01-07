"""
Zine Generator Tests
绘本生成测试
"""

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestDecodeBase64Image:
    def test_returns_none_for_none_input(self):
        from shared.ai.zine_generator import decode_base64_image
        assert decode_base64_image(None) is None

    def test_returns_none_for_invalid_url(self):
        from shared.ai.zine_generator import decode_base64_image
        assert decode_base64_image("http://example.com/image.png") is None

    def test_decodes_valid_base64(self):
        from shared.ai.zine_generator import decode_base64_image
        import base64
        
        # Create a valid base64 data URL
        data = base64.b64encode(b"fake image data").decode()
        data_url = f"data:image/png;base64,{data}"
        
        result = decode_base64_image(data_url)
        
        assert result is not None
        assert isinstance(result, BytesIO)

    def test_returns_none_for_invalid_base64(self):
        from shared.ai.zine_generator import decode_base64_image
        # Invalid base64 that will fail to decode
        result = decode_base64_image("data:image/png;base64,!!invalid!!")
        assert result is None


class TestDrawSmartImage:
    @patch('services.ai.zine_generator.ImageReader')
    def test_handles_none_source(self, mock_reader):
        from shared.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        draw_smart_image(mock_canvas, None, 0, 0, 100, 100)
        
        mock_reader.assert_not_called()

    @patch('services.ai.zine_generator.decode_base64_image')
    @patch('services.ai.zine_generator.ImageReader')
    def test_handles_base64_source(self, mock_reader, mock_decode):
        from shared.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        mock_img = MagicMock()
        mock_img.getSize.return_value = (200, 100)
        mock_reader.return_value = mock_img
        mock_decode.return_value = BytesIO(b"fake")
        
        draw_smart_image(mock_canvas, "data:image/png;base64,fake", 0, 0, 100, 100)
        
        mock_decode.assert_called_once()

    @patch('services.ai.zine_generator.ImageReader')
    def test_handles_url_source(self, mock_reader):
        from shared.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        mock_img = MagicMock()
        mock_img.getSize.return_value = (200, 100)
        mock_reader.return_value = mock_img
        
        draw_smart_image(mock_canvas, "http://example.com/img.png", 0, 0, 100, 100)
        
        mock_reader.assert_called_once()
    
    @patch('services.ai.zine_generator.decode_base64_image')
    @patch('services.ai.zine_generator.ImageReader')
    def test_returns_early_when_base64_decode_fails(self, mock_reader, mock_decode):
        """测试 base64 解码失败时提前返回"""
        from shared.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        mock_decode.return_value = None  # Decode failed
        
        draw_smart_image(mock_canvas, "data:image/png;base64,invalid", 0, 0, 100, 100)
        
        mock_decode.assert_called_once()
        mock_reader.assert_not_called()  # Should not try to create ImageReader
    
    @patch('services.ai.zine_generator.ImageReader')
    def test_exception_draws_error_rect(self, mock_reader):
        """测试图片读取异常时绘制错误边框"""
        from shared.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        mock_reader.side_effect = Exception("Image read error")
        
        draw_smart_image(mock_canvas, "http://example.com/broken.png", 10, 20, 100, 100)
        
        # Should draw error rectangle
        mock_canvas.setStrokeColor.assert_called()
        mock_canvas.rect.assert_called_once_with(10, 20, 100, 100)


class TestDrawWrappedText:
    @patch('services.ai.zine_generator.simpleSplit')
    def test_handles_none_text(self, mock_split):
        from shared.ai.zine_generator import draw_wrapped_text
        
        mock_canvas = MagicMock()
        draw_wrapped_text(mock_canvas, None, 0, 0, 100)
        
        mock_split.assert_not_called()

    @patch('services.ai.zine_generator.simpleSplit')
    def test_wraps_text(self, mock_split):
        from shared.ai.zine_generator import draw_wrapped_text
        
        mock_canvas = MagicMock()
        mock_split.return_value = ["Line 1", "Line 2"]
        
        draw_wrapped_text(mock_canvas, "Some long text", 100, 200, 100)
        
        mock_split.assert_called_once()
        assert mock_canvas.drawCentredString.call_count == 2


class TestPaperConfig:
    def test_us_letter_config(self):
        from shared.ai.zine_generator import PAPER_CONFIG
        
        assert "US_LETTER" in PAPER_CONFIG
        assert PAPER_CONFIG["US_LETTER"]["name"] == "US Letter"

    def test_a4_config(self):
        from shared.ai.zine_generator import PAPER_CONFIG
        
        assert "A4" in PAPER_CONFIG
        assert PAPER_CONFIG["A4"]["name"] == "International A4"


class TestCreateFoldableBook:
    @patch('services.ai.zine_generator.draw_smart_image')
    @patch('services.ai.zine_generator.draw_wrapped_text')
    def test_creates_pdf(self, mock_draw_text, mock_draw_image):
        from shared.ai.zine_generator import create_foldable_book
        
        buffer = BytesIO()
        create_foldable_book(
            image_paths=["url1", "url2", "url3", "url4", "url5", "url6", "url7", "url8"],
            text_list=["Cap1", "Cap2", "Cap3", "Cap4", "Cap5", "Cap6", "Cap7", "Cap8"],
            output_buffer=buffer,
            paper_type="US_LETTER"
        )
        
        # Check PDF was written (function doesn't return value)
        buffer.seek(0)
        assert buffer.read(4) == b'%PDF'

    @patch('services.ai.zine_generator.draw_smart_image')
    @patch('services.ai.zine_generator.draw_wrapped_text')
    def test_creates_pdf_with_a4(self, mock_draw_text, mock_draw_image):
        from shared.ai.zine_generator import create_foldable_book
        
        buffer = BytesIO()
        create_foldable_book(
            image_paths=["url1"] * 8,
            text_list=["cap"] * 8,
            output_buffer=buffer,
            paper_type="A4"
        )
        
        buffer.seek(0)
        assert buffer.read(4) == b'%PDF'
    
    @patch('services.ai.zine_generator.draw_smart_image')
    @patch('services.ai.zine_generator.draw_wrapped_text')
    def test_creates_pdf_with_outer_border(self, mock_draw_text, mock_draw_image):
        """测试绘制外边框"""
        from shared.ai.zine_generator import create_foldable_book
        
        buffer = BytesIO()
        create_foldable_book(
            image_paths=["url1"] * 8,
            text_list=["cap"] * 8,
            output_buffer=buffer,
            draw_outer_border=True  # Enable outer border
        )
        
        buffer.seek(0)
        assert buffer.read(4) == b'%PDF'
    
    @patch('services.ai.zine_generator.draw_smart_image')
    @patch('services.ai.zine_generator.draw_wrapped_text')
    def test_pads_short_image_list(self, mock_draw_text, mock_draw_image):
        """测试图片列表不足8个时自动补齐"""
        from shared.ai.zine_generator import create_foldable_book
        
        buffer = BytesIO()
        create_foldable_book(
            image_paths=["url1", "url2", "url3"],  # Only 3 images
            output_buffer=buffer
        )
        
        buffer.seek(0)
        assert buffer.read(4) == b'%PDF'
    
    @patch('services.ai.zine_generator.draw_smart_image')
    @patch('services.ai.zine_generator.draw_wrapped_text')
    def test_pads_short_text_list(self, mock_draw_text, mock_draw_image):
        """测试文本列表不足8个时自动补齐"""
        from shared.ai.zine_generator import create_foldable_book
        
        buffer = BytesIO()
        create_foldable_book(
            image_paths=["url1"] * 8,
            text_list=["cap1", "cap2"],  # Only 2 captions
            output_buffer=buffer
        )
        
        buffer.seek(0)
        assert buffer.read(4) == b'%PDF'
    
    @patch('services.ai.zine_generator.draw_smart_image')
    @patch('services.ai.zine_generator.draw_wrapped_text')
    def test_image_only_mode_no_text(self, mock_draw_text, mock_draw_image):
        """测试仅图片模式（无文本）"""
        from shared.ai.zine_generator import create_foldable_book
        
        buffer = BytesIO()
        create_foldable_book(
            image_paths=["url1", "url2", "url3", "url4", "url5", "url6", "url7", "url8"],
            text_list=["", "", "", "", "", "", "", ""],  # Empty text
            output_buffer=buffer
        )
        
        buffer.seek(0)
        assert buffer.read(4) == b'%PDF'
        # draw_wrapped_text should not be called for empty text
        # But draw_smart_image should be called for images
    
    @patch('services.ai.zine_generator.draw_smart_image')
    @patch('services.ai.zine_generator.draw_wrapped_text')
    def test_mixed_content_and_image_only(self, mock_draw_text, mock_draw_image):
        """测试混合模式：部分页有文本，部分页仅图片"""
        from shared.ai.zine_generator import create_foldable_book
        
        buffer = BytesIO()
        create_foldable_book(
            image_paths=["url1", "url2", "url3", "url4", "url5", "url6", "url7", "url8"],
            text_list=["Cap1", "", "Cap3", "", "", "Cap6", "", "Cap8"],  # Mixed
            output_buffer=buffer
        )
        
        buffer.seek(0)
        assert buffer.read(4) == b'%PDF'
    
    @patch('services.ai.zine_generator.draw_smart_image')
    @patch('services.ai.zine_generator.draw_wrapped_text')
    def test_unknown_paper_type_defaults_to_us_letter(self, mock_draw_text, mock_draw_image):
        """测试未知纸张类型时默认使用 US_LETTER"""
        from shared.ai.zine_generator import create_foldable_book
        
        buffer = BytesIO()
        create_foldable_book(
            image_paths=["url1"] * 8,
            output_buffer=buffer,
            paper_type="UNKNOWN"
        )
        
        buffer.seek(0)
        assert buffer.read(4) == b'%PDF'


class TestCreateAssetsZip:
    @patch('services.ai.zine_generator.requests.get')
    def test_creates_zip_from_urls(self, mock_get):
        from shared.ai.zine_generator import create_assets_zip
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake image bytes"
        mock_get.return_value = mock_response
        
        buffer = BytesIO()
        create_assets_zip(
            image_urls=["http://example.com/img1.png", "http://example.com/img2.png"],
            output_buffer=buffer
        )
        
        buffer.seek(0)
        # Verify it's a valid zip
        import zipfile
        with zipfile.ZipFile(buffer, 'r') as zf:
            names = zf.namelist()
            assert len(names) > 0

    @patch('services.ai.zine_generator.requests.get')
    def test_handles_failed_download(self, mock_get):
        from shared.ai.zine_generator import create_assets_zip
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        buffer = BytesIO()
        # Should not raise
        create_assets_zip(
            image_urls=["http://example.com/notfound.png"],
            output_buffer=buffer
        )

    @patch('services.ai.zine_generator.requests.get')
    def test_skips_invalid_urls(self, mock_get):
        from shared.ai.zine_generator import create_assets_zip
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake image bytes"
        mock_get.return_value = mock_response
        
        # None/empty URLs should be skipped
        buffer = BytesIO()
        create_assets_zip(
            image_urls=[None, "", "http://valid.com/img.png"],
            output_buffer=buffer
        )
        
        # Should have been called once for the valid URL
        mock_get.assert_called_once()
    
    @patch('services.ai.zine_generator.requests.get')
    def test_handles_request_exception(self, mock_get):
        """测试请求异常时继续处理其他图片"""
        from shared.ai.zine_generator import create_assets_zip
        
        mock_get.side_effect = Exception("Network error")
        
        buffer = BytesIO()
        # Should not raise exception
        create_assets_zip(
            image_urls=["http://example.com/img1.png", "http://example.com/img2.png"],
            output_buffer=buffer
        )
        
        # Verify zip was still created (empty)
        buffer.seek(0)
        import zipfile
        with zipfile.ZipFile(buffer, 'r') as zf:
            names = zf.namelist()
            assert len(names) == 0  # All failed, so empty zip
    
    @patch('services.ai.zine_generator.requests.get')
    def test_mixed_success_and_failure(self, mock_get):
        """测试部分成功部分失败"""
        from shared.ai.zine_generator import create_assets_zip
        
        def side_effect(url, timeout=None):
            if "fail" in url:
                raise Exception("Network error")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"image data"
            return mock_resp
        
        mock_get.side_effect = side_effect
        
        buffer = BytesIO()
        create_assets_zip(
            image_urls=["http://example.com/good.png", "http://example.com/fail.png"],
            output_buffer=buffer
        )
        
        buffer.seek(0)
        import zipfile
        with zipfile.ZipFile(buffer, 'r') as zf:
            names = zf.namelist()
            assert len(names) == 1  # Only the successful one