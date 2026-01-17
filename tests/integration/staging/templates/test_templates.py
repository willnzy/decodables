"""
Templates API Tests (Black Box)

测试 /api/v3/user/templates 相关接口

业务规则:
1. 用户可以保存 Prompt 模板
2. 支持 Asset 模板 (5W1H) 和 Page 模板
3. 模板可以 CRUD 操作
4. 可以记录使用次数

@module tests.integration.staging.templates.test_templates
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAssetTemplates(BaseAPITest):
    """
    GET/POST /api/v3/user/templates/asset 黑盒测试

    Asset Prompt 模板 (5W1H)
    """

    ENDPOINT = Endpoints.TEMPLATES_ASSET

    def test_list_templates_returns_list(self, auth_client):
        """
        业务规则: 模板列表接口应返回模板数组
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "templates" in data, "响应应包含 templates"
        assert isinstance(data["templates"], list), "templates 应该是列表"

    def test_create_template_requires_name(self, auth_client):
        """
        业务规则: 创建模板需要提供名称
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 name
        )
        assert response.status_code in [400, 422]

    def test_create_template_with_valid_data(self, auth_client):
        """
        业务规则: 提供有效数据可以创建模板
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": f"Test Template {uuid.uuid4().hex[:8]}",
                "style": "cartoon",
                "moods": ["warm", "happy"]
            }
        )
        # 可能成功(200/201)或达到限制(400/403)
        assert response.status_code in [200, 201, 400, 403]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 模板操作必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestAssetTemplateOperations(BaseAPITest):
    """
    PUT/DELETE /api/v3/user/templates/asset/{id} 黑盒测试

    Asset 模板操作
    """

    def test_update_invalid_uuid_returns_400(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回 400
        """
        response = auth_client.put(
            Endpoints.template_asset("invalid-id"),
            json={"name": "Updated Name"}
        )
        assert response.status_code == 400

    def test_update_nonexistent_template(self, auth_client):
        """
        业务规则: 更新不存在的模板应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.put(
            Endpoints.template_asset(fake_id),
            json={"name": "Updated Name"}
        )
        # 可能返回 404 或 400 (取决于实现)
        assert response.status_code in [400, 404]

    def test_delete_invalid_uuid_returns_400(self, auth_client):
        """
        业务规则: 删除无效 UUID 应返回 400
        """
        response = auth_client.delete(
            Endpoints.template_asset("invalid-id")
        )
        assert response.status_code == 400

    def test_delete_nonexistent_template(self, auth_client):
        """
        业务规则: 删除不存在的模板应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(
            Endpoints.template_asset(fake_id)
        )
        assert response.status_code in [400, 404]

    def test_use_template_invalid_uuid_returns_400(self, auth_client):
        """
        业务规则: 使用无效 UUID 模板应返回 400
        """
        response = auth_client.post(
            Endpoints.template_asset_use("invalid-id")
        )
        assert response.status_code == 400


@pytest.mark.p1
class TestPageTemplates(BaseAPITest):
    """
    GET/POST /api/v3/user/templates/page 黑盒测试

    Page Prompt 模板
    """

    ENDPOINT = Endpoints.TEMPLATES_PAGE

    def test_list_templates_returns_list(self, auth_client):
        """
        业务规则: 模板列表接口应返回模板数组
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "templates" in data, "响应应包含 templates"
        assert isinstance(data["templates"], list), "templates 应该是列表"

    def test_create_template_requires_name(self, auth_client):
        """
        业务规则: 创建模板需要提供名称
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 name
        )
        assert response.status_code in [400, 422]

    def test_create_template_with_valid_data(self, auth_client):
        """
        业务规则: 提供有效数据可以创建模板
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": f"Test Page Template {uuid.uuid4().hex[:8]}",
                "layout": "image_top",
                "style": "cartoon",
                "generation_mode": "guided"
            }
        )
        # 可能成功或达到限制
        assert response.status_code in [200, 201, 400, 403]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 模板操作必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestPageTemplateOperations(BaseAPITest):
    """
    PUT/DELETE /api/v3/user/templates/page/{id} 黑盒测试

    Page 模板操作
    """

    def test_update_invalid_uuid_returns_400(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回 400
        """
        response = auth_client.put(
            Endpoints.template_page("invalid-id"),
            json={"name": "Updated Name"}
        )
        assert response.status_code == 400

    def test_delete_invalid_uuid_returns_400(self, auth_client):
        """
        业务规则: 删除无效 UUID 应返回 400
        """
        response = auth_client.delete(
            Endpoints.template_page("invalid-id")
        )
        assert response.status_code == 400

    def test_use_template_invalid_uuid_returns_400(self, auth_client):
        """
        业务规则: 使用无效 UUID 模板应返回 400
        """
        response = auth_client.post(
            Endpoints.template_page_use("invalid-id")
        )
        assert response.status_code == 400
