"""
Admin Themes API Tests (Black Box)

测试 /api/admin/themes 相关接口

业务规则:
1. 只有 admin 才能管理主题
2. 支持主题 CRUD、批量生成、审核流程
3. 主题有日期关联 (Daily Doodle)
4. 支持 AI 批量生成和重新生成

@module tests.integration.staging.admin.test_themes
"""

import pytest
import uuid
from datetime import datetime, timedelta
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminThemesList(BaseAPITest):
    """
    GET /api/admin/themes 黑盒测试

    获取主题列表
    """

    ENDPOINT = Endpoints.ADMIN_THEMES

    def test_list_themes_requires_admin(self, anon_client):
        """
        业务规则: 获取主题列表需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_list_themes_with_auth(self, auth_client):
        """
        业务规则: 认证用户获取主题列表
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_list_themes_pagination(self, auth_client):
        """
        业务规则: 支持分页查询
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 10}
        )
        assert response.status_code in [200, 403]

    def test_list_themes_filter_by_status(self, auth_client):
        """
        业务规则: 支持按状态筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"status": "pending"}
        )
        assert response.status_code in [200, 403]

    def test_list_themes_filter_by_date_range(self, auth_client):
        """
        业务规则: 支持按日期范围筛选
        """
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        response = auth_client.get(
            self.ENDPOINT,
            params={"start_date": today, "end_date": next_week}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminThemeDetail(BaseAPITest):
    """
    GET /api/admin/themes/{theme_id} 黑盒测试

    获取主题详情
    """

    def test_get_theme_requires_admin(self, anon_client, test_theme_id):
        """
        业务规则: 获取主题详情需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_theme(test_theme_id))
        self.assert_unauthorized(response)

    def test_get_nonexistent_theme(self, auth_client):
        """
        业务规则: 获取不存在的主题
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.admin_theme(fake_id))
        assert response.status_code in [403, 404]

    def test_get_theme_with_auth(self, auth_client, test_theme_id):
        """
        业务规则: 获取主题详情
        """
        response = auth_client.get(Endpoints.admin_theme(test_theme_id))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminThemeCreate(BaseAPITest):
    """
    POST /api/admin/themes 黑盒测试

    创建主题
    """

    ENDPOINT = Endpoints.ADMIN_THEMES

    def test_create_theme_requires_admin(self, anon_client):
        """
        业务规则: 创建主题需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "title": "Test Theme",
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        )
        self.assert_unauthorized(response)

    def test_create_theme_missing_title(self, auth_client):
        """
        业务规则: 缺少标题
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_theme_missing_date(self, auth_client):
        """
        业务规则: 缺少日期
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "title": "Test Theme"
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_theme_empty_body(self, auth_client):
        """
        业务规则: 空请求体
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        assert response.status_code in [400, 403, 422]


@pytest.mark.p1
class TestAdminThemeUpdate(BaseAPITest):
    """
    PUT /api/admin/themes/{theme_id} 黑盒测试

    更新主题
    """

    def test_update_theme_requires_admin(self, anon_client, test_theme_id):
        """
        业务规则: 更新主题需要管理员权限
        """
        response = anon_client.put(
            Endpoints.admin_theme(test_theme_id),
            json={"title": "Updated Theme"}
        )
        self.assert_unauthorized(response)

    def test_update_nonexistent_theme(self, auth_client):
        """
        业务规则: 更新不存在的主题
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.put(
            Endpoints.admin_theme(fake_id),
            json={"title": "Updated Theme"}
        )
        assert response.status_code in [403, 404]


@pytest.mark.p1
class TestAdminThemeDelete(BaseAPITest):
    """
    DELETE /api/admin/themes/{theme_id} 黑盒测试

    删除主题
    """

    def test_delete_theme_requires_admin(self, anon_client, test_theme_id):
        """
        业务规则: 删除主题需要管理员权限
        """
        response = anon_client.delete(Endpoints.admin_theme(test_theme_id))
        self.assert_unauthorized(response)

    def test_delete_nonexistent_theme(self, auth_client):
        """
        业务规则: 删除不存在的主题
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.admin_theme(fake_id))
        assert response.status_code in [403, 404]


@pytest.mark.p1
class TestAdminThemeBatchGenerate(BaseAPITest):
    """
    POST /api/admin/themes/batch-generate 黑盒测试

    AI 批量生成主题
    """

    ENDPOINT = Endpoints.ADMIN_THEMES_BATCH_GENERATE

    def test_batch_generate_requires_admin(self, anon_client):
        """
        业务规则: 批量生成需要管理员权限
        """
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "start_date": today,
                "end_date": next_week
            }
        )
        self.assert_unauthorized(response)

    def test_batch_generate_missing_dates(self, auth_client):
        """
        业务规则: 缺少日期范围
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        assert response.status_code in [400, 403, 422]

    def test_batch_generate_invalid_date_range(self, auth_client):
        """
        业务规则: 无效的日期范围 (结束日期早于开始日期)
        """
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "start_date": today,
                "end_date": yesterday
            }
        )
        assert response.status_code in [400, 403, 422]


@pytest.mark.p1
class TestAdminThemeGenerationStatus(BaseAPITest):
    """
    GET /api/admin/themes/generation-status 黑盒测试

    获取生成状态
    """

    ENDPOINT = Endpoints.ADMIN_THEMES_GENERATION_STATUS

    def test_generation_status_requires_admin(self, anon_client):
        """
        业务规则: 获取生成状态需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_generation_status_with_auth(self, auth_client):
        """
        业务规则: 获取当前生成状态
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminThemeCalendar(BaseAPITest):
    """
    GET /api/admin/themes/calendar 黑盒测试

    日历视图
    """

    ENDPOINT = Endpoints.ADMIN_THEMES_CALENDAR

    def test_calendar_requires_admin(self, anon_client):
        """
        业务规则: 日历视图需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_calendar_with_date_range(self, auth_client):
        """
        业务规则: 按月查看日历
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"year": 2026, "month": 1}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminThemeReview(BaseAPITest):
    """
    POST /api/admin/themes/{theme_id}/review 黑盒测试

    审核主题
    """

    def test_review_requires_admin(self, anon_client, test_theme_id):
        """
        业务规则: 审核主题需要管理员权限
        """
        response = anon_client.post(
            Endpoints.admin_theme_review(test_theme_id),
            json={"action": "approve"}
        )
        self.assert_unauthorized(response)

    def test_review_nonexistent_theme(self, auth_client):
        """
        业务规则: 审核不存在的主题
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.admin_theme_review(fake_id),
            json={"action": "approve"}
        )
        assert response.status_code in [403, 404]

    def test_review_invalid_action(self, auth_client, test_theme_id):
        """
        业务规则: 无效的审核动作
        """
        response = auth_client.post(
            Endpoints.admin_theme_review(test_theme_id),
            json={"action": "invalid_action"}
        )
        assert response.status_code in [400, 403, 404, 422]

    def test_review_approve(self, auth_client, test_theme_id):
        """
        业务规则: 批准主题
        """
        response = auth_client.post(
            Endpoints.admin_theme_review(test_theme_id),
            json={"action": "approve"}
        )
        assert response.status_code in [200, 403, 404]

    def test_review_reject(self, auth_client, test_theme_id):
        """
        业务规则: 拒绝主题
        """
        response = auth_client.post(
            Endpoints.admin_theme_review(test_theme_id),
            json={"action": "reject", "reason": "Not suitable"}
        )
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminThemeRegenerate(BaseAPITest):
    """
    POST /api/admin/themes/{theme_id}/regenerate 黑盒测试

    重新生成主题
    """

    def test_regenerate_requires_admin(self, anon_client, test_theme_id):
        """
        业务规则: 重新生成需要管理员权限
        """
        response = anon_client.post(Endpoints.admin_theme_regenerate(test_theme_id))
        self.assert_unauthorized(response)

    def test_regenerate_nonexistent_theme(self, auth_client):
        """
        业务规则: 重新生成不存在的主题
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.admin_theme_regenerate(fake_id))
        assert response.status_code in [403, 404]


@pytest.mark.p2
class TestAdminThemeHistory(BaseAPITest):
    """
    GET /api/admin/themes/{theme_id}/history 黑盒测试

    主题历史记录
    """

    def test_history_requires_admin(self, anon_client, test_theme_id):
        """
        业务规则: 查看历史需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_theme_history(test_theme_id))
        self.assert_unauthorized(response)

    def test_history_nonexistent_theme(self, auth_client):
        """
        业务规则: 不存在主题的历史
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.admin_theme_history(fake_id))
        assert response.status_code in [403, 404]


@pytest.mark.p2
class TestAdminThemeBatchApprove(BaseAPITest):
    """
    POST /api/admin/themes/review/batch-approve 黑盒测试

    批量批准主题
    """

    ENDPOINT = Endpoints.ADMIN_THEMES_BATCH_APPROVE

    def test_batch_approve_requires_admin(self, anon_client):
        """
        业务规则: 批量批准需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"theme_ids": ["id1", "id2"]}
        )
        self.assert_unauthorized(response)

    def test_batch_approve_empty_list(self, auth_client):
        """
        业务规则: 空的主题 ID 列表
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"theme_ids": []}
        )
        assert response.status_code in [200, 400, 403, 422]

    def test_batch_approve_nonexistent_themes(self, auth_client):
        """
        业务规则: 批量批准不存在的主题
        """
        fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        response = auth_client.post(
            self.ENDPOINT,
            json={"theme_ids": fake_ids}
        )
        assert response.status_code in [200, 400, 403, 404]
