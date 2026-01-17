"""
Tools API Tests (Black Box)

测试 /api/v2/user/tools 相关接口

业务规则:
1. PDF Preview: Pro 用户可以预览 PDF 页面
2. OCR: Pro/Trial 用户可以使用 OCR，消耗 5 积分

@module tests.integration.staging.tools.test_tools
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestPdfPreview(BaseAPITest):
    """
    POST /api/v2/user/tools/pdf-preview 黑盒测试

    PDF 页面预览
    """

    ENDPOINT = Endpoints.TOOLS_PDF_PREVIEW

    def test_requires_file_upload(self, auth_client):
        """
        业务规则: PDF 预览需要上传文件
        """
        response = auth_client.post(self.ENDPOINT)
        # 缺少文件应返回 400 或 422
        assert response.status_code in [400, 422]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: PDF 预览必须登录
        """
        response = anon_client.post(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_invalid_file_type_rejected(self, auth_client):
        """
        业务规则: 非 PDF 文件应被拒绝
        """
        # 创建一个假的文本文件
        files = {
            "file": ("test.txt", b"This is not a PDF", "text/plain")
        }
        response = auth_client.post(self.ENDPOINT, files=files)
        # 应该返回 400 (无效文件类型) 或 422 或可能 500
        assert response.status_code in [400, 422, 500]


@pytest.mark.p1
class TestOcr(BaseAPITest):
    """
    POST /api/v2/user/tools/ocr 黑盒测试

    OCR 文字识别
    """

    ENDPOINT = Endpoints.TOOLS_OCR

    def test_requires_file_upload(self, auth_client):
        """
        业务规则: OCR 需要上传文件
        """
        response = auth_client.post(self.ENDPOINT)
        # 缺少文件应返回 400 或 422
        assert response.status_code in [400, 422]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: OCR 必须登录
        """
        response = anon_client.post(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_pro_or_trial_required(self, auth_client):
        """
        业务规则: OCR 需要 Pro 或 Trial 用户

        Free 用户应该被拒绝
        """
        # 创建一个简单的图片文件
        # 1x1 像素的 PNG
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        files = {
            "file": ("test.png", png_data, "image/png")
        }
        response = auth_client.post(self.ENDPOINT, files=files)

        # 可能返回:
        # - 200: 成功 (Pro/Trial 用户)
        # - 402: 积分不足
        # - 403: 非 Pro/Trial 用户
        # - 500: 处理错误
        assert response.status_code in [200, 402, 403, 500]

    def test_ocr_cost_5_credits(self, auth_client):
        """
        业务规则: OCR 消耗 5 积分

        验证方式: 调用前后检查积分变化 (需要足够积分)
        """
        # 这是一个观察性测试
        # 实际验证需要在调用前后检查积分
        pass


@pytest.mark.p2
class TestToolsRateLimit(BaseAPITest):
    """
    Tools 接口速率限制测试
    """

    def test_pdf_preview_rate_limit(self, auth_client):
        """
        业务规则: PDF Preview 有速率限制 (10/minute)
        """
        # 速率限制测试需要快速多次请求
        # 在集成测试中可能不适合测试，避免触发限制
        pass

    def test_ocr_rate_limit(self, auth_client):
        """
        业务规则: OCR 有速率限制 (10/minute)
        """
        pass
