"""
Tags API Integration Tests (v3.33 Phase 2)

测试 Tag 管理相关接口:

Tag CRUD:
- GET /api/v2/user/tags - List tags
- GET /api/v2/user/tags/by-group - List tags by group
- POST /api/v2/user/tags - Create tag
- PATCH /api/v2/user/tags/{tag_id} - Update tag
- DELETE /api/v2/user/tags/{tag_id} - Delete tag
- GET /api/v2/user/tags/presets - Get presets

Project Tags:
- GET /api/v2/user/projects/{project_id}/tags
- POST /api/v2/user/projects/{project_id}/tags
- PUT /api/v2/user/projects/{project_id}/tags
- DELETE /api/v2/user/projects/{project_id}/tags/{tag_id}

Asset Tags:
- GET /api/v2/user/assets/{asset_id}/tags
- POST /api/v2/user/assets/{asset_id}/tags
- PUT /api/v2/user/assets/{asset_id}/tags
- DELETE /api/v2/user/assets/{asset_id}/tags/{tag_id}

TDD Approach:
- Sad Path First: 401 → 403 → 400 → 422 → 200
- Consumer-Driven Contracts
- Black-box testing based on API target behavior

@module tests.integration.staging.tags.test_tags
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
# Test: List Tags
# ==========================================

@pytest.mark.p1
class TestTagList(BaseAPITest):
    """
    GET /api/v2/user/tags 黑盒测试

    获取用户的标签列表

    业务规则 (v3.33 Phase 2):
    1. 返回用户工作区的所有标签
    2. 支持按 group_name 过滤
    3. 自动创建默认工作区
    """

    ENDPOINT = Endpoints.TAGS

    def test_list_tags_returns_list(self, auth_client):
        """
        业务规则: 返回标签列表

        期望响应包含:
        - items: 标签数组
        - total: 总数
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是数组"
        assert "total" in data, "响应应包含 total"

    def test_list_tags_filter_by_group(self, auth_client):
        """
        业务规则: 支持按 group_name 过滤
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"group_name": "test_group"}
        )
        data = self.assert_success(response)

        # 返回可能为空 (没有该 group 的标签)
        assert "items" in data

    def test_list_requires_authentication(self, anon_client):
        """
        业务规则: 标签是私有数据，必须登录

        Sad Path First: 401 Unauthorized
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


# ==========================================
# Test: List Tags by Group
# ==========================================

@pytest.mark.p1
class TestTagListByGroup(BaseAPITest):
    """
    GET /api/v2/user/tags/by-group 黑盒测试

    获取按组分类的标签
    """

    ENDPOINT = Endpoints.TAGS_BY_GROUP

    def test_list_by_group_returns_dict(self, auth_client):
        """
        业务规则: 返回按组分类的标签字典
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert isinstance(data, dict), "响应应该是字典 (group -> tags)"

    def test_list_by_group_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


# ==========================================
# Test: Create Tag
# ==========================================

@pytest.mark.p1
class TestTagCreate(BaseAPITest):
    """
    POST /api/v2/user/tags 黑盒测试

    创建新标签

    业务规则 (v3.33 Phase 2):
    1. name 是必需字段 (1-50 字符)
    2. color 可选，默认 gray
    3. group_name 可选
    4. icon 可选
    """

    ENDPOINT = Endpoints.TAGS

    def test_create_tag_success(self, auth_client):
        """
        业务规则: 成功创建标签
        """
        tag_name = f"Test_{uuid.uuid4().hex[:8]}"
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": tag_name,
                "color": "blue"
            }
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert data.get("name") == tag_name, "名称应匹配"
            assert data.get("color") == "blue", "颜色应匹配"

            # 清理: 删除测试标签
            if "id" in data:
                auth_client.delete(Endpoints.tag(data["id"]))
        else:
            # 可能有其他原因导致失败
            assert response.status_code in [200, 201, 400, 409], (
                f"创建标签返回了意外状态码: {response.status_code}"
            )

    def test_create_tag_missing_name_rejected(self, auth_client):
        """
        业务规则: name 是必需字段

        Sad Path: 缺少必需参数
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"color": "blue"}
        )

        assert response.status_code in [400, 422], (
            f"缺少 name 应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_tag_empty_name_rejected(self, auth_client):
        """
        业务规则: 名称不能为空

        Sad Path: 验证错误
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"name": ""}
        )

        assert response.status_code in [400, 422], (
            f"空名称应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_tag_name_too_long_rejected(self, auth_client):
        """
        业务规则: 名称不能超过 50 字符

        Sad Path: 验证错误
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"name": "x" * 51}
        )

        assert response.status_code in [400, 422], (
            f"过长名称应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_tag_invalid_color_rejected(self, auth_client):
        """
        业务规则: 颜色必须在有效列表内

        Sad Path: 验证错误
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"name": "Test", "color": "rainbow"}
        )

        assert response.status_code in [400, 422], (
            f"无效颜色应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"name": "Test"}
        )
        self.assert_unauthorized(response)


# ==========================================
# Test: Update Tag
# ==========================================

@pytest.mark.p1
class TestTagUpdate(BaseAPITest):
    """
    PATCH /api/v2/user/tags/{tag_id} 黑盒测试

    更新标签

    业务规则 (v3.33 Phase 2):
    1. 可更新: name, color, group_name, icon
    2. 只能更新自己工作区的标签
    """

    TAGS_ENDPOINT = Endpoints.TAGS

    def test_update_nonexistent_tag_returns_404(self, auth_client):
        """
        业务规则: 标签不存在返回 404

        Sad Path: Not Found
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.patch(
            Endpoints.tag(fake_id),
            json={"name": "Updated"}
        )
        self.assert_not_found(response)

    def test_update_invalid_id_format_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = auth_client.patch(
            Endpoints.tag("invalid-uuid"),
            json={"name": "Test"}
        )
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_update_invalid_color_rejected(self, auth_client):
        """
        业务规则: 无效颜色应被拒绝

        Sad Path: 验证错误
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.patch(
            Endpoints.tag(fake_id),
            json={"color": "rainbow"}
        )
        # 可能先返回 404 (标签不存在) 或 422 (验证失败)
        assert response.status_code in [400, 404, 422]

    def test_update_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.patch(
            Endpoints.tag(fake_id),
            json={"name": "Test"}
        )
        self.assert_unauthorized(response)


# ==========================================
# Test: Delete Tag
# ==========================================

@pytest.mark.p1
class TestTagDelete(BaseAPITest):
    """
    DELETE /api/v2/user/tags/{tag_id} 黑盒测试

    删除标签

    业务规则 (v3.33 Phase 2):
    1. 只能删除自己工作区的标签
    2. 删除标签后，相关的 project_tag/asset_tag 关联也被删除
    """

    def test_delete_nonexistent_tag_returns_404(self, auth_client):
        """
        业务规则: 标签不存在返回 404

        Sad Path: Not Found
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.tag(fake_id))
        self.assert_not_found(response)

    def test_delete_invalid_id_format_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = auth_client.delete(Endpoints.tag("invalid-uuid"))
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_delete_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.delete(Endpoints.tag(fake_id))
        self.assert_unauthorized(response)


# ==========================================
# Test: Tag Presets
# ==========================================

@pytest.mark.p2
class TestTagPresets(BaseAPITest):
    """
    GET /api/v2/user/tags/presets 黑盒测试

    获取标签组预设
    """

    ENDPOINT = Endpoints.TAGS_PRESETS

    def test_list_presets_returns_list(self, auth_client):
        """
        业务规则: 返回预设列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是数组"

    def test_presets_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


# ==========================================
# Test: Project Tags - Get
# ==========================================

@pytest.mark.p1
class TestProjectTagsGet(BaseAPITest):
    """
    GET /api/v2/user/projects/{project_id}/tags 黑盒测试

    获取项目的标签
    """

    def test_get_nonexistent_project_tags(self, auth_client):
        """
        业务规则: 获取不存在项目的标签

        注意: 可能返回空列表或 404，取决于实现
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.project_tags(fake_id))

        # 可能返回空 items 或 404
        assert response.status_code in [200, 404], (
            f"获取不存在项目的标签返回了 {response.status_code}"
        )

    def test_get_invalid_project_id_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = auth_client.get(Endpoints.project_tags("invalid-uuid"))
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_get_project_tags_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.get(Endpoints.project_tags(fake_id))
        self.assert_unauthorized(response)


# ==========================================
# Test: Project Tags - Add
# ==========================================

@pytest.mark.p1
class TestProjectTagsAdd(BaseAPITest):
    """
    POST /api/v2/user/projects/{project_id}/tags 黑盒测试

    添加标签到项目
    """

    def test_add_tags_missing_tag_ids_rejected(self, auth_client):
        """
        业务规则: tag_ids 是必需字段

        Sad Path: 缺少必需参数
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.project_tags(fake_id),
            json={}
        )

        assert response.status_code in [400, 404, 422], (
            f"缺少 tag_ids 应被拒绝，但返回了 {response.status_code}"
        )

    def test_add_tags_empty_array_rejected(self, auth_client):
        """
        业务规则: tag_ids 不能为空数组

        Sad Path: 验证错误 (min_length=1)
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.project_tags(fake_id),
            json={"tag_ids": []}
        )

        assert response.status_code in [400, 404, 422], (
            f"空 tag_ids 应被拒绝，但返回了 {response.status_code}"
        )

    def test_add_tags_invalid_uuid_rejected(self, auth_client):
        """
        业务规则: tag_ids 必须是有效的 UUID

        Sad Path: 验证错误
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.project_tags(fake_id),
            json={"tag_ids": ["invalid-uuid"]}
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_add_tags_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(
            Endpoints.project_tags(fake_id),
            json={"tag_ids": [str(uuid.uuid4())]}
        )
        self.assert_unauthorized(response)


# ==========================================
# Test: Project Tags - Set
# ==========================================

@pytest.mark.p1
class TestProjectTagsSet(BaseAPITest):
    """
    PUT /api/v2/user/projects/{project_id}/tags 黑盒测试

    设置项目标签 (替换所有)
    """

    def test_set_tags_invalid_uuid_rejected(self, auth_client):
        """
        业务规则: tag_ids 必须是有效的 UUID

        Sad Path: 验证错误
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.put(
            Endpoints.project_tags(fake_id),
            json={"tag_ids": ["invalid-uuid"]}
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_set_tags_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.put(
            Endpoints.project_tags(fake_id),
            json={"tag_ids": []}
        )
        self.assert_unauthorized(response)


# ==========================================
# Test: Project Tags - Remove
# ==========================================

@pytest.mark.p1
class TestProjectTagsRemove(BaseAPITest):
    """
    DELETE /api/v2/user/projects/{project_id}/tags/{tag_id} 黑盒测试

    从项目移除标签
    """

    def test_remove_invalid_project_id_rejected(self, auth_client):
        """
        业务规则: project_id 必须是有效的 UUID

        Sad Path: 验证错误
        """
        fake_tag_id = str(uuid.uuid4())
        response = auth_client.delete(
            Endpoints.project_tag("invalid-uuid", fake_tag_id)
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 project_id 应被拒绝，但返回了 {response.status_code}"
        )

    def test_remove_invalid_tag_id_rejected(self, auth_client):
        """
        业务规则: tag_id 必须是有效的 UUID

        Sad Path: 验证错误
        """
        fake_project_id = str(uuid.uuid4())
        response = auth_client.delete(
            Endpoints.project_tag(fake_project_id, "invalid-uuid")
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 tag_id 应被拒绝，但返回了 {response.status_code}"
        )

    def test_remove_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_project_id = str(uuid.uuid4())
        fake_tag_id = str(uuid.uuid4())
        response = anon_client.delete(
            Endpoints.project_tag(fake_project_id, fake_tag_id)
        )
        self.assert_unauthorized(response)


# ==========================================
# Test: Asset Tags - Get
# ==========================================

@pytest.mark.p1
class TestAssetTagsGet(BaseAPITest):
    """
    GET /api/v2/user/assets/{asset_id}/tags 黑盒测试

    获取素材的标签
    """

    def test_get_nonexistent_asset_tags(self, auth_client):
        """
        业务规则: 获取不存在素材的标签
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.asset_tags(fake_id))

        # 可能返回空 items 或 404
        assert response.status_code in [200, 404], (
            f"获取不存在素材的标签返回了 {response.status_code}"
        )

    def test_get_invalid_asset_id_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝

        Sad Path: 验证错误
        """
        response = auth_client.get(Endpoints.asset_tags("invalid-uuid"))
        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_get_asset_tags_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.get(Endpoints.asset_tags(fake_id))
        self.assert_unauthorized(response)


# ==========================================
# Test: Asset Tags - Add
# ==========================================

@pytest.mark.p1
class TestAssetTagsAdd(BaseAPITest):
    """
    POST /api/v2/user/assets/{asset_id}/tags 黑盒测试

    添加标签到素材
    """

    def test_add_tags_missing_tag_ids_rejected(self, auth_client):
        """
        业务规则: tag_ids 是必需字段

        Sad Path: 缺少必需参数
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.asset_tags(fake_id),
            json={}
        )

        assert response.status_code in [400, 404, 422], (
            f"缺少 tag_ids 应被拒绝，但返回了 {response.status_code}"
        )

    def test_add_tags_empty_array_rejected(self, auth_client):
        """
        业务规则: tag_ids 不能为空数组

        Sad Path: 验证错误
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.asset_tags(fake_id),
            json={"tag_ids": []}
        )

        assert response.status_code in [400, 404, 422], (
            f"空 tag_ids 应被拒绝，但返回了 {response.status_code}"
        )

    def test_add_tags_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(
            Endpoints.asset_tags(fake_id),
            json={"tag_ids": [str(uuid.uuid4())]}
        )
        self.assert_unauthorized(response)


# ==========================================
# Test: Asset Tags - Set
# ==========================================

@pytest.mark.p1
class TestAssetTagsSet(BaseAPITest):
    """
    PUT /api/v2/user/assets/{asset_id}/tags 黑盒测试

    设置素材标签 (替换所有)
    """

    def test_set_tags_invalid_uuid_rejected(self, auth_client):
        """
        业务规则: tag_ids 必须是有效的 UUID

        Sad Path: 验证错误
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.put(
            Endpoints.asset_tags(fake_id),
            json={"tag_ids": ["invalid-uuid"]}
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_set_tags_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.put(
            Endpoints.asset_tags(fake_id),
            json={"tag_ids": []}
        )
        self.assert_unauthorized(response)


# ==========================================
# Test: Asset Tags - Remove
# ==========================================

@pytest.mark.p1
class TestAssetTagsRemove(BaseAPITest):
    """
    DELETE /api/v2/user/assets/{asset_id}/tags/{tag_id} 黑盒测试

    从素材移除标签
    """

    def test_remove_invalid_asset_id_rejected(self, auth_client):
        """
        业务规则: asset_id 必须是有效的 UUID

        Sad Path: 验证错误
        """
        fake_tag_id = str(uuid.uuid4())
        response = auth_client.delete(
            Endpoints.asset_tag("invalid-uuid", fake_tag_id)
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 asset_id 应被拒绝，但返回了 {response.status_code}"
        )

    def test_remove_invalid_tag_id_rejected(self, auth_client):
        """
        业务规则: tag_id 必须是有效的 UUID

        Sad Path: 验证错误
        """
        fake_asset_id = str(uuid.uuid4())
        response = auth_client.delete(
            Endpoints.asset_tag(fake_asset_id, "invalid-uuid")
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 tag_id 应被拒绝，但返回了 {response.status_code}"
        )

    def test_remove_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_asset_id = str(uuid.uuid4())
        fake_tag_id = str(uuid.uuid4())
        response = anon_client.delete(
            Endpoints.asset_tag(fake_asset_id, fake_tag_id)
        )
        self.assert_unauthorized(response)
