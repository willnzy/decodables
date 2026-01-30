"""
Support API Tests (Black Box)

测试 /api/v2/user/support 相关接口

业务规则:
1. 用户可以创建支持工单
2. 用户可以使用 AI 客服聊天
3. 用户可以提交联系表单
4. 用户可以提交反馈

@module tests.integration.staging.support.test_support
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestSupportTicket(BaseAPITest):
    """
    POST /api/v2/user/support/ticket 黑盒测试

    创建支持工单
    """

    ENDPOINT = Endpoints.SUPPORT_TICKET

    def test_create_ticket_requires_message(self, auth_client):
        """
        业务规则: 创建工单需要提供消息内容
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 message
        )
        assert response.status_code in [400, 422]

    def test_create_ticket_with_valid_data(self, auth_client):
        """
        业务规则: 提供有效数据可以创建工单
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "This is a test support ticket. Please ignore."
            }
        )
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_create_ticket_with_email(self, auth_client):
        """
        业务规则: 可以指定联系邮箱
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "Test ticket with email",
                "email": "test@example.com"
            }
        )
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_invalid_email_format_rejected(self, auth_client):
        """
        业务规则: 无效的邮箱格式应被拒绝
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "Test ticket",
                "email": "invalid-email-format"
            }
        )
        assert response.status_code in [400, 422]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 创建工单必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"message": "Test"}
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestSupportChat(BaseAPITest):
    """
    POST /api/v2/user/support/chat 黑盒测试

    AI 客服聊天
    """

    ENDPOINT = Endpoints.SUPPORT_CHAT

    def test_chat_requires_message(self, auth_client):
        """
        业务规则: 聊天需要提供消息内容
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 message
        )
        assert response.status_code in [400, 422]

    def test_chat_with_valid_message(self, auth_client):
        """
        业务规则: 提供有效消息可以获得 AI 响应
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "Hello, I need help with my project."
            }
        )
        data = self.assert_success(response)
        assert "status" in data
        assert "message" in data  # AI 响应

    def test_chat_with_images(self, auth_client):
        """
        业务规则: 可以附带图片进行聊天
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "What is this error?",
                "images": ["https://example.com/screenshot.png"]
            }
        )
        # 可能成功或图片验证失败
        assert response.status_code in [200, 400]

    def test_chat_images_limit(self, auth_client):
        """
        业务规则: 图片数量限制为 4 张
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "Test with too many images",
                "images": [
                    "https://example.com/1.png",
                    "https://example.com/2.png",
                    "https://example.com/3.png",
                    "https://example.com/4.png",
                    "https://example.com/5.png",  # 超过 4 张
                ]
            }
        )
        assert response.status_code in [400, 422]

    def test_conversation_history_limit(self, auth_client):
        """
        业务规则: 对话历史限制为 20 条
        """
        # 创建 21 条历史
        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(21)
        ]
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "New message",
                "conversation_history": history
            }
        )
        assert response.status_code in [400, 422]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: AI 聊天必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"message": "Test"}
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestContactForm(BaseAPITest):
    """
    POST /api/v2/user/support/contact 黑盒测试

    联系表单
    """

    ENDPOINT = Endpoints.SUPPORT_CONTACT

    def test_contact_requires_fields(self, auth_client):
        """
        业务规则: 联系表单需要必填字段

        必填: name, email, message
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少必填字段
        )
        assert response.status_code in [400, 422]

    def test_contact_with_valid_data(self, auth_client):
        """
        业务规则: 提供有效数据可以提交联系表单
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test User",
                "email": "test@example.com",
                "message": "This is a test contact message."
            }
        )
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_contact_with_subject(self, auth_client):
        """
        业务规则: 可以指定主题
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test User",
                "email": "test@example.com",
                "message": "Test message",
                "subject": "Partnership Inquiry"
            }
        )
        data = self.assert_success(response)

    def test_invalid_email_rejected(self, auth_client):
        """
        业务规则: 无效的邮箱格式应被拒绝
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "name": "Test User",
                "email": "invalid-email",
                "message": "Test message"
            }
        )
        assert response.status_code in [400, 422]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 联系表单必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "name": "Test",
                "email": "test@example.com",
                "message": "Test"
            }
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestFeedback(BaseAPITest):
    """
    POST /api/v2/user/support/feedback 黑盒测试

    用户反馈
    """

    ENDPOINT = Endpoints.SUPPORT_FEEDBACK

    def test_feedback_requires_message(self, auth_client):
        """
        业务规则: 反馈需要提供消息内容
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 message
        )
        assert response.status_code in [400, 422]

    def test_feedback_with_valid_data(self, auth_client):
        """
        业务规则: 提供有效数据可以提交反馈
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "Great product! I love it."
            }
        )
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_feedback_with_images(self, auth_client):
        """
        业务规则: 可以附带截图反馈
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "Found a bug",
                "images": ["https://example.com/screenshot.png"]
            }
        )
        # 可能成功或图片验证失败
        assert response.status_code in [200, 400]

    def test_feedback_images_limit(self, auth_client):
        """
        业务规则: 反馈图片限制为 5 张
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "message": "Test with too many images",
                "images": [
                    "https://example.com/1.png",
                    "https://example.com/2.png",
                    "https://example.com/3.png",
                    "https://example.com/4.png",
                    "https://example.com/5.png",
                    "https://example.com/6.png",  # 超过 5 张
                ]
            }
        )
        assert response.status_code in [400, 422]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 提交反馈必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"message": "Test"}
        )
        self.assert_unauthorized(response)
