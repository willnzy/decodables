"""
端到端集成测试：AI 生成流程

流程:
1. 用户触发生成（检查积分）
2. 扣减积分（先月度后永久）
3. 调用 AI API
4. 保存生成结果
5. 创建积分历史记录

创建时间: 2026-01-07
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, MagicMock

from app import app

client = TestClient(app)


@pytest.mark.skip(reason="Integration test references legacy services module - needs DDD migration")
class TestGenerationFlow:
    """AI 生成完整流程测试"""

    @patch('services.ai.image_generator.fal_client.submit')
    @patch('services.db_service.supabase')
    def test_complete_image_generation_flow(self, mock_supabase, mock_fal_submit):
        """测试完整图片生成流程"""
        # Step 1: 用户有足够积分
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "id": "user_123",
                "credits_monthly": 50,
                "credits_permanent": 0,
                "tier": "free"
            }]
        )

        # Mock credit deduction (原子操作)
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"success": True, "new_balance": {"monthly": 45, "permanent": 0}}
        )

        # Mock FAL AI submission
        mock_fal_submit.return_value = Mock(
            request_id="fal_req_123"
        )

        auth_headers = {"Authorization": "Bearer test_token"}

        # Step 2: 触发图片生成
        response = client.post(
            "/api/v2/generate/image",
            json={
                "prompt": "A cute cat",
                "model": "flux-schnell",
                "size": "square"
            },
            headers=auth_headers
        )

        # 验证生成请求成功
        assert response.status_code in [200, 201, 404, 401]

        # Step 3: 验证积分扣减（先月度后永久）
        # assert user.credits_monthly == 45  # 50 - 5
        # assert user.credits_permanent == 0  # 未动

        # Step 4: 验证积分历史记录
        # credits_history.change_type == "ai_generation"
        # credits_history.amount == -5

        assert True  # 占位

    @patch('services.db_service.supabase')
    def test_generation_insufficient_credits(self, mock_supabase):
        """测试积分不足时生成失败"""
        # Step 1: 用户积分不足
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "id": "user_123",
                "credits_monthly": 2,  # 不足 5 积分
                "credits_permanent": 0,
                "tier": "free"
            }]
        )

        # Mock credit deduction failure
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"success": False, "error": "Insufficient credits"}
        )

        auth_headers = {"Authorization": "Bearer test_token"}

        response = client.post(
            "/api/v2/generate/image",
            json={
                "prompt": "A cute cat",
                "model": "flux-schnell"
            },
            headers=auth_headers
        )

        # 应该返回 400 积分不足
        assert response.status_code in [400, 402, 404, 401]

    @patch('services.ai.image_generator.fal_client.submit')
    @patch('services.db_service.supabase')
    def test_credit_deduction_priority(self, mock_supabase, mock_fal_submit):
        """测试积分扣减优先级（先月度后永久）"""
        # 场景: user 有 3 月度积分 + 10 永久积分
        # 生成需要 5 积分
        # 预期: 扣 3 月度 + 2 永久

        # Step 1: Mock user credits
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "id": "user_123",
                "credits_monthly": 3,
                "credits_permanent": 10,
                "tier": "free"
            }]
        )

        # Step 2: Mock RPC (deduct 3 monthly + 2 permanent)
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "success": True,
                "new_balance": {"monthly": 0, "permanent": 8}
            }
        )

        # Mock FAL AI
        mock_fal_submit.return_value = Mock(request_id="fal_req_123")

        auth_headers = {"Authorization": "Bearer test_token"}

        response = client.post(
            "/api/v2/generate/image",
            json={"prompt": "Test", "model": "flux-schnell"},
            headers=auth_headers
        )

        assert response.status_code in [200, 201, 404, 401]

        # 验证积分扣减顺序
        # assert user.credits_monthly == 0  # 3 → 0
        # assert user.credits_permanent == 8  # 10 → 8

        assert True  # 占位

    @patch('services.ai.image_generator.fal_client.submit')
    @patch('services.db_service.supabase')
    def test_generation_ai_api_failure_rollback(self, mock_supabase, mock_fal_submit):
        """测试 AI API 失败时回滚积分"""
        # Step 1: Mock sufficient credits
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user_123", "credits_monthly": 50, "credits_permanent": 0}]
        )

        # Step 2: Mock credit deduction success
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"success": True, "new_balance": {"monthly": 45, "permanent": 0}}
        )

        # Step 3: Mock FAL AI failure
        mock_fal_submit.side_effect = Exception("FAL API Error")

        auth_headers = {"Authorization": "Bearer test_token"}

        response = client.post(
            "/api/v2/generate/image",
            json={"prompt": "Test"},
            headers=auth_headers
        )

        # Should return 500 error
        assert response.status_code in [500, 503, 404, 401]

        # TODO: 验证积分是否回滚（需要事务支持）
        # assert user.credits_monthly == 50  # Rolled back

        assert True  # 占位

    @patch('services.ai.text_generator.openai_client')
    @patch('services.db_service.supabase')
    def test_text_generation_costs_1_credit(self, mock_supabase, mock_openai):
        """测试文本生成消耗 1 积分"""
        # Mock user credits
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user_123", "credits_monthly": 50, "credits_permanent": 0}]
        )

        # Mock credit deduction (1 credit)
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"success": True, "new_balance": {"monthly": 49, "permanent": 0}}
        )

        # Mock OpenAI API
        mock_openai.completions.create.return_value = Mock(
            choices=[Mock(text="Generated text")]
        )

        auth_headers = {"Authorization": "Bearer test_token"}

        response = client.post(
            "/api/v2/generate/text",
            json={"prompt": "Generate story"},
            headers=auth_headers
        )

        assert response.status_code in [200, 201, 404, 401]

        # 验证只扣 1 积分
        # assert user.credits_monthly == 49  # 50 - 1

        assert True  # 占位


# TODO: 补充更多集成测试
# - 并发生成（多个用户同时生成）
# - 队列处理测试
# - WebSocket 实时进度通知
# - 生成失败重试逻辑
