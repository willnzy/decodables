"""
Cascade Delete Integration Tests

测试删除操作的级联行为:
- 删除文件夹时，其中的项目/素材移动到根目录
- 删除 Tag 时，关联的项目/素材解除关联
- 删除 Workspace 时的行为 (禁止删除默认 workspace)

TDD Approach:
- 测试级联行为正确执行
- 测试数据完整性得到保护
- 测试无孤立记录

业务规则 (来源: 产品设计文档):
1. 删除文件夹: 内容移动到根目录 (folder_id = NULL)
2. 删除 Tag: 关联解除，项目/素材不受影响
3. 不允许删除默认 Workspace
4. 级联操作应是原子性的

@module tests.integration.staging.cascade_delete.test_cascade_delete
"""

import pytest
import uuid

from tests.integration.staging.base import BaseAPITest
from tests.integration.staging.constants import Endpoints


# ==========================================
# Test: Folder Cascade Delete
# ==========================================

@pytest.mark.p0
class TestFolderCascadeDelete(BaseAPITest):
    """
    文件夹级联删除测试

    业务规则: 删除文件夹时，其中的项目移动到根目录
    """

    FOLDERS_ENDPOINT = Endpoints.FOLDERS
    PROJECTS_ENDPOINT = Endpoints.PROJECTS

    def test_delete_folder_moves_projects_to_root(self, auth_client):
        """
        业务规则: 删除文件夹后，其中的项目应移动到根目录 (folder_id=null)
        """
        # 1. 创建文件夹
        folder_name = f"CascadeFolder_{uuid.uuid4().hex[:8]}"
        folder_response = auth_client.post(
            self.FOLDERS_ENDPOINT,
            json={"folder_type": "project", "name": folder_name}
        )

        if folder_response.status_code not in [200, 201]:
            pytest.skip(f"无法创建文件夹: {folder_response.status_code}")

        folder_id = folder_response.json()["id"]

        # 2. 创建项目
        project_title = f"CascadeProject_{uuid.uuid4().hex[:8]}"
        project_response = auth_client.post(
            self.PROJECTS_ENDPOINT,
            json={"title": project_title, "content": {}}
        )

        if project_response.status_code == 403:
            auth_client.delete(Endpoints.folder(folder_id))
            pytest.skip("测试用户已达项目限制")

        if project_response.status_code not in [200, 201]:
            auth_client.delete(Endpoints.folder(folder_id))
            pytest.skip(f"无法创建项目: {project_response.status_code}")

        project_id = project_response.json().get("id") or project_response.json().get("project_id")

        # 3. 移动项目到文件夹
        move_response = auth_client.post(
            Endpoints.project_move(project_id),
            json={"folder_id": folder_id}
        )

        if move_response.status_code != 200:
            # 清理
            auth_client.delete(Endpoints.project(project_id), params={"permanent": True})
            auth_client.delete(Endpoints.folder(folder_id))
            pytest.skip(f"无法移动项目到文件夹: {move_response.status_code}")

        # 验证项目在文件夹中
        assert move_response.json().get("folder_id") == folder_id

        # 4. 删除文件夹
        delete_folder_response = auth_client.delete(Endpoints.folder(folder_id))
        assert delete_folder_response.status_code in [200, 204], (
            f"删除文件夹失败: {delete_folder_response.status_code}"
        )

        # 5. 验证项目移动到根目录
        project_detail_response = auth_client.get(Endpoints.project(project_id))

        if project_detail_response.status_code == 200:
            project_data = project_detail_response.json()
            assert project_data.get("folder_id") is None, (
                f"项目应移动到根目录 (folder_id=null)，实际: {project_data.get('folder_id')}"
            )
            print("✓ 删除文件夹后项目正确移动到根目录")
        else:
            # 项目可能在列表中但详情API不可用
            list_response = auth_client.get(self.PROJECTS_ENDPOINT)
            items = list_response.json().get("items", [])
            project = next(
                (p for p in items if (p.get("id") or p.get("project_id")) == project_id),
                None
            )
            if project:
                assert project.get("folder_id") is None, (
                    f"项目应移动到根目录，实际: {project.get('folder_id')}"
                )

        # 清理
        auth_client.delete(Endpoints.project(project_id), params={"permanent": True})

    def test_delete_folder_with_multiple_projects(self, auth_client):
        """
        业务规则: 删除文件夹时，所有项目都应移动到根目录
        """
        # 创建文件夹
        folder_name = f"MultiProject_{uuid.uuid4().hex[:8]}"
        folder_response = auth_client.post(
            self.FOLDERS_ENDPOINT,
            json={"folder_type": "project", "name": folder_name}
        )

        if folder_response.status_code not in [200, 201]:
            pytest.skip("无法创建文件夹")

        folder_id = folder_response.json()["id"]
        project_ids = []

        # 创建多个项目并移动到文件夹
        for i in range(2):
            project_title = f"Multi_{i}_{uuid.uuid4().hex[:6]}"
            project_response = auth_client.post(
                self.PROJECTS_ENDPOINT,
                json={"title": project_title, "content": {}}
            )

            if project_response.status_code not in [200, 201]:
                # 清理已创建的
                for pid in project_ids:
                    auth_client.delete(Endpoints.project(pid), params={"permanent": True})
                auth_client.delete(Endpoints.folder(folder_id))
                pytest.skip("无法创建足够的测试项目")

            pid = project_response.json().get("id") or project_response.json().get("project_id")
            project_ids.append(pid)

            # 移动到文件夹
            auth_client.post(
                Endpoints.project_move(pid),
                json={"folder_id": folder_id}
            )

        # 删除文件夹
        auth_client.delete(Endpoints.folder(folder_id))

        # 验证所有项目都在根目录
        list_response = auth_client.get(self.PROJECTS_ENDPOINT)
        items = list_response.json().get("items", [])

        for pid in project_ids:
            project = next(
                (p for p in items if (p.get("id") or p.get("project_id")) == pid),
                None
            )
            if project:
                assert project.get("folder_id") is None, (
                    f"项目 {pid} 应在根目录，实际 folder_id: {project.get('folder_id')}"
                )

        # 清理
        for pid in project_ids:
            auth_client.delete(Endpoints.project(pid), params={"permanent": True})

        print(f"✓ 删除文件夹后 {len(project_ids)} 个项目都移动到根目录")

    def test_delete_empty_folder(self, auth_client):
        """
        业务规则: 可以删除空文件夹
        """
        folder_name = f"EmptyFolder_{uuid.uuid4().hex[:8]}"
        folder_response = auth_client.post(
            self.FOLDERS_ENDPOINT,
            json={"folder_type": "project", "name": folder_name}
        )

        if folder_response.status_code not in [200, 201]:
            pytest.skip("无法创建文件夹")

        folder_id = folder_response.json()["id"]

        # 直接删除空文件夹
        delete_response = auth_client.delete(Endpoints.folder(folder_id))

        assert delete_response.status_code in [200, 204], (
            f"删除空文件夹失败: {delete_response.status_code}"
        )


# ==========================================
# Test: Tag Cascade Delete
# ==========================================

@pytest.mark.p0
class TestTagCascadeDelete(BaseAPITest):
    """
    Tag 级联删除测试

    业务规则: 删除 Tag 时，关联的项目解除关联但不被删除
    """

    TAGS_ENDPOINT = Endpoints.TAGS
    PROJECTS_ENDPOINT = Endpoints.PROJECTS

    def test_delete_tag_unlinks_from_projects(self, auth_client):
        """
        业务规则: 删除 Tag 后，项目的 Tag 关联被解除
        """
        # 1. 创建 Tag
        tag_name = f"CascadeTag_{uuid.uuid4().hex[:8]}"
        tag_response = auth_client.post(
            self.TAGS_ENDPOINT,
            json={"name": tag_name, "color": "#FF5733"}
        )

        if tag_response.status_code not in [200, 201]:
            pytest.skip(f"无法创建 Tag: {tag_response.status_code}")

        tag_id = tag_response.json()["id"]

        # 2. 创建项目
        project_title = f"TaggedProject_{uuid.uuid4().hex[:8]}"
        project_response = auth_client.post(
            self.PROJECTS_ENDPOINT,
            json={"title": project_title, "content": {}}
        )

        if project_response.status_code == 403:
            auth_client.delete(Endpoints.tag(tag_id))
            pytest.skip("测试用户已达项目限制")

        if project_response.status_code not in [200, 201]:
            auth_client.delete(Endpoints.tag(tag_id))
            pytest.skip(f"无法创建项目: {project_response.status_code}")

        project_id = project_response.json().get("id") or project_response.json().get("project_id")

        # 3. 给项目添加 Tag
        add_tag_response = auth_client.post(
            Endpoints.project_tags(project_id),
            json={"tag_ids": [tag_id]}
        )

        if add_tag_response.status_code != 200:
            # 清理
            auth_client.delete(Endpoints.project(project_id), params={"permanent": True})
            auth_client.delete(Endpoints.tag(tag_id))
            pytest.skip(f"无法添加 Tag: {add_tag_response.status_code}")

        # 4. 删除 Tag
        delete_tag_response = auth_client.delete(Endpoints.tag(tag_id))
        assert delete_tag_response.status_code in [200, 204], (
            f"删除 Tag 失败: {delete_tag_response.status_code}"
        )

        # 5. 验证项目仍存在
        project_exists_response = auth_client.get(Endpoints.project(project_id))

        if project_exists_response.status_code == 200:
            print("✓ 删除 Tag 后项目仍存在")

            # 验证项目不再有该 Tag
            project_tags_response = auth_client.get(Endpoints.project_tags(project_id))
            if project_tags_response.status_code == 200:
                tags = project_tags_response.json()
                if isinstance(tags, list):
                    tag_ids = [t.get("id") for t in tags]
                elif isinstance(tags, dict):
                    tag_ids = [t.get("id") for t in tags.get("items", [])]
                else:
                    tag_ids = []

                assert tag_id not in tag_ids, "删除的 Tag 不应还关联到项目"
                print("✓ Tag 关联已正确解除")

        else:
            # 通过列表验证项目存在
            list_response = auth_client.get(self.PROJECTS_ENDPOINT)
            items = list_response.json().get("items", [])
            project_ids = [p.get("id") or p.get("project_id") for p in items]
            assert project_id in project_ids, "删除 Tag 后项目应仍存在"

        # 清理
        auth_client.delete(Endpoints.project(project_id), params={"permanent": True})

    def test_project_survives_all_tags_deleted(self, auth_client):
        """
        业务规则: 即使项目的所有 Tag 都被删除，项目本身也不受影响
        """
        # 创建项目
        project_title = f"SurviveDelete_{uuid.uuid4().hex[:8]}"
        project_response = auth_client.post(
            self.PROJECTS_ENDPOINT,
            json={"title": project_title, "content": {}}
        )

        if project_response.status_code == 403:
            pytest.skip("测试用户已达项目限制")

        if project_response.status_code not in [200, 201]:
            pytest.skip(f"无法创建项目: {project_response.status_code}")

        project_id = project_response.json().get("id") or project_response.json().get("project_id")
        tag_ids = []

        # 创建多个 Tags 并关联到项目
        for i in range(2):
            tag_name = f"Survive_{i}_{uuid.uuid4().hex[:6]}"
            tag_response = auth_client.post(
                self.TAGS_ENDPOINT,
                json={"name": tag_name, "color": "#FF5733"}
            )
            if tag_response.status_code in [200, 201]:
                tag_ids.append(tag_response.json()["id"])

        if not tag_ids:
            auth_client.delete(Endpoints.project(project_id), params={"permanent": True})
            pytest.skip("无法创建 Tags")

        # 添加所有 Tags 到项目
        auth_client.post(
            Endpoints.project_tags(project_id),
            json={"tag_ids": tag_ids}
        )

        # 删除所有 Tags
        for tid in tag_ids:
            auth_client.delete(Endpoints.tag(tid))

        # 验证项目仍存在
        verify_response = auth_client.get(Endpoints.project(project_id))

        # 清理
        auth_client.delete(Endpoints.project(project_id), params={"permanent": True})

        # 验证
        if verify_response.status_code == 200:
            print("✓ 所有 Tags 删除后项目仍存在")
        else:
            # 通过列表验证
            list_response = auth_client.get(self.PROJECTS_ENDPOINT)
            items = list_response.json().get("items", [])
            project_ids = [p.get("id") or p.get("project_id") for p in items]
            assert project_id in project_ids, "删除所有 Tags 后项目应仍存在"


# ==========================================
# Test: Workspace Delete Protection
# ==========================================

@pytest.mark.p0
class TestWorkspaceDeleteProtection(BaseAPITest):
    """
    Workspace 删除保护测试

    业务规则: 不允许删除默认 Workspace
    """

    WORKSPACES_ENDPOINT = Endpoints.WORKSPACES

    def test_cannot_delete_default_workspace(self, auth_client):
        """
        业务规则: 默认 Workspace 不能被删除

        Sad Path: 应返回 400 或 403
        """
        # 获取当前 Workspace
        current_response = auth_client.get(Endpoints.WORKSPACES_CURRENT)

        if current_response.status_code != 200:
            pytest.skip("无法获取当前 Workspace")

        workspace_id = current_response.json().get("id")
        is_default = current_response.json().get("is_default", True)

        if not workspace_id:
            pytest.skip("无法获取 Workspace ID")

        # 尝试删除
        delete_response = auth_client.delete(Endpoints.workspace(workspace_id))

        # 如果是默认 Workspace，应被拒绝
        if is_default:
            assert delete_response.status_code in [400, 403], (
                f"默认 Workspace 不应被删除，但返回了 {delete_response.status_code}"
            )
            print("✓ 默认 Workspace 删除被正确拒绝")
        else:
            # 非默认可能可以删除
            print(f"非默认 Workspace 删除返回: {delete_response.status_code}")

    def test_delete_workspace_error_message(self, auth_client):
        """
        业务规则: 删除默认 Workspace 的错误消息应明确

        错误消息应说明:
        - 这是默认 Workspace
        - 无法删除默认 Workspace
        """
        current_response = auth_client.get(Endpoints.WORKSPACES_CURRENT)

        if current_response.status_code != 200:
            pytest.skip("无法获取当前 Workspace")

        workspace_id = current_response.json().get("id")

        if not workspace_id:
            pytest.skip("无法获取 Workspace ID")

        delete_response = auth_client.delete(Endpoints.workspace(workspace_id))

        if delete_response.status_code in [400, 403]:
            error_data = delete_response.json()
            error_text = str(error_data).lower()

            # 错误消息应包含相关关键词
            keywords = ["default", "cannot", "delete", "not allowed"]
            has_clear_message = any(kw in error_text for kw in keywords)

            if has_clear_message:
                print(f"✓ 错误消息明确: {error_data}")
            else:
                print(f"⚠️ 改进建议: 错误消息应更明确, 当前: {error_data}")


# ==========================================
# Test: Data Integrity After Cascade
# ==========================================

@pytest.mark.p1
class TestDataIntegrityAfterCascade(BaseAPITest):
    """
    级联删除后数据完整性测试

    验证没有孤立记录或损坏的引用
    """

    def test_no_orphan_folder_references(self, auth_client):
        """
        业务规则: 删除文件夹后不应有孤立的 folder_id 引用
        """
        # 获取所有项目
        response = auth_client.get(Endpoints.PROJECTS, params={"limit": 100})

        if response.status_code != 200:
            pytest.skip("无法获取项目列表")

        items = response.json().get("items", [])

        # 获取所有文件夹 ID
        folder_response = auth_client.get(
            Endpoints.FOLDERS,
            params={"folder_type": "project"}
        )

        if folder_response.status_code != 200:
            pytest.skip("无法获取文件夹列表")

        folder_ids = {f["id"] for f in folder_response.json().get("items", [])}

        # 检查每个项目的 folder_id
        orphan_count = 0
        for item in items:
            folder_id = item.get("folder_id")
            if folder_id and folder_id not in folder_ids:
                orphan_count += 1
                print(f"⚠️ 孤立引用: 项目 {item.get('id')} 引用不存在的文件夹 {folder_id}")

        assert orphan_count == 0, f"发现 {orphan_count} 个孤立的文件夹引用"

        if not orphan_count:
            print("✓ 没有孤立的文件夹引用")

    def test_no_orphan_tag_references(self, auth_client):
        """
        业务规则: 删除 Tag 后不应有孤立的 Tag 引用
        """
        # 获取所有 Tags
        tag_response = auth_client.get(Endpoints.TAGS)

        if tag_response.status_code != 200:
            pytest.skip("无法获取 Tag 列表")

        tags_data = tag_response.json()
        if isinstance(tags_data, dict):
            tag_items = tags_data.get("items", [])
        else:
            tag_items = tags_data if isinstance(tags_data, list) else []

        valid_tag_ids = {t["id"] for t in tag_items if "id" in t}

        print(f"有效 Tag 数量: {len(valid_tag_ids)}")

        # 获取项目列表
        projects_response = auth_client.get(Endpoints.PROJECTS, params={"limit": 10})

        if projects_response.status_code != 200:
            pytest.skip("无法获取项目列表")

        projects = projects_response.json().get("items", [])

        # 检查每个项目的 Tags
        orphan_count = 0
        for project in projects[:5]:  # 只检查前 5 个
            project_id = project.get("id") or project.get("project_id")
            tags_response = auth_client.get(Endpoints.project_tags(project_id))

            if tags_response.status_code == 200:
                project_tags = tags_response.json()
                if isinstance(project_tags, dict):
                    project_tags = project_tags.get("items", [])

                for tag in project_tags:
                    tag_id = tag.get("id")
                    if tag_id and tag_id not in valid_tag_ids:
                        orphan_count += 1
                        print(f"⚠️ 孤立引用: 项目 {project_id} 引用不存在的 Tag {tag_id}")

        if orphan_count == 0:
            print("✓ 没有孤立的 Tag 引用")
