# 后端问题解决方案设计 (Solution Design for Backend Issues)

**日期**: 2026-01-11
**设计人**: Claude Sonnet 4.5
**参考**: Backend-Readiness-Verification-2026-01-11.md

---

## 问题优先级排序

根据影响程度和紧急性，重新排序后的问题清单：

| 优先级 | ID | 问题 | 影响范围 | 用户可见 | 估算 |
|-------|----|----|---------|---------|------|
| **🔴 P0** | **Issue-1** | **`system_resources` 表缺失** | SystemResource API全部不可用 | 是 | 4-6h |
| 🟡 P1 | Issue-2 | Asset-Category 管理API未实施 | 无法管理分类层级 | 否 (Admin功能) | 2-3天 |
| 🟢 P2 | Issue-3 | Feature-Flag 前端UI 0% | 前端无法使用功能开关 | 是 (前端) | 2-3天 |
| 🟢 P2 | Issue-4 | Onboarding 前端UI 0% | 用户无引导体验 | 是 (前端) | 3-4周 |
| 🟢 P2 | Issue-5 | Theme 前端UI 0% | 用户无主题切换 | 是 (前端) | 1-2周 |

**说明**:
- P0: 后端阻塞问题，影响现有功能
- P1: 后端功能不完整，影响管理员操作
- P2: 前端未实施，不影响后端就绪度（本次关注点）

---

## 🔴 Solution 1: 创建 system_resources 表 (P0)

### 问题分析

**当前状态**:
- ✅ 代码层面: SystemResource 聚合根、Repository、Service 已完整实现
- ❌ 数据库层面: `system_resources` 表完全缺失
- ❌ 影响: 所有 SystemResource API 调用失败 (Supabase "table not found" 错误)

**根本原因**:
- v3 迁移中遗漏了 `system_resources` 表的创建
- 只创建了 `asset_categories` 表但未创建实际存储资源的表

### 解决方案设计

#### 方案A: 创建专用 system_resources 表 (推荐 ⭐)

**优势**:
- ✅ 符合 DDD 设计 (SystemResource 聚合根有专用表)
- ✅ 清晰的职责分离 (系统资源 vs 用户资产)
- ✅ 支持完整的资源管理功能
- ✅ 与现有代码 100% 兼容 (无需修改代码)

**劣势**:
- ⚠️ 需要创建新表 (迁移风险低)

**表结构设计**:

```sql
CREATE TABLE system_resources (
    -- 主键
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 资源标识
    resource_type TEXT NOT NULL CHECK (resource_type IN (
        'text', 'image', 'shape', 'table', 'sticker',
        'icon', 'frame', 'background', 'font', 'pattern'
    )),

    -- 分类关联
    category_id UUID REFERENCES asset_categories(id) ON DELETE SET NULL,
    category TEXT,  -- 冗余字段，便于快速查询

    -- 资源内容
    url TEXT NOT NULL,
    thumbnail_url TEXT,

    -- 元数据
    name TEXT,
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}',

    -- 尺寸/格式
    file_size INTEGER,  -- bytes
    width INTEGER,
    height INTEGER,
    format TEXT,  -- png, svg, jpg, etc.

    -- 访问控制
    allowed_tiers TEXT[] DEFAULT ARRAY['t1']::TEXT[],  -- t1=Free, t2=Starter, t3=Pro
    min_tier TEXT DEFAULT 't1' CHECK (min_tier IN ('t1', 't2', 't3')),

    -- 显示控制
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    updated_by TEXT,

    -- Soft delete (遵循项目规范)
    deleted_at TIMESTAMPTZ,
    recovery_expires_at TIMESTAMPTZ,

    CONSTRAINT chk_system_resources_recovery_consistency
    CHECK (
        recovery_expires_at IS NULL OR
        (deleted_at IS NOT NULL AND recovery_expires_at > deleted_at)
    )
);

-- 索引优化
CREATE INDEX idx_sr_type ON system_resources(resource_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_category ON system_resources(category_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_active ON system_resources(is_active, resource_type) WHERE deleted_at IS NULL AND is_active = true;
CREATE INDEX idx_sr_tier ON system_resources(min_tier) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_tags ON system_resources USING GIN(tags) WHERE deleted_at IS NULL;
CREATE INDEX idx_sr_created ON system_resources(created_at DESC) WHERE deleted_at IS NULL;

-- 审计日志触发器 (复用现有 updated_at 触发器)
CREATE TRIGGER update_system_resources_updated_at
    BEFORE UPDATE ON system_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**数据字段映射** (与现有代码对应):

| SystemResource字段 | 表字段 | 类型 | 说明 |
|-------------------|-------|------|------|
| resource_id | id | UUID | 主键 |
| resource_type | resource_type | TEXT | ResourceType 枚举 |
| url | url | TEXT | 资源URL |
| category | category | TEXT | ResourceCategory 枚举 |
| access_control.allowed_tiers | allowed_tiers | TEXT[] | 访问控制 |
| metadata.name | name | TEXT | 显示名称 |
| metadata.tags | tags | TEXT[] | 搜索标签 |
| metadata.dimensions | metadata→dimensions | JSONB | 宽高信息 |
| metadata.file_size | file_size | INTEGER | 文件大小 |
| created_at | created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | updated_at | TIMESTAMPTZ | 更新时间 |

#### 方案B: 复用 assets 表 (不推荐 ❌)

**优势**:
- ✅ 无需创建新表

**劣势**:
- ❌ 职责混乱 (系统资源 vs 用户资产)
- ❌ 需要修改现有代码 (Repository 引用 "assets")
- ❌ 需要添加 `is_system_resource` 布尔字段区分
- ❌ 破坏 DDD 架构纯净性
- ❌ 未来扩展困难 (系统资源与用户资产的字段需求不同)

**结论**: 不推荐

### 实施步骤

#### Step 1: 创建迁移文件 (30分钟)

```bash
# 文件: migrations/v3/04_create_system_resources_table.sql
```

内容:
1. 创建 `system_resources` 表
2. 添加 6个索引
3. 关联 `updated_at` 触发器
4. 插入初始数据 (可选, 10-20个基础资源)

#### Step 2: 更新 ddl.sql (10分钟)

将表定义同步到 `migrations/ddl.sql` (遵循项目规范)

#### Step 3: 验证 Repository 兼容性 (30分钟)

检查 `infrastructure/repositories/system_resource_repository.py` 字段映射:

```python
# 确认以下映射是否正确
def _row_to_aggregate(self, row: dict) -> SystemResource:
    return SystemResource(
        resource_id=row["id"],
        resource_type=ResourceType(row["resource_type"]),
        url=row["url"],
        category=ResourceCategory(row["category"]) if row.get("category") else None,
        access_control=AccessControl(
            allowed_tiers=row.get("allowed_tiers", ["t1"])
        ),
        metadata=ResourceMetadata(
            name=row.get("name"),
            tags=row.get("tags"),
            dimensions=row.get("metadata", {}).get("dimensions"),
            file_size=row.get("file_size")
        ),
        created_at=...,
        updated_at=...
    )
```

#### Step 4: 执行迁移 (10分钟)

```bash
# 连接 Supabase
psql $DATABASE_URL

# 执行迁移
\i migrations/v3/04_create_system_resources_table.sql

# 验证表创建
\d system_resources
SELECT count(*) FROM system_resources;
```

#### Step 5: 测试验证 (1-2小时)

**单元测试**:
```python
# tests/infrastructure/repositories/test_system_resource_repository.py
def test_create_system_resource():
    # 测试创建资源
    resource = SystemResource.create_new(...)
    repo.create(resource)

    # 验证读取
    fetched = repo.get_by_id(resource.resource_id)
    assert fetched.url == resource.url
```

**集成测试**:
```bash
# 测试 Admin API
curl -X POST http://localhost:8000/api/v3/admin/system-resources \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@sticker.png" \
  -F "type=sticker" \
  -F "category=animals"

# 验证响应
# 预期: 201 Created, 返回 resource_id
```

**验收标准**:
- ✅ 表创建成功，包含所有字段和索引
- ✅ Repository 所有方法正常工作
- ✅ Admin API 创建/查询/更新/删除正常
- ✅ User API 查询正常 (带tier过滤)
- ✅ 无 Supabase 错误日志

### 估算工时

| 任务 | 时间 |
|-----|------|
| 编写迁移SQL | 30分钟 |
| 更新ddl.sql | 10分钟 |
| 验证代码兼容性 | 30分钟 |
| 执行迁移 | 10分钟 |
| 编写测试 | 1小时 |
| 测试验证 | 1小时 |
| **总计** | **3.5-4小时** |

### 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|-----|-------|------|---------|
| 迁移执行失败 | 低 (10%) | 中 | 在测试环境先执行 |
| 字段映射不匹配 | 中 (30%) | 中 | 代码审查 + 单元测试 |
| 性能问题 | 低 (10%) | 低 | 已添加 6个索引 |
| 数据丢失 | 极低 (1%) | 高 | 备份数据库 (Supabase 自动备份) |

**结论**: 低风险，可立即实施

---

## 🟡 Solution 2: 实施 Asset-Category 管理API (P1)

### 问题分析

**当前状态**:
- ✅ 数据库: `asset_categories` 表完整 (LTREE 层级结构)
- ✅ 领域层: Value Objects (ResourceType, ResourceCategory) 已实现
- ⚠️ API层: 缺少专门的分类管理端点

**缺失功能**:
1. 创建/更新/删除分类
2. 查询分类树 (父子关系)
3. 移动分类 (重新设置parent)
4. 批量操作

### 解决方案设计

#### 方案A: 创建完整的 Category Service + Admin API (推荐 ⭐)

**新增文件**:

```
decodables/
├── domains/content/
│   ├── category_service.py  (NEW)
│   └── category_repository.py  (NEW)
├── infrastructure/repositories/
│   └── category_repository_impl.py  (NEW)
├── application/
│   ├── queries/
│   │   └── categories.py  (NEW)
│   └── commands/
│       └── categories.py  (NEW)
└── api/admin/
    └── asset_categories.py  (NEW)
```

**CategoryService 核心方法**:

```python
# domains/content/category_service.py
class CategoryService:
    """分类管理业务逻辑"""

    def get_category_tree(
        self,
        asset_type: Optional[str] = None,
        include_hidden: bool = False
    ) -> List[CategoryNode]:
        """获取分类树 (LTREE查询)"""

    def create_category(
        self,
        name: str,
        slug: str,
        asset_type: str,
        parent_slug: Optional[str] = None,
        min_tier: str = "t1"
    ) -> Category:
        """创建新分类 (自动计算path和level)"""

    def move_category(
        self,
        category_slug: str,
        new_parent_slug: Optional[str]
    ) -> Category:
        """移动分类 (更新path, level, 并级联更新子分类)"""

    def delete_category(
        self,
        category_slug: str,
        cascade: bool = False
    ):
        """删除分类 (cascade=True则删除所有子分类)"""
```

**Admin API 端点**:

```python
# api/admin/asset_categories.py

@router.get("/categories")
async def list_categories(
    asset_type: Optional[str] = None,
    parent_slug: Optional[str] = None,
    level: Optional[int] = None
):
    """
    获取分类列表
    - 支持按 asset_type 过滤
    - 支持按 parent_slug 查询子分类
    - 支持按 level 过滤 (1=顶级, 2=二级, 3=三级)
    """

@router.get("/categories/tree")
async def get_category_tree(
    asset_type: Optional[str] = None
):
    """
    获取完整分类树 (嵌套JSON)
    - 使用 LTREE 查询优化
    - 返回父子嵌套结构
    """

@router.post("/categories")
async def create_category(
    name: str,
    slug: str,
    asset_type: str,
    parent_slug: Optional[str] = None,
    min_tier: str = "t1"
):
    """创建新分类"""

@router.patch("/categories/{slug}")
async def update_category(
    slug: str,
    name: Optional[str] = None,
    is_visible: Optional[bool] = None,
    min_tier: Optional[str] = None
):
    """更新分类信息 (不包括移动)"""

@router.put("/categories/{slug}/move")
async def move_category(
    slug: str,
    new_parent_slug: Optional[str]
):
    """移动分类到新父分类下"""

@router.delete("/categories/{slug}")
async def delete_category(
    slug: str,
    cascade: bool = False
):
    """删除分类 (cascade=True 删除所有子分类)"""

@router.get("/categories/{slug}/resources")
async def get_category_resources(
    slug: str,
    page: int = 1,
    limit: int = 50
):
    """获取分类下的所有资源"""
```

#### 数据库查询优化 (LTREE)

**优势**: PostgreSQL LTREE 扩展提供高效的层级查询

```sql
-- 查询所有子分类 (包括孙分类)
SELECT * FROM asset_categories
WHERE path <@ 'animals'::ltree  -- <@ = "is descendant of"
ORDER BY path;

-- 查询直接子分类 (不包括孙分类)
SELECT * FROM asset_categories
WHERE parent_id = (SELECT id FROM asset_categories WHERE slug = 'animals');

-- 查询祖先路径
SELECT * FROM asset_categories
WHERE path @> 'animals.cats'::ltree  -- @> = "is ancestor of"
ORDER BY level;

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

### 实施步骤

**Phase 1: 数据层** (4小时)
1. 创建 `category_repository.py` 接口
2. 实现 `category_repository_impl.py` (Supabase + LTREE查询)
3. 编写单元测试

**Phase 2: 业务层** (4小时)
1. 创建 `category_service.py`
2. 实现 7个核心方法
3. 编写业务逻辑测试

**Phase 3: 应用层** (2小时)
1. 创建 Query Handlers (4个)
2. 创建 Command Handlers (3个)

**Phase 4: API层** (4小时)
1. 创建 `api/admin/asset_categories.py`
2. 实现 7个端点
3. 添加 rate limiting + 安全验证

**Phase 5: 测试** (2-4小时)
1. 集成测试 (API端到端)
2. 性能测试 (LTREE查询效率)
3. 边界测试 (循环引用、深度限制)

**总计**: 16-20小时 = **2-3个工作日**

### 验收标准

- ✅ 7个 Admin API 端点全部正常工作
- ✅ LTREE 查询性能 < 50ms (1000分类)
- ✅ 支持3级层级结构
- ✅ 移动分类时正确更新所有子分类的 path
- ✅ 删除父分类时正确处理子分类 (cascade或阻止)
- ✅ 测试覆盖率 ≥ 70%

---

## 🟢 Solution 3-5: 前端UI实施 (P2) - 仅概述

由于本次关注点是**后端就绪度**，前端实施仅列出概要方案。

### Solution 3: Feature-Flag 前端UI (2-3天)

**目录结构**:
```
decodables-fe/
├── lib/
│   └── feature-flags/
│       ├── context.tsx  (FeatureFlagProvider)
│       ├── hooks.ts  (useFeatureFlag, useVariant)
│       └── api.ts  (API调用封装)
```

**核心功能**:
- React Context Provider (从后端获取flags)
- `useFeatureFlag(key)` Hook
- `<FeatureFlag>` Component

**估算**: 2-3天

### Solution 4: Onboarding 前端UI (3-4周)

**第三方库**:
- react-joyride (步骤引导)
- react-confetti (完成动画)
- framer-motion (动画效果)

**5种引导类型**:
1. Welcome Tour (Modal)
2. Editor Tour (Joyride)
3. Checklist (Dashboard侧边栏)
4. Feature Spotlight (气泡提示)
5. Contextual Help (内嵌帮助)

**估算**: 3-4周

### Solution 5: Theme 前端UI (1-2周)

**核心功能**:
- 主题切换组件
- 节日主题显示
- 与 Events API 集成

**估算**: 1-2周

---

## 总结: 解决方案优先级

### 立即实施 (本周)

| 方案 | 优先级 | 估算 | 价值 |
|-----|-------|------|------|
| **Solution 1** | 🔴 P0 | 3.5-4h | 解除系统资源功能阻塞 |
| **Solution 2** | 🟡 P1 | 2-3天 | 完善分类管理功能 |

### 后续实施 (下周起)

| 方案 | 优先级 | 估算 | 价值 |
|-----|-------|------|------|
| Solution 3 | 🟢 P2 | 2-3天 | 前端功能开关 |
| Solution 5 | 🟢 P2 | 1-2周 | 前端主题切换 |
| Solution 4 | 🟢 P2 | 3-4周 | 用户引导体验 |

**关键路径**:
```
Solution 1 (4h) → Solution 2 (3天) → 后端完全就绪 ✅
                                  ↓
                        前端实施 (5-7周)
```

---

**文档生成时间**: 2026-01-11
**设计人员**: Claude Sonnet 4.5
**设计原则**: DDD架构 + 业界最佳实践 + 项目规范
**可行性**: 高 (基于现有架构和代码)
