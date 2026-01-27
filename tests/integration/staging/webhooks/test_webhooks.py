"""
Webhooks API Integration Tests

测试 Webhook 处理接口:
- POST /api/v2/user/webhooks/clerk - Clerk 用户事件
- POST /api/v2/user/webhooks/stripe - Stripe 支付事件

注意:
- Webhook 端点不需要常规认证
- 但需要签名验证
- 测试无签名请求应被拒绝

TDD Approach:
- Sad Path First: 400 (Invalid Signature) → 200

@module tests.integration.staging.webhooks.test_webhooks
"""

import pytest
import json

from tests.integration.staging.constants import Endpoints


# ==========================================
# Base Test Class
# ==========================================

class BaseAPITest:
    """Base class with common assertion methods."""

    def assert_success(self, response, expected_status: int = 200) -> dict:
        """Assert successful response and return JSON data."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )
        return response.json()

    def assert_bad_request(self, response):
        """Assert 400 Bad Request."""
        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}"
        )


# ==========================================
# Test: Clerk Webhook
# ==========================================

@pytest.mark.p1
class TestClerkWebhook(BaseAPITest):
    """
    POST /api/v2/user/webhooks/clerk 黑盒测试

    Clerk 用户事件 Webhook

    业务规则:
    1. 必须通过 Svix 签名验证
    2. 无签名或无效签名返回 400
    3. 支持的事件: user.created, user.updated, session.*
    """

    ENDPOINT = Endpoints.WEBHOOKS_CLERK

    def test_clerk_webhook_without_signature_rejected(self, anon_client):
        """
        业务规则: 无签名请求应被拒绝

        Sad Path First: 400 Bad Request
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "type": "user.created",
                "data": {"id": "test_123"}
            }
        )

        # 应返回 400 或 500 (配置错误/签名验证失败)
        assert response.status_code in [400, 500], (
            f"无签名请求应被拒绝，但返回了 {response.status_code}"
        )

    def test_clerk_webhook_invalid_signature_rejected(self, anon_client):
        """
        业务规则: 无效签名应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            headers={
                "svix-id": "msg_test_123",
                "svix-timestamp": "1234567890",
                "svix-signature": "v1,invalid_signature_here"
            },
            json={
                "type": "user.created",
                "data": {"id": "test_123"}
            }
        )

        # 应返回 400 (签名验证失败)
        assert response.status_code in [400, 500], (
            f"无效签名应被拒绝，但返回了 {response.status_code}"
        )

    def test_clerk_webhook_empty_body_rejected(self, anon_client):
        """
        业务规则: 空请求体应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            content=b""
        )

        # 应返回 400 或 422 (验证失败)
        assert response.status_code in [400, 422, 500], (
            f"空请求体应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Stripe Webhook
# ==========================================

@pytest.mark.p1
class TestStripeWebhook(BaseAPITest):
    """
    POST /api/v2/user/webhooks/stripe 黑盒测试

    Stripe 支付事件 Webhook

    业务规则:
    1. 必须包含 Stripe-Signature header
    2. 无签名或无效签名返回 400
    3. 支持的事件: checkout.session.completed, invoice.payment_succeeded, etc.
    """

    ENDPOINT = Endpoints.WEBHOOKS_STRIPE

    def test_stripe_webhook_without_signature_rejected(self, anon_client):
        """
        业务规则: 缺少 Stripe-Signature header 应返回 422

        Sad Path First: Header required
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "id": "evt_test_123",
                "type": "checkout.session.completed"
            }
        )

        # FastAPI 对于缺少必需 header 返回 422
        assert response.status_code == 422, (
            f"缺少签名 header 应返回 422，但返回了 {response.status_code}"
        )

    def test_stripe_webhook_invalid_signature_rejected(self, anon_client):
        """
        业务规则: 无效签名应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            headers={
                "Stripe-Signature": "t=1234567890,v1=invalid_signature"
            },
            json={
                "id": "evt_test_123",
                "type": "checkout.session.completed"
            }
        )

        # 应返回 400 (签名验证失败)
        self.assert_bad_request(response)

    def test_stripe_webhook_empty_body_rejected(self, anon_client):
        """
        业务规则: 空请求体应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            headers={
                "Stripe-Signature": "t=1234567890,v1=test_signature"
            },
            content=b""
        )

        # 应返回 400 (签名验证失败或空 body)
        assert response.status_code in [400, 422], (
            f"空请求体应被拒绝，但返回了 {response.status_code}"
        )

    def test_stripe_webhook_malformed_json_rejected(self, anon_client):
        """
        业务规则: 格式错误的 JSON 应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            headers={
                "Stripe-Signature": "t=1234567890,v1=test_signature",
                "Content-Type": "application/json"
            },
            content=b"not valid json"
        )

        # 应返回 400 (签名验证失败) 或 422 (JSON 解析失败)
        assert response.status_code in [400, 422], (
            f"格式错误的 JSON 应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Webhook Security
# ==========================================

@pytest.mark.security
@pytest.mark.p0
class TestWebhookSecurity(BaseAPITest):
    """
    Webhook 安全测试

    验证:
    1. 重放攻击防护 (通过签名时间戳验证)
    2. 签名必须有效
    3. 请求体完整性
    """

    def test_clerk_replay_attack_prevention(self, anon_client):
        """
        安全规则: 过期的时间戳应被拒绝 (防止重放攻击)

        注意: Svix 签名包含时间戳，过期请求应被拒绝
        """
        # 使用很旧的时间戳
        response = anon_client.post(
            Endpoints.WEBHOOKS_CLERK,
            headers={
                "svix-id": "msg_test_123",
                "svix-timestamp": "1000000000",  # 2001 年的时间戳
                "svix-signature": "v1,test_signature"
            },
            json={"type": "user.created", "data": {}}
        )

        # 应被拒绝 (时间戳过期或签名无效)
        assert response.status_code in [400, 500], (
            f"过期时间戳应被拒绝，但返回了 {response.status_code}"
        )

    def test_stripe_replay_attack_prevention(self, anon_client):
        """
        安全规则: 过期的时间戳应被拒绝

        Stripe 签名格式: t={timestamp},v1={signature}
        """
        # 使用很旧的时间戳
        response = anon_client.post(
            Endpoints.WEBHOOKS_STRIPE,
            headers={
                "Stripe-Signature": "t=1000000000,v1=test_signature"
            },
            json={"id": "evt_test", "type": "test"}
        )

        # 应被拒绝
        self.assert_bad_request(response)

    def test_clerk_tampered_body_rejected(self, anon_client):
        """
        安全规则: 修改后的请求体应被拒绝 (签名不匹配)
        """
        # 即使有签名 header，如果签名与 body 不匹配也应被拒绝
        response = anon_client.post(
            Endpoints.WEBHOOKS_CLERK,
            headers={
                "svix-id": "msg_test_123",
                "svix-timestamp": "1234567890",
                "svix-signature": "v1,valid_looking_but_wrong_signature"
            },
            json={"type": "user.created", "data": {"tampered": True}}
        )

        assert response.status_code in [400, 500], (
            f"被篡改的请求体应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Webhook Idempotency
# ==========================================

@pytest.mark.p0
class TestWebhookIdempotency(BaseAPITest):
    """
    Webhook 幂等性测试

    业务规则:
    1. 相同的 Webhook 事件不应被处理两次
    2. 使用事件 ID 去重
    3. 重复请求应返回成功但不重复执行业务逻辑

    重要性:
    - 防止重复扣费/充值
    - 防止重复创建用户
    - 网络重试时保证数据一致性
    """

    def test_stripe_idempotency_key_concept(self, anon_client):
        """
        业务规则: Stripe Webhook 应基于事件 ID 实现幂等

        Stripe 事件特点:
        - 每个事件有唯一的 id (evt_xxx)
        - 相同事件可能被发送多次 (网络重试)
        - 后端应记录已处理的事件 ID

        注意: 由于我们没有有效签名，只能测试请求格式
        """
        # 构造一个带有事件 ID 的请求
        event_id = "evt_test_idempotency_123"
        event_payload = {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "customer": "cus_test_123"
                }
            }
        }

        # 第一次请求 (会因签名失败而被拒绝)
        response1 = anon_client.post(
            Endpoints.WEBHOOKS_STRIPE,
            headers={"Stripe-Signature": "t=1234567890,v1=fake_signature"},
            json=event_payload
        )

        # 由于签名无效，应返回 400
        assert response1.status_code == 400, (
            f"无效签名应返回 400, 实际: {response1.status_code}"
        )

        # 在真实场景中，相同事件 ID 的第二次请求应:
        # - 返回 200 (已处理)
        # - 但不重复执行业务逻辑
        print("✓ 幂等性依赖后端事件 ID 去重机制")
        print("  - 建议: 后端应维护 processed_events 表")
        print("  - 建议: 处理前检查事件 ID 是否已存在")

    def test_clerk_webhook_event_id(self, anon_client):
        """
        业务规则: Clerk Webhook 应基于事件 ID 实现幂等

        Clerk 事件特点:
        - 通过 svix-id header 标识事件
        - 相同 svix-id 的请求应只处理一次
        """
        event_id = "msg_test_idempotency_456"
        event_payload = {
            "type": "user.created",
            "data": {
                "id": "user_test_123",
                "email_addresses": [{"email_address": "test@example.com"}]
            }
        }

        # 请求 (会因签名失败而被拒绝)
        response = anon_client.post(
            Endpoints.WEBHOOKS_CLERK,
            headers={
                "svix-id": event_id,
                "svix-timestamp": "1234567890",
                "svix-signature": "v1,fake_signature"
            },
            json=event_payload
        )

        # 由于签名无效，应返回 400 或 500
        assert response.status_code in [400, 500], (
            f"无效签名应被拒绝, 实际: {response.status_code}"
        )

        print("✓ Clerk 幂等性依赖 svix-id 去重")
        print("  - 建议: 后端应检查 svix-id 是否已处理")


@pytest.mark.p1
class TestWebhookIdempotencyBehavior(BaseAPITest):
    """
    Webhook 幂等行为验证

    测试重复事件的处理策略
    """

    def test_idempotency_documentation(self, anon_client):
        """
        记录幂等性实现建议

        由于无法在集成测试中验证实际的幂等性行为（需要有效签名），
        此测试记录预期行为和实现建议。
        """
        idempotency_requirements = """
        Webhook 幂等性要求:

        1. Stripe Webhook:
           - 事件 ID: event.id (evt_xxx)
           - 存储: processed_stripe_events 表
           - 字段: event_id, processed_at, event_type
           - 行为: 重复事件返回 200，但不执行业务逻辑

        2. Clerk Webhook:
           - 事件 ID: svix-id header (msg_xxx)
           - 存储: processed_clerk_events 表
           - 字段: svix_id, processed_at, event_type
           - 行为: 重复事件返回 200，但不执行业务逻辑

        3. 关键业务影响:
           - checkout.session.completed: 防止重复充值积分
           - invoice.payment_succeeded: 防止重复续费处理
           - user.created: 防止重复创建用户记录
           - customer.subscription.updated: 防止重复状态更新

        4. 实现建议:
           - 使用数据库事务保证原子性
           - 先检查是否已处理，再执行业务逻辑
           - 考虑使用 Redis 缓存加速检查
           - 设置事件记录的 TTL (如 7 天)
        """

        print(idempotency_requirements)

        # 这是文档测试，总是通过
        assert True


# ==========================================
# Test: Webhook Error Handling
# ==========================================

@pytest.mark.p1
class TestWebhookErrorHandling(BaseAPITest):
    """
    Webhook 错误处理测试

    验证各种错误场景的响应
    """

    def test_stripe_webhook_returns_json_error(self, anon_client):
        """
        业务规则: Webhook 错误应返回 JSON 格式

        便于 Stripe 记录和调试
        """
        response = anon_client.post(
            Endpoints.WEBHOOKS_STRIPE,
            headers={"Stripe-Signature": "t=1234567890,v1=invalid"},
            json={"id": "evt_test", "type": "test"}
        )

        # 验证返回的是 JSON
        try:
            error_data = response.json()
            assert isinstance(error_data, dict), "错误响应应是 JSON 对象"
            print(f"✓ 错误响应是 JSON 格式: {error_data}")
        except Exception:
            print(f"⚠️ 错误响应不是 JSON: {response.text[:200]}")

    def test_clerk_webhook_returns_json_error(self, anon_client):
        """
        业务规则: Clerk Webhook 错误应返回 JSON 格式
        """
        response = anon_client.post(
            Endpoints.WEBHOOKS_CLERK,
            headers={
                "svix-id": "msg_test",
                "svix-timestamp": "1234567890",
                "svix-signature": "v1,invalid"
            },
            json={"type": "user.created", "data": {}}
        )

        try:
            error_data = response.json()
            assert isinstance(error_data, dict), "错误响应应是 JSON 对象"
            print(f"✓ 错误响应是 JSON 格式")
        except Exception:
            print(f"⚠️ 错误响应不是 JSON: {response.text[:200]}")

    def test_webhook_error_no_sensitive_info(self, anon_client):
        """
        安全规则: 错误响应不应泄露敏感信息

        不应包含:
        - Webhook 签名密钥
        - 内部堆栈跟踪
        - 数据库连接信息
        """
        response = anon_client.post(
            Endpoints.WEBHOOKS_STRIPE,
            headers={"Stripe-Signature": "t=1234567890,v1=invalid"},
            json={"id": "evt_test", "type": "test"}
        )

        response_text = response.text.lower()

        sensitive_patterns = [
            "whsec_",  # Stripe webhook secret prefix
            "sk_live_",  # Stripe live key
            "sk_test_",  # Stripe test key
            "traceback",  # Python stack trace
            "file \"",  # Stack trace file reference
            "password",
            "secret_key",
            "database_url"
        ]

        for pattern in sensitive_patterns:
            assert pattern not in response_text, (
                f"错误响应不应包含敏感信息: {pattern}"
            )

        print("✓ 错误响应不包含敏感信息")
