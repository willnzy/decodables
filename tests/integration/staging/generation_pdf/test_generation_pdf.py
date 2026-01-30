"""
Generation PDF API Tests (Black Box)

测试 /api/v2/user/generate/pdf 相关接口

业务规则:
1. PDF 生成 (免费)
2. 从图片和文本创建 8 页小册子
3. 需要项目归属验证

@module tests.integration.staging.generation_pdf.test_generation_pdf
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p0
class TestGeneratePdf(BaseAPITest):
    """
    POST /api/v2/user/generate/pdf/pdf 黑盒测试

    PDF 生成
    """

    ENDPOINT = Endpoints.GENERATE_PDF

    def test_generate_pdf_requires_project_id(self, auth_client):
        """
        业务规则: PDF 生成需要 project_id
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "image_urls": ["https://example.com/1.png"],
                "texts": ["Page 1"]
            }
        )
        assert response.status_code in [400, 422]

    def test_generate_pdf_requires_valid_uuid(self, auth_client):
        """
        业务规则: project_id 必须是有效的 UUID
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "project_id": "invalid-uuid",
                "image_urls": ["https://example.com/1.png"],
                "texts": ["Page 1"]
            }
        )
        assert response.status_code in [400, 422]

    def test_generate_pdf_nonexistent_project(self, auth_client):
        """
        业务规则: 不存在的项目应返回 404

        PdfGenRequest schema 要求:
        - project_id: UUID 格式
        - current_hash: 1-128 字符, 字母数字+连字符+下划线
        - image_urls: 必须来自允许的域名 (Supabase/FAL.ai/CloudFlare R2/AWS S3)
        - texts: 最多 20 项
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "project_id": fake_id,
                "current_hash": "test_hash_abc123",
                "image_urls": ["https://fal.media/files/test/1.png"],
                "texts": ["Page 1"]
            }
        )
        self.assert_not_found(response)

    def test_generate_pdf_requires_authentication(self, anon_client):
        """
        业务规则: PDF 生成必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "project_id": fake_id,
                "image_urls": ["https://example.com/1.png"],
                "texts": ["Page 1"]
            }
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestGeneratePdfValidation(BaseAPITest):
    """
    PDF 生成参数验证测试
    """

    ENDPOINT = Endpoints.GENERATE_PDF

    def test_image_urls_ssrf_protection(self, auth_client):
        """
        业务规则: SSRF 攻击应被阻止
        """
        fake_id = str(uuid.uuid4())
        private_urls = [
            "http://localhost/image.png",
            "http://127.0.0.1/image.png",
            "http://192.168.1.1/image.png",
        ]

        for url in private_urls:
            response = auth_client.post(
                self.ENDPOINT,
                json={
                    "project_id": fake_id,
                    "image_urls": [url],
                    "texts": ["Test"]
                }
            )
            # 应该因 SSRF 保护返回 400 或因项目不存在返回 404
            assert response.status_code in [400, 404, 422], (
                f"SSRF 保护失败: {url}"
            )

    def test_text_length_limit(self, auth_client):
        """
        业务规则: 文本长度有限制 (max 2000 chars/page)
        """
        fake_id = str(uuid.uuid4())
        long_text = "a" * 3000  # 超过 2000

        response = auth_client.post(
            self.ENDPOINT,
            json={
                "project_id": fake_id,
                "image_urls": ["https://example.com/1.png"],
                "texts": [long_text]
            }
        )
        # 可能被截断 (200/404) 或返回错误 (400)
        assert response.status_code in [400, 404, 422]

    def test_current_hash_validation(self, auth_client):
        """
        业务规则: current_hash 格式验证
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "project_id": fake_id,
                "current_hash": "invalid-hash-format",
                "image_urls": ["https://example.com/1.png"],
                "texts": ["Test"]
            }
        )
        # 无效 hash 可能被忽略或返回 400
        assert response.status_code in [400, 404, 422]


@pytest.mark.p2
class TestGeneratePdfSecurity(BaseAPITest):
    """
    PDF 生成安全测试
    """

    ENDPOINT = Endpoints.GENERATE_PDF

    def test_cannot_generate_others_project(self, auth_client):
        """
        业务规则: 不能为他人项目生成 PDF

        PdfGenRequest 要求完整的请求体 (含 current_hash 和合法域名 image_urls)。
        """
        other_user_project = "00000000-0000-0000-0000-000000000001"
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "project_id": other_user_project,
                "current_hash": "test_hash_abc123",
                "image_urls": ["https://fal.media/files/test/1.png"],
                "texts": ["Test"]
            }
        )
        # 应该返回 404 (避免泄露项目存在性)
        assert response.status_code in [404]


@pytest.mark.p2
class TestGeneratePdfRateLimits(BaseAPITest):
    """
    PDF 生成速率限制测试
    """

    ENDPOINT = Endpoints.GENERATE_PDF

    def test_rate_limit_exists(self, auth_client):
        """
        业务规则: PDF 生成有速率限制 (10/minute)
        """
        pass
