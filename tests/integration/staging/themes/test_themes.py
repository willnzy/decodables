"""
Themes API Tests (Black Box)

测试 /api/v2/user/themes 相关接口

业务规则:
1. 系统可以配置节日主题
2. 主题根据日期自动激活
3. 返回主题配置 (颜色/徽章/装饰)

@module tests.integration.staging.themes.test_themes
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p2
class TestCurrentTheme(BaseAPITest):
    """
    GET /api/v2/user/themes/current 黑盒测试

    获取当前激活的主题
    """

    ENDPOINT = Endpoints.THEMES_CURRENT

    def test_get_current_theme_returns_theme_or_null(self, auth_client):
        """
        业务规则: 获取当前主题

        如果有激活的主题，返回主题数据
        如果没有激活的主题，返回空值
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 可能有主题或没有
        # 有主题时应包含 theme_id, name, config
        if data.get("theme_id"):
            assert "name" in data, "有主题时应包含 name"

    def test_theme_config_structure(self, auth_client):
        """
        业务规则: 主题配置应包含视觉相关设置

        可能包含:
        - colors: 主题颜色
        - badge: 徽章配置
        - decorations: 装饰配置
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 如果有主题配置
        if data.get("config"):
            config = data["config"]
            # config 应该是字典
            assert isinstance(config, dict), "config 应该是字典"

    def test_public_endpoint_works_without_auth(self, anon_client):
        """
        业务规则: 主题接口可能是公开的 (不需要认证)

        或者需要认证 - 取决于业务需求
        """
        response = anon_client.get(self.ENDPOINT)
        # 可能返回 200 (公开) 或 401 (需要认证)
        assert response.status_code in [200, 401]

    def test_response_time_acceptable(self, auth_client):
        """
        业务规则: 主题查询应该快速响应

        主题是高频查询，应该有缓存
        SLA: < 1s
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code == 200
        self.assert_response_time(response, max_seconds=1.0)
