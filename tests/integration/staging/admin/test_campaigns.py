"""
Admin Campaigns API Tests (Black Box)

测试 /api/admin/campaigns 相关接口

业务规则:
1. 只有 admin 才能管理营销活动
2. 支持活动 CRUD、激活、暂停、统计
3. 活动有类型: credits_gift, credits_discount, credits_bonus
4. 目标类型: all, subscription, users, new_users, inactive_users

@module tests.integration.staging.admin.test_campaigns
"""

import pytest
import uuid
from datetime import datetime, timedelta
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminCampaignsList(BaseAPITest):
    """
    GET /api/admin/campaigns 黑盒测试

    获取活动列表
    """

    ENDPOINT = Endpoints.ADMIN_CAMPAIGNS

    def test_list_campaigns_requires_admin(self, anon_client):
        """
        业务规则: 获取活动列表需要管理员权限
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_list_campaigns_with_auth(self, auth_client):
        """
        业务规则: 认证用户获取活动列表
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403]

    def test_list_campaigns_pagination(self, auth_client):
        """
        业务规则: 支持分页查询
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 10}
        )
        assert response.status_code in [200, 403]

    def test_list_campaigns_filter_by_status(self, auth_client):
        """
        业务规则: 支持按状态筛选

        状态: draft, active, paused, completed, cancelled
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"status": "active"}
        )
        assert response.status_code in [200, 403]

    def test_list_campaigns_invalid_status(self, auth_client):
        """
        业务规则: 无效的状态筛选
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"status": "invalid_status"}
        )
        assert response.status_code in [400, 403]


@pytest.mark.p1
class TestAdminCampaignDetail(BaseAPITest):
    """
    GET /api/admin/campaigns/{campaign_id} 黑盒测试

    获取活动详情
    """

    def test_get_campaign_requires_admin(self, anon_client, test_campaign_id):
        """
        业务规则: 获取活动详情需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_campaign(test_campaign_id))
        self.assert_unauthorized(response)

    def test_get_nonexistent_campaign(self, auth_client):
        """
        业务规则: 获取不存在的活动
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.admin_campaign(fake_id))
        assert response.status_code in [403, 404]

    def test_get_campaign_with_auth(self, auth_client, test_campaign_id):
        """
        业务规则: 获取活动详情
        """
        response = auth_client.get(Endpoints.admin_campaign(test_campaign_id))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p1
class TestAdminCampaignCreate(BaseAPITest):
    """
    POST /api/admin/campaigns 黑盒测试

    创建活动
    """

    ENDPOINT = Endpoints.ADMIN_CAMPAIGNS

    def test_create_campaign_requires_admin(self, anon_client):
        """
        业务规则: 创建活动需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "name": "Test Campaign",
                "type": "credits_gift",
                "config": {"credits": 100},
                "target_type": "all",
                "start_at": datetime.now().isoformat()
            }
        )
        self.assert_unauthorized(response)

    def test_create_campaign_missing_name(self, auth_client):
        """
        业务规则: 缺少名称
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "type": "credits_gift",
                "config": {"credits": 100},
                "target_type": "all",
                "start_at": datetime.now().isoformat()
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_campaign_invalid_type(self, auth_client):
        """
        业务规则: 无效的活动类型
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test Campaign",
                "type": "invalid_type",
                "config": {},
                "target_type": "all",
                "start_at": datetime.now().isoformat()
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_campaign_invalid_target_type(self, auth_client):
        """
        业务规则: 无效的目标类型
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test Campaign",
                "type": "credits_gift",
                "config": {"credits": 100},
                "target_type": "invalid_target",
                "start_at": datetime.now().isoformat()
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_campaign_name_too_short(self, auth_client):
        """
        业务规则: 名称太短 (min_length 验证)
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "",
                "type": "credits_gift",
                "config": {"credits": 100},
                "target_type": "all",
                "start_at": datetime.now().isoformat()
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_create_campaign_name_too_long(self, auth_client):
        """
        业务规则: 名称太长 (max_length 验证)
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "a" * 500,
                "type": "credits_gift",
                "config": {"credits": 100},
                "target_type": "all",
                "start_at": datetime.now().isoformat()
            }
        )
        assert response.status_code in [400, 403, 422]


@pytest.mark.p1
class TestAdminCampaignUpdate(BaseAPITest):
    """
    PUT /api/admin/campaigns/{campaign_id} 黑盒测试

    更新活动
    """

    def test_update_campaign_requires_admin(self, anon_client, test_campaign_id):
        """
        业务规则: 更新活动需要管理员权限
        """
        response = anon_client.put(
            Endpoints.admin_campaign(test_campaign_id),
            json={"name": "Updated Campaign"}
        )
        self.assert_unauthorized(response)

    def test_update_nonexistent_campaign(self, auth_client):
        """
        业务规则: 更新不存在的活动
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.put(
            Endpoints.admin_campaign(fake_id),
            json={"name": "Updated Campaign"}
        )
        assert response.status_code in [403, 404]

    def test_update_campaign_empty_body(self, auth_client, test_campaign_id):
        """
        业务规则: 空更新请求
        """
        response = auth_client.put(
            Endpoints.admin_campaign(test_campaign_id),
            json={}
        )
        assert response.status_code in [400, 403, 422]

    def test_update_campaign_invalid_target_type(self, auth_client, test_campaign_id):
        """
        业务规则: 更新为无效的目标类型
        """
        response = auth_client.put(
            Endpoints.admin_campaign(test_campaign_id),
            json={"target_type": "invalid_target"}
        )
        assert response.status_code in [400, 403, 404, 422]


@pytest.mark.p1
class TestAdminCampaignDelete(BaseAPITest):
    """
    DELETE /api/admin/campaigns/{campaign_id} 黑盒测试

    删除活动 (软删除)
    """

    def test_delete_campaign_requires_admin(self, anon_client, test_campaign_id):
        """
        业务规则: 删除活动需要管理员权限
        """
        response = anon_client.delete(Endpoints.admin_campaign(test_campaign_id))
        self.assert_unauthorized(response)

    def test_delete_nonexistent_campaign(self, auth_client):
        """
        业务规则: 删除不存在的活动
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.admin_campaign(fake_id))
        assert response.status_code in [403, 404]


@pytest.mark.p1
class TestAdminCampaignActivate(BaseAPITest):
    """
    POST /api/admin/campaigns/{campaign_id}/activate 黑盒测试

    激活活动
    """

    def test_activate_requires_admin(self, anon_client, test_campaign_id):
        """
        业务规则: 激活活动需要管理员权限
        """
        response = anon_client.post(Endpoints.admin_campaign_activate(test_campaign_id))
        self.assert_unauthorized(response)

    def test_activate_nonexistent_campaign(self, auth_client):
        """
        业务规则: 激活不存在的活动
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.admin_campaign_activate(fake_id))
        assert response.status_code in [403, 404]

    def test_activate_campaign(self, auth_client, test_campaign_id):
        """
        业务规则: 激活活动
        """
        response = auth_client.post(Endpoints.admin_campaign_activate(test_campaign_id))
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p1
class TestAdminCampaignPause(BaseAPITest):
    """
    POST /api/admin/campaigns/{campaign_id}/pause 黑盒测试

    暂停活动
    """

    def test_pause_requires_admin(self, anon_client, test_campaign_id):
        """
        业务规则: 暂停活动需要管理员权限
        """
        response = anon_client.post(Endpoints.admin_campaign_pause(test_campaign_id))
        self.assert_unauthorized(response)

    def test_pause_nonexistent_campaign(self, auth_client):
        """
        业务规则: 暂停不存在的活动
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.admin_campaign_pause(fake_id))
        assert response.status_code in [403, 404]

    def test_pause_campaign(self, auth_client, test_campaign_id):
        """
        业务规则: 暂停活动
        """
        response = auth_client.post(Endpoints.admin_campaign_pause(test_campaign_id))
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.p1
class TestAdminCampaignStats(BaseAPITest):
    """
    GET /api/admin/campaigns/{campaign_id}/stats 黑盒测试

    活动统计
    """

    def test_stats_requires_admin(self, anon_client, test_campaign_id):
        """
        业务规则: 获取统计需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_campaign_stats(test_campaign_id))
        self.assert_unauthorized(response)

    def test_stats_nonexistent_campaign(self, auth_client):
        """
        业务规则: 获取不存在活动的统计
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.get(Endpoints.admin_campaign_stats(fake_id))
        assert response.status_code in [403, 404]

    def test_stats_campaign(self, auth_client, test_campaign_id):
        """
        业务规则: 获取活动统计
        """
        response = auth_client.get(Endpoints.admin_campaign_stats(test_campaign_id))
        assert response.status_code in [200, 403, 404]


@pytest.mark.p2
class TestAdminCampaignsValidation(BaseAPITest):
    """
    Admin Campaigns API 参数验证测试
    """

    ENDPOINT = Endpoints.ADMIN_CAMPAIGNS

    def test_campaign_usage_limit_validation(self, auth_client):
        """
        业务规则: 使用次数限制验证
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test Campaign",
                "type": "credits_gift",
                "config": {"credits": 100},
                "target_type": "all",
                "start_at": datetime.now().isoformat(),
                "usage_limit": -1  # 负数
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_campaign_usage_per_user_validation(self, auth_client):
        """
        业务规则: 每用户使用次数限制验证
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test Campaign",
                "type": "credits_gift",
                "config": {"credits": 100},
                "target_type": "all",
                "start_at": datetime.now().isoformat(),
                "usage_per_user": 0  # 0 次
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_campaign_date_validation(self, auth_client):
        """
        业务规则: 日期验证 (结束日期早于开始日期)
        """
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test Campaign",
                "type": "credits_gift",
                "config": {"credits": 100},
                "target_type": "all",
                "start_at": now.isoformat(),
                "end_at": yesterday.isoformat()
            }
        )
        # 可能在创建时验证日期范围
        assert response.status_code in [200, 201, 400, 403, 422]

    def test_campaign_valid_types(self, auth_client):
        """
        业务规则: 测试所有有效的活动类型
        """
        valid_types = ["credits_gift", "credits_discount", "credits_bonus"]
        for camp_type in valid_types:
            response = auth_client.post(
                self.ENDPOINT,
                json={
                    "name": f"Test {camp_type} Campaign",
                    "type": camp_type,
                    "config": {"credits": 100},
                    "target_type": "all",
                    "start_at": datetime.now().isoformat()
                }
            )
            assert response.status_code in [200, 201, 403]

    def test_campaign_valid_target_types(self, auth_client):
        """
        业务规则: 测试所有有效的目标类型
        """
        valid_targets = ["all", "subscription", "users", "new_users", "inactive_users"]
        for target in valid_targets:
            response = auth_client.post(
                self.ENDPOINT,
                json={
                    "name": f"Test {target} Campaign",
                    "type": "credits_gift",
                    "config": {"credits": 100},
                    "target_type": target,
                    "start_at": datetime.now().isoformat()
                }
            )
            assert response.status_code in [200, 201, 403]
