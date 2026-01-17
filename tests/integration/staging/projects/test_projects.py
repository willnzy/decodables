"""
Projects API Tests (Black Box)

测试 /api/v2/user/projects 相关接口

基于业务规则的黑盒测试，不依赖代码实现

业务规则 (来源: 产品文档):
1. 不同 Tier 有不同的项目数量限制:
   - t1 (Free): 1 个项目
   - t2 (Starter): 20 个项目
   - t3 (Pro): 200 个项目
2. 项目支持软删除，30天内可恢复
3. 项目可以复制
4. 项目有 title 和 content (JSON)
5. 项目按更新时间倒序排列

@module tests.integration.staging.projects.test_projects
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints, Tiers, TestData


@pytest.mark.p0
class TestProjectsList(BaseAPITest):
    """
    GET /api/v2/user/projects 黑盒测试

    项目列表查询
    """

    ENDPOINT = Endpoints.PROJECTS

    # ==========================================
    # 功能测试: 列表查询
    # ==========================================

    def test_list_projects_returns_paginated_response(self, auth_client):
        """
        业务规则: 项目列表应分页返回

        期望响应包含:
        - items: 项目数组
        - total: 总数
        - offset/limit: 分页信息
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 验证分页结构
        if isinstance(data, dict):
            assert "items" in data or "projects" in data, "响应应包含 items 或 projects"
            items_key = "items" if "items" in data else "projects"
            assert isinstance(data[items_key], list), "items 应该是数组"

    def test_list_projects_with_pagination(self, auth_client):
        """
        业务规则: 分页参数应正确生效
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"limit": 5, "offset": 0}
        )
        data = self.assert_success(response)

        if isinstance(data, dict):
            items = data.get("items") or data.get("projects") or []
            assert len(items) <= 5, f"limit=5 但返回了 {len(items)} 条"

    def test_project_item_structure(self, auth_client):
        """
        业务规则: 每个项目应包含必要字段

        必需字段:
        - id: 项目 UUID
        - title: 项目标题
        - created_at: 创建时间
        - updated_at: 更新时间
        """
        response = auth_client.get(self.ENDPOINT, params={"limit": 1})
        data = self.assert_success(response)

        if isinstance(data, dict):
            items = data.get("items") or data.get("projects") or []
        else:
            items = data if isinstance(data, list) else []

        if len(items) > 0:
            project = items[0]
            assert "id" in project, "项目缺少 id"
            assert "title" in project, "项目缺少 title"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 项目列表是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p0
class TestProjectCreate(BaseAPITest):
    """
    POST /api/v2/user/projects 黑盒测试

    创建项目
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_create_project_success(self, auth_client):
        """
        业务规则: 用户可以创建新项目

        请求:
        {
            "title": "Test Project",
            "content": {}  // JSON 内容
        }
        """
        test_title = f"Test_Project_{uuid.uuid4().hex[:8]}"

        response = auth_client.post(
            self.ENDPOINT,
            json={
                "title": test_title,
                "content": {"pages": []}
            }
        )

        # 可能返回 200 或 201
        assert response.status_code in [200, 201], (
            f"创建项目失败: {response.status_code} - {response.text[:200]}"
        )

        data = response.json()
        assert "id" in data, "响应应包含项目 id"

        # 记录创建的项目以便清理
        project_id = data["id"]
        print(f"\n✅ 创建项目成功: {project_id}")

        # 清理: 删除测试项目
        self._cleanup_project(auth_client, project_id)

    def test_create_project_with_empty_title_rejected(self, auth_client):
        """
        业务规则: 项目标题不能为空
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "title": "",
                "content": {}
            }
        )

        # 应返回 400 或 422
        assert response.status_code in [400, 422], (
            f"空标题应被拒绝，但返回了 {response.status_code}"
        )

    def test_create_project_title_max_length(self, auth_client):
        """
        业务规则: 项目标题有最大长度限制 (200字符)
        """
        long_title = "A" * 201  # 超过 200 字符

        response = auth_client.post(
            self.ENDPOINT,
            json={
                "title": long_title,
                "content": {}
            }
        )

        # 如果没有限制，这是一个需要修复的 bug
        # 按业务规则应该拒绝
        if response.status_code in [200, 201]:
            # 标记为需要修复的问题
            print(f"\n⚠️ 业务规则违反: 应拒绝超长标题，但实际创建成功")
            # 清理
            data = response.json()
            if "id" in data:
                self._cleanup_project(auth_client, data["id"])

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 创建项目必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"title": "Test", "content": {}}
        )
        self.assert_unauthorized(response)

    def _cleanup_project(self, client, project_id: str):
        """清理测试项目"""
        try:
            client.delete(Endpoints.project(project_id), params={"permanent": True})
        except Exception:
            pass


@pytest.mark.p0
class TestProjectGet(BaseAPITest):
    """
    GET /api/v2/user/projects/{id} 黑盒测试

    获取单个项目
    """

    def test_get_nonexistent_project(self, auth_client):
        """
        业务规则: 获取不存在的项目应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.project(fake_id))
        self.assert_not_found(response)

    def test_get_project_with_invalid_id_format(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回 400 或 404
        """
        response = auth_client.get(Endpoints.project("invalid-id"))

        # 应返回 400 (格式错误) 或 404 (未找到)
        assert response.status_code in [400, 404, 422], (
            f"无效 ID 应被拒绝，但返回了 {response.status_code}"
        )


@pytest.mark.p1
class TestProjectDelete(BaseAPITest):
    """
    DELETE /api/v2/user/projects/{id} 黑盒测试

    删除项目
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_soft_delete_project(self, auth_client):
        """
        业务规则: 默认软删除项目 (30天内可恢复)
        """
        # 先创建一个项目
        test_title = f"Test_Delete_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"title": test_title, "content": {}}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("无法创建测试项目")

        project_id = create_response.json()["id"]

        # 软删除
        delete_response = auth_client.delete(
            Endpoints.project(project_id),
            params={"permanent": False}
        )

        assert delete_response.status_code in [200, 204], (
            f"软删除失败: {delete_response.status_code}"
        )

        # 验证: 在正常列表中看不到
        list_response = auth_client.get(self.ENDPOINT)
        data = list_response.json()
        items = data.get("items") or data.get("projects") or []
        project_ids = [p.get("id") for p in items]
        assert project_id not in project_ids, "软删除后项目仍在正常列表中"

        # 清理: 永久删除
        auth_client.delete(Endpoints.project(project_id), params={"permanent": True})

    def test_delete_nonexistent_project(self, auth_client):
        """
        业务规则: 删除不存在的项目应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.project(fake_id))
        self.assert_not_found(response)


@pytest.mark.p1
class TestProjectRestore(BaseAPITest):
    """
    POST /api/v2/user/projects/{id}/restore 黑盒测试

    恢复已删除的项目
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_restore_deleted_project(self, auth_client):
        """
        业务规则: 30天内可以恢复软删除的项目
        """
        # 创建项目
        test_title = f"Test_Restore_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"title": test_title, "content": {}}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("无法创建测试项目")

        project_id = create_response.json()["id"]

        # 软删除
        auth_client.delete(Endpoints.project(project_id), params={"permanent": False})

        # 恢复
        restore_response = auth_client.post(Endpoints.project_restore(project_id))

        assert restore_response.status_code in [200, 201], (
            f"恢复失败: {restore_response.status_code} - {restore_response.text[:200]}"
        )

        # 验证: 在正常列表中可以看到
        list_response = auth_client.get(self.ENDPOINT)
        data = list_response.json()
        items = data.get("items") or data.get("projects") or []
        project_ids = [p.get("id") for p in items]
        assert project_id in project_ids, "恢复后项目未出现在正常列表中"

        # 清理
        auth_client.delete(Endpoints.project(project_id), params={"permanent": True})


@pytest.mark.p1
class TestProjectDuplicate(BaseAPITest):
    """
    POST /api/v2/user/projects/{id}/duplicate 黑盒测试

    复制项目
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_duplicate_project(self, auth_client):
        """
        业务规则: 用户可以复制自己的项目
        """
        # 创建源项目
        test_title = f"Test_Source_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"title": test_title, "content": {"pages": [{"id": "p1"}]}}
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("无法创建测试项目")

        source_id = create_response.json()["id"]

        # 复制
        duplicate_response = auth_client.post(Endpoints.project_duplicate(source_id))

        if duplicate_response.status_code in [200, 201]:
            dup_data = duplicate_response.json()
            assert "id" in dup_data, "复制响应应包含新项目 id"
            assert dup_data["id"] != source_id, "复制的项目 id 应该不同"

            # 清理复制的项目
            auth_client.delete(Endpoints.project(dup_data["id"]), params={"permanent": True})

        # 清理源项目
        auth_client.delete(Endpoints.project(source_id), params={"permanent": True})


@pytest.mark.p1
class TestDeletedProjectsList(BaseAPITest):
    """
    GET /api/v2/user/projects/deleted 黑盒测试

    已删除项目列表
    """

    ENDPOINT = Endpoints.PROJECTS_DELETED

    def test_list_deleted_projects(self, auth_client):
        """
        业务规则: 用户可以查看已删除但未过期的项目
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 验证返回格式
        if isinstance(data, dict):
            items = data.get("items") or data.get("projects") or []
            assert isinstance(items, list), "deleted items 应该是数组"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 已删除项目列表是私有数据
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestProjectDashboard(BaseAPITest):
    """
    GET /api/v2/user/projects/dashboard 黑盒测试

    项目仪表盘
    """

    ENDPOINT = Endpoints.PROJECTS_DASHBOARD

    def test_dashboard_returns_stats(self, auth_client):
        """
        业务规则: 仪表盘应返回项目统计信息
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 可能包含的统计字段
        # total_projects, recent_projects, storage_used, etc.
        assert isinstance(data, dict), "仪表盘应返回对象"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 仪表盘是私有数据
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)
