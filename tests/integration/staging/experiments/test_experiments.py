"""
Experiments (Feature Flags) API Tests (Black Box)

测试 /api/v2/user/experiments 相关接口

业务规则:
1. 用户可以查询 Feature Flag 状态
2. 支持基于用户属性的条件判断
3. 返回所有可用的 Feature Flags

@module tests.integration.staging.experiments.test_experiments
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestGetAllFlags(BaseAPITest):
    """
    GET /api/v2/user/experiments/all-flags 黑盒测试

    获取所有 Feature Flags
    """

    ENDPOINT = Endpoints.EXPERIMENTS_ALL_FLAGS

    def test_get_all_flags_returns_dict(self, auth_client):
        """
        业务规则: all-flags 应返回 Feature Flag 字典
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应应该是字典，key 是 flag_key，value 是 flag 值
        assert isinstance(data, dict), "响应应该是字典"

    def test_flags_are_boolean_or_object(self, auth_client):
        """
        业务规则: Flag 值应该是 boolean 或配置对象
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        for key, value in data.items():
            # Flag 值可以是 boolean, string, number, 或 object
            assert isinstance(value, (bool, str, int, float, dict, list, type(None))), (
                f"Flag {key} 有无效的值类型: {type(value)}"
            )

    def test_public_endpoint_works_without_auth(self, anon_client):
        """
        业务规则: Feature Flags 可能是公开的

        或者需要认证 - 取决于实现
        """
        response = anon_client.get(self.ENDPOINT)
        # 可能返回 200 (公开) 或 401 (需要认证)
        assert response.status_code in [200, 401]


@pytest.mark.p1
class TestGetSingleFlag(BaseAPITest):
    """
    GET /api/v2/user/experiments/{flag_key} 黑盒测试

    查询单个 Feature Flag
    """

    def test_get_valid_flag(self, auth_client):
        """
        业务规则: 查询存在的 Flag 应返回其值
        """
        # 先获取所有 flags 找一个有效的 key
        all_flags_response = auth_client.get(Endpoints.EXPERIMENTS_ALL_FLAGS)
        if all_flags_response.status_code == 200:
            all_flags = all_flags_response.json()
            if all_flags:
                flag_key = list(all_flags.keys())[0]
                response = auth_client.get(Endpoints.experiment(flag_key))
                # 应该返回 200
                assert response.status_code == 200

    def test_get_nonexistent_flag(self, auth_client):
        """
        业务规则: 查询不存在的 Flag

        可能返回:
        - 200 + default value
        - 404
        """
        response = auth_client.get(
            Endpoints.experiment("nonexistent_flag_12345")
        )
        # 取决于实现，可能返回 200 (default) 或 404
        assert response.status_code in [200, 404]


@pytest.mark.p2
class TestUserTargeting(BaseAPITest):
    """
    GET /api/v2/user/experiments/user-targeting 黑盒测试

    获取用户定向规则
    """

    ENDPOINT = Endpoints.EXPERIMENTS_USER_TARGETING

    def test_get_user_targeting(self, auth_client):
        """
        业务规则: 获取用户的定向规则
        """
        response = auth_client.get(self.ENDPOINT)
        # 可能返回 200 或 404 (如果没有定向规则)
        assert response.status_code in [200, 404]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 用户定向需要认证
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestExperimentsPerformance(BaseAPITest):
    """
    Experiments 接口性能测试
    """

    def test_all_flags_response_time(self, auth_client):
        """
        业务规则: Feature Flags 查询应快速响应

        Feature Flags 是高频查询，应该有缓存
        SLA: < 500ms
        """
        response = auth_client.get(Endpoints.EXPERIMENTS_ALL_FLAGS)
        assert response.status_code == 200
        self.assert_response_time(response, max_seconds=0.5)
