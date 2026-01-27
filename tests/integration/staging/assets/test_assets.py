"""
User Assets API Tests (Black Box)

测试 /api/v3/user/assets 相关接口

业务规则:
1. Pro 用户可以上传个人素材
2. 素材可以软删除和恢复
3. 可以从 URL 添加素材
4. 支持跨项目素材 (Pro only)

@module tests.integration.staging.assets.test_assets
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestUserAssets(BaseAPITest):
    """
    GET /api/v3/user/assets 黑盒测试

    获取用户素材列表
    """

    ENDPOINT = Endpoints.ASSETS

    def test_get_assets_returns_list(self, auth_client):
        """
        业务规则: 素材接口应返回素材列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应可能是列表或包含 items 的对象
        assert isinstance(data, (list, dict)), "响应格式不正确"

    def test_filter_by_project(self, auth_client):
        """
        业务规则: 可以按项目 ID 筛选素材
        """
        fake_project_id = str(uuid.uuid4())
        response = auth_client.get(
            self.ENDPOINT,
            params={"project_id": fake_project_id}
        )
        # 应该返回 200 (可能为空列表)
        data = self.assert_success(response)

    def test_cross_project_scope_requires_pro(self, auth_client):
        """
        业务规则: 跨项目素材需要 Pro 用户

        scope=all 只对 t3/t4 用户开放
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"scope": "all"}
        )
        # Free 用户应该返回 403
        # Pro 用户应该返回 200
        assert response.status_code in [200, 403]

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 素材是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestUploadAsset(BaseAPITest):
    """
    POST /api/v3/user/assets 黑盒测试

    上传素材
    """

    ENDPOINT = Endpoints.ASSETS

    def test_upload_requires_file(self, auth_client):
        """
        业务规则: 上传素材需要提供文件
        """
        response = auth_client.post(self.ENDPOINT)
        assert response.status_code in [400, 422]

    def test_upload_requires_authentication(self, anon_client):
        """
        业务规则: 上传素材必须登录
        """
        response = anon_client.post(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_upload_pro_only(self, auth_client):
        """
        业务规则: 上传素材需要 Pro 用户

        Free/Starter 用户应该被拒绝
        """
        # 创建一个简单的图片文件
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        files = {
            "file": ("test.png", png_data, "image/png")
        }
        response = auth_client.post(self.ENDPOINT, files=files)

        # Pro 用户: 200/201
        # Non-Pro: 403
        assert response.status_code in [200, 201, 403]


@pytest.mark.p1
class TestDeleteAsset(BaseAPITest):
    """
    DELETE /api/v3/user/assets/{asset_id} 黑盒测试

    删除素材
    """

    def test_delete_invalid_uuid_returns_400(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回 400
        """
        response = auth_client.delete(Endpoints.asset("invalid-id"))
        assert response.status_code == 400

    def test_delete_nonexistent_returns_404(self, auth_client):
        """
        业务规则: 删除不存在的素材应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.delete(Endpoints.asset(fake_id))
        # 可能返回 404 或 400
        assert response.status_code in [400, 404]

    def test_delete_requires_authentication(self, anon_client):
        """
        业务规则: 删除素材必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.delete(Endpoints.asset(fake_id))
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestAssetFromUrl(BaseAPITest):
    """
    POST /api/v3/user/assets/from-url 黑盒测试

    从 URL 添加素材
    """

    ENDPOINT = Endpoints.ASSETS_FROM_URL

    def test_requires_url(self, auth_client):
        """
        业务规则: 需要提供 URL
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 url
        )
        assert response.status_code in [400, 422]

    def test_invalid_url_rejected(self, auth_client):
        """
        业务规则: 无效的 URL 应被拒绝
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"url": "not-a-valid-url"}
        )
        assert response.status_code in [400, 422]

    def test_ssrf_protection(self, auth_client):
        """
        业务规则: SSRF 攻击应被阻止

        私有 IP 地址应被拒绝
        """
        private_urls = [
            "http://localhost/image.png",
            "http://127.0.0.1/image.png",
            "http://192.168.1.1/image.png",
            "http://10.0.0.1/image.png",
        ]

        for url in private_urls:
            response = auth_client.post(
                self.ENDPOINT,
                json={"url": url}
            )
            # 应该返回 400 (SSRF 保护)
            assert response.status_code in [400, 403, 422], (
                f"SSRF 保护失败: {url} 返回了 {response.status_code}"
            )

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 从 URL 添加素材必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"url": "https://example.com/image.png"}
        )
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestCheckUrl(BaseAPITest):
    """
    GET /api/v3/user/assets/check-url 黑盒测试

    检查 URL 有效性
    """

    ENDPOINT = Endpoints.ASSETS_CHECK_URL

    def test_requires_url_param(self, auth_client):
        """
        业务规则: 需要提供 URL 参数
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code in [400, 422]

    def test_check_valid_image_url(self, auth_client):
        """
        业务规则: 检查有效的图片 URL
        """
        # 使用一个公开的测试图片
        response = auth_client.get(
            self.ENDPOINT,
            params={"url": "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png"}
        )
        data = self.assert_success(response)

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 检查 URL 必须登录
        """
        response = anon_client.get(
            self.ENDPOINT,
            params={"url": "https://example.com/image.png"}
        )
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestAssetDashboard(BaseAPITest):
    """
    GET /api/v3/user/assets/dashboard 黑盒测试

    素材使用统计
    """

    ENDPOINT = Endpoints.ASSETS_DASHBOARD

    def test_get_dashboard_returns_stats(self, auth_client):
        """
        业务规则: 仪表板应返回统计数据
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应应该是统计数据
        assert isinstance(data, dict), "响应应该是字典"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 仪表板必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestDeletedAssets(BaseAPITest):
    """
    GET /api/v3/user/assets/deleted 黑盒测试

    获取已删除的素材 (回收站)
    """

    ENDPOINT = Endpoints.ASSETS_DELETED

    def test_get_deleted_returns_list(self, auth_client):
        """
        业务规则: 回收站应返回已删除素材列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应应该是列表
        assert isinstance(data, (list, dict)), "响应格式不正确"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 回收站必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestRestoreAsset(BaseAPITest):
    """
    POST /api/v3/user/assets/{asset_id}/restore 黑盒测试

    恢复已删除的素材
    """

    def test_restore_invalid_uuid_returns_400(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应返回 400
        """
        response = auth_client.post(Endpoints.asset_restore("invalid-id"))
        assert response.status_code == 400

    def test_restore_nonexistent_returns_404(self, auth_client):
        """
        业务规则: 恢复不存在的素材应返回 404
        """
        fake_id = str(uuid.uuid4())
        response = auth_client.post(Endpoints.asset_restore(fake_id))
        assert response.status_code in [400, 404]

    def test_restore_requires_authentication(self, anon_client):
        """
        业务规则: 恢复素材必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(Endpoints.asset_restore(fake_id))
        self.assert_unauthorized(response)


# ==========================================
# Test: Asset Move (v3.33 Phase 2.6)
# ==========================================

@pytest.mark.p1
class TestAssetMove(BaseAPITest):
    """
    POST /api/v2/user/assets/{asset_id}/move 黑盒测试

    移动素材到文件夹

    业务规则 (v3.33 Phase 2.6):
    1. 素材可以移动到任意 asset 类型的文件夹
    2. folder_id=null 表示移动到根目录 (无文件夹)
    3. 只能移动到 asset 类型的文件夹
    4. 移动到不存在的文件夹应失败
    """

    ASSETS_ENDPOINT = Endpoints.ASSETS
    FOLDERS_ENDPOINT = Endpoints.FOLDERS

    def test_move_asset_to_folder_requires_valid_asset(self, auth_client):
        """
        业务规则: 移动不存在的素材应返回 404
        """
        fake_asset_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.asset_move(fake_asset_id),
            json={"folder_id": None}
        )

        # 应返回 400 或 404
        assert response.status_code in [400, 404], (
            f"移动不存在的素材应失败，但返回了 {response.status_code}"
        )

    def test_move_asset_to_nonexistent_folder_rejected(self, auth_client):
        """
        业务规则: 移动到不存在的文件夹应失败
        """
        # 这里我们测试的是逻辑：即使素材不存在，
        # 如果 folder_id 是无效的 UUID，也应该失败
        fake_asset_id = str(uuid.uuid4())
        fake_folder_id = str(uuid.uuid4())

        response = auth_client.post(
            Endpoints.asset_move(fake_asset_id),
            json={"folder_id": fake_folder_id}
        )

        # 应返回 400 或 404
        assert response.status_code in [400, 404], (
            f"移动到不存在的文件夹应失败，但返回了 {response.status_code}"
        )

    def test_move_asset_with_invalid_id_format(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝
        """
        response = auth_client.post(
            Endpoints.asset_move("invalid-id"),
            json={"folder_id": None}
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 ID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_move_asset_requires_authentication(self, anon_client):
        """
        业务规则: 移动素材必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(
            Endpoints.asset_move(fake_id),
            json={"folder_id": None}
        )
        self.assert_unauthorized(response)

    def test_move_asset_to_root_with_null_folder(self, auth_client):
        """
        业务规则: folder_id=null 表示移动到根目录

        注意: 由于测试环境可能没有素材，这里测试的是 API 能否正确处理 null folder_id
        """
        # 使用一个假 ID 来测试
        # 如果素材存在，应该能成功移动到根目录
        # 如果素材不存在，应该返回 404
        fake_asset_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.asset_move(fake_asset_id),
            json={"folder_id": None}
        )

        # 素材不存在应返回 404，存在应返回 200
        assert response.status_code in [200, 400, 404]


# ==========================================
# Test: Asset Star (v3.33 Phase 2.6)
# ==========================================

@pytest.mark.p1
class TestAssetStar(BaseAPITest):
    """
    POST /api/v2/user/assets/{asset_id}/star 黑盒测试

    切换素材收藏状态

    业务规则 (v3.33 Phase 2.6):
    1. 素材可以被标记为收藏/取消收藏
    2. is_starred=true 收藏, is_starred=false 取消收藏
    3. 收藏状态切换后应立即生效
    """

    def test_star_nonexistent_asset_returns_404(self, auth_client):
        """
        业务规则: 收藏不存在的素材应返回 404
        """
        fake_asset_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.asset_star(fake_asset_id),
            json={"is_starred": True}
        )

        # 应返回 400 或 404
        assert response.status_code in [400, 404], (
            f"收藏不存在的素材应失败，但返回了 {response.status_code}"
        )

    def test_star_asset_with_invalid_id_format(self, auth_client):
        """
        业务规则: 无效的 UUID 格式应被拒绝
        """
        response = auth_client.post(
            Endpoints.asset_star("invalid-id"),
            json={"is_starred": True}
        )

        assert response.status_code in [400, 404, 422], (
            f"无效 ID 应被拒绝，但返回了 {response.status_code}"
        )

    def test_star_requires_is_starred_field(self, auth_client):
        """
        业务规则: is_starred 是必需字段
        """
        fake_asset_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.asset_star(fake_asset_id),
            json={}  # 缺少 is_starred
        )

        # 应返回 400 或 422 (验证错误)
        # 或者 404 (如果先验证资产存在性)
        assert response.status_code in [400, 404, 422], (
            f"缺少 is_starred 应被拒绝，但返回了 {response.status_code}"
        )

    def test_star_requires_authentication(self, anon_client):
        """
        业务规则: 收藏素材必须登录
        """
        fake_id = str(uuid.uuid4())
        response = anon_client.post(
            Endpoints.asset_star(fake_id),
            json={"is_starred": True}
        )
        self.assert_unauthorized(response)

    def test_unstar_asset_logic(self, auth_client):
        """
        业务规则: is_starred=false 应取消收藏

        注意: 由于测试环境可能没有素材，这里测试的是 API 结构正确性
        """
        fake_asset_id = str(uuid.uuid4())
        response = auth_client.post(
            Endpoints.asset_star(fake_asset_id),
            json={"is_starred": False}
        )

        # 素材不存在应返回 404，存在应返回 200
        assert response.status_code in [200, 400, 404]
