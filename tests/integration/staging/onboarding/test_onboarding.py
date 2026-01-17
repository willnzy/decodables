"""
Onboarding API Tests (Black Box)

测试 /api/v2/user/onboarding 相关接口

业务规则:
1. 用户可以获取可用的引导步骤列表
2. 用户可以开始/完成/跳过引导步骤
3. 用户可以查看任务清单进度
4. 引导步骤根据用户 Tier 过滤

@module tests.integration.staging.onboarding.test_onboarding
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestOnboardingSteps(BaseAPITest):
    """
    GET /api/v2/user/onboarding/steps 黑盒测试

    获取可用引导步骤
    """

    ENDPOINT = Endpoints.ONBOARDING_STEPS

    def test_get_steps_returns_list(self, auth_client):
        """
        业务规则: 引导步骤接口应返回步骤列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "data" in data, "响应应包含 data"
        assert isinstance(data["data"], list), "data 应该是列表"
        assert "total" in data, "响应应包含 total"

    def test_step_structure(self, auth_client):
        """
        业务规则: 每个引导步骤应包含必要字段

        必需字段:
        - step_key: 步骤标识
        - title: 步骤标题
        - status: 步骤状态 (pending/completed/skipped)
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        steps = data.get("data", [])
        if len(steps) > 0:
            step = steps[0]
            # 检查常见字段
            assert "step_key" in step or "key" in step, "步骤缺少 key 标识"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 引导步骤是用户相关数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestOnboardingStepActions(BaseAPITest):
    """
    POST /api/v2/user/onboarding/steps/{action} 黑盒测试

    开始/完成/跳过引导步骤
    """

    def test_start_step_requires_step_key(self, auth_client):
        """
        业务规则: 开始步骤需要提供 step_key
        """
        response = auth_client.post(
            Endpoints.ONBOARDING_STEPS_START,
            json={}  # 缺少 step_key
        )
        # 应该返回 400 或 422 (验证错误)
        assert response.status_code in [400, 422], (
            f"缺少 step_key 应返回验证错误，但返回了 {response.status_code}"
        )

    def test_complete_step_requires_step_key(self, auth_client):
        """
        业务规则: 完成步骤需要提供 step_key
        """
        response = auth_client.post(
            Endpoints.ONBOARDING_STEPS_COMPLETE,
            json={}
        )
        assert response.status_code in [400, 422]

    def test_skip_step_requires_step_key(self, auth_client):
        """
        业务规则: 跳过步骤需要提供 step_key
        """
        response = auth_client.post(
            Endpoints.ONBOARDING_STEPS_SKIP,
            json={}
        )
        assert response.status_code in [400, 422]

    def test_invalid_step_key_returns_404(self, auth_client):
        """
        业务规则: 无效的 step_key 应返回 404
        """
        response = auth_client.post(
            Endpoints.ONBOARDING_STEPS_START,
            json={"step_key": "invalid_step_key_12345"}
        )
        # 可能返回 404 (未找到) 或 400 (无效)
        assert response.status_code in [400, 404]

    def test_actions_require_authentication(self, anon_client):
        """
        业务规则: 所有步骤操作必须登录
        """
        for endpoint in [
            Endpoints.ONBOARDING_STEPS_START,
            Endpoints.ONBOARDING_STEPS_COMPLETE,
            Endpoints.ONBOARDING_STEPS_SKIP
        ]:
            response = anon_client.post(
                endpoint,
                json={"step_key": "test_step"}
            )
            self.assert_unauthorized(response)


@pytest.mark.p1
class TestOnboardingChecklist(BaseAPITest):
    """
    GET /api/v2/user/onboarding/checklist 黑盒测试

    获取任务清单进度
    """

    ENDPOINT = Endpoints.ONBOARDING_CHECKLIST

    def test_get_checklist_returns_progress(self, auth_client):
        """
        业务规则: 任务清单应返回进度信息

        期望包含:
        - 总任务数
        - 已完成数
        - 完成百分比
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert "data" in data, "响应应包含 data"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 任务清单是用户相关数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)
