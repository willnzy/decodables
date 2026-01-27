"""
Workspaces API Integration Tests (v3.33 Phase 2)

测试 Workspace 管理相关接口:
- GET /api/v2/user/workspaces - List workspaces
- GET /api/v2/user/workspaces/current - Get current workspace
- GET /api/v2/user/workspaces/{workspace_id} - Get workspace by ID
- PATCH /api/v2/user/workspaces/{workspace_id} - Update workspace
- DELETE /api/v2/user/workspaces/{workspace_id} - Delete workspace
- GET /api/v2/user/workspaces/{workspace_id}/stats - Get stats

TDD Approach:
- Sad Path First: 401 → 403 → 400 → 422 → 200
- Consumer-Driven Contracts
- Black-box testing based on API target behavior

@module tests.integration.staging.workspaces.test_workspaces
"""

import uuid
import pytest

from tests.integration.staging.constants import Endpoints


# ==========================================
# Base Test Class
# ==========================================

class BaseAPITest:
    """Base class with common assertion methods."""

    def assert_success(self, response, expected_status: int = 200) -> dict:
        """Assert successful response and return JSON data."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )
        return response.json()

    def assert_unauthorized(self, response):
        """Assert 401 Unauthorized."""
        assert response.status_code == 401, (
            f"Expected 401, got {response.status_code}"
        )

    def assert_forbidden(self, response):
        """Assert 403 Forbidden."""
        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}"
        )

    def assert_not_found(self, response):
        """Assert 404 Not Found."""
        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}"
        )

    def assert_bad_request(self, response):
        """Assert 400 Bad Request."""
        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}"
        )


# ==========================================
# Test: List Workspaces
# ==========================================

@pytest.mark.p1
class TestWorkspaceList(BaseAPITest):
    """
    GET /api/v2/user/workspaces 黑盒测试

    获取用户的工作区列表

    业务规则 (v3.33 Phase 2):
    1. 返回用户的所有工作区
    2. Phase 1: 每个用户有且仅有一个默认 Personal Workspace
    3. 工作区在用户注册时自动创建
    """

    ENDPOINT = Endpoints.WORKSPACES

    def test_list_workspaces_returns_list(self, auth_client):
        """
        业务规则: 返回工作区列表

        期望响应包含:
        - items: 工作区数组
        - total: 总数
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是数组"
        assert "total" in data, "响应应包含 total"

    def test_list_has_default_workspace(self, auth_client):
        """
        业务规则: Phase 1 用户至少有一个默认工作区
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        items = data.get("items", [])
        assert len(items) >= 1, "用户应该至少有一个工作区"

        # 检查默认工作区
        has_default = any(ws.get("is_default") for ws in items)
        assert has_default, "应该有一个默认工作区"

    def test_workspace_has_required_fields(self, auth_client):
        """
        业务规则: 工作区应包含必要字段
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        items = data.get("items", [])
        if items:
            workspace = items[0]
            required_fields = ["id", "name", "owner_id", "is_default", "is_personal"]
            for field in required_fields:
                assert field in workspace, f"工作区应包含 {field} 字段"

    def test_list_requires_authentication(self, anon_client):
        """
        业务规则: 工作区是私有数据，必须登录

        Sad Path First: 401 Unauthorized
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


# ==========================================
# Test: Get Current Workspace
# ==========================================

@pytest.mark.p1
class TestWorkspaceCurrent(BaseAPITest):
    """
    GET /api/v2/user/workspaces/current 黑盒测试

    获取当前(默认)工作区

    业务规则 (v3.33 Phase 2):
    1. Phase 1: 总是返回用户唯一的默认工作区
    2. Phase 2+: 可能支持工作区切换
    """

    ENDPOINT = Endpoints.WORKSPACES_CURRENT

    def test_get_current_workspace(self, auth_client):
        """
        业务规则: 返回当前工作区详情
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "id" in data, "应返回工作区 ID"
        assert "name" in data, "应返回工作区名称"
        assert data.get("is_default") is True, "当前工作区应是默认工作区"

    def test_current_is_personal(self, auth_client):
        """
        业务规则: Phase 1 当前工作区是 Personal Workspace
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert data.get("is_personal") is True, "当前工作区应是个人工作区"

    def test_current_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


# ==========================================
# Test: Get Workspace by ID
# ==========================================

@pytest.mark.p1
class TestWorkspaceGet(BaseAPITest):
    """
    GET /api/v2/user/workspaces/{workspace_id} 黑盒测试

    通过 ID 获取工作区详情

    业务规则 (v3.33 Phase 2):
    1. 只能访问自己拥有的工作区
    2. 返回工作区完整信息
    """

    CURRENT_ENDPOINT = Endpoints.WORKSPACES_CURRENT

    def test_get_workspace_by_id(self, auth_client):
        """
        业务规则: 通过 ID 获取工作区
        """
        # 先获取当前工作区
        current_resp = auth_client.get(self.CURRENT_ENDPOINT)
        current_data = self.assert_success(current_resp)
        workspace_id = current_data["id"]

        # 通过 ID 获取
        response = auth_client.get(Endpoints.workspace(workspace_id))
        data = self.assert_success(response)

        assert data["id"] == workspace_id, "应返回请求的工作区"

    def test_get_nonexistent_workspace_returns_404(self, auth_client):
        """
        业务规则: 工作区不存在返回 404

        Sad Path: Not Found
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.workspace(fake_id))
        self.assert_not_found(response)

    def test_get_invalid_id_format_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = auth_client.get(Endpoints.workspace("invalid-uuid"))
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_get_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.get(Endpoints.workspace(fake_id))
        self.assert_unauthorized(response)


# ==========================================
# Test: Update Workspace
# ==========================================

@pytest.mark.p1
class TestWorkspaceUpdate(BaseAPITest):
    """
    PATCH /api/v2/user/workspaces/{workspace_id} 黑盒测试

    更新工作区信息

    业务规则 (v3.33 Phase 2):
    1. Phase 1: 只能更新 name 和 description
    2. 只能更新自己拥有的工作区
    """

    CURRENT_ENDPOINT = Endpoints.WORKSPACES_CURRENT

    def test_update_workspace_name(self, auth_client):
        """
        业务规则: 可以更新工作区名称
        """
        # 获取当前工作区
        current_resp = auth_client.get(self.CURRENT_ENDPOINT)
        current_data = self.assert_success(current_resp)
        workspace_id = current_data["id"]
        original_name = current_data["name"]

        # 更新名称
        new_name = f"Updated_{uuid.uuid4().hex[:8]}"
        response = auth_client.patch(
            Endpoints.workspace(workspace_id),
            json={"name": new_name}
        )
        data = self.assert_success(response)

        assert data.get("name") == new_name, "名称应已更新"

        # 恢复原名称
        auth_client.patch(
            Endpoints.workspace(workspace_id),
            json={"name": original_name}
        )

    def test_update_workspace_description(self, auth_client):
        """
        业务规则: 可以更新工作区描述
        """
        # 获取当前工作区
        current_resp = auth_client.get(self.CURRENT_ENDPOINT)
        current_data = self.assert_success(current_resp)
        workspace_id = current_data["id"]

        # 更新描述
        new_desc = f"Test description {uuid.uuid4().hex[:8]}"
        response = auth_client.patch(
            Endpoints.workspace(workspace_id),
            json={"description": new_desc}
        )
        data = self.assert_success(response)

        assert data.get("description") == new_desc, "描述应已更新"

    def test_update_nonexistent_workspace_returns_404(self, auth_client):
        """
        业务规则: 工作区不存在返回 404

        Sad Path: Not Found
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.patch(
            Endpoints.workspace(fake_id),
            json={"name": "Test"}
        )
        self.assert_not_found(response)

    def test_update_empty_body_rejected(self, auth_client):
        """
        业务规则: 空更新请求应被拒绝

        Sad Path: 验证错误
        """
        # 获取当前工作区
        current_resp = auth_client.get(self.CURRENT_ENDPOINT)
        current_data = self.assert_success(current_resp)
        workspace_id = current_data["id"]

        # 发送空更新
        response = auth_client.patch(
            Endpoints.workspace(workspace_id),
            json={}
        )

        assert response.status_code in [400, 422], (
            f"空更新应被拒绝，但返回了 {response.status_code}"
        )

    def test_update_invalid_id_format_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = auth_client.patch(
            Endpoints.workspace("invalid-uuid"),
            json={"name": "Test"}
        )
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_update_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.patch(
            Endpoints.workspace(fake_id),
            json={"name": "Test"}
        )
        self.assert_unauthorized(response)

    def test_update_name_too_long_rejected(self, auth_client):
        """
        业务规则: 名称超过最大长度应被拒绝

        Sad Path: 验证错误 (max_length=100)
        """
        current_resp = auth_client.get(self.CURRENT_ENDPOINT)
        current_data = self.assert_success(current_resp)
        workspace_id = current_data["id"]

        response = auth_client.patch(
            Endpoints.workspace(workspace_id),
            json={"name": "x" * 101}  # 超过 100 字符
        )

        assert response.status_code in [400, 422], (
            f"过长名称应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Delete Workspace
# ==========================================

@pytest.mark.p2
class TestWorkspaceDelete(BaseAPITest):
    """
    DELETE /api/v2/user/workspaces/{workspace_id} 黑盒测试

    删除工作区

    业务规则 (v3.33 Phase 2):
    1. Phase 1: 不能删除默认工作区
    2. Phase 2+: 支持删除非默认工作区
    """

    CURRENT_ENDPOINT = Endpoints.WORKSPACES_CURRENT

    def test_delete_default_workspace_rejected(self, auth_client):
        """
        业务规则: Phase 1 不能删除默认工作区

        Sad Path: 业务规则限制
        """
        # 获取当前默认工作区
        current_resp = auth_client.get(self.CURRENT_ENDPOINT)
        current_data = self.assert_success(current_resp)
        workspace_id = current_data["id"]

        # 尝试删除默认工作区
        response = auth_client.delete(Endpoints.workspace(workspace_id))

        # 应返回 400 (业务规则) 或 403 (权限)
        assert response.status_code in [400, 403], (
            f"删除默认工作区应被拒绝，但返回了 {response.status_code}"
        )

    def test_delete_nonexistent_workspace_returns_404(self, auth_client):
        """
        业务规则: 工作区不存在返回 404

        Sad Path: Not Found
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.workspace(fake_id))
        self.assert_not_found(response)

    def test_delete_invalid_id_format_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = auth_client.delete(Endpoints.workspace("invalid-uuid"))
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_delete_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.delete(Endpoints.workspace(fake_id))
        self.assert_unauthorized(response)


# ==========================================
# Test: Workspace Stats
# ==========================================

@pytest.mark.p2
class TestWorkspaceStats(BaseAPITest):
    """
    GET /api/v2/user/workspaces/{workspace_id}/stats 黑盒测试

    获取工作区统计信息

    业务规则 (v3.33 Phase 2):
    1. 返回标签、项目、素材数量
    2. 只能查看自己工作区的统计
    """

    CURRENT_ENDPOINT = Endpoints.WORKSPACES_CURRENT

    def test_get_workspace_stats(self, auth_client):
        """
        业务规则: 返回工作区统计信息
        """
        # 获取当前工作区
        current_resp = auth_client.get(self.CURRENT_ENDPOINT)
        current_data = self.assert_success(current_resp)
        workspace_id = current_data["id"]

        # 获取统计
        response = auth_client.get(Endpoints.workspace_stats(workspace_id))
        data = self.assert_success(response)

        assert "workspace_id" in data, "应包含 workspace_id"
        assert "tag_count" in data, "应包含 tag_count"

    def test_stats_nonexistent_workspace_returns_404(self, auth_client):
        """
        业务规则: 工作区不存在返回 404

        Sad Path: Not Found
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.workspace_stats(fake_id))
        self.assert_not_found(response)

    def test_stats_invalid_id_format_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = auth_client.get(Endpoints.workspace_stats("invalid-uuid"))
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_stats_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.get(Endpoints.workspace_stats(fake_id))
        self.assert_unauthorized(response)
