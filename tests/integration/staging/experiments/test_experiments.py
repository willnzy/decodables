"""
Experiments API Tests (Black Box)

测试 /api/v2/user/experiments 相关接口

业务规则:
1. 用户可以被分配到实验组
2. 支持记录曝光和转化事件
3. 支持获取用户的实验状态

实际端点:
- POST /experiments/{experiment_key}/assign - 分配到实验组
- POST /experiments/{experiment_key}/exposure - 记录曝光
- POST /experiments/{experiment_key}/conversion - 记录转化
- GET /experiments/user/{user_identifier} - 获取用户实验状态

@module tests.integration.staging.experiments.test_experiments
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestExperimentAssign(BaseAPITest):
    """
    POST /api/v2/user/experiments/{experiment_key}/assign 黑盒测试

    分配用户到实验组
    """

    def test_assign_requires_user_identifier(self, anon_client):
        """
        业务规则: 分配实验组需要 user_identifier

        这是公开端点，但需要 user_identifier 参数
        """
        response = anon_client.post(
            Endpoints.experiment_assign("test_experiment"),
            json={}
        )
        # 缺少 user_identifier 返回 422 验证错误
        assert response.status_code == 422

    def test_assign_nonexistent_experiment(self, auth_client):
        """
        业务规则: 分配到不存在的实验

        AssignmentRequest 需要 user_identifier 字段
        """
        fake_key = f"nonexistent_exp_{uuid.uuid4().hex[:10]}"
        response = auth_client.post(
            Endpoints.experiment_assign(fake_key),
            json={"user_identifier": "test_user_123"}
        )
        # 可能返回 404 (实验不存在) 或 200 (创建新分配)
        assert response.status_code in [200, 400, 404]

    def test_assign_valid_experiment(self, auth_client):
        """
        业务规则: 分配到有效实验

        AssignmentRequest 需要 user_identifier 字段
        """
        response = auth_client.post(
            Endpoints.experiment_assign("test_experiment"),
            json={"user_identifier": "test_user_123"}
        )
        # 可能成功分配或实验不存在
        assert response.status_code in [200, 400, 404]


@pytest.mark.p1
class TestExperimentExposure(BaseAPITest):
    """
    POST /api/v2/user/experiments/{experiment_key}/exposure 黑盒测试

    记录实验曝光
    """

    def test_exposure_requires_params(self, anon_client):
        """
        业务规则: 记录曝光需要 user_identifier 和 variant_key

        这是公开端点，但需要必填参数
        """
        response = anon_client.post(
            Endpoints.experiment_exposure("test_experiment"),
            json={}
        )
        # 缺少 user_identifier 和 variant_key 返回 422 验证错误
        assert response.status_code == 422

    def test_exposure_nonexistent_experiment(self, auth_client):
        """
        业务规则: 记录不存在实验的曝光

        ExposureRequest 需要 user_identifier + variant_key
        """
        fake_key = f"nonexistent_exp_{uuid.uuid4().hex[:10]}"
        response = auth_client.post(
            Endpoints.experiment_exposure(fake_key),
            json={"user_identifier": "test_user_123", "variant_key": "control"}
        )
        assert response.status_code in [200, 400, 404]


@pytest.mark.p1
class TestExperimentConversion(BaseAPITest):
    """
    POST /api/v2/user/experiments/{experiment_key}/conversion 黑盒测试

    记录实验转化
    """

    def test_conversion_requires_user_identifier(self, anon_client):
        """
        业务规则: 记录转化需要 user_identifier

        这是公开端点，但需要必填参数
        """
        response = anon_client.post(
            Endpoints.experiment_conversion("test_experiment"),
            json={}
        )
        # 缺少 user_identifier 返回 422 验证错误
        assert response.status_code == 422

    def test_conversion_nonexistent_experiment(self, auth_client):
        """
        业务规则: 记录不存在实验的转化

        ConversionRequest 需要 user_identifier (metric_key 默认 "primary")
        """
        fake_key = f"nonexistent_exp_{uuid.uuid4().hex[:10]}"
        response = auth_client.post(
            Endpoints.experiment_conversion(fake_key),
            json={"user_identifier": "test_user_123"}
        )
        assert response.status_code in [200, 400, 404]


@pytest.mark.p2
class TestExperimentUserStatus(BaseAPITest):
    """
    GET /api/v2/user/experiments/user/{user_identifier} 黑盒测试

    获取用户实验状态
    """

    def test_user_status_public_endpoint(self, anon_client):
        """
        业务规则: 获取用户实验状态是公开端点

        任何人都可以查询某个 user_identifier 的实验状态
        """
        response = anon_client.get(
            Endpoints.experiment_user("test_user_123")
        )
        # 公开端点，返回 200 (可能为空列表)
        data = self.assert_success(response)
        assert "experiments" in data

    def test_user_status_nonexistent_user(self, auth_client):
        """
        业务规则: 获取不存在用户的实验状态
        """
        fake_user = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.get(
            Endpoints.experiment_user(fake_user)
        )
        # 可能返回 200 (空列表) 或 404
        assert response.status_code in [200, 404]

    def test_user_status_with_auth(self, auth_client):
        """
        业务规则: 获取有效用户的实验状态
        """
        response = auth_client.get(
            Endpoints.experiment_user("test_user_123")
        )
        assert response.status_code in [200, 404]


@pytest.mark.p2
class TestExperimentsValidation(BaseAPITest):
    """
    Experiments API 参数验证测试
    """

    def test_assign_with_metadata(self, auth_client):
        """
        业务规则: 分配时附带元数据

        AssignmentRequest 需要 user_identifier
        """
        response = auth_client.post(
            Endpoints.experiment_assign("test_experiment"),
            json={"user_identifier": "test_user_123", "metadata": {"source": "test"}}
        )
        assert response.status_code in [200, 400, 404]

    def test_conversion_with_value(self, auth_client):
        """
        业务规则: 转化时附带转化值

        ConversionRequest 需要 user_identifier
        """
        response = auth_client.post(
            Endpoints.experiment_conversion("test_experiment"),
            json={"user_identifier": "test_user_123", "conversion_value": 100}
        )
        assert response.status_code in [200, 400, 404]

    def test_experiment_key_special_chars(self, auth_client):
        """
        业务规则: 实验 key 包含特殊字符

        AssignmentRequest 需要 user_identifier
        """
        response = auth_client.post(
            Endpoints.experiment_assign("test/experiment/key"),
            json={"user_identifier": "test_user_123"}
        )
        # 特殊字符可能导致路由问题
        assert response.status_code in [400, 404]
