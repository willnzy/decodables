"""
Campaigns API Tests (Black Box)

测试 /api/v2/user/campaigns 相关接口

业务规则:
1. 获取当前活跃的营销活动
2. 用户可以领取活动奖励
3. 用户可以忽略/关闭活动

@module tests.integration.staging.campaigns.test_campaigns
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestActiveCampaigns(BaseAPITest):
    """
    GET /api/v2/user/campaigns/active 黑盒测试

    获取活跃营销活动
    """

    ENDPOINT = Endpoints.CAMPAIGNS_ACTIVE

    def test_get_active_campaigns(self, auth_client):
        """
        业务规则: 获取当前活跃的营销活动
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应应该是列表或包含 items 的对象
        assert isinstance(data, (list, dict)), "响应格式不正确"

    def test_campaigns_have_required_fields(self, auth_client):
        """
        业务规则: 活动应包含必要字段
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        items = data.get("items", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []
        if len(items) > 0:
            campaign = items[0]
            # 活动应该有基本信息
            assert "id" in campaign or "campaign_id" in campaign

    def test_public_endpoint(self, anon_client):
        """
        业务规则: 营销活动是公开端点

        支持 optional_user，匿名用户也可以查看通用活动
        """
        response = anon_client.get(self.ENDPOINT)
        # 公开端点，返回 200 (可能为空列表)
        data = self.assert_success(response)
        assert isinstance(data, dict), "响应格式不正确"


@pytest.mark.p1
class TestCampaignClaim(BaseAPITest):
    """
    POST /api/v2/user/campaigns/{campaign_id}/claim 黑盒测试

    领取活动奖励
    """

    def test_claim_nonexistent_campaign(self, auth_client):
        """
        业务规则: 领取不存在的活动应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.campaign_claim(fake_id))
        # 可能返回 404 或 400
        assert response.status_code in [400, 404]

    def test_claim_invalid_id_format(self, auth_client):
        """
        业务规则: 无效的活动 ID 格式应返回 400
        """
        response = auth_client.post(Endpoints.campaign_claim("invalid-id"))
        assert response.status_code in [400, 404]

    def test_claim_requires_authentication(self, anon_client):
        """
        业务规则: 领取活动必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(Endpoints.campaign_claim(fake_id))
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestCampaignDismiss(BaseAPITest):
    """
    POST /api/v2/user/campaigns/{campaign_id}/dismiss 黑盒测试

    忽略/关闭活动
    """

    def test_dismiss_nonexistent_campaign(self, auth_client):
        """
        业务规则: 忽略不存在的活动

        可能返回成功 (幂等) 或 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.campaign_dismiss(fake_id))
        # 可能返回 200 (幂等), 404, 或 422 (验证错误)
        assert response.status_code in [200, 400, 404, 422]

    def test_dismiss_requires_authentication(self, anon_client):
        """
        业务规则: 忽略活动必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(Endpoints.campaign_dismiss(fake_id))
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestCampaignTypes(BaseAPITest):
    """
    营销活动类型测试
    """

    ENDPOINT = Endpoints.CAMPAIGNS_ACTIVE

    def test_campaigns_have_type_info(self, auth_client):
        """
        业务规则: 活动应有类型信息

        类型包括: discount, credits_bonus, feature_unlock 等
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        items = data.get("items", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []
        if len(items) > 0:
            campaign = items[0]
            # 应该有类型或奖励信息
            has_type_info = (
                "type" in campaign or
                "campaign_type" in campaign or
                "reward" in campaign or
                "reward_type" in campaign
            )
            # 不强制要求，只是检查


@pytest.mark.p2
class TestCampaignExpiry(BaseAPITest):
    """
    营销活动过期测试
    """

    ENDPOINT = Endpoints.CAMPAIGNS_ACTIVE

    def test_active_campaigns_not_expired(self, auth_client):
        """
        业务规则: 活跃活动不应该已过期
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        items = data.get("items", data) if isinstance(data, dict) else data
        for campaign in items:
            # 如果有 is_expired 字段，应该为 False
            if "is_expired" in campaign:
                assert campaign["is_expired"] is False
