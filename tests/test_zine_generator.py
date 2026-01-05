"""
Zine Generator Tests
绘本生成测试
"""

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestDecodeBase64Image:
    def test_returns_none_for_none_input(self):
        from services.ai.zine_generator import decode_base64_image
        assert decode_base64_image(None) is None

    def test_returns_none_for_invalid_url(self):
        from services.ai.zine_generator import decode_base64_image
        assert decode_base64_image("http://example.com/image.png") is None

    def test_decodes_valid_base64(self):
        from services.ai.zine_generator import decode_base64_image
        import base64
        
        # Create a valid base64 data URL
        data = base64.b64encode(b"fake image data").decode()
        data_url = f"data:image/png;base64,{data}"
        
        result = decode_base64_image(data_url)
        
        assert result is not None
        assert isinstance(result, BytesIO)

    def test_returns_none_for_invalid_base64(self):
        from services.ai.zine_generator import decode_base64_image
        # Invalid base64 that will fail to decode
        result = decode_base64_image("data:image/png;base64,!!invalid!!")
        assert result is None


class TestDrawSmartImage:
    @patch('services.ai.zine_generator.ImageReader')
    def test_handles_none_source(self, mock_reader):
        from services.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        draw_smart_image(mock_canvas, None, 0, 0, 100, 100)
        
        mock_reader.assert_not_called()

    @patch('services.ai.zine_generator.decode_base64_image')
    @patch('services.ai.zine_generator.ImageReader')
    def test_handles_base64_source(self, mock_reader, mock_decode):
        from services.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        mock_img = MagicMock()
        mock_img.getSize.return_value = (200, 100)
        mock_reader.return_value = mock_img
        mock_decode.return_value = BytesIO(b"fake")
        
        draw_smart_image(mock_canvas, "data:image/png;base64,fake", 0, 0, 100, 100)
        
        mock_decode.assert_called_once()

    @patch('services.ai.zine_generator.ImageReader')
    def test_handles_url_source(self, mock_reader):
        from services.ai.zine_generator import draw_smart_image
        
        mock_canvas = MagicMock()
        mock_img = MagicMock()
        mock_img.getSize.return_value = (200, 100)
        mock_reader.return_value = mock_img
        
        draw_smart_image(mock_canvas, "http://example.com/img.png", 0, 0, 100, 100)
        
        mock_reader.assert_called_once()


class TestDrawWrappedText:
    @patch('services.ai.zine_generator.simpleSplit')
    def test_handles_none_text(self, mock_split):
        from services.ai.zine_generator import draw_wrapped_text
        
        mock_canvas = MagicMock()
        draw_wrapped_text(mock_canvas, None, 0, 0, 100)
        
        mock_split.assert_not_called()

    @patch('services.ai.zine_generator.simpleSplit')
    def test_wraps_text(self, mock_split):
        from services.ai.zine_generator import draw_wrapped_text
        
        mock_canvas = MagicMock()
        mock_split.return_value = ["Line 1", "Line 2"]
        
        draw_wrapped_text(mock_canvas, "Some long text", 100, 200, 100)
        
        mock_split.assert_called_once()
        assert mock_canvas.drawCentredString.call_count == 2


class TestPaperConfig:
    def test_us_letter_config(self):
        from services.ai.zine_generator import PAPER_CONFIG
        
        assert "US_LETTER" in PAPER_CONFIG
        assert PAPER_CONFIG["US_LETTER"]["name"] == "US Letter"

    def test_a4_config(self):
        from services.ai.zine_generator import PAPER_CONFIG
        
        assert "A4" in PAPER_CONFIG
        assert PAPER_CONFIG["A4"]["name"] == "International A4"


class TestCreateFoldableBook:
    @patch('services.ai.zine_generator.draw_smart_image')
    @patch('services.ai.zine_generator.draw_wrapped_text')
    def test_creates_pdf(self, mock_draw_text, mock_draw_image):
        from services.ai.zine_generator import create_foldable_book
        
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
        from services.ai.zine_generator import create_foldable_book
        
        buffer = BytesIO()
        create_foldable_book(
            image_paths=["url1"] * 8,
            text_list=["cap"] * 8,
            output_buffer=buffer,
            paper_type="A4"
        )
        
        buffer.seek(0)
        assert buffer.read(4) == b'%PDF'


class TestCreateAssetsZip:
    @patch('services.ai.zine_generator.requests.get')
    def test_creates_zip_from_urls(self, mock_get):
        from services.ai.zine_generator import create_assets_zip
        
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
        from services.ai.zine_generator import create_assets_zip
        
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
        from services.ai.zine_generator import create_assets_zip
        
        # None/empty URLs should be skipped
        buffer = BytesIO()
        create_assets_zip(
            image_urls=[None, "", "http://valid.com/img.png"],
            output_buffer=buffer
        )
        
        # Should have been called once for the valid URL
        mock_get.assert_called_once()
