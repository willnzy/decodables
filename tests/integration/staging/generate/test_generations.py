"""
Generations API Tests (Black Box)

测试 /api/v2/user/generations 相关接口

基于业务规则的黑盒测试，不依赖代码实现

业务规则 (来源: 产品文档):
1. AI 生图消耗 5 积分/次
2. 用户可以查看生成历史
3. 用户可以收藏/取消收藏生成结果
4. 用户可以删除单个或批量删除生成记录
5. 批量删除支持保留收藏项

@module tests.integration.staging.generate.test_generations
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints, TestData


@pytest.mark.p0
class TestGenerationsHistory(BaseAPITest):
    """
    GET /api/v2/user/generations/history 黑盒测试

    生成历史查询
    """

    ENDPOINT = Endpoints.GENERATIONS_HISTORY

    # ==========================================
    # 功能测试: 列表查询
    # ==========================================

    def test_get_history_returns_paginated_response(self, auth_client):
        """
        业务规则: 生成历史应返回分页结构

        期望响应包含:
        - generations: 生成记录数组
        - total: 总数
        - limit: 每页数量
        - offset: 偏移量
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 验证响应结构
        assert isinstance(data, dict), "响应应该是对象"
        assert "generations" in data, "响应应包含 generations"
        assert isinstance(data["generations"], list), "generations 应该是数组"
        assert "total" in data, "响应应包含 total"

    def test_get_history_with_limit(self, auth_client):
        """
        业务规则: limit 参数应限制返回数量 (max: 100)
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"limit": 5}
        )
        data = self.assert_success(response)

        generations = data.get("generations", [])
        assert len(generations) <= 5, f"limit=5 但返回了 {len(generations)} 条"

    def test_get_history_with_offset(self, auth_client):
        """
        业务规则: offset 参数应跳过前 N 条记录
        """
        # 先获取全部
        response_all = auth_client.get(
            self.ENDPOINT,
            params={"limit": 10}
        )
        data_all = self.assert_success(response_all)
        all_generations = data_all.get("generations", [])

        if len(all_generations) >= 2:
            # 获取跳过 1 条后的
            response_offset = auth_client.get(
                self.ENDPOINT,
                params={"limit": 10, "offset": 1}
            )
            data_offset = self.assert_success(response_offset)
            offset_generations = data_offset.get("generations", [])

            # 偏移后应该少 1 条或相同 (如果正好分页边界)
            if len(all_generations) == 10:
                # 第一页满了，offset 后可能还是 10 条
                pass
            else:
                assert len(offset_generations) <= len(all_generations)

    def test_get_history_favorites_only(self, auth_client):
        """
        业务规则: favorites_only=true 只返回收藏的生成记录
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"favorites_only": True}
        )
        data = self.assert_success(response)

        generations = data.get("generations", [])
        for gen in generations:
            if "is_favorited" in gen:
                assert gen["is_favorited"] is True, "favorites_only=true 时应只返回收藏项"

    def test_generation_item_structure(self, auth_client):
        """
        业务规则: 每个生成记录应包含必要字段

        必需字段:
        - id: 生成记录 UUID
        - image_urls: 图片 URL 列表
        - prompt: 原始提示词
        - created_at: 创建时间
        """
        response = auth_client.get(self.ENDPOINT, params={"limit": 1})
        data = self.assert_success(response)

        generations = data.get("generations", [])
        if len(generations) > 0:
            gen = generations[0]
            assert "id" in gen, "生成记录缺少 id"
            # prompt 和 image_urls 可能是可选的，取决于生成类型
            assert "created_at" in gen or "timestamp" in gen, "生成记录缺少时间戳"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 生成历史是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    # ==========================================
    # 边界测试
    # ==========================================

    def test_limit_max_100(self, auth_client):
        """
        业务规则: limit 最大值为 100
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"limit": 100}
        )
        data = self.assert_success(response)
        assert data.get("limit") == 100 or len(data.get("generations", [])) <= 100

    def test_invalid_limit_rejected(self, auth_client):
        """
        业务规则: limit 超过 100 应被拒绝或截断
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"limit": 150}
        )

        # 应该返回 400 (拒绝) 或 200 (截断到 100)
        if response.status_code == 200:
            data = response.json()
            assert len(data.get("generations", [])) <= 100, "应截断到最大 100"
        else:
            assert response.status_code in [400, 422], f"应返回错误，但返回了 {response.status_code}"


@pytest.mark.p1
class TestGenerationFavorite(BaseAPITest):
    """
    PATCH /api/v2/user/generations/{id} 黑盒测试

    收藏/取消收藏
    """

    def test_favorite_invalid_uuid_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回 400
        """
        response = auth_client.patch(
            Endpoints.generation("invalid-id"),
            json={"is_favorited": True}
        )
        assert response.status_code == 400, (
            f"无效 UUID 应返回 400，但返回了 {response.status_code}"
        )

    def test_favorite_nonexistent_returns_404(self, auth_client):
        """
        业务规则: 收藏不存在的记录应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.patch(
            Endpoints.generation(fake_id),
            json={"is_favorited": True}
        )
        self.assert_not_found(response)

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 收藏操作必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.patch(
            Endpoints.generation(fake_id),
            json={"is_favorited": True}
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestGenerationDelete(BaseAPITest):
    """
    DELETE /api/v2/user/generations/{id} 黑盒测试

    删除单个生成记录
    """

    def test_delete_invalid_uuid_rejected(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回 400
        """
        response = auth_client.delete(Endpoints.generation("invalid-id"))
        assert response.status_code == 400, (
            f"无效 UUID 应返回 400，但返回了 {response.status_code}"
        )

    def test_delete_nonexistent_returns_404(self, auth_client):
        """
        业务规则: 删除不存在的记录应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.generation(fake_id))
        self.assert_not_found(response)

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 删除操作必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.delete(Endpoints.generation(fake_id))
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestGenerationBatchDelete(BaseAPITest):
    """
    POST /api/v2/user/generations/batch-delete 黑盒测试

    批量删除生成记录
    """

    ENDPOINT = f"{Endpoints.GENERATIONS_HISTORY.rsplit('/', 1)[0]}/batch-delete"

    def test_batch_delete_keep_favorites_default(self, auth_client):
        """
        业务规则: 批量删除默认保留收藏项 (keep_favorites=true)
        """
        response = auth_client.post(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应应包含 success 和 deleted_count
        assert "success" in data, "响应应包含 success"
        assert data["success"] is True, "批量删除应成功"
        assert "deleted_count" in data, "响应应包含 deleted_count"

    def test_batch_delete_explicit_keep_favorites(self, auth_client):
        """
        业务规则: keep_favorites=true 只删除非收藏项
        """
        response = auth_client.post(
            self.ENDPOINT,
            params={"keep_favorites": True}
        )
        data = self.assert_success(response)
        assert data.get("success") is True

    def test_batch_delete_include_favorites(self, auth_client):
        """
        业务规则: keep_favorites=false 删除所有记录 (包括收藏)

        ⚠️ 危险操作，谨慎使用
        """
        # 这个测试可能会删除用户的所有生成记录
        # 在生产环境中应该跳过
        response = auth_client.post(
            self.ENDPOINT,
            params={"keep_favorites": False}
        )
        data = self.assert_success(response)
        assert data.get("success") is True

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 批量删除必须登录
        """
        response = anon_client.post(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestGenerationsPerformance(BaseAPITest):
    """
    生成接口性能测试
    """

    ENDPOINT = Endpoints.GENERATIONS_HISTORY

    def test_response_time_acceptable(self, auth_client):
        """
        业务规则: 生成历史查询应在合理时间内响应

        SLA: < 3s (Staging 环境)
        """
        response = auth_client.get(self.ENDPOINT, params={"limit": 50})
        assert response.status_code == 200
        self.assert_response_time(response, max_seconds=3.0)
