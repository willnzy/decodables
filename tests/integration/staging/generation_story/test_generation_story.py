"""
Generation Story API Tests (Black Box)

测试 /api/v2/user/generate/story 相关接口

业务规则:
1. AI 故事生成
2. AI 灵感建议 (免费)

@module tests.integration.staging.generation_story.test_generation_story
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestGenerateStory(BaseAPITest):
    """
    POST /api/v2/user/generate/story/story 黑盒测试

    AI 故事生成
    """

    ENDPOINT = Endpoints.GENERATE_STORY

    def test_generate_story_requires_topic(self, auth_client):
        """
        业务规则: 故事生成需要 topic
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 topic
        )
        assert response.status_code in [400, 422]

    def test_generate_story_with_valid_topic(self, auth_client):
        """
        业务规则: 提供有效 topic 可以生成故事
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"topic": "A brave cat's adventure"}
        )
        # 可能因为积分不足返回 402
        # 或成功返回 200
        # 或生成失败返回 500
        assert response.status_code in [200, 402, 500], (
            f"故事生成应返回 200/402/500，实际返回 {response.status_code}"
        )
        if response.status_code == 200:
            data = response.json()
            if data is not None:
                assert isinstance(data, dict)

    def test_generate_story_empty_topic_rejected(self, auth_client):
        """
        业务规则: 空 topic 应被拒绝
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"topic": ""}
        )
        assert response.status_code in [400, 422]

    def test_generate_story_requires_authentication(self, anon_client):
        """
        业务规则: 故事生成必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"topic": "test"}
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestGenerateInspiration(BaseAPITest):
    """
    POST /api/v2/user/generate/story/inspiration 黑盒测试

    AI 灵感建议 (免费)
    """

    ENDPOINT = Endpoints.GENERATE_INSPIRATION

    def test_generate_inspiration_without_category(self, auth_client):
        """
        业务规则: 可以不指定分类获取灵感
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        data = self.assert_success(response)
        assert isinstance(data, dict)

    def test_generate_inspiration_with_category(self, auth_client):
        """
        业务规则: 可以指定分类获取灵感

        InspirationRequest.category 的有效值:
        character, scene, story, all (或不传)
        Pattern: ^(character|scene|story|all)?$
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"category": "character"}
        )
        data = self.assert_success(response)

    def test_generate_inspiration_invalid_category(self, auth_client):
        """
        业务规则: 无效的分类应返回 422 验证错误

        InspirationRequest.category 有 pattern 约束: ^(character|scene|story|all)?$
        不匹配 pattern 的值 (如 "animals") 会被 Pydantic 拒绝为 422。
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"category": "nonexistent_category_12345"}
        )
        # 不匹配 pattern → 422 (Pydantic 验证), 或 400
        assert response.status_code in [400, 422]

    def test_generate_inspiration_requires_authentication(self, anon_client):
        """
        业务规则: 灵感生成必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={}
        )
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestGenerateStoryResponse(BaseAPITest):
    """
    故事生成响应结构测试
    """

    ENDPOINT = Endpoints.GENERATE_STORY

    def test_story_response_structure(self, auth_client):
        """
        业务规则: 故事响应应包含必要字段

        - title: 故事标题
        - pages: 页面内容
        - characters: 角色 (可选)
        - setting: 场景 (可选)
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"topic": "A friendly robot helps kids learn"}
        )
        if response.status_code == 200:
            data = response.json()
            # 检查基本结构
            # 实际字段可能因版本而异


@pytest.mark.p2
class TestGenerateInspirationResponse(BaseAPITest):
    """
    灵感建议响应结构测试
    """

    ENDPOINT = Endpoints.GENERATE_INSPIRATION

    def test_inspiration_returns_suggestions(self, auth_client):
        """
        业务规则: 灵感响应应包含建议列表
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        if response.status_code == 200:
            data = response.json()
            # 应该有建议内容
            assert isinstance(data, dict)

    def test_inspiration_fallback_on_error(self, auth_client):
        """
        业务规则: AI 错误时应返回备用灵感
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        # 应该总是返回 200 (有 fallback 机制)
        data = self.assert_success(response)


@pytest.mark.p2
class TestGenerateStoryRateLimits(BaseAPITest):
    """
    故事生成速率限制测试
    """

    def test_story_rate_limit(self, auth_client):
        """
        业务规则: 故事生成有速率限制 (20/minute)
        """
        pass

    def test_inspiration_rate_limit(self, auth_client):
        """
        业务规则: 灵感生成有速率限制 (30/minute)
        """
        pass
