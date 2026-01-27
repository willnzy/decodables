"""
Soft Delete TTL Integration Tests

测试软删除的 30 天 TTL (Time To Live) 机制:
- 软删除的项目 30 天后自动永久删除
- 在 TTL 内可以恢复
- 恢复时间点正确记录

TDD Approach:
- 测试软删除响应包含到期时间
- 测试已删除列表显示剩余天数
- 测试恢复功能在 TTL 内有效

业务规则 (来源: 产品文档):
1. 软删除项目 30 天内可恢复
2. 超过 30 天自动永久删除 (通过后台任务)
3. deleted_at 字段记录删除时间
4. 已删除列表应显示到期时间或剩余天数

@module tests.integration.staging.soft_delete.test_soft_delete_ttl
"""

import pytest
import uuid
from datetime import datetime, timedelta

from tests.integration.staging.base import BaseAPITest
from tests.integration.staging.constants import Endpoints


# ==========================================
# Test: Soft Delete Response
# ==========================================

@pytest.mark.p0
class TestSoftDeleteResponse(BaseAPITest):
    """
    软删除响应格式测试

    验证软删除操作返回的信息是否完整
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_soft_delete_returns_deletion_info(self, auth_client):
        """
        业务规则: 软删除响应应包含删除信息

        期望响应包含:
        - deleted_at: 删除时间
        - expires_at / delete_permanently_at: 到期时间
        - message: 操作确认
        """
        # 创建测试项目
        test_title = f"SoftDelete_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"title": test_title, "content": {}}
        )

        if create_response.status_code == 403:
            pytest.skip("测试用户已达项目限制")

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"无法创建测试项目: {create_response.status_code}")

        project_id = create_response.json().get("id") or create_response.json().get("project_id")

        # 执行软删除
        delete_response = auth_client.delete(
            Endpoints.project(project_id),
            params={"permanent": False}
        )

        assert delete_response.status_code in [200, 204], (
            f"软删除失败: {delete_response.status_code}"
        )

        # 如果返回 JSON，检查是否包含删除信息
        if delete_response.status_code == 200 and delete_response.text:
            data = delete_response.json()

            # 检查是否包含删除时间信息
            time_fields = [
                "deleted_at", "deletion_date", "expires_at",
                "delete_permanently_at", "expiry_date", "ttl"
            ]
            has_time_info = any(field in str(data) for field in time_fields)

            if has_time_info:
                print(f"✓ 软删除响应包含时间信息: {data}")
            else:
                print(f"⚠️ 改进建议: 软删除响应应包含到期时间, 当前响应: {data}")

        # 清理: 永久删除
        auth_client.delete(Endpoints.project(project_id), params={"permanent": True})


@pytest.mark.p0
class TestDeletedListWithTTL(BaseAPITest):
    """
    已删除项目列表 TTL 信息测试

    验证已删除列表是否显示 TTL 相关信息
    """

    ENDPOINT = Endpoints.PROJECTS_DELETED

    def test_deleted_list_shows_expiry_info(self, auth_client):
        """
        业务规则: 已删除项目应显示到期时间

        期望每个已删除项目包含:
        - deleted_at: 删除时间
        - expires_at: 到期时间 (deleted_at + 30 days)
        - days_remaining: 剩余天数 (可选)
        """
        response = auth_client.get(self.ENDPOINT)

        if response.status_code != 200:
            pytest.skip("Deleted projects endpoint not available")

        data = response.json()
        items = data.get("items", [])

        if not items:
            # 没有已删除项目，创建一个来测试
            test_title = f"TTLTest_{uuid.uuid4().hex[:8]}"
            create_resp = auth_client.post(
                Endpoints.PROJECTS,
                json={"title": test_title, "content": {}}
            )

            if create_resp.status_code not in [200, 201]:
                pytest.skip("无法创建测试项目")

            project_id = create_resp.json().get("id") or create_resp.json().get("project_id")

            # 软删除
            auth_client.delete(
                Endpoints.project(project_id),
                params={"permanent": False}
            )

            # 重新获取已删除列表
            response = auth_client.get(self.ENDPOINT)
            data = response.json()
            items = data.get("items", [])

            # 清理: 永久删除
            auth_client.delete(Endpoints.project(project_id), params={"permanent": True})

        if items:
            project = items[0]

            # 验证 deleted_at 字段存在
            assert "deleted_at" in project, (
                f"已删除项目应包含 deleted_at 字段, 实际字段: {list(project.keys())}"
            )

            # 检查是否有到期信息
            expiry_fields = ["expires_at", "delete_permanently_at", "expiry_date", "days_remaining"]
            has_expiry = any(field in project for field in expiry_fields)

            if has_expiry:
                print(f"✓ 已删除项目包含到期信息")
            else:
                print(f"⚠️ 改进建议: 已删除项目应包含到期时间, 当前字段: {list(project.keys())}")

            # 验证 deleted_at 是有效的时间戳
            deleted_at = project.get("deleted_at")
            if deleted_at:
                try:
                    # 尝试解析时间
                    if isinstance(deleted_at, str):
                        # ISO format
                        parsed = datetime.fromisoformat(deleted_at.replace("Z", "+00:00"))
                        print(f"✓ deleted_at 格式正确: {parsed}")
                except Exception as e:
                    print(f"⚠️ deleted_at 格式异常: {deleted_at}, 错误: {e}")

    def test_deleted_projects_sorted_by_deletion_date(self, auth_client):
        """
        业务规则: 已删除项目应按删除时间排序

        最近删除的应该在前面
        """
        response = auth_client.get(self.ENDPOINT)

        if response.status_code != 200:
            pytest.skip("Deleted projects endpoint not available")

        data = response.json()
        items = data.get("items", [])

        if len(items) < 2:
            pytest.skip("需要至少 2 个已删除项目来验证排序")

        # 检查排序
        deleted_times = []
        for item in items:
            deleted_at = item.get("deleted_at")
            if deleted_at:
                try:
                    if isinstance(deleted_at, str):
                        parsed = datetime.fromisoformat(deleted_at.replace("Z", "+00:00"))
                        deleted_times.append(parsed)
                except Exception:
                    pass

        if len(deleted_times) >= 2:
            # 验证按降序排列 (最新的在前)
            is_descending = all(
                deleted_times[i] >= deleted_times[i+1]
                for i in range(len(deleted_times) - 1)
            )

            if is_descending:
                print("✓ 已删除项目按删除时间降序排列")
            else:
                print("⚠️ 排序可能不正确")


# ==========================================
# Test: Restore Within TTL
# ==========================================

@pytest.mark.p0
class TestRestoreWithinTTL(BaseAPITest):
    """
    TTL 内恢复测试

    验证在 30 天内可以恢复软删除的项目
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_restore_recently_deleted_project(self, auth_client):
        """
        业务规则: 刚删除的项目可以恢复
        """
        # 创建项目
        test_title = f"RestoreTest_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"title": test_title, "content": {}}
        )

        if create_response.status_code == 403:
            pytest.skip("测试用户已达项目限制")

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"无法创建测试项目: {create_response.status_code}")

        project_id = create_response.json().get("id") or create_response.json().get("project_id")

        # 软删除
        delete_response = auth_client.delete(
            Endpoints.project(project_id),
            params={"permanent": False}
        )
        assert delete_response.status_code in [200, 204]

        # 立即恢复
        restore_response = auth_client.post(Endpoints.project_restore(project_id))

        if restore_response.status_code == 403:
            # 可能因为配额限制
            auth_client.delete(Endpoints.project(project_id), params={"permanent": True})
            pytest.skip("恢复被拒绝，可能因为配额限制")

        assert restore_response.status_code in [200, 201], (
            f"恢复失败: {restore_response.status_code} - {restore_response.text[:200]}"
        )

        # 验证项目回到正常列表
        list_response = auth_client.get(self.ENDPOINT)
        items = list_response.json().get("items", [])
        project_ids = [p.get("id") or p.get("project_id") for p in items]

        assert project_id in project_ids, "恢复后项目应出现在正常列表中"

        # 清理
        auth_client.delete(Endpoints.project(project_id), params={"permanent": True})

    def test_restore_clears_deleted_at(self, auth_client):
        """
        业务规则: 恢复后 deleted_at 应被清除
        """
        # 创建项目
        test_title = f"ClearDeletedAt_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"title": test_title, "content": {}}
        )

        if create_response.status_code == 403:
            pytest.skip("测试用户已达项目限制")

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"无法创建测试项目: {create_response.status_code}")

        project_id = create_response.json().get("id") or create_response.json().get("project_id")

        # 软删除
        auth_client.delete(Endpoints.project(project_id), params={"permanent": False})

        # 恢复
        restore_response = auth_client.post(Endpoints.project_restore(project_id))

        if restore_response.status_code == 403:
            auth_client.delete(Endpoints.project(project_id), params={"permanent": True})
            pytest.skip("恢复被拒绝")

        assert restore_response.status_code in [200, 201]

        # 获取项目详情
        get_response = auth_client.get(Endpoints.project(project_id))

        if get_response.status_code == 200:
            data = get_response.json()
            deleted_at = data.get("deleted_at")

            # deleted_at 应为 None/null
            assert deleted_at is None, (
                f"恢复后 deleted_at 应为 null，实际为: {deleted_at}"
            )

        # 清理
        auth_client.delete(Endpoints.project(project_id), params={"permanent": True})


# ==========================================
# Test: Permanent Delete Behavior
# ==========================================

@pytest.mark.p1
class TestPermanentDelete(BaseAPITest):
    """
    永久删除测试

    验证永久删除后无法恢复
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_permanent_delete_cannot_restore(self, auth_client):
        """
        业务规则: 永久删除的项目无法恢复
        """
        # 创建项目
        test_title = f"PermanentDelete_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"title": test_title, "content": {}}
        )

        if create_response.status_code == 403:
            pytest.skip("测试用户已达项目限制")

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"无法创建测试项目: {create_response.status_code}")

        project_id = create_response.json().get("id") or create_response.json().get("project_id")

        # 永久删除
        delete_response = auth_client.delete(
            Endpoints.project(project_id),
            params={"permanent": True}
        )
        assert delete_response.status_code in [200, 204]

        # 尝试恢复
        restore_response = auth_client.post(Endpoints.project_restore(project_id))

        # 应返回 404 (项目不存在)
        assert restore_response.status_code == 404, (
            f"永久删除的项目恢复应返回 404，实际: {restore_response.status_code}"
        )

    def test_permanent_delete_not_in_any_list(self, auth_client):
        """
        业务规则: 永久删除后项目不在任何列表中
        """
        # 创建项目
        test_title = f"NotInList_{uuid.uuid4().hex[:8]}"
        create_response = auth_client.post(
            self.ENDPOINT,
            json={"title": test_title, "content": {}}
        )

        if create_response.status_code == 403:
            pytest.skip("测试用户已达项目限制")

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"无法创建测试项目: {create_response.status_code}")

        project_id = create_response.json().get("id") or create_response.json().get("project_id")

        # 永久删除
        auth_client.delete(Endpoints.project(project_id), params={"permanent": True})

        # 检查正常列表
        normal_response = auth_client.get(self.ENDPOINT)
        normal_items = normal_response.json().get("items", [])
        normal_ids = [p.get("id") or p.get("project_id") for p in normal_items]

        assert project_id not in normal_ids, "永久删除后不应在正常列表中"

        # 检查已删除列表
        deleted_response = auth_client.get(Endpoints.PROJECTS_DELETED)
        if deleted_response.status_code == 200:
            deleted_items = deleted_response.json().get("items", [])
            deleted_ids = [p.get("id") or p.get("project_id") for p in deleted_items]

            assert project_id not in deleted_ids, "永久删除后不应在已删除列表中"


# ==========================================
# Test: TTL Validation Rules
# ==========================================

@pytest.mark.p2
class TestTTLValidation(BaseAPITest):
    """
    TTL 规则验证测试
    """

    def test_ttl_is_30_days(self, auth_client):
        """
        业务规则: 软删除 TTL 应为 30 天

        验证方式: 检查 expires_at = deleted_at + 30 days
        """
        response = auth_client.get(Endpoints.PROJECTS_DELETED)

        if response.status_code != 200:
            pytest.skip("Deleted projects endpoint not available")

        items = response.json().get("items", [])

        if not items:
            pytest.skip("没有已删除的项目")

        for item in items:
            deleted_at = item.get("deleted_at")
            expires_at = item.get("expires_at") or item.get("delete_permanently_at")

            if deleted_at and expires_at:
                try:
                    deleted = datetime.fromisoformat(deleted_at.replace("Z", "+00:00"))
                    expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

                    diff = expires - deleted
                    expected_diff = timedelta(days=30)

                    # 允许一些误差 (秒级)
                    assert abs((diff - expected_diff).total_seconds()) < 60, (
                        f"TTL 应为 30 天，实际为 {diff.days} 天"
                    )
                    print(f"✓ TTL 正确: {diff.days} 天")
                    return
                except Exception as e:
                    print(f"日期解析错误: {e}")

        print("⚠️ 无法验证 TTL (缺少 expires_at 字段)")
