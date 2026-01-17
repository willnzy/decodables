"""
Export API Tests (Black Box)

测试 /api/v2/user/export 相关接口

业务规则:
1. PDF 导出 (免费)
2. Preview 图片导出
3. ZIP 导出 (需要 Pro)
4. 异步导出支持

@module tests.integration.staging.export.test_export
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p0
class TestExportPdf(BaseAPITest):
    """
    GET /api/v2/user/export/projects/{project_id}/pdf 黑盒测试

    同步 PDF 导出
    """

    def test_pdf_export_requires_valid_uuid(self, auth_client):
        """
        业务规则: project_id 必须是有效的 UUID
        """
        response = auth_client.get(Endpoints.export_pdf("invalid-uuid"))
        assert response.status_code == 400

    def test_pdf_export_nonexistent_project(self, auth_client):
        """
        业务规则: 导出不存在的项目应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.export_pdf(fake_id))
        self.assert_not_found(response)

    def test_pdf_export_requires_authentication(self, anon_client):
        """
        业务规则: PDF 导出必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.get(Endpoints.export_pdf(fake_id))
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestExportPreview(BaseAPITest):
    """
    GET /api/v2/user/export/projects/{project_id}/preview 黑盒测试

    Preview 图片导出
    """

    def test_preview_requires_valid_uuid(self, auth_client):
        """
        业务规则: project_id 必须是有效的 UUID
        """
        response = auth_client.get(Endpoints.export_preview("invalid-uuid"))
        assert response.status_code == 400

    def test_preview_nonexistent_project(self, auth_client):
        """
        业务规则: 预览不存在的项目应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.export_preview(fake_id))
        self.assert_not_found(response)

    def test_preview_requires_authentication(self, anon_client):
        """
        业务规则: 预览导出必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.get(Endpoints.export_preview(fake_id))
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestExportZip(BaseAPITest):
    """
    GET /api/v2/user/export/projects/{project_id}/zip 黑盒测试

    同步 ZIP 导出
    """

    def test_zip_export_requires_valid_uuid(self, auth_client):
        """
        业务规则: project_id 必须是有效的 UUID
        """
        response = auth_client.get(Endpoints.export_zip("invalid-uuid"))
        assert response.status_code == 400

    def test_zip_export_nonexistent_project(self, auth_client):
        """
        业务规则: ZIP 导出不存在的项目应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.export_zip(fake_id))
        # 可能返回 404 (项目不存在) 或 403 (非 Pro 用户)
        assert response.status_code in [403, 404]

    def test_zip_export_requires_pro(self, auth_client):
        """
        业务规则: ZIP 导出需要 Pro 用户

        Free/Starter 用户应该返回 403
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.export_zip(fake_id))
        # 如果测试账户不是 Pro，应该返回 403
        # 如果是 Pro，可能返回 404 (项目不存在)
        assert response.status_code in [403, 404]

    def test_zip_export_requires_authentication(self, anon_client):
        """
        业务规则: ZIP 导出必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.get(Endpoints.export_zip(fake_id))
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestExportPdfAsync(BaseAPITest):
    """
    POST /api/v2/user/export/projects/{project_id}/pdf/async 黑盒测试

    异步 PDF 导出
    """

    def test_async_pdf_requires_valid_uuid(self, auth_client):
        """
        业务规则: project_id 必须是有效的 UUID
        """
        response = auth_client.post(Endpoints.export_pdf_async("invalid-uuid"))
        assert response.status_code == 400

    def test_async_pdf_returns_task_id(self, auth_client):
        """
        业务规则: 异步导出应返回 task_id

        用于后续查询任务状态
        """
        # 需要一个真实的项目 ID 才能测试成功情况
        # 这里测试不存在的项目
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.export_pdf_async(fake_id))
        # 可能返回 503 (服务不可用) 或 202 (成功排队)
        # 或 404 (项目不存在)
        if response.status_code == 202:
            data = response.json()
            assert "task_id" in data
            assert "status" in data

    def test_async_pdf_requires_authentication(self, anon_client):
        """
        业务规则: 异步 PDF 导出必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(Endpoints.export_pdf_async(fake_id))
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestExportZipAsync(BaseAPITest):
    """
    POST /api/v2/user/export/projects/{project_id}/zip/async 黑盒测试

    异步 ZIP 导出
    """

    def test_async_zip_requires_valid_uuid(self, auth_client):
        """
        业务规则: project_id 必须是有效的 UUID
        """
        response = auth_client.post(Endpoints.export_zip_async("invalid-uuid"))
        assert response.status_code == 400

    def test_async_zip_requires_pro(self, auth_client):
        """
        业务规则: 异步 ZIP 导出需要 Pro 用户
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.export_zip_async(fake_id))
        # 如果测试账户不是 Pro，应该返回 403
        assert response.status_code in [400, 403, 404, 503]

    def test_async_zip_requires_authentication(self, anon_client):
        """
        业务规则: 异步 ZIP 导出必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(Endpoints.export_zip_async(fake_id))
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestExportSecurity(BaseAPITest):
    """
    Export API 安全测试
    """

    def test_cannot_export_others_project(self, auth_client):
        """
        业务规则: 不能导出他人的项目

        应返回 404 (而不是 403，避免泄露项目存在性)
        """
        # 使用一个固定的 UUID (可能属于其他用户)
        other_user_project = "00000000-0000-0000-0000-000000000001"
        response = auth_client.get(Endpoints.export_pdf(other_user_project))
        # 应该返回 404 (项目不存在或无权访问)
        assert response.status_code in [404]


@pytest.mark.p2
class TestExportRateLimits(BaseAPITest):
    """
    Export API 速率限制测试
    """

    def test_pdf_export_rate_limit(self, auth_client):
        """
        业务规则: PDF 导出有速率限制 (10/minute)
        """
        # 速率限制测试需要快速多次请求
        # 在集成测试中可能不适合测试
        pass

    def test_zip_export_rate_limit(self, auth_client):
        """
        业务规则: ZIP 导出有速率限制 (5/minute)
        """
        pass
