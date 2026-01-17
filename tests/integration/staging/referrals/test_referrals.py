"""
Referrals API Tests (Black Box)

测试 /api/v2/user/referrals 相关接口

业务规则:
1. 用户可以创建推荐记录
2. 用户可以查看自己的推荐列表
3. 用户可以获取推荐统计
4. 推荐完成后奖励积分
5. 不能自己推荐自己

@module tests.integration.staging.referrals.test_referrals
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestReferralsList(BaseAPITest):
    """
    GET /api/v2/user/referrals 黑盒测试

    获取用户推荐列表
    """

    ENDPOINT = Endpoints.REFERRALS

    def test_get_referrals_returns_paginated_response(self, auth_client):
        """
        业务规则: 推荐列表应返回分页结构
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "data" in data, "响应应包含 data"
        assert isinstance(data["data"], list), "data 应该是列表"
        assert "pagination" in data, "响应应包含 pagination"

    def test_pagination_works(self, auth_client):
        """
        业务规则: 分页参数应生效
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"offset": 0, "limit": 5}
        )
        data = self.assert_success(response)

        referrals = data.get("data", [])
        assert len(referrals) <= 5, f"limit=5 但返回了 {len(referrals)} 条"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 推荐列表是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestReferralsStats(BaseAPITest):
    """
    GET /api/v2/user/referrals/stats 黑盒测试

    获取推荐统计
    """

    ENDPOINT = Endpoints.REFERRALS_STATS

    def test_get_stats_returns_statistics(self, auth_client):
        """
        业务规则: 统计接口应返回推荐数据

        期望包含:
        - 总推荐数
        - 完成数
        - 待定数
        - 总奖励积分
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "data" in data, "响应应包含 data"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 统计数据是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestCreateReferral(BaseAPITest):
    """
    POST /api/v2/user/referrals 黑盒测试

    创建推荐记录
    """

    ENDPOINT = Endpoints.REFERRALS

    def test_create_referral_requires_referee_id(self, auth_client):
        """
        业务规则: 创建推荐需要提供被推荐人 ID
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 referee_id
        )
        assert response.status_code in [400, 422]

    def test_cannot_refer_self(self, auth_client):
        """
        业务规则: 不能自己推荐自己

        先获取当前用户 ID，然后尝试推荐自己
        """
        # 获取当前用户信息
        profile_response = auth_client.get(Endpoints.PROFILE_ME)
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            user_id = profile_data.get("id") or profile_data.get("user_id")

            if user_id:
                response = auth_client.post(
                    self.ENDPOINT,
                    json={"referee_id": user_id}
                )
                # 应该返回 400 (禁止自我推荐)
                assert response.status_code == 400

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 创建推荐必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"referee_id": "user_test123"}
        )
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestReferralByCode(BaseAPITest):
    """
    GET /api/v2/user/referrals/code/{code} 黑盒测试

    根据推荐码查询推荐信息
    """

    def test_invalid_code_returns_404(self, auth_client):
        """
        业务规则: 无效的推荐码应返回 404
        """
        response = auth_client.get(
            Endpoints.referral_by_code("INVALID_CODE_12345")
        )
        self.assert_not_found(response)

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 查询推荐码必须登录
        """
        response = anon_client.get(
            Endpoints.referral_by_code("TEST_CODE")
        )
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestCompleteReferral(BaseAPITest):
    """
    POST /api/v2/user/referrals/{id}/complete 黑盒测试

    完成推荐
    """

    def test_complete_nonexistent_returns_404(self, auth_client):
        """
        业务规则: 完成不存在的推荐应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.referral_complete(fake_id)
        )
        self.assert_not_found(response)

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 完成推荐必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(
            Endpoints.referral_complete(fake_id)
        )
        self.assert_unauthorized(response)
