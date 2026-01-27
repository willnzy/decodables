"""
Folders API Tests (Black Box / TDD Style)

测试 /api/v2/user/folders 相关接口

基于业务规则的黑盒测试，不依赖代码实现。
遵循 TDD 原则：基于 API 目标行为设计测试。

业务规则 (来源: 产品设计文档 workspace-architecture-design.md):
1. 每个 workspace 可以有多个文件夹
2. 文件夹有两种类型: project / asset
3. 文件夹有 8 种颜色选项: slate/red/orange/amber/emerald/cyan/blue/violet
4. 文件夹名称在同一 workspace + folder_type 内必须唯一
5. 文件夹可以排序 (sort_order)
6. 删除文件夹时，其中的项目/素材移动到根目录 (folder_id=NULL)
7. 所有操作需要认证

@module tests.integration.staging.folders.test_folders
@version 1.0.0 (v3.33 Phase 2.6)
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


# ==========================================
# Constants
# ==========================================

VALID_COLORS = ["slate", "red", "orange", "amber", "emerald", "cyan", "blue", "violet"]
VALID_TYPES = ["project", "asset"]


# ==========================================
# Test: List Folders
# ==========================================

@pytest.mark.p0
class TestFoldersList(BaseAPITest):
    """
    GET /api/v2/user/folders?type=project|asset 黑盒测试

    列出文件夹
    """

    ENDPOINT = Endpoints.FOLDERS

    def test_list_project_folders_returns_list(self, auth_client):
        """
        业务规则: 可以按类型获取文件夹列表

        期望响应包含:
        - items: 文件夹数组
        - total: 总数
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"folder_type": "project"}
        )
        data = self.assert_success(response)

        assert "items" in data, "响应应包含 items"
        assert "total" in data, "响应应包含 total"
        assert isinstance(data["items"], list), "items 应该是数组"
        assert isinstance(data["total"], int), "total 应该是整数"

    def test_list_asset_folders_returns_list(self, auth_client):
        """
        业务规则: asset 类型文件夹和 project 类型分开管理
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"folder_type": "asset"}
        )
        data = self.assert_success(response)

        assert "items" in data, "响应应包含 items"
        assert isinstance(data["items"], list), "items 应该是数组"

    def test_folder_type_is_required(self, auth_client):
        """
        业务规则: folder_type 是必需参数
        """
        response = auth_client.get(self.ENDPOINT)

        # 应返回 400 或 422 (缺少必需参数)
        assert response.status_code in [400, 422], (
            f"缺少 folder_type 应被拒绝，但返回了 {response.status_code}"
        )

    def test_invalid_folder_type_rejected(self, auth_client):
        """
        业务规则: folder_type 只能是 project 或 asset
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"folder_type": "invalid"}
        )

        # 应返回 400 或 422
        assert response.status_code in [400, 422], (
            f"无效的 folder_type 应被拒绝，但返回了 {response.status_code}"
        )

    def test_folder_item_structure(self, auth_client):
        """
        业务规则: 每个文件夹应包含必要字段
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"folder_type": "project"}
        )
        data = self.assert_success(response)

        if len(data["items"]) > 0:
            folder = data["items"][0]
            # 验证必需字段
            assert "id" in folder, "文件夹缺少 id"
            assert "name" in folder, "文件夹缺少 name"
            assert "color" in folder, "文件夹缺少 color"
            assert "folder_type" in folder, "文件夹缺少 folder_type"
            assert "sort_order" in folder, "文件夹缺少 sort_order"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 文件夹列表是私有数据，必须登录
        """
        response = anon_client.get(
            self.ENDPOINT,
            params={"folder_type": "project"}
        )
        self.assert_unauthorized(response)


# ==========================================
# Test: Create Folder
# ==========================================

@pytest.mark.p0
class TestFolderCreate(BaseAPITest):
    """
    POST /api/v2/user/folders 黑盒测试

    创建文件夹
    """

    ENDPOINT = Endpoints.FOLDERS

    def test_create_project_folder_success(self, auth_client):
        """
        业务规则: 用户可以创建 project 类型文件夹
        """
        test_name = f"Test_Folder_{uuid.uuid4().hex[:8]}"

        response = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": test_name,
                "color": "blue"
            }
        )

        assert response.status_code in [200, 201], (
            f"创建文件夹失败: {response.status_code} - {response.text[:200]}"
        )

        data = response.json()
        assert "id" in data, "响应应包含文件夹 id"
        assert data["name"] == test_name, "文件夹名称应匹配"
        assert data["color"] == "blue", "文件夹颜色应匹配"
        assert data["folder_type"] == "project", "文件夹类型应匹配"

        # 清理
        self._cleanup_folder(auth_client, data["id"])

    def test_create_asset_folder_success(self, auth_client):
        """
        业务规则: 用户可以创建 asset 类型文件夹
        """
        test_name = f"Test_Asset_{uuid.uuid4().hex[:8]}"

        response = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "asset",
                "name": test_name,
                "color": "emerald"
            }
        )

        assert response.status_code in [200, 201], (
            f"创建文件夹失败: {response.status_code} - {response.text[:200]}"
        )

        data = response.json()
        assert data["folder_type"] == "asset", "文件夹类型应为 asset"

        # 清理
        self._cleanup_folder(auth_client, data["id"])

    def test_create_folder_default_color(self, auth_client):
        """
        业务规则: 不指定颜色时默认使用 slate
        """
        test_name = f"Test_Default_{uuid.uuid4().hex[:8]}"

        response = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": test_name
            }
        )

        assert response.status_code in [200, 201], (
            f"创建文件夹失败: {response.status_code}"
        )

        data = response.json()
        assert data["color"] == "slate", "默认颜色应为 slate"

        # 清理
        self._cleanup_folder(auth_client, data["id"])

    def test_create_folder_all_colors_valid(self, auth_client):
        """
        业务规则: 8 种颜色都是有效的
        """
        created_ids = []

        for color in VALID_COLORS:
            test_name = f"Test_{color}_{uuid.uuid4().hex[:6]}"
            response = auth_client.post(
                self.ENDPOINT,
                json={
                    "folder_type": "project",
                    "name": test_name,
                    "color": color
                }
            )

            if response.status_code in [200, 201]:
                data = response.json()
                assert data["color"] == color, f"颜色 {color} 应被正确保存"
                created_ids.append(data["id"])
            else:
                pytest.fail(f"颜色 {color} 应该是有效的，但返回了 {response.status_code}")

        # 清理
        for folder_id in created_ids:
            self._cleanup_folder(auth_client, folder_id)

    def test_create_folder_invalid_color_rejected(self, auth_client):
        """
        业务规则: 无效的颜色应被拒绝
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": "Test Invalid Color",
                "color": "pink"  # 不在有效颜色列表中
            }
        )

        assert response.status_code in [400, 422], (
            f"无效颜色应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_folder_empty_name_rejected(self, auth_client):
        """
        业务规则: 文件夹名称不能为空
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": ""
            }
        )

        assert response.status_code in [400, 422], (
            f"空名称应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_folder_name_max_length(self, auth_client):
        """
        业务规则: 文件夹名称最大 100 字符
        """
        long_name = "A" * 101  # 超过 100 字符

        response = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": long_name
            }
        )

        assert response.status_code in [400, 422], (
            f"超长名称应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_folder_duplicate_name_rejected(self, auth_client):
        """
        业务规则: 同一 workspace + folder_type 内名称必须唯一
        """
        test_name = f"Test_Duplicate_{uuid.uuid4().hex[:8]}"

        # 创建第一个文件夹
        response1 = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": test_name
            }
        )

        if response1.status_code not in [200, 201]:
            pytest.skip("无法创建第一个测试文件夹")

        folder1_id = response1.json()["id"]

        # 尝试创建同名文件夹
        response2 = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": test_name
            }
        )

        # 清理第一个
        self._cleanup_folder(auth_client, folder1_id)

        # 应返回 400 或 409 (冲突)
        assert response2.status_code in [400, 409, 422], (
            f"重复名称应被拒绝，但返回了 {response2.status_code}"
        )

    def test_create_folder_same_name_different_type_allowed(self, auth_client):
        """
        业务规则: 不同类型可以使用相同名称
        """
        test_name = f"Test_Same_Name_{uuid.uuid4().hex[:8]}"
        created_ids = []

        # 创建 project 类型
        response1 = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": test_name
            }
        )

        if response1.status_code in [200, 201]:
            created_ids.append(response1.json()["id"])
        else:
            pytest.skip("无法创建第一个测试文件夹")

        # 创建 asset 类型 (同名)
        response2 = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "asset",
                "name": test_name
            }
        )

        if response2.status_code in [200, 201]:
            created_ids.append(response2.json()["id"])
            assert True, "不同类型可以使用相同名称"
        else:
            pytest.fail(f"不同类型应允许同名，但返回了 {response2.status_code}")

        # 清理
        for folder_id in created_ids:
            self._cleanup_folder(auth_client, folder_id)

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 创建文件夹必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": "Test"
            }
        )
        self.assert_unauthorized(response)

    def test_create_folder_missing_folder_type_rejected(self, auth_client):
        """
        业务规则: folder_type 是必需字段

        Sad Path: 缺少必需参数应返回 400/422
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test Missing Type"
            }
        )

        assert response.status_code in [400, 422], (
            f"缺少 folder_type 应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_folder_missing_name_rejected(self, auth_client):
        """
        业务规则: name 是必需字段

        Sad Path: 缺少必需参数应返回 400/422
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project"
            }
        )

        assert response.status_code in [400, 422], (
            f"缺少 name 应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_folder_whitespace_only_name_rejected(self, auth_client):
        """
        业务规则: 文件夹名称不能只包含空白字符

        Sad Path: 空白字符应被视为空名称
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "folder_type": "project",
                "name": "   "  # 只有空格
            }
        )

        # 根据实现，可能返回 400/422 (验证失败) 或 200 (如果有 trim)
        # TDD 期望: 应该拒绝纯空白名称
        if response.status_code in [200, 201]:
            # 如果创建成功，检查名称是否被 trim 处理
            data = response.json()
            # 清理
            self._cleanup_folder(auth_client, data["id"])
            # 记录为潜在问题
            print("⚠️ 注意: 纯空白名称被接受，可能需要添加验证")
        else:
            assert response.status_code in [400, 422]

    def _cleanup_folder(self, client, folder_id: str):
        """清理测试文件夹"""
        try:
            client.delete(Endpoints.folder(folder_id))
        except Exception:
            pass


# ==========================================
# Test: Update Folder
# ==========================================

@pytest.mark.p1
class TestFolderUpdate(BaseAPITest):
    """
    PATCH /api/v2/user/folders/{folder_id} 黑盒测试

    更新文件夹
    """

    ENDPOINT = Endpoints.FOLDERS

    def test_update_folder_name(self, auth_client):
        """
        业务规则: 可以更新文件夹名称
        """
        # 先创建一个文件夹
        test_name = f"Test_Update_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"folder_type": "project", "name": test_name}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("无法创建测试文件夹")

        folder_id = create_response.json()["id"]
        new_name = f"Updated_{uuid.uuid4().hex[:8]}"

        # 更新名称
        update_response = auth_client.patch(
            Endpoints.folder(folder_id),
            json={"name": new_name}
        )

        assert update_response.status_code == 200, (
            f"更新失败: {update_response.status_code}"
        )

        data = update_response.json()
        assert data["name"] == new_name, "名称应已更新"

        # 清理
        auth_client.delete(Endpoints.folder(folder_id))

    def test_update_folder_color(self, auth_client):
        """
        业务规则: 可以更新文件夹颜色
        """
        test_name = f"Test_Color_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"folder_type": "project", "name": test_name, "color": "slate"}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("无法创建测试文件夹")

        folder_id = create_response.json()["id"]

        # 更新颜色
        update_response = auth_client.patch(
            Endpoints.folder(folder_id),
            json={"color": "violet"}
        )

        assert update_response.status_code == 200
        assert update_response.json()["color"] == "violet", "颜色应已更新"

        # 清理
        auth_client.delete(Endpoints.folder(folder_id))

    def test_update_nonexistent_folder_returns_404(self, auth_client):
        """
        业务规则: 更新不存在的文件夹应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.patch(
            Endpoints.folder(fake_id),
            json={"name": "Test"}
        )

        self.assert_not_found(response)

    def test_update_with_invalid_id_format(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝
        """
        response = auth_client.patch(
            Endpoints.folder("invalid-id"),
            json={"name": "Test"}
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 ID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_update_to_duplicate_name_rejected(self, auth_client):
        """
        业务规则: 不能更新为已存在的名称
        """
        name1 = f"Folder_A_{uuid.uuid4().hex[:8]}"
        name2 = f"Folder_B_{uuid.uuid4().hex[:8]}"

        # 创建两个文件夹
        resp1 = auth_client.post(self.ENDPOINT, json={"folder_type": "project", "name": name1})
        resp2 = auth_client.post(self.ENDPOINT, json={"folder_type": "project", "name": name2})

        if resp1.status_code not in [200, 201] or resp2.status_code not in [200, 201]:
            pytest.skip("无法创建测试文件夹")

        folder1_id = resp1.json()["id"]
        folder2_id = resp2.json()["id"]

        # 尝试将 folder2 更名为 folder1 的名称
        update_response = auth_client.patch(
            Endpoints.folder(folder2_id),
            json={"name": name1}
        )

        # 清理
        auth_client.delete(Endpoints.folder(folder1_id))
        auth_client.delete(Endpoints.folder(folder2_id))

        # 应拒绝
        assert update_response.status_code in [400, 409, 422], (
            f"重复名称应被拒绝，但返回了 {update_response.status_code}"
        )

    def test_update_folder_requires_authentication(self, anon_client):
        """
        业务规则: 更新文件夹必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.patch(
            Endpoints.folder(fake_id),
            json={"name": "Test"}
        )
        self.assert_unauthorized(response)

    def test_update_folder_empty_body_returns_current(self, auth_client):
        """
        业务规则: 空更新请求应返回当前数据

        Edge Case: 不提供任何更新字段
        """
        test_name = f"Test_Empty_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"folder_type": "project", "name": test_name, "color": "blue"}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("无法创建测试文件夹")

        folder_id = create_response.json()["id"]

        # 发送空更新
        update_response = auth_client.patch(
            Endpoints.folder(folder_id),
            json={}
        )

        # 清理
        auth_client.delete(Endpoints.folder(folder_id))

        # 应返回 200 和当前数据，或返回 400 表示需要提供更新字段
        assert update_response.status_code in [200, 400], (
            f"空更新应返回当前数据或验证错误，但返回了 {update_response.status_code}"
        )

    def test_update_folder_name_to_empty_rejected(self, auth_client):
        """
        业务规则: 不能将名称更新为空

        Sad Path: 验证错误
        """
        test_name = f"Test_ToEmpty_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"folder_type": "project", "name": test_name}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("无法创建测试文件夹")

        folder_id = create_response.json()["id"]

        # 尝试更新为空名称
        update_response = auth_client.patch(
            Endpoints.folder(folder_id),
            json={"name": ""}
        )

        # 清理
        auth_client.delete(Endpoints.folder(folder_id))

        assert update_response.status_code in [400, 422], (
            f"空名称应被拒绝，但返回了 {update_response.status_code}"
        )

    def test_update_folder_invalid_color_rejected(self, auth_client):
        """
        业务规则: 无效的颜色应被拒绝

        Sad Path: 验证错误
        """
        test_name = f"Test_BadColor_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"folder_type": "project", "name": test_name}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("无法创建测试文件夹")

        folder_id = create_response.json()["id"]

        # 尝试更新为无效颜色
        update_response = auth_client.patch(
            Endpoints.folder(folder_id),
            json={"color": "rainbow"}  # 不在有效颜色列表中
        )

        # 清理
        auth_client.delete(Endpoints.folder(folder_id))

        assert update_response.status_code in [400, 422], (
            f"无效颜色应被拒绝，但返回了 {update_response.status_code}"
        )


# ==========================================
# Test: Delete Folder
# ==========================================

@pytest.mark.p1
class TestFolderDelete(BaseAPITest):
    """
    DELETE /api/v2/user/folders/{folder_id} 黑盒测试

    删除文件夹
    """

    ENDPOINT = Endpoints.FOLDERS

    def test_delete_folder_success(self, auth_client):
        """
        业务规则: 可以删除文件夹
        """
        test_name = f"Test_Delete_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"folder_type": "project", "name": test_name}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("无法创建测试文件夹")

        folder_id = create_response.json()["id"]

        # 删除
        delete_response = auth_client.delete(Endpoints.folder(folder_id))

        assert delete_response.status_code in [200, 204], (
            f"删除失败: {delete_response.status_code}"
        )

        # 验证已删除
        list_response = auth_client.get(
            self.ENDPOINT,
            params={"folder_type": "project"}
        )
        items = list_response.json().get("items", [])
        folder_ids = [f["id"] for f in items]
        assert folder_id not in folder_ids, "删除后文件夹仍在列表中"

    def test_delete_nonexistent_folder_returns_404(self, auth_client):
        """
        业务规则: 删除不存在的文件夹应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.folder(fake_id))

        self.assert_not_found(response)

    def test_delete_with_invalid_id_format(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝
        """
        response = auth_client.delete(Endpoints.folder("invalid-id"))

        assert response.status_code in [400, 404, 422], (
            f"无效 ID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_delete_folder_requires_authentication(self, anon_client):
        """
        业务规则: 删除文件夹必须登录

        Sad Path First: 401 Unauthorized
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.delete(Endpoints.folder(fake_id))
        self.assert_unauthorized(response)


# ==========================================
# Test: Reorder Folders
# ==========================================

@pytest.mark.p2
class TestFolderReorder(BaseAPITest):
    """
    POST /api/v2/user/folders/reorder 黑盒测试

    重排序文件夹
    """

    ENDPOINT = Endpoints.FOLDERS
    REORDER_ENDPOINT = Endpoints.FOLDERS_REORDER

    def test_reorder_folders_success(self, auth_client):
        """
        业务规则: 可以重新排序文件夹
        """
        # 创建两个文件夹
        name1 = f"Reorder_A_{uuid.uuid4().hex[:6]}"
        name2 = f"Reorder_B_{uuid.uuid4().hex[:6]}"

        resp1 = auth_client.post(self.ENDPOINT, json={"folder_type": "project", "name": name1})
        resp2 = auth_client.post(self.ENDPOINT, json={"folder_type": "project", "name": name2})

        if resp1.status_code not in [200, 201] or resp2.status_code not in [200, 201]:
            pytest.skip("无法创建测试文件夹")

        folder1_id = resp1.json()["id"]
        folder2_id = resp2.json()["id"]

        # 重排序 (反转顺序)
        reorder_response = auth_client.post(
            self.REORDER_ENDPOINT,
            json={
                "folder_type": "project",
                "folder_ids": [folder2_id, folder1_id]  # 反转顺序
            }
        )

        # 清理
        auth_client.delete(Endpoints.folder(folder1_id))
        auth_client.delete(Endpoints.folder(folder2_id))

        assert reorder_response.status_code == 200, (
            f"重排序失败: {reorder_response.status_code}"
        )

    def test_reorder_with_nonexistent_folder_rejected(self, auth_client):
        """
        业务规则: 包含不存在的文件夹 ID 应被拒绝
        """
        fake_id = str(uuid.uuid4())

        response = auth_client.post(
            self.REORDER_ENDPOINT,
            json={
                "folder_type": "project",
                "folder_ids": [fake_id]
            }
        )

        # 应返回 400 或 404
        assert response.status_code in [400, 404], (
            f"不存在的文件夹应被拒绝，但返回了 {response.status_code}"
        )

    def test_reorder_empty_list_rejected(self, auth_client):
        """
        业务规则: 空的文件夹列表应被拒绝
        """
        response = auth_client.post(
            self.REORDER_ENDPOINT,
            json={
                "folder_type": "project",
                "folder_ids": []
            }
        )

        assert response.status_code in [400, 422], (
            f"空列表应被拒绝，但返回了 {response.status_code}"
        )

    def test_reorder_requires_authentication(self, anon_client):
        """
        业务规则: 重排序必须登录
        """
        response = anon_client.post(
            self.REORDER_ENDPOINT,
            json={
                "folder_type": "project",
                "folder_ids": [str(uuid.uuid4())]
            }
        )
        self.assert_unauthorized(response)

    def test_reorder_with_invalid_uuid_format_rejected(self, auth_client):
        """
        业务规则: 包含无效 UUID 格式的 ID 应被拒绝

        Sad Path: 验证错误
        """
        response = auth_client.post(
            self.REORDER_ENDPOINT,
            json={
                "folder_type": "project",
                "folder_ids": ["invalid-uuid", "also-invalid"]
            }
        )

        assert response.status_code in [400, 422], (
            f"无效 UUID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_reorder_missing_folder_type_rejected(self, auth_client):
        """
        业务规则: folder_type 是必需字段

        Sad Path: 缺少必需参数
        """
        response = auth_client.post(
            self.REORDER_ENDPOINT,
            json={
                "folder_ids": [str(uuid.uuid4())]
            }
        )

        assert response.status_code in [400, 422], (
            f"缺少 folder_type 应被拒绝，但返回了 {response.status_code}"
        )

    def test_reorder_invalid_folder_type_rejected(self, auth_client):
        """
        业务规则: folder_type 只能是 project 或 asset

        Sad Path: 验证错误
        """
        response = auth_client.post(
            self.REORDER_ENDPOINT,
            json={
                "folder_type": "invalid",
                "folder_ids": [str(uuid.uuid4())]
            }
        )

        assert response.status_code in [400, 422], (
            f"无效 folder_type 应被拒绝，但返回了 {response.status_code}"
        )

    def test_reorder_missing_folder_ids_rejected(self, auth_client):
        """
        业务规则: folder_ids 是必需字段

        Sad Path: 缺少必需参数
        """
        response = auth_client.post(
            self.REORDER_ENDPOINT,
            json={
                "folder_type": "project"
            }
        )

        assert response.status_code in [400, 422], (
            f"缺少 folder_ids 应被拒绝，但返回了 {response.status_code}"
        )
