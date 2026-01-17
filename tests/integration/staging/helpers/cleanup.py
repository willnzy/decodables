"""
Test Data Cleanup Utilities

测试数据清理工具,确保测试隔离

@module tests.integration.staging.helpers.cleanup
"""

import logging
from typing import List, Tuple, Callable, Optional
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)


# ==========================================
# Cleanup Registry
# ==========================================

@dataclass
class CleanupItem:
    """清理项"""
    resource_type: str
    resource_id: str
    cleanup_func: Optional[Callable] = None
    priority: int = 0  # Higher = cleanup first


class CleanupRegistry:
    """
    测试数据清理注册表

    在测试中注册创建的资源,测试结束后自动清理

    Usage:
        def test_create(cleanup_registry, auth_client):
            response = auth_client.post("/projects", json={...})
            project_id = response.json()["id"]

            # 注册清理
            cleanup_registry.register("project", project_id)

            # 测试逻辑...

            # 测试结束后自动调用 cleanup_all()
    """

    def __init__(self, client: Optional[httpx.Client] = None):
        self._items: List[CleanupItem] = []
        self._client = client
        self._cleanup_endpoints = {
            "project": "/api/v2/user/projects/{id}",
            "asset": "/api/v3/user/assets/{id}",
            "listing": "/api/v2/user/marketplace/listings/{id}",
            "template": "/api/v2/user/templates/{id}",
            "notification": "/api/v2/user/profile/notifications/{id}",
        }

    def set_client(self, client: httpx.Client):
        """设置 HTTP 客户端"""
        self._client = client

    def register(
        self,
        resource_type: str,
        resource_id: str,
        cleanup_func: Optional[Callable] = None,
        priority: int = 0,
    ):
        """
        注册需要清理的资源

        Args:
            resource_type: 资源类型 (project, asset, listing, etc.)
            resource_id: 资源 ID
            cleanup_func: 自定义清理函数 (可选)
            priority: 清理优先级 (高优先级先清理)
        """
        item = CleanupItem(
            resource_type=resource_type,
            resource_id=resource_id,
            cleanup_func=cleanup_func,
            priority=priority,
        )
        self._items.append(item)
        logger.debug(f"Registered cleanup: {resource_type} {resource_id}")

    def unregister(self, resource_type: str, resource_id: str):
        """取消注册 (资源已被删除)"""
        self._items = [
            item for item in self._items
            if not (item.resource_type == resource_type and item.resource_id == resource_id)
        ]

    def cleanup_all(self) -> Tuple[int, int]:
        """
        清理所有注册的资源

        Returns:
            (成功数, 失败数)
        """
        # Sort by priority (descending)
        self._items.sort(key=lambda x: x.priority, reverse=True)

        success_count = 0
        failure_count = 0

        for item in self._items:
            try:
                if item.cleanup_func:
                    item.cleanup_func(item.resource_id)
                else:
                    self._default_cleanup(item.resource_type, item.resource_id)
                success_count += 1
                logger.debug(f"Cleaned up: {item.resource_type} {item.resource_id}")
            except Exception as e:
                failure_count += 1
                logger.warning(
                    f"Failed to cleanup {item.resource_type} {item.resource_id}: {e}"
                )

        # Clear the registry
        self._items.clear()

        return success_count, failure_count

    def _default_cleanup(self, resource_type: str, resource_id: str):
        """默认清理方法: 调用 DELETE 接口"""
        if self._client is None:
            logger.warning("No client set, skipping cleanup")
            return

        endpoint_template = self._cleanup_endpoints.get(resource_type)
        if not endpoint_template:
            logger.warning(f"No cleanup endpoint for type: {resource_type}")
            return

        endpoint = endpoint_template.format(id=resource_id)

        try:
            # Try soft delete first
            response = self._client.delete(endpoint, params={"permanent": False})
            if response.status_code not in [200, 204, 404]:
                logger.warning(
                    f"Cleanup request failed: {response.status_code} {response.text[:100]}"
                )
        except Exception as e:
            logger.warning(f"Cleanup request error: {e}")

    def __len__(self) -> int:
        return len(self._items)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all()
        return False


# ==========================================
# Cleanup Fixtures for pytest
# ==========================================

def create_cleanup_fixture(client: httpx.Client):
    """
    创建清理 fixture 的工厂函数

    Usage in conftest.py:
        @pytest.fixture
        def cleanup(auth_client):
            registry = CleanupRegistry(auth_client)
            yield registry
            registry.cleanup_all()
    """
    registry = CleanupRegistry(client)
    return registry


# ==========================================
# Specific Cleanup Helpers
# ==========================================

def cleanup_project(client: httpx.Client, project_id: str) -> bool:
    """清理单个项目"""
    try:
        # Soft delete
        response = client.delete(
            f"/api/v2/user/projects/{project_id}",
            params={"permanent": False}
        )
        if response.status_code == 404:
            return True  # Already deleted

        # Hard delete
        response = client.delete(
            f"/api/v2/user/projects/{project_id}",
            params={"permanent": True}
        )
        return response.status_code in [200, 204, 404]
    except Exception as e:
        logger.error(f"Failed to cleanup project {project_id}: {e}")
        return False


def cleanup_projects_by_prefix(
    client: httpx.Client,
    title_prefix: str,
    max_count: int = 100,
) -> int:
    """清理标题以指定前缀开头的所有项目"""
    cleaned = 0
    try:
        # List projects
        response = client.get(
            "/api/v2/user/projects",
            params={"limit": max_count, "search": title_prefix}
        )
        if response.status_code != 200:
            return 0

        data = response.json()
        items = data.get("items", [])

        for item in items:
            if item.get("title", "").startswith(title_prefix):
                if cleanup_project(client, item["id"]):
                    cleaned += 1

    except Exception as e:
        logger.error(f"Failed to cleanup projects by prefix: {e}")

    return cleaned


def cleanup_test_data(
    client: httpx.Client,
    test_prefix: str = "Test_",
):
    """
    清理所有测试数据

    查找并删除所有以测试前缀命名的资源
    """
    results = {
        "projects": 0,
        "assets": 0,
        "listings": 0,
    }

    # Clean projects
    results["projects"] = cleanup_projects_by_prefix(client, test_prefix)

    # Clean assets (if applicable)
    # results["assets"] = cleanup_assets_by_prefix(client, test_prefix)

    # Clean listings (if applicable)
    # results["listings"] = cleanup_listings_by_prefix(client, test_prefix)

    logger.info(f"Test data cleanup results: {results}")
    return results
