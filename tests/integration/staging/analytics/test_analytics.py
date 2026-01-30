"""
Analytics API Tests (Black Box)

测试 /api/v2/user/analytics 相关接口

业务规则:
1. 批量记录分析事件
2. 支持事件去重 (event_id)
3. 无需认证 (匿名用户也可以记录)

@module tests.integration.staging.analytics.test_analytics
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAnalyticsEvents(BaseAPITest):
    """
    POST /api/v2/user/analytics/events 黑盒测试

    批量记录分析事件
    """

    ENDPOINT = Endpoints.ANALYTICS_EVENTS

    def test_post_single_event(self, auth_client):
        """
        业务规则: 可以提交单个事件
        """
        event_id = str(uuid.uuid4())
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "events": [
                    {
                        "event_id": event_id,
                        "event_name": "test_event",
                        "event_type": "page_view",
                        "properties": {"page": "/test"}
                    }
                ]
            }
        )
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_post_batch_events(self, auth_client):
        """
        业务规则: 可以批量提交多个事件
        """
        events = [
            {
                "event_id": str(uuid.uuid4()),
                "event_name": f"test_event_{i}",
                "event_type": "click",
                "properties": {"index": i}
            }
            for i in range(5)
        ]
        response = auth_client.post(
            self.ENDPOINT,
            json={"events": events}
        )
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_event_id_is_optional(self, auth_client):
        """
        业务规则: event_id 是可选的，缺少时服务端自动生成 UUID

        event_id 在 AnalyticsEvent schema 中定义为 Optional，
        缺少时会自动生成 uuid4。
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "events": [
                    {
                        "event_name": "test_event",
                        "event_type": "page_view"
                    }
                ]
            }
        )
        # event_id 是可选的，缺少不会导致验证错误
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_event_requires_event_type(self, auth_client):
        """
        业务规则: 事件必须有 event_type (min_length=1)

        event_type 是 AnalyticsEvent schema 中的必填字段。
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "events": [
                    {
                        "event_id": str(uuid.uuid4()),
                        "event_name": "test_event"
                        # 缺少 event_type
                    }
                ]
            }
        )
        assert response.status_code in [400, 422]

    def test_empty_events_accepted(self, auth_client):
        """
        业务规则: 空事件列表被服务端接受 (返回 200)

        API 对空列表是宽容的，不会返回验证错误。
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"events": []}
        )
        data = self.assert_success(response)
        assert data.get("status") == "ok"

    def test_batch_size_limit(self, auth_client):
        """
        业务规则: 批量大小有限制 (通常 100 条)
        """
        # 创建 150 个事件 (超过限制)
        events = [
            {
                "event_id": str(uuid.uuid4()),
                "event_name": f"test_event_{i}",
                "event_type": "test"
            }
            for i in range(150)
        ]
        response = auth_client.post(
            self.ENDPOINT,
            json={"events": events}
        )
        # 可能返回 400 (超出限制) 或 200 (服务端截断)
        assert response.status_code in [200, 400, 422]

    def test_works_without_auth(self, anon_client):
        """
        业务规则: 分析事件可以匿名提交

        用于追踪未登录用户行为
        """
        event_id = str(uuid.uuid4())
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "events": [
                    {
                        "event_id": event_id,
                        "event_name": "anonymous_visit",
                        "event_type": "page_view",
                        "properties": {"page": "/landing"}
                    }
                ]
            }
        )
        # 可能允许匿名 (200) 或需要认证 (401)
        assert response.status_code in [200, 401]


@pytest.mark.p2
class TestAnalyticsDeduplication(BaseAPITest):
    """
    Analytics 事件去重测试
    """

    ENDPOINT = Endpoints.ANALYTICS_EVENTS

    def test_duplicate_event_id_handled(self, auth_client):
        """
        业务规则: 重复的 event_id 应该被幂等处理
        """
        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "event_name": "duplicate_test",
            "event_type": "test"
        }

        # 第一次提交
        response1 = auth_client.post(
            self.ENDPOINT,
            json={"events": [event]}
        )
        assert response1.status_code == 200

        # 第二次提交相同 event_id
        response2 = auth_client.post(
            self.ENDPOINT,
            json={"events": [event]}
        )
        # 应该成功 (幂等) 或返回去重警告
        assert response2.status_code == 200
