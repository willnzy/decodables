# 后端问题修复实施计划 (Implementation Plan for Backend Fixes)

**日期**: 2026-01-11
**计划人**: Claude Sonnet 4.5
**参考文档**:
- Backend-Readiness-Verification-2026-01-11.md
- Solution-Design-Backend-Issues-2026-01-11.md

---

## 计划概览

### 目标

修复后端验证中发现的所有问题，确保后端100%就绪，为前端开发扫清障碍。

### 范围

| 任务 | 优先级 | 估算 | 开始日期 | 完成日期 |
|-----|-------|------|---------|---------|
| **Task 1**: 创建 system_resources 表 | 🔴 P0 | 4h | 2026-01-11 (今天) | 2026-01-11 (今天) |
| **Task 2**: 实施 Asset-Category 管理API | 🟡 P1 | 2-3天 | 2026-01-13 (周一) | 2026-01-15 (周三) |
| **Task 3-5**: 前端UI实施 | 🟢 P2 | 5-7周 | TBD | TBD |

**本计划重点**: Task 1 和 Task 2 (后端部分)

---

## Task 1: 创建 system_resources 表 🔴 P0

### 时间安排: 2026-01-11 (今天, 4小时)

| 阶段 | 任务 | 时间 | 负责人 | 产出 |
|-----|-----|------|-------|-----|
| 1.1 | 编写迁移SQL文件 | 30分钟 | Backend Dev | `migrations/v3/04_create_system_resources_table.sql` |
| 1.2 | 更新 ddl.sql | 10分钟 | Backend Dev | `migrations/ddl.sql` (更新) |
| 1.3 | 代码兼容性验证 | 30分钟 | Backend Dev | 验证报告 |
| 1.4 | 执行迁移 (测试环境) | 10分钟 | Backend Dev | 测试DB更新 |
| 1.5 | 编写单元测试 | 1小时 | Backend Dev | `tests/infrastructure/repositories/test_system_resource_repository.py` |
| 1.6 | 集成测试 | 1小时 | Backend Dev + QA | 测试报告 |
| 1.7 | 执行迁移 (生产环境) | 10分钟 | Backend Dev | 生产DB更新 |
| **总计** | | **3.5-4小时** | | |

### 详细实施步骤

#### 阶段 1.1: 编写迁移SQL文件 (30分钟)

**文件路径**: `decodables/migrations/v3/04_create_system_resources_table.sql`

**完整SQL内容**:

```sql
-- ============================================================================
-- Migration: Create system_resources table
-- Version: v3.04
-- Date: 2026-01-11
-- Author: Backend Team
-- Description: 创建系统资源表,用于存储官方提供的素材 (贴纸/模板/背景等)
--
-- Dependencies:
--   - asset_categories table (创建于 01_core_business.sql)
--   - update_updated_at_column() 函数 (通用触发器函数)
--
-- Rollback: See rollback section at end of file
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. 创建 system_resources 表
-- ----------------------------------------------------------------------------
CREATE TABLE system_resources (
    -- ========== 主键 ==========
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- ========== 资源标识 ==========
    resource_type TEXT NOT NULL CHECK (resource_type IN (
        'text', 'image', 'shape', 'table', 'sticker',
        'icon', 'frame', 'background', 'font', 'pattern'
    )),

    -- ========== 分类关联 ==========
    category_id UUID REFERENCES asset_categories(id) ON DELETE SET NULL,
    category TEXT,  -- 冗余字段 (ResourceCategory 枚举值),便于快速查询

    -- ========== 资源内容 ==========
    url TEXT NOT NULL,  -- 主要资源URL
    thumbnail_url TEXT,  -- 缩略图URL (可选)

    -- ========== 元数据 ==========
    name TEXT,  -- 显示名称
    description TEXT,  -- 描述
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],  -- 搜索标签
    metadata JSONB DEFAULT '{}',  -- 扩展元数据 (如: dimensions, colors, etc.)

    -- ========== 文件信息 ==========
    file_size INTEGER,  -- 文件大小 (bytes)
    width INTEGER,  -- 宽度 (px)
    height INTEGER,  -- 高度 (px)
    format TEXT,  -- 文件格式 (png, svg, jpg, etc.)

    -- ========== 访问控制 ==========
    allowed_tiers TEXT[] DEFAULT ARRAY['t1']::TEXT[],  -- 允许访问的层级 (t1=Free, t2=Starter, t3=Pro)
    min_tier TEXT DEFAULT 't1' CHECK (min_tier IN ('t1', 't2', 't3')),  -- 最低访问层级

    -- ========== 显示控制 ==========
    is_active BOOLEAN DEFAULT TRUE,  -- 是否激活
    is_featured BOOLEAN DEFAULT FALSE,  -- 是否精选
    display_order INTEGER DEFAULT 0,  -- 显示顺序 (值越小越靠前)

    -- ========== 时间戳 ==========
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,  -- 创建者 (Admin user_id)
    updated_by TEXT,  -- 最后更新者

    -- ========== Soft Delete (遵循项目规范) ==========
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,  -- 恢复期截止时间

    -- ========== 约束 ==========
    CONSTRAINT chk_system_resources_recovery_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

-- 添加表注释
COMMENT ON TABLE system_resources IS '系统资源表 - 存储官方提供的素材 (贴纸/模板/背景等)';
COMMENT ON COLUMN system_resources.category_id IS '关联的分类ID (外键到 asset_categories)';
COMMENT ON COLUMN system_resources.category IS '冗余的分类字符串 (ResourceCategory枚举值),便于查询';
COMMENT ON COLUMN system_resources.allowed_tiers IS '允许访问的用户层级数组 (t1/t2/t3)';
COMMENT ON COLUMN system_resources.min_tier IS '最低访问层级 (兼容旧逻辑)';


-- ----------------------------------------------------------------------------
-- 2. 创建索引 (性能优化)
-- ----------------------------------------------------------------------------

-- 资源类型索引 (过滤未删除的记录)
CREATE INDEX idx_sr_type ON system_resources(resource_type)
WHERE deleted_at IS NULL;

-- 分类索引
CREATE INDEX idx_sr_category ON system_resources(category_id)
WHERE deleted_at IS NULL;

-- 激活状态 + 类型复合索引 (最常用查询)
CREATE INDEX idx_sr_active_type ON system_resources(is_active, resource_type)
WHERE deleted_at IS NULL AND is_active = true;

-- 层级索引 (访问控制过滤)
CREATE INDEX idx_sr_tier ON system_resources(min_tier)
WHERE deleted_at IS NULL;

-- 标签GIN索引 (数组搜索优化)
CREATE INDEX idx_sr_tags ON system_resources USING GIN(tags)
WHERE deleted_at IS NULL;

-- 创建时间索引 (最新资源查询)
CREATE INDEX idx_sr_created ON system_resources(created_at DESC)
WHERE deleted_at IS NULL;

-- 精选资源索引
CREATE INDEX idx_sr_featured ON system_resources(is_featured, display_order)
WHERE deleted_at IS NULL AND is_featured = true;


-- ----------------------------------------------------------------------------
-- 3. 创建触发器 (自动更新 updated_at)
-- ----------------------------------------------------------------------------

CREATE TRIGGER update_system_resources_updated_at
    BEFORE UPDATE ON system_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TRIGGER update_system_resources_updated_at ON system_resources IS
'自动更新 updated_at 字段 (使用通用触发器函数)';


-- ----------------------------------------------------------------------------
-- 4. 插入初始数据 (可选 - 10个示例资源)
-- ----------------------------------------------------------------------------

-- 示例: 插入 10个 Sticker 资源
INSERT INTO system_resources (
    resource_type,
    category,
    url,
    thumbnail_url,
    name,
    tags,
    min_tier,
    allowed_tiers,
    is_active,
    is_featured,
    display_order,
    created_by
) VALUES
    -- Animals 分类
    ('sticker', 'animals', 'https://storage.example.com/stickers/cat-01.png', NULL, 'Cute Cat', ARRAY['cat', 'animal', 'cute'], 't1', ARRAY['t1', 't2', 't3'], true, true, 1, 'system'),
    ('sticker', 'animals', 'https://storage.example.com/stickers/dog-01.png', NULL, 'Happy Dog', ARRAY['dog', 'animal', 'happy'], 't1', ARRAY['t1', 't2', 't3'], true, true, 2, 'system'),
    ('sticker', 'animals', 'https://storage.example.com/stickers/bird-01.png', NULL, 'Flying Bird', ARRAY['bird', 'animal', 'flying'], 't1', ARRAY['t1', 't2', 't3'], true, false, 3, 'system'),

    -- Nature 分类
    ('sticker', 'nature', 'https://storage.example.com/stickers/tree-01.png', NULL, 'Green Tree', ARRAY['tree', 'nature', 'green'], 't1', ARRAY['t1', 't2', 't3'], true, false, 4, 'system'),
    ('sticker', 'nature', 'https://storage.example.com/stickers/flower-01.png', NULL, 'Red Flower', ARRAY['flower', 'nature', 'red'], 't2', ARRAY['t2', 't3'], true, true, 5, 'system'),

    -- People 分类 (Pro only)
    ('sticker', 'people', 'https://storage.example.com/stickers/person-01.png', NULL, 'Smiling Person', ARRAY['people', 'happy', 'smile'], 't3', ARRAY['t3'], true, true, 6, 'system'),

    -- Emotions 分类
    ('sticker', 'emotions', 'https://storage.example.com/stickers/heart-01.png', NULL, 'Red Heart', ARRAY['heart', 'love', 'emotion'], 't1', ARRAY['t1', 't2', 't3'], true, true, 7, 'system'),
    ('sticker', 'emotions', 'https://storage.example.com/stickers/star-01.png', NULL, 'Gold Star', ARRAY['star', 'award', 'emotion'], 't1', ARRAY['t1', 't2', 't3'], true, false, 8, 'system'),

    -- Education 分类
    ('sticker', 'education', 'https://storage.example.com/stickers/book-01.png', NULL, 'Open Book', ARRAY['book', 'education', 'study'], 't1', ARRAY['t1', 't2', 't3'], true, false, 9, 'system'),
    ('sticker', 'education', 'https://storage.example.com/stickers/pencil-01.png', NULL, 'Yellow Pencil', ARRAY['pencil', 'education', 'write'], 't1', ARRAY['t1', 't2', 't3'], true, false, 10, 'system');


-- ----------------------------------------------------------------------------
-- 5. 验证数据完整性
-- ----------------------------------------------------------------------------

-- 验证表创建
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'system_resources') THEN
        RAISE EXCEPTION 'Table system_resources was not created successfully';
    END IF;

    RAISE NOTICE '✅ Table system_resources created successfully';
END $$;

-- 验证索引创建 (应该有7个索引 + 1个主键)
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE tablename = 'system_resources';

    IF index_count < 8 THEN
        RAISE WARNING 'Expected at least 8 indexes, found %', index_count;
    ELSE
        RAISE NOTICE '✅ All indexes created successfully (% indexes)', index_count;
    END IF;
END $$;

-- 验证初始数据
DO $$
DECLARE
    resource_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO resource_count FROM system_resources;

    RAISE NOTICE '✅ Initial data inserted: % resources', resource_count;
END $$;


-- ============================================================================
-- ROLLBACK SCRIPT (如需回滚)
-- ============================================================================
/*
-- 删除触发器
DROP TRIGGER IF EXISTS update_system_resources_updated_at ON system_resources;

-- 删除所有索引 (会随表自动删除,但可手动删除)
DROP INDEX IF EXISTS idx_sr_type;
DROP INDEX IF EXISTS idx_sr_category;
DROP INDEX IF EXISTS idx_sr_active_type;
DROP INDEX IF EXISTS idx_sr_tier;
DROP INDEX IF EXISTS idx_sr_tags;
DROP INDEX IF EXISTS idx_sr_created;
DROP INDEX IF EXISTS idx_sr_featured;

-- 删除表 (CASCADE 删除所有依赖)
DROP TABLE IF EXISTS system_resources CASCADE;

-- 验证回滚
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'system_resources') THEN
        RAISE EXCEPTION 'Rollback failed: Table system_resources still exists';
    ELSE
        RAISE NOTICE '✅ Rollback successful: Table system_resources dropped';
    END IF;
END $$;
*/
```

**验证清单**:
- [ ] SQL语法正确 (无错误)
- [ ] 字段类型与 SystemResource 聚合根匹配
- [ ] 约束完整 (CHECK, FK, NOT NULL)
- [ ] 索引覆盖常用查询
- [ ] Soft delete 遵循项目规范
- [ ] 初始数据合理 (10个示例资源)

---

#### 阶段 1.2: 更新 ddl.sql (10分钟)

**文件路径**: `decodables/migrations/ddl.sql`

**操作**: 将 `system_resources` 表定义追加到 ddl.sql 末尾

```bash
# 自动追加 (保留注释和格式)
cat migrations/v3/04_create_system_resources_table.sql >> migrations/ddl.sql
```

---

#### 阶段 1.3: 代码兼容性验证 (30分钟)

**检查文件**: `infrastructure/repositories/system_resource_repository.py`

**验证点**:

1. **字段映射正确性**:

```python
def _row_to_aggregate(self, row: dict) -> SystemResource:
    # 验证所有字段都有对应的表列
    return SystemResource(
        resource_id=row["id"],  # ✅ 表字段: id
        resource_type=ResourceType(row["resource_type"]),  # ✅ resource_type
        url=row["url"],  # ✅ url
        category=ResourceCategory(row["category"]) if row.get("category") else None,  # ✅ category
        access_control=AccessControl(
            allowed_tiers=row.get("allowed_tiers", ["t1"])  # ✅ allowed_tiers
        ),
        metadata=ResourceMetadata(
            name=row.get("name"),  # ✅ name
            tags=row.get("tags"),  # ✅ tags
            dimensions=row.get("metadata", {}).get("dimensions"),  # ✅ metadata→dimensions
            file_size=row.get("file_size")  # ✅ file_size
        ),
        created_at=self._parse_timestamp(row.get("created_at")),  # ✅ created_at
        updated_at=self._parse_timestamp(row.get("updated_at"))  # ✅ updated_at
    )
```

2. **INSERT语句字段对应**:

```python
def create(self, resource: SystemResource) -> SystemResource:
    data = {
        "id": resource.resource_id,
        "resource_type": resource.resource_type.value,
        "url": resource.url,
        "category": resource.category.value if resource.category else None,
        "allowed_tiers": resource.access_control.allowed_tiers,
        "min_tier": resource.access_control.allowed_tiers[0] if resource.access_control.allowed_tiers else "t1",
        "name": resource.metadata.name if resource.metadata else None,
        "tags": resource.metadata.tags if resource.metadata else [],
        "file_size": resource.metadata.file_size if resource.metadata else None,
        # ...其他字段
    }
    result = self.client.table("system_resources").insert(data).execute()
```

**验证命令**:

```bash
# 静态检查
cd decodables
python -m pylint infrastructure/repositories/system_resource_repository.py

# 类型检查
python -m mypy infrastructure/repositories/system_resource_repository.py
```

---

#### 阶段 1.4: 执行迁移 (测试环境) (10分钟)

```bash
# 1. 连接测试数据库
export TEST_DATABASE_URL="postgresql://user:pass@test-db.supabase.co:5432/postgres"
psql $TEST_DATABASE_URL

# 2. 执行迁移
\i migrations/v3/04_create_system_resources_table.sql

# 3. 验证表结构
\d system_resources

# 预期输出:
#                                  Table "public.system_resources"
#       Column       |           Type           |                       Modifiers
# -------------------+--------------------------+------------------------------------------------------
#  id                | uuid                     | not null default uuid_generate_v4()
#  resource_type     | text                     | not null
#  category_id       | uuid                     |
#  category          | text                     |
#  url               | text                     | not null
#  ...

# 4. 验证索引
\di idx_sr_*

# 预期输出: 7个索引

# 5. 验证初始数据
SELECT count(*) FROM system_resources;
# 预期: 10

# 6. 测试查询
SELECT id, name, resource_type, category, min_tier FROM system_resources WHERE is_active = true LIMIT 5;
```

**验收标准**:
- ✅ 表创建成功，包含所有字段
- ✅ 7个索引全部创建
- ✅ 10条初始数据插入成功
- ✅ 查询正常返回结果

---

#### 阶段 1.5: 编写单元测试 (1小时)

**文件路径**: `decodables/tests/infrastructure/repositories/test_system_resource_repository.py`

```python
"""
SystemResourceRepository Unit Tests

@module tests.infrastructure.repositories.test_system_resource_repository
@version 1.0.0
"""

import pytest
from unittest.mock import MagicMock
from domains.content.aggregates.system_resource import SystemResource
from domains.content.value_objects import ResourceType, ResourceCategory, AccessControl, ResourceMetadata
from infrastructure.repositories.system_resource_repository import SystemResourceRepository


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock = MagicMock()
    mock.table.return_value = mock
    return mock


@pytest.fixture
def repository(mock_supabase):
    """SystemResourceRepository instance with mocked Supabase"""
    return SystemResourceRepository(mock_supabase)


class TestSystemResourceRepository:
    """Test SystemResourceRepository"""

    def test_create_system_resource_success(self, repository, mock_supabase):
        """Test creating a new system resource"""
        # Arrange
        resource = SystemResource.create_new(
            resource_type=ResourceType.STICKER,
            url="https://example.com/sticker.png",
            category=ResourceCategory.ANIMALS,
            allowed_tiers=["t1", "t2"],
            name="Test Sticker",
            tags=["test", "animal"]
        )

        mock_supabase.insert.return_value.execute.return_value.data = [{
            "id": resource.resource_id,
            "resource_type": "sticker",
            "url": resource.url,
            "category": "animals",
            "allowed_tiers": ["t1", "t2"],
            "name": "Test Sticker",
            "tags": ["test", "animal"],
            "created_at": "2026-01-11T10:00:00Z",
            "updated_at": "2026-01-11T10:00:00Z"
        }]

        # Act
        result = repository.create(resource)

        # Assert
        assert result.resource_id == resource.resource_id
        assert result.url == resource.url
        assert result.category == ResourceCategory.ANIMALS
        mock_supabase.table.assert_called_once_with("system_resources")
        mock_supabase.insert.assert_called_once()

    def test_get_by_id_success(self, repository, mock_supabase):
        """Test retrieving a resource by ID"""
        # Arrange
        resource_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_supabase.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": resource_id,
            "resource_type": "sticker",
            "url": "https://example.com/sticker.png",
            "category": "animals",
            "allowed_tiers": ["t1"],
            "name": "Cat Sticker",
            "tags": ["cat", "cute"],
            "created_at": "2026-01-11T10:00:00Z",
            "updated_at": "2026-01-11T10:00:00Z"
        }]

        # Act
        result = repository.get_by_id(resource_id)

        # Assert
        assert result is not None
        assert result.resource_id == resource_id
        assert result.resource_type == ResourceType.STICKER
        assert result.category == ResourceCategory.ANIMALS

    def test_get_by_id_not_found(self, repository, mock_supabase):
        """Test retrieving a non-existent resource"""
        # Arrange
        mock_supabase.select.return_value.eq.return_value.execute.return_value.data = []

        # Act
        result = repository.get_by_id("non-existent-id")

        # Assert
        assert result is None

    def test_list_with_filters(self, repository, mock_supabase):
        """Test listing resources with filters"""
        # Arrange
        mock_supabase.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "id1",
                "resource_type": "sticker",
                "url": "https://example.com/sticker1.png",
                "category": "animals",
                "allowed_tiers": ["t1"],
                "name": "Cat 1",
                "tags": ["cat"],
                "created_at": "2026-01-11T10:00:00Z",
                "updated_at": "2026-01-11T10:00:00Z"
            },
            {
                "id": "id2",
                "resource_type": "sticker",
                "url": "https://example.com/sticker2.png",
                "category": "animals",
                "allowed_tiers": ["t1"],
                "name": "Dog 1",
                "tags": ["dog"],
                "created_at": "2026-01-11T10:01:00Z",
                "updated_at": "2026-01-11T10:01:00Z"
            }
        ]

        # Act
        results = repository.list(
            resource_type="sticker",
            category="animals",
            is_active=True
        )

        # Assert
        assert len(results) == 2
        assert all(r.resource_type == ResourceType.STICKER for r in results)
        assert all(r.category == ResourceCategory.ANIMALS for r in results)

    def test_update_system_resource(self, repository, mock_supabase):
        """Test updating a resource"""
        # Arrange
        resource_id = "550e8400-e29b-41d4-a716-446655440000"
        update_data = {
            "name": "Updated Name",
            "tags": ["new", "tags"]
        }

        mock_supabase.update.return_value.eq.return_value.execute.return_value.data = [{
            "id": resource_id,
            "resource_type": "sticker",
            "url": "https://example.com/sticker.png",
            "category": "animals",
            "allowed_tiers": ["t1"],
            "name": "Updated Name",
            "tags": ["new", "tags"],
            "created_at": "2026-01-11T10:00:00Z",
            "updated_at": "2026-01-11T11:00:00Z"
        }]

        # Act
        result = repository.update(resource_id, update_data)

        # Assert
        assert result.metadata.name == "Updated Name"
        assert result.metadata.tags == ["new", "tags"]

    def test_delete_system_resource_soft_delete(self, repository, mock_supabase):
        """Test soft deleting a resource"""
        # Arrange
        resource_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_supabase.update.return_value.eq.return_value.execute.return_value.data = [{"id": resource_id}]

        # Act
        repository.delete(resource_id, soft=True)

        # Assert
        mock_supabase.update.assert_called_once()
        # 验证调用了软删除 (设置 deleted_at)

    def test_tier_access_control(self, repository):
        """Test tier-based access control logic"""
        # Arrange
        resource = SystemResource.create_new(
            resource_type=ResourceType.STICKER,
            url="https://example.com/pro-sticker.png",
            allowed_tiers=["t3"]  # Pro only
        )

        # Act & Assert
        assert resource.access_control.is_accessible_by_tier("t3") == True
        assert resource.access_control.is_accessible_by_tier("t2") == False
        assert resource.access_control.is_accessible_by_tier("t1") == False


# 运行测试
# pytest tests/infrastructure/repositories/test_system_resource_repository.py -v
```

**运行测试**:
```bash
cd decodables
pytest tests/infrastructure/repositories/test_system_resource_repository.py -v

# 预期: 所有测试通过
```

---

#### 阶段 1.6: 集成测试 (1小时)

**测试场景**:

**Scenario 1: Admin创建新资源**

```bash
curl -X POST http://localhost:8000/api/v3/admin/system-resources \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "sticker",
    "category": "animals",
    "url": "https://example.com/new-cat-sticker.png",
    "name": "New Cat Sticker",
    "tags": ["cat", "new", "cute"],
    "allowed_tiers": ["t1", "t2", "t3"]
  }'

# 预期响应: 201 Created
# {
#   "id": "uuid",
#   "resource_type": "sticker",
#   "url": "...",
#   "created_at": "2026-01-11T..."
# }
```

**Scenario 2: User查询Free Tier资源**

```bash
curl -X GET "http://localhost:8000/api/v3/user/system-resources?type=sticker&category=animals" \
  -H "Authorization: Bearer $FREE_USER_TOKEN"

# 预期响应: 200 OK
# {
#   "data": [
#     {"id": "...", "name": "Cute Cat", "min_tier": "t1"},
#     {"id": "...", "name": "Happy Dog", "min_tier": "t1"}
#   ],
#   "total": 2
# }
# 注意: Pro-only资源不应出现在结果中
```

**Scenario 3: 查询分类下的资源**

```bash
curl -X GET "http://localhost:8000/api/v3/user/system-resources?category=animals" \
  -H "Authorization: Bearer $PRO_USER_TOKEN"

# 预期响应: 包含所有animals分类资源 (包括Pro-only)
```

**验收标准**:
- ✅ Admin可创建/更新/删除资源
- ✅ User查询正确应用tier过滤
- ✅ 分类过滤正常工作
- ✅ 标签搜索正常工作
- ✅ 无数据库错误日志

---

#### 阶段 1.7: 执行迁移 (生产环境) (10分钟)

**前置条件**:
- ✅ 测试环境验证通过
- ✅ 单元测试全部通过
- ✅ 集成测试全部通过

**执行步骤**:

```bash
# 1. 备份数据库 (Supabase自动备份,但手动触发一次)
# 通过 Supabase Dashboard: Settings → Backups → Create Backup

# 2. 连接生产数据库
export PROD_DATABASE_URL="postgresql://user:pass@prod-db.supabase.co:5432/postgres"
psql $PROD_DATABASE_URL

# 3. 执行迁移 (只读模式下验证)
BEGIN;
\i migrations/v3/04_create_system_resources_table.sql
-- 检查结果
SELECT count(*) FROM system_resources;
-- 如果一切正常:
COMMIT;
-- 如果有问题:
-- ROLLBACK;

# 4. 验证
\d system_resources
SELECT * FROM system_resources LIMIT 5;

# 5. 重启后端服务 (如需要)
# Railway/Vercel 会自动重启
```

**回滚计划** (如失败):

```sql
-- 使用迁移文件末尾的回滚脚本
\i migrations/v3/04_create_system_resources_table_rollback.sql
```

---

### Task 1 验收标准总结

| 验收项 | 标准 | 验证方法 |
|-------|------|---------|
| 表创建 | ✅ system_resources 表存在 | `\d system_resources` |
| 字段完整 | ✅ 所有必需字段存在 | 查看表结构 |
| 索引优化 | ✅ 7个索引全部创建 | `\di idx_sr_*` |
| 触发器 | ✅ updated_at 自动更新 | UPDATE测试 |
| 初始数据 | ✅ 10条示例资源 | `SELECT count(*)` |
| 代码兼容 | ✅ Repository无错误 | 单元测试 |
| API正常 | ✅ 所有端点响应200/201 | 集成测试 |
| 性能 | ✅ 查询 < 50ms (1000条) | 性能测试 |

---

## Task 2: 实施 Asset-Category 管理API 🟡 P1

### 时间安排: 2026-01-13 ~ 2026-01-15 (3天)

| 阶段 | 任务 | 时间 | 负责人 | 产出 |
|-----|-----|------|-------|-----|
| 2.1 | 创建 Repository 接口和实现 | 4h | Backend Dev | `domains/content/category_repository.py` + `infrastructure/repositories/category_repository_impl.py` |
| 2.2 | 创建 Category Service | 4h | Backend Dev | `domains/content/category_service.py` |
| 2.3 | 创建 CQRS Handlers | 2h | Backend Dev | `application/queries/categories.py` + `application/commands/categories.py` |
| 2.4 | 创建 Admin API | 4h | Backend Dev | `api/admin/asset_categories.py` |
| 2.5 | 编写测试 | 3h | Backend Dev + QA | 单元测试 + 集成测试 |
| 2.6 | 性能优化和验证 | 1h | Backend Dev | 性能测试报告 |
| **总计** | | **18h = 2.25天** | | |

### 核心实施要点

#### 2.1 Repository层 - LTREE查询优化

```python
class CategoryRepository(ABC):
    """分类Repository接口"""

    @abstractmethod
    def get_tree(self, asset_type: Optional[str] = None) -> List[Category]:
        """获取分类树 (LTREE优化查询)"""

    @abstractmethod
    def get_children(self, parent_slug: str) -> List[Category]:
        """获取直接子分类"""

    @abstractmethod
    def move(self, slug: str, new_parent_slug: Optional[str]) -> Category:
        """移动分类 (级联更新path)"""
```

**关键SQL** (LTREE):

```sql
-- 查询所有子孙分类
SELECT * FROM asset_categories
WHERE path <@ 'animals'::ltree
ORDER BY path;

-- 移动分类 (更新path)
WITH RECURSIVE descendants AS (
    SELECT id, path FROM asset_categories WHERE slug = 'cats'
    UNION ALL
    SELECT c.id, c.path FROM asset_categories c
    JOIN descendants d ON c.parent_id = d.id
)
UPDATE asset_categories
SET path = 'animals.felines.cats'::ltree || subpath(path, nlevel('animals.cats'::ltree))
WHERE id IN (SELECT id FROM descendants);
```

#### 2.2 Service层 - 业务逻辑

```python
class CategoryService:
    """分类管理服务"""

    def create_category(self, name: str, slug: str, asset_type: str, parent_slug: Optional[str]) -> Category:
        """创建分类 - 自动计算path和level"""
        # 1. 验证slug唯一性
        # 2. 查询父分类 (如有)
        # 3. 计算path (parent.path + slug)
        # 4. 计算level (parent.level + 1)
        # 5. 保存到数据库

    def move_category(self, slug: str, new_parent_slug: Optional[str]) -> Category:
        """移动分类 - 级联更新所有子分类的path"""
        # 1. 验证目标父分类存在
        # 2. 检查不形成循环引用
        # 3. 更新当前分类的path和level
        # 4. 级联更新所有子分类 (使用LTREE)
```

#### 2.3 API层 - 7个端点

| 端点 | 方法 | 功能 | 权限 |
|-----|------|-----|------|
| `/api/admin/categories` | GET | 列出所有分类 | Admin |
| `/api/admin/categories/tree` | GET | 获取分类树 | Admin |
| `/api/admin/categories` | POST | 创建分类 | Admin |
| `/api/admin/categories/{slug}` | PATCH | 更新分类 | Admin |
| `/api/admin/categories/{slug}/move` | PUT | 移动分类 | Admin |
| `/api/admin/categories/{slug}` | DELETE | 删除分类 | Admin |
| `/api/admin/categories/{slug}/resources` | GET | 获取分类下资源 | Admin |

---

### Task 2 验收标准

| 验收项 | 标准 | 验证方法 |
|-------|------|---------|
| Repository | ✅ LTREE查询正常 | 单元测试 |
| Service | ✅ 7个方法全部实现 | 单元测试 |
| API | ✅ 7个端点响应正常 | 集成测试 |
| 性能 | ✅ 树查询 < 50ms (100分类) | 性能测试 |
| 边界测试 | ✅ 循环引用检测正常 | 边界测试 |
| 测试覆盖率 | ✅ ≥ 70% | Coverage报告 |

---

## 风险管理

### 高风险项

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| LTREE扩展未启用 | Task 2阻塞 | 提前验证: `CREATE EXTENSION IF NOT EXISTS ltree;` |
| 迁移执行失败 | Task 1阻塞 | 测试环境先执行 + 备份 |
| 性能不达标 | 用户体验差 | 索引优化 + 查询优化 |

### 低风险项

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| 测试覆盖率不足 | 潜在bug | 强制70%覆盖率要求 |
| 文档不完整 | 维护困难 | Code Review检查文档 |

---

## 进度跟踪

### 每日进度报告

**格式**:
```
日期: 2026-01-XX
完成: Task X.X (XX%)
阻塞: 无 / [具体问题]
明日计划: Task X.X
```

### 里程碑

| 里程碑 | 完成日期 | 验收标准 |
|-------|---------|---------|
| M1: system_resources表上线 | 2026-01-11 | ✅ API正常工作 |
| M2: Category管理API上线 | 2026-01-15 | ✅ 7个端点正常 |
| M3: 后端100%就绪 | 2026-01-15 | ✅ 所有验收标准通过 |

---

## 后续工作 (Out of Scope)

**前端实施** (P2 优先级):
- Task 3: Feature-Flag 前端UI (2-3天)
- Task 4: Onboarding 前端UI (3-4周)
- Task 5: Theme 前端UI (1-2周)

**总估算**: 5-7周

---

**计划生成时间**: 2026-01-11
**计划人员**: Claude Sonnet 4.5
**下次更新**: 每完成一个Task后更新进度
**计划状态**: Draft (待用户批准)
