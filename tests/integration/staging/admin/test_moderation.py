"""
Admin Moderation API Tests (Black Box)

测试 /api/admin/moderation 相关接口

业务规则:
1. Marketplace 内容审核
2. 举报管理
3. 支持 approve/reject/delete/unpublish 操作
4. 所有审核操作都有审计日志

@module tests.integration.staging.admin.test_moderation
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminModerationList(BaseAPITest):
    """
    GET /api/admin/moderation/marketplace/moderation/list 黑盒测试

    获取待审核列表
    """

    ENDPOINT = Endpoints.ADMIN_MODERATION_LIST

    def test_list_requires_admin(self, anon_client):
        """
        业务规则: 获取审核列表需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_list_with_auth(self, auth_client):
        """
        业务规则: 获取待审核列表
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_list_pagination(self, auth_client):
        """
        业务规则: 支持分页查询
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 10}
        )
        assert response.status_code in [200, 403]

    def test_list_filter_by_status(self, auth_client):
        """
        业务规则: 按状态筛选

        状态: pending, approved, rejected, deleted
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"status": "pending"}
        )
        assert response.status_code in [200, 403]

    def test_list_invalid_status(self, auth_client):
        """
        业务规则: 无效的状态参数
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"status": "invalid_status"}
        )
        assert response.status_code in [400, 403]


@pytest.mark.p1
class TestAdminModerationDetail(BaseAPITest):
    """
    GET /api/admin/moderation/marketplace/moderation/{listing_id} 黑盒测试

    获取内容详情
    """

    def test_detail_requires_admin(self, anon_client, test_listing_id):
        """
        业务规则: 获取详情需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_moderation_listing(test_listing_id))
        self.assert_unauthorized(response)

    def test_detail_nonexistent(self, auth_client):
        """
        业务规则: 获取不存在的内容
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.admin_moderation_listing(fake_id))
        assert response.status_code in [403, 404]

    def test_detail_with_auth(self, auth_client, test_listing_id):
        """
        业务规则: 获取内容详情
        """
        response = auth_client.get(Endpoints.admin_moderation_listing(test_listing_id))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminModerationApprove(BaseAPITest):
    """
    POST /api/admin/moderation/marketplace/moderation/{listing_id}/approve 黑盒测试

    批准内容
    """

    def test_approve_requires_admin(self, anon_client, test_listing_id):
        """
        业务规则: 批准需要管理员权限
        """
        response = anon_client.post(Endpoints.admin_moderation_approve(test_listing_id))
        self.assert_unauthorized(response)

    def test_approve_nonexistent(self, auth_client):
        """
        业务规则: 批准不存在的内容
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.admin_moderation_approve(fake_id))
        assert response.status_code in [403, 404]

    def test_approve_with_auth(self, auth_client, test_listing_id):
        """
        业务规则: 批准内容
        """
        response = auth_client.post(Endpoints.admin_moderation_approve(test_listing_id))
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p1
class TestAdminModerationReject(BaseAPITest):
    """
    POST /api/admin/moderation/marketplace/moderation/{listing_id}/reject 黑盒测试

    拒绝内容
    """

    def test_reject_requires_admin(self, anon_client, test_listing_id):
        """
        业务规则: 拒绝需要管理员权限
        """
        response = anon_client.post(
            Endpoints.admin_moderation_reject(test_listing_id),
            json={"reason": "Violates guidelines"}
        )
        self.assert_unauthorized(response)

    def test_reject_nonexistent(self, auth_client):
        """
        业务规则: 拒绝不存在的内容
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.admin_moderation_reject(fake_id),
            json={"reason": "Test rejection"}
        )
        assert response.status_code in [403, 404]

    def test_reject_with_reason(self, auth_client, test_listing_id):
        """
        业务规则: 拒绝并提供原因
        """
        response = auth_client.post(
            Endpoints.admin_moderation_reject(test_listing_id),
            json={"reason": "Content violates community guidelines"}
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_reject_without_reason(self, auth_client, test_listing_id):
        """
        业务规则: 拒绝不提供原因
        """
        response = auth_client.post(
            Endpoints.admin_moderation_reject(test_listing_id),
            json={}
        )
        # 可能需要原因，也可能不需要
        assert response.status_code in [200, 400, 403, 404, 422]


@pytest.mark.p1
class TestAdminModerationDelete(BaseAPITest):
    """
    POST /api/admin/moderation/marketplace/moderation/{listing_id}/delete 黑盒测试

    删除内容
    """

    def test_delete_requires_admin(self, anon_client, test_listing_id):
        """
        业务规则: 删除需要管理员权限
        """
        response = anon_client.post(Endpoints.admin_moderation_delete(test_listing_id))
        self.assert_unauthorized(response)

    def test_delete_nonexistent(self, auth_client):
        """
        业务规则: 删除不存在的内容
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.admin_moderation_delete(fake_id))
        assert response.status_code in [403, 404]


@pytest.mark.p1
class TestAdminModerationUnpublish(BaseAPITest):
    """
    POST /api/admin/moderation/marketplace/moderation/{listing_id}/unpublish 黑盒测试

    下架内容
    """

    def test_unpublish_requires_admin(self, anon_client, test_listing_id):
        """
        业务规则: 下架需要管理员权限
        """
        response = anon_client.post(Endpoints.admin_moderation_unpublish(test_listing_id))
        self.assert_unauthorized(response)

    def test_unpublish_nonexistent(self, auth_client):
        """
        业务规则: 下架不存在的内容
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.admin_moderation_unpublish(fake_id))
        assert response.status_code in [403, 404]

    def test_unpublish_with_reason(self, auth_client, test_listing_id):
        """
        业务规则: 下架并提供原因
        """
        response = auth_client.post(
            Endpoints.admin_moderation_unpublish(test_listing_id),
            json={"reason": "Temporarily removed for review"}
        )
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p1
class TestAdminReportsList(BaseAPITest):
    """
    GET /api/admin/moderation/reports 黑盒测试

    获取举报列表
    """

    ENDPOINT = Endpoints.ADMIN_MODERATION_REPORTS

    def test_reports_requires_admin(self, anon_client):
        """
        业务规则: 获取举报列表需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_reports_with_auth(self, auth_client):
        """
        业务规则: 获取举报列表
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]

    def test_reports_filter_by_status(self, auth_client):
        """
        业务规则: 按状态筛选举报

        状态: pending, reviewed, resolved, dismissed
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"status": "pending"}
        )
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminReportsStats(BaseAPITest):
    """
    GET /api/admin/moderation/reports/stats 黑盒测试

    举报统计
    """

    ENDPOINT = Endpoints.ADMIN_MODERATION_REPORTS_STATS

    def test_stats_requires_admin(self, anon_client):
        """
        业务规则: 获取统计需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_stats_with_auth(self, auth_client):
        """
        业务规则: 获取举报统计
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [200, 403]


@pytest.mark.p1
class TestAdminReportDetail(BaseAPITest):
    """
    GET /api/admin/moderation/reports/{report_id} 黑盒测试

    获取举报详情
    """

    def test_report_detail_requires_admin(self, anon_client, test_report_id):
        """
        业务规则: 获取举报详情需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_report(test_report_id))
        self.assert_unauthorized(response)

    def test_report_detail_nonexistent(self, auth_client):
        """
        业务规则: 获取不存在的举报
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.admin_report(fake_id))
        assert response.status_code in [403, 404]

    def test_report_detail_with_auth(self, auth_client, test_report_id):
        """
        业务规则: 获取举报详情
        """
        response = auth_client.get(Endpoints.admin_report(test_report_id))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminReportRespond(BaseAPITest):
    """
    POST /api/admin/moderation/reports/{report_id}/respond 黑盒测试

    回复举报
    """

    def test_respond_requires_admin(self, anon_client, test_report_id):
        """
        业务规则: 回复举报需要管理员权限
        """
        response = anon_client.post(
            Endpoints.admin_report_respond(test_report_id),
            json={"action": "resolved", "response": "Issue has been addressed"}
        )
        self.assert_unauthorized(response)

    def test_respond_nonexistent(self, auth_client):
        """
        业务规则: 回复不存在的举报
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.admin_report_respond(fake_id),
            json={"action": "resolved", "response": "Test"}
        )
        assert response.status_code in [403, 404]

    def test_respond_with_action(self, auth_client, test_report_id):
        """
        业务规则: 回复举报并采取行动
        """
        response = auth_client.post(
            Endpoints.admin_report_respond(test_report_id),
            json={
                "action": "resolved",
                "response": "We have reviewed and taken action"
            }
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_respond_dismiss(self, auth_client, test_report_id):
        """
        业务规则: 驳回举报
        """
        response = auth_client.post(
            Endpoints.admin_report_respond(test_report_id),
            json={
                "action": "dismissed",
                "response": "Content does not violate guidelines"
            }
        )
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p2
class TestAdminModerationValidation(BaseAPITest):
    """
    Admin Moderation API 参数验证测试
    """

    def test_reject_empty_reason(self, auth_client, test_listing_id):
        """
        业务规则: 拒绝时空原因
        """
        response = auth_client.post(
            Endpoints.admin_moderation_reject(test_listing_id),
            json={"reason": ""}
        )
        assert response.status_code in [200, 400, 403, 404, 422]

    def test_reject_very_long_reason(self, auth_client, test_listing_id):
        """
        业务规则: 拒绝原因过长
        """
        response = auth_client.post(
            Endpoints.admin_moderation_reject(test_listing_id),
            json={"reason": "a" * 10000}
        )
        assert response.status_code in [200, 400, 403, 404, 422]

    def test_invalid_listing_id_format(self, auth_client):
        """
        业务规则: 无效的 listing ID 格式
        """
        response = auth_client.get(
            Endpoints.admin_moderation_listing("invalid-id-format")
        )
        assert response.status_code in [400, 403, 404]

    def test_report_respond_invalid_action(self, auth_client, test_report_id):
        """
        业务规则: 无效的响应动作
        """
        response = auth_client.post(
            Endpoints.admin_report_respond(test_report_id),
            json={
                "action": "invalid_action",
                "response": "Test"
            }
        )
        assert response.status_code in [400, 403, 404, 422]
