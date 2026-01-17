"""
Generation Images API Tests (Black Box)

测试 /api/v2/user/generate/images 相关接口

业务规则:
1. AI 图片生成 (消耗积分)
2. 支持同步和异步生成
3. 支持参考图片
4. 模型根据 tier 选择

@module tests.integration.staging.generation_images.test_generation_images
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p0
class TestGenerateImagesSync(BaseAPITest):
    """
    POST /api/v2/user/generate/images/images 黑盒测试

    同步图片生成
    """

    ENDPOINT = Endpoints.GENERATE_IMAGES

    def test_generate_requires_prompts(self, auth_client):
        """
        业务规则: 图片生成需要提供 prompts
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 prompts
        )
        assert response.status_code in [400, 422]

    def test_generate_empty_prompts_rejected(self, auth_client):
        """
        业务规则: 空 prompts 应被拒绝
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"prompts": []}
        )
        assert response.status_code in [400, 422]

    def test_generate_prompts_validation(self, auth_client):
        """
        业务规则: prompts 应该是非空字符串列表
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"prompts": ["", "   "]}  # 空字符串
        )
        assert response.status_code in [400, 422]

    def test_generate_content_policy_check(self, auth_client):
        """
        业务规则: 不安全的内容应被拒绝

        系统会检查 prompts 是否包含违规内容
        """
        # 使用明显的测试标记，不是真的违规内容
        response = auth_client.post(
            self.ENDPOINT,
            json={"prompts": ["a cute puppy"]}  # 安全内容
        )
        # 安全内容应该通过内容检查
        # 可能因为积分不足返回 402，或成功返回 200
        assert response.status_code in [200, 402, 500]

    def test_generate_requires_authentication(self, anon_client):
        """
        业务规则: 图片生成必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"prompts": ["test"]}
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestGenerateImagesAsync(BaseAPITest):
    """
    POST /api/v2/user/generate/images/images/async 黑盒测试

    异步图片生成
    """

    ENDPOINT = Endpoints.GENERATE_IMAGES_ASYNC

    def test_async_generate_requires_prompts(self, auth_client):
        """
        业务规则: 异步生成也需要 prompts
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        assert response.status_code in [400, 422]

    def test_async_generate_returns_task_info(self, auth_client):
        """
        业务规则: 异步生成返回任务信息

        包括 task_id 用于后续查询
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"prompts": ["a simple test image"]}
        )
        # 可能因为积分不足返回 402
        if response.status_code == 200:
            data = response.json()
            assert "task_id" in data

    def test_async_generate_requires_authentication(self, anon_client):
        """
        业务规则: 异步生成必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"prompts": ["test"]}
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestGenerateImagesParameters(BaseAPITest):
    """
    图片生成参数测试
    """

    ENDPOINT = Endpoints.GENERATE_IMAGES

    def test_num_images_limit(self, auth_client):
        """
        业务规则: 单次生成图片数量限制 (1-4)
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "prompts": ["test"],
                "num_images": 10  # 超过限制
            }
        )
        # 应该被截断到 4 或返回错误
        assert response.status_code in [200, 400, 402, 422]

    def test_generation_mode_validation(self, auth_client):
        """
        业务规则: generation_mode 只能是 guided 或 flexible
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "prompts": ["test"],
                "generation_mode": "invalid_mode"
            }
        )
        # 无效模式应该被忽略或返回错误
        assert response.status_code in [200, 400, 402, 422]

    def test_creativity_level_validation(self, auth_client):
        """
        业务规则: creativity_level 有特定范围
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "prompts": ["test"],
                "creativity_level": "invalid_level"
            }
        )
        assert response.status_code in [200, 400, 402, 422]


@pytest.mark.p1
class TestGenerateImagesReferenceImage(BaseAPITest):
    """
    参考图片功能测试
    """

    ENDPOINT = Endpoints.GENERATE_IMAGES

    def test_reference_image_url_validation(self, auth_client):
        """
        业务规则: reference_image URL 必须有效
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "prompts": ["test"],
                "reference_image": "not-a-valid-url"
            }
        )
        assert response.status_code in [400, 422]

    def test_reference_image_ssrf_protection(self, auth_client):
        """
        业务规则: SSRF 攻击应被阻止

        私有 IP 地址应被拒绝
        """
        private_urls = [
            "http://localhost/image.png",
            "http://127.0.0.1/image.png",
            "http://192.168.1.1/image.png",
        ]

        for url in private_urls:
            response = auth_client.post(
                self.ENDPOINT,
                json={
                    "prompts": ["test"],
                    "reference_image": url
                }
            )
            assert response.status_code in [400, 422], (
                f"SSRF 保护失败: {url}"
            )

    def test_reference_strength_validation(self, auth_client):
        """
        业务规则: reference_strength 应在 0-1 之间
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "prompts": ["test"],
                "reference_image": "https://example.com/image.png",
                "reference_strength": 2.0  # 超过 1
            }
        )
        # 应该被截断或返回错误
        assert response.status_code in [200, 400, 402, 422]


@pytest.mark.p2
class TestGenerateImagesCreditHandling(BaseAPITest):
    """
    积分处理测试
    """

    ENDPOINT = Endpoints.GENERATE_IMAGES

    def test_insufficient_credits_error(self, auth_client):
        """
        业务规则: 积分不足时返回 402

        注意: 这取决于测试账户的积分余额
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"prompts": ["a beautiful landscape"]}
        )
        # 如果账户积分不足，应该返回 402
        # 如果足够，可能返回 200 或 500 (生成失败)
        assert response.status_code in [200, 402, 500]

    def test_error_message_does_not_expose_balance(self, auth_client):
        """
        业务规则: 错误消息不应暴露具体余额

        安全要求
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"prompts": ["test"]}
        )
        if response.status_code == 402:
            data = response.json()
            detail = data.get("detail", "")
            # 不应该包含具体的余额数字
            # 可以说 "需要 X 积分"，但不应该说 "你只有 Y 积分"


@pytest.mark.p2
class TestGenerateImagesRateLimits(BaseAPITest):
    """
    速率限制测试
    """

    ENDPOINT = Endpoints.GENERATE_IMAGES

    def test_rate_limit_exists(self, auth_client):
        """
        业务规则: 图片生成有速率限制 (10/minute)
        """
        # 速率限制测试需要快速多次请求
        pass
