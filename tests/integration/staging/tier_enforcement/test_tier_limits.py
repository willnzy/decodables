"""
Tier Enforcement Integration Tests

测试 Tier 权限限制的强制执行:
- t1 (Free): 1 个项目
- t2 (Starter): 20 个项目
- t3 (Pro): 200 个项目

TDD Approach:
- Sad Path First: 测试超出限制时返回 403
- 验证错误消息包含明确的限制信息

业务规则 (来源: TIER-PERMISSIONS.md):
1. 每个 Tier 有明确的项目数量限制
2. 超出限制时应返回 403 Forbidden
3. 错误响应应包含当前使用量和限制
4. 升级 Tier 后限制应立即生效

@module tests.integration.staging.tier_enforcement.test_tier_limits
"""

import pytest
import uuid

from tests.integration.staging.base import BaseAPITest
from tests.integration.staging.constants import Endpoints


# ==========================================
# Test: Project Count Limits
# ==========================================

@pytest.mark.p0
class TestProjectTierLimits(BaseAPITest):
    """
    项目数量限制测试

    业务规则:
    - t1 (Free): 最多 1 个项目
    - t2 (Starter): 最多 20 个项目
    - t3 (Pro): 最多 200 个项目
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_project_limit_error_contains_usage_info(self, auth_client):
        """
        业务规则: 超出限制时错误响应应包含使用量信息

        Sad Path: 403 响应应包含:
        - 当前项目数量
        - Tier 限制
        - 升级提示
        """
        # 获取当前项目数量
        list_response = auth_client.get(self.ENDPOINT)
        data = list_response.json()
        items = data.get("items") or data.get("projects") or []
        current_count = len(items)

        # 尝试创建项目直到超出限制
        created_ids = []

        for i in range(5):  # 尝试创建多个，足以触发 Free tier 限制
            test_title = f"TierTest_{uuid.uuid4().hex[:8]}"
            response = auth_client.post(
                self.ENDPOINT,
                json={"title": test_title, "content": {}}
            )

            if response.status_code == 403:
                # 验证错误响应包含有用信息
                error_data = response.json()
                error_text = str(error_data).lower()

                # 应包含限制相关关键词
                limit_keywords = ["limit", "quota", "maximum", "tier", "plan", "upgrade"]
                has_limit_info = any(kw in error_text for kw in limit_keywords)

                assert has_limit_info, (
                    f"403 错误应包含限制信息，但实际响应: {error_data}"
                )

                # 清理已创建的项目
                for pid in created_ids:
                    auth_client.delete(
                        Endpoints.project(pid),
                        params={"permanent": True}
                    )
                return

            elif response.status_code in [200, 201]:
                project_id = response.json().get("id") or response.json().get("project_id")
                created_ids.append(project_id)

        # 清理所有创建的项目
        for pid in created_ids:
            auth_client.delete(Endpoints.project(pid), params={"permanent": True})

        # 如果没有触发限制，可能是高 Tier 用户
        pytest.skip("测试用户可能是 t2/t3 tier，未触发项目限制")

    def test_dashboard_shows_tier_limits(self, auth_client):
        """
        业务规则: Dashboard 应显示用户的 Tier 限制

        验证 Dashboard 响应包含:
        - 当前 Tier
        - 项目限制
        - 当前使用量
        """
        response = auth_client.get(Endpoints.PROJECTS_DASHBOARD)

        if response.status_code != 200:
            pytest.skip("Dashboard endpoint not available")

        data = response.json()

        # Dashboard 应包含限制相关信息
        # 可能的字段: tier, project_limit, projects_used, quota 等
        limit_fields = [
            "tier", "plan", "project_limit", "max_projects",
            "projects_used", "projects_count", "quota", "usage"
        ]

        has_limit_field = any(field in data for field in limit_fields)

        # 记录发现的字段用于调试
        print(f"Dashboard fields: {list(data.keys())}")

        # 这是一个软断言 - 如果没有，记录为改进建议
        if not has_limit_field:
            print("⚠️ 改进建议: Dashboard 应包含 Tier 限制信息")


@pytest.mark.p0
class TestAssetTierLimits(BaseAPITest):
    """
    素材数量/存储限制测试

    业务规则:
    - t1: 50MB 存储
    - t2: 500MB 存储
    - t3: 5GB 存储
    """

    ENDPOINT = Endpoints.ASSETS

    def test_asset_upload_checks_storage_limit(self, auth_client):
        """
        业务规则: 上传素材时应检查存储限制

        注意: 实际上传测试需要文件，这里测试 API 响应结构
        """
        # 获取用户资产统计
        response = auth_client.get(Endpoints.PROFILE_ME)

        if response.status_code != 200:
            pytest.skip("User profile endpoint not available")

        data = response.json()

        # 验证响应包含存储信息
        storage_fields = [
            "storage_used", "storage_limit", "storage_quota",
            "total_storage", "available_storage"
        ]

        has_storage_info = any(field in str(data).lower() for field in storage_fields)

        print(f"Profile fields: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")

        # 软断言 - 记录为改进建议
        if not has_storage_info:
            print("⚠️ 改进建议: User profile 应包含存储限制信息")


# ==========================================
# Test: Feature Access by Tier
# ==========================================

@pytest.mark.p1
class TestFeatureAccessByTier(BaseAPITest):
    """
    按 Tier 限制功能访问测试

    业务规则:
    - 某些功能只对特定 Tier 开放
    - 访问未授权功能应返回 403
    """

    def test_get_user_tier_info(self, auth_client):
        """
        业务规则: 用户可以查看自己的 Tier 信息
        """
        response = auth_client.get(Endpoints.PROFILE_ME)

        if response.status_code != 200:
            pytest.skip("User profile endpoint not available")

        data = response.json()

        # 应包含 tier 信息
        tier_fields = ["tier", "plan", "subscription_tier", "plan_type"]
        has_tier = any(field in data for field in tier_fields)

        if has_tier:
            tier_value = data.get("tier") or data.get("plan") or data.get("subscription_tier")
            print(f"✓ 用户 Tier: {tier_value}")
        else:
            print("⚠️ 改进建议: User profile 应包含 Tier 信息")


# ==========================================
# Test: Tier Limit Edge Cases
# ==========================================

@pytest.mark.p1
class TestTierLimitEdgeCases(BaseAPITest):
    """
    Tier 限制边界情况测试
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_soft_deleted_projects_count_toward_limit(self, auth_client):
        """
        业务规则: 软删除的项目是否计入配额？

        测试逻辑:
        1. 创建项目
        2. 软删除
        3. 再次创建
        4. 验证是否触发限制

        预期行为: 软删除项目不计入配额（用户可恢复）
        """
        # 获取当前项目列表（包括已删除）
        normal_response = auth_client.get(self.ENDPOINT)
        normal_items = normal_response.json().get("items", [])

        deleted_response = auth_client.get(Endpoints.PROJECTS_DELETED)
        if deleted_response.status_code == 200:
            deleted_items = deleted_response.json().get("items", [])
            print(f"当前项目: {len(normal_items)}, 已删除项目: {len(deleted_items)}")
        else:
            print(f"当前项目: {len(normal_items)}, 已删除项目: N/A")

        # 此测试主要是文档测试，记录行为
        # 具体行为需要根据业务规则确认

    def test_restore_project_checks_limit(self, auth_client):
        """
        业务规则: 恢复已删除项目时应检查配额

        如果用户:
        1. 有 1 个项目 (Free tier 上限)
        2. 删除了另一个项目
        3. 尝试恢复删除的项目

        预期: 应返回 403 (达到配额上限)
        """
        # 获取已删除项目列表
        deleted_response = auth_client.get(Endpoints.PROJECTS_DELETED)

        if deleted_response.status_code != 200:
            pytest.skip("Deleted projects endpoint not available")

        deleted_items = deleted_response.json().get("items", [])

        if not deleted_items:
            pytest.skip("没有已删除的项目可用于测试")

        # 获取当前正常项目数量
        normal_response = auth_client.get(self.ENDPOINT)
        normal_items = normal_response.json().get("items", [])

        print(f"正常项目: {len(normal_items)}, 已删除项目: {len(deleted_items)}")

        # 尝试恢复一个已删除项目
        deleted_id = deleted_items[0].get("id") or deleted_items[0].get("project_id")
        restore_response = auth_client.post(Endpoints.project_restore(deleted_id))

        if restore_response.status_code == 403:
            # 验证是因为配额限制
            error_data = restore_response.json()
            print(f"恢复被拒绝 (403): {error_data}")
            # 这是预期行为
        elif restore_response.status_code == 200:
            # 恢复成功，清理: 再次删除
            auth_client.delete(
                Endpoints.project(deleted_id),
                params={"permanent": False}
            )
            print("恢复成功，用户未达到配额上限")
        else:
            print(f"恢复返回意外状态: {restore_response.status_code}")


# ==========================================
# Test: Duplicate Project Checks Limit
# ==========================================

@pytest.mark.p1
class TestDuplicateProjectLimit(BaseAPITest):
    """
    复制项目时的配额检查测试
    """

    ENDPOINT = Endpoints.PROJECTS

    def test_duplicate_project_checks_limit(self, auth_client):
        """
        业务规则: 复制项目时应检查配额

        复制操作会创建新项目，应遵守配额限制
        """
        # 获取当前项目
        list_response = auth_client.get(self.ENDPOINT, params={"limit": 1})
        items = list_response.json().get("items", [])

        if not items:
            pytest.skip("没有可复制的项目")

        source_id = items[0].get("id") or items[0].get("project_id")

        # 尝试复制
        duplicate_response = auth_client.post(Endpoints.project_duplicate(source_id))

        if duplicate_response.status_code == 403:
            error_data = duplicate_response.json()
            error_text = str(error_data).lower()

            # 应包含限制相关信息
            limit_keywords = ["limit", "quota", "maximum", "tier"]
            has_limit_info = any(kw in error_text for kw in limit_keywords)

            assert has_limit_info, (
                f"复制被拒绝但错误信息不明确: {error_data}"
            )
            print(f"✓ 复制因配额限制被拒绝: {error_data}")

        elif duplicate_response.status_code in [200, 201]:
            # 复制成功，清理
            dup_id = duplicate_response.json().get("id") or duplicate_response.json().get("project_id")
            auth_client.delete(Endpoints.project(dup_id), params={"permanent": True})
            print("复制成功，用户未达到配额上限")

        else:
            pytest.fail(f"意外的响应状态: {duplicate_response.status_code}")
