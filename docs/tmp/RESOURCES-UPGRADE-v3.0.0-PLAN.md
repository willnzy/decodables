# Resources API v3.0.0 升级计划

## 背景

Resources API v2.1.0 已经使用了 Query Handlers 架构,但与 v3.0.0 标准存在架构差异。

### 当前状态 (v2.1.0)

**架构模式**: Inline Handler Pattern
```python
handler = GetResourcesHandler(content_service)  # Inline 创建
result = await handler.handle(query)
```

**依赖注入**: FastAPI Depends()
```python
content_service: ContentService = Depends(get_content_service)
```

### 目标状态 (v3.0.0)

**架构模式**: Container Pattern
```python
container = get_container()
handler = container.get_resources_handler  # 从 Container 获取
result = await handler.handle(query)
```

**依赖注入**: Container Property
```python
# Container 内部管理所有依赖
@property
def get_resources_handler(self):
    return GetResourcesHandler(self.content_service)
```

---

## 架构差距分析

### 合规性对比

| 维度 | v2.1.0 | v3.0.0 标准 | 状态 |
|------|---------|-------------|------|
| Query 对象 | ✅ 有 (8个) | ✅ 有 | ✅ 合规 |
| Handler 类 | ✅ 有 (7个) | ✅ 有 | ✅ 合规 |
| Result 对象 | ⚠️ 部分有 (3个) | ✅ 都有 | ⚠️ 部分合规 |
| Container 注册 | ❌ 无 | ✅ 有 | ❌ **不合规** |
| Handler 创建 | ❌ Inline | ✅ Container | ❌ **不合规** |
| Service DI | ⚠️ Depends() | ✅ Container | ⚠️ **方式不同** |

### Result 对象现状

| Handler | 返回类型 | v3.0.0 标准 |
|---------|----------|-------------|
| GetResourcesHandler | `GetResourcesResult` | ✅ 已符合 |
| GetResourceByIdHandler | `GetResourceByIdResult` | ✅ 已符合 |
| GetCategoriesHandler | `GetCategoriesResult` | ✅ 已符合 |
| GetStickersHandler | `Dict[str, Any]` | ❌ 需要创建 `GetStickersResult` |
| GetBackgroundsHandler | `Dict[str, Any]` | ❌ 需要创建 `GetBackgroundsResult` |
| GetProjectTemplatesHandler | `Dict[str, Any]` | ❌ 需要创建 `GetProjectTemplatesResult` |
| GetResourceStatsHandler | `GetResourceStatsResult` | ✅ 已符合 |

### 当前评分

**⭐⭐⭐⭐** (4星)

**评分详情**:
- **架构一致性**: 60/100 (有 CQRS 但不符合 Container 标准)
- **代码质量**: 95/100 (代码简洁,职责清晰)
- **测试覆盖**: 未知 (需要检查)
- **安全性**: 90/100 (有验证,有 rate limiting)

---

## 升级方案

### Phase 1: 完善 Result 对象 (application/queries/content.py)

**新增 3 个 Result 对象** (+30 行):

```python
@dataclass
class GetStickersResult:
    """Result of stickers query."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int

@dataclass
class GetBackgroundsResult:
    """Result of backgrounds query."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int

@dataclass
class GetProjectTemplatesResult:
    """Result of project templates query."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
```

**更新 3 个 Handler 的返回类型** (~15 行改动):

```python
# Before
class GetStickersHandler:
    async def handle(self, query: GetStickersQuery) -> Dict[str, Any]:
        return await self._content_service.get_stickers(...)

# After
class GetStickersHandler:
    async def handle(self, query: GetStickersQuery) -> GetStickersResult:
        result = await self._content_service.get_stickers(...)
        return GetStickersResult(
            items=result.get("items", []),
            total=result.get("total", 0),
            page=query.page,
            limit=query.limit,
        )
```

### Phase 2: Container 注册 (container.py)

**新增 7 个 Handler Properties** (+70 行):

```python
# ========== Resources Query Handlers (v3.0.0) ==========

@property
def get_resources_handler(self):
    """Get resources query handler (v3.0.0)."""
    from application.queries.content import GetResourcesHandler
    if 'get_resources' not in self._handlers:
        self._handlers['get_resources'] = GetResourcesHandler(self.content_service)
    return self._handlers['get_resources']

@property
def get_resource_by_id_handler(self):
    """Get resource by ID query handler (v3.0.0)."""
    from application.queries.content import GetResourceByIdHandler
    if 'get_resource_by_id' not in self._handlers:
        self._handlers['get_resource_by_id'] = GetResourceByIdHandler(self.content_service)
    return self._handlers['get_resource_by_id']

@property
def get_stickers_handler(self):
    """Get stickers query handler (v3.0.0)."""
    from application.queries.content import GetStickersHandler
    if 'get_stickers' not in self._handlers:
        self._handlers['get_stickers'] = GetStickersHandler(self.content_service)
    return self._handlers['get_stickers']

@property
def get_backgrounds_handler(self):
    """Get backgrounds query handler (v3.0.0)."""
    from application.queries.content import GetBackgroundsHandler
    if 'get_backgrounds' not in self._handlers:
        self._handlers['get_backgrounds'] = GetBackgroundsHandler(self.content_service)
    return self._handlers['get_backgrounds']

@property
def get_project_templates_handler(self):
    """Get project templates query handler (v3.0.0)."""
    from application.queries.content import GetProjectTemplatesHandler
    if 'get_project_templates' not in self._handlers:
        self._handlers['get_project_templates'] = GetProjectTemplatesHandler(self.content_service)
    return self._handlers['get_project_templates']

@property
def get_categories_handler(self):
    """Get categories query handler (v3.0.0)."""
    from application.queries.content import GetCategoriesHandler
    if 'get_categories' not in self._handlers:
        self._handlers['get_categories'] = GetCategoriesHandler(self.content_service)
    return self._handlers['get_categories']

@property
def get_resource_stats_handler(self):
    """Get resource stats query handler (v3.0.0)."""
    from application.queries.content import GetResourceStatsHandler
    if 'get_resource_stats' not in self._handlers:
        self._handlers['get_resource_stats'] = GetResourceStatsHandler(self.content_service)
    return self._handlers['get_resource_stats']
```

### Phase 3: API 层重构 (api/user/resources.py)

**重构 7 个 Endpoints** (~100 行改动):

#### 模式对比

**Before (v2.1.0)**:
```python
@router.get("", response_model=ResourcesListResponse)
async def list_resources(
    type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    content_service: ContentService = Depends(get_content_service),  # ❌ Depends()
    user: dict = Depends(get_current_user),
) -> ResourcesListResponse:
    # TL-MEDIUM-2: Validate type whitelist
    if type and type not in ["sticker", "background", "template", ...]:
        raise HTTPException(status_code=400, detail="Invalid type")

    query = GetResourcesQuery(
        user_tier=user.get("tier", "t1"),
        resource_type=type,
        category=category,
        page=page,
        limit=limit,
    )
    handler = GetResourcesHandler(content_service)  # ❌ Inline 创建
    result = await handler.handle(query)

    return ResourcesListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        limit=result.limit,
    )
```

**After (v3.0.0)**:
```python
@router.get("", response_model=ResourcesListResponse)
async def list_resources(
    type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),  # ✅ 只保留认证 Depends
) -> ResourcesListResponse:
    """
    Get system resources with filtering.

    v3.0.0: Now uses GetResourcesHandler (Container pattern).
    """
    # TL-MEDIUM-2: Validate type whitelist
    if type and type not in ["sticker", "background", "template", ...]:
        raise HTTPException(status_code=400, detail="Invalid type")

    container = get_container()  # ✅ 从 Container 获取
    handler = container.get_resources_handler  # ✅ Property

    query = GetResourcesQuery(
        user_tier=user.get("tier", "t1"),
        resource_type=type,
        category=category,
        page=page,
        limit=limit,
    )

    result = await handler.handle(query)

    return ResourcesListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        limit=result.limit,
    )
```

**关键变化**:
1. ❌ 移除 `content_service: ContentService = Depends(get_content_service)`
2. ✅ 新增 `container = get_container()`
3. ✅ 改为 `handler = container.get_resources_handler`
4. ✅ 保留所有参数验证逻辑 (TL-MEDIUM-2 等)

#### 7 个 Endpoints 改造清单

| Endpoint | Handler Property | Result 类型改动 |
|----------|------------------|-----------------|
| `GET /resources` | `get_resources_handler` | ✅ 无需改动 |
| `GET /resources/{id}` | `get_resource_by_id_handler` | ✅ 无需改动 |
| `GET /resources/stickers` | `get_stickers_handler` | ⚠️ 改为 `GetStickersResult` |
| `GET /resources/backgrounds` | `get_backgrounds_handler` | ⚠️ 改为 `GetBackgroundsResult` |
| `GET /resources/templates` | `get_project_templates_handler` | ⚠️ 改为 `GetProjectTemplatesResult` |
| `GET /resources/categories/{type}` | `get_categories_handler` | ✅ 无需改动 |
| `GET /resources/types` | 无 (直接返回常量) | ✅ 无需改动 |

**注意**: `GET /resources/types` 端点返回固定常量,不需要 Handler。

### Phase 4: 更新文档注释

**api/user/resources.py 顶部注释** 更新版本号:
```python
"""
Resources API - System resources endpoints (v3).

@module api.user.resources
@version 3.0.0

Changes:
- v3.0.0: DDD architecture upgrade - CQRS Query pattern
  - Migrated from Inline Handler to Container pattern
  - All 7 Query Handlers now registered in Container
  - Removed Depends(get_content_service) from endpoints
  - Added Result objects for Stickers/Backgrounds/Templates
  - Improved architecture consistency with other v3 modules

- v2.1.0: Security improvements
  - TL-MEDIUM-1: Added UUID format validation
  - TL-MEDIUM-2: Added type whitelist validation
  - TL-LOW-1: Added category whitelist validation
  - TL-LOW-2: Added name length validation

Endpoints:
- GET /api/v2/user/resources - List resources with filtering
- GET /api/v2/user/resources/{id} - Get single resource
- GET /api/v2/user/resources/stickers - Get stickers
- GET /api/v2/user/resources/backgrounds - Get backgrounds
- GET /api/v2/user/resources/templates - Get project templates
- GET /api/v2/user/resources/categories/{type} - Get categories
- GET /api/v2/user/resources/types - Get resource types
"""
```

**Router Tag 更新**:
```python
router = APIRouter(prefix="/resources", tags=["user-resources-v3"])  # v2 → v3
```

### Phase 5: 测试迁移 (tests/api/user/test_resources.py)

**测试模式迁移**:

**Before (Mock Service)**:
```python
@patch('api.user.resources.get_content_service')
def test_list_resources(self, mock_get_service, ...):
    mock_service = MagicMock()
    mock_service.get_resources_with_access = AsyncMock(return_value=[...])
    mock_get_service.return_value = mock_service
    # ...
```

**After (Mock Handler via Container)**:
```python
def test_list_resources(self, ...):
    from application.queries.content import GetResourcesHandler, GetResourcesResult

    mock_handler = MagicMock(spec=GetResourcesHandler)
    mock_handler.handle = AsyncMock(return_value=GetResourcesResult(
        items=[{...}],
        total=1,
        page=1,
        limit=50,
    ))

    from container import get_container
    container = get_container()
    original = container._handlers.get('get_resources')
    container._handlers['get_resources'] = mock_handler

    try:
        response = client.get("/api/v2/user/resources")
        assert response.status_code == 200
        mock_handler.handle.assert_called_once()

        # 验证 Query 参数
        call_args = mock_handler.handle.call_args[0][0]
        assert isinstance(call_args, GetResourcesQuery)
        assert call_args.user_tier == "t1"
    finally:
        if original:
            container._handlers['get_resources'] = original
        else:
            container._handlers.pop('get_resources', None)
```

**测试更新清单**:
- 检查是否有现有测试文件
- 如果有,迁移所有测试到 Handler mocking
- 如果无,记录在文档中 (测试覆盖率待评估)

---

## 实施步骤

### Step 1: 检查测试文件
```bash
find tests -name "*resources*" -type f
```

### Step 2: Phase 1 - 完善 Result 对象
- 编辑 `application/queries/content.py`
- 新增 3 个 Result dataclass
- 更新 3 个 Handler 的返回类型

### Step 3: Phase 2 - Container 注册
- 编辑 `container.py`
- 新增 7 个 Handler properties
- 确保在 `# ========== Query Handlers ==========` 区域

### Step 4: Phase 3 - API 层重构
- 编辑 `api/user/resources.py`
- 更新版本号和文档注释
- 重构 7 个 endpoints (移除 Depends,使用 Container)

### Step 5: Phase 4 - 测试验证
- 如果有测试: 迁移到 Handler mocking
- 如果无测试: 运行 API 手动测试

### Step 6: Git 提交
```bash
cd /Users/zhangyi/Code_all/AI-WEB/decodables
git add application/queries/content.py
git add container.py
git add api/user/resources.py
git add tests/api/user/test_resources.py  # 如果有
git commit -m "refactor(resources): upgrade Resources API to v3.0.0 Container pattern

- Migrated from Inline Handler to Container-based architecture
- Added 3 new Result objects (Stickers/Backgrounds/Templates)
- Registered 7 Query Handlers in Container
- Updated all 7 endpoints to use container.handler_property
- Removed Depends(get_content_service) from API layer
- Updated router tag: user-resources-v2 → user-resources-v3
- Improved architecture consistency with Support/Tools/Tasks v3

Architecture improvements:
- Handler creation: Inline → Container Property
- Dependency injection: Depends() → Container
- Result objects: 4/7 → 7/7 (100%)
- CQRS compliance: Partial → Full

Version: v2.1.0 → v3.0.0"
git push origin main
```

### Step 7: 更新进度文档
- 编辑 `docs/tmp/5-STAR-REVIEW-PLAN.md`
- Resources: ⭐⭐⭐⭐ → ⭐⭐⭐⭐⭐
- 完成进度: 19/24 → 20/24 (83%)

---

## 预期结果

### 架构改进

| 指标 | v2.1.0 | v3.0.0 | 提升 |
|------|--------|--------|------|
| 架构一致性 | 60/100 | 100/100 | +40 |
| Result 对象覆盖 | 4/7 (57%) | 7/7 (100%) | +43% |
| Container 集成 | 0/7 (0%) | 7/7 (100%) | +100% |
| CQRS 合规性 | 部分 | 完全 | ✅ |

### 评分提升

**v2.1.0**: ⭐⭐⭐⭐ (4星)
- 架构一致性: 60/100
- 代码质量: 95/100
- 安全性: 90/100

**v3.0.0**: ⭐⭐⭐⭐⭐ (5星)
- 架构一致性: 100/100 (+40)
- 代码质量: 95/100 (保持)
- 安全性: 90/100 (保持)

### 文件改动总结

| 文件 | 行数变化 | 主要改动 |
|------|----------|----------|
| `application/queries/content.py` | +45 行 | 新增 3 个 Result 对象 |
| `container.py` | +70 行 | 新增 7 个 Handler properties |
| `api/user/resources.py` | ~50 行改动 | 重构 7 个 endpoints |
| `tests/api/user/test_resources.py` | ? | 如果有,迁移到 Handler mocking |

**总计**: ~165 行新增/改动

---

## 风险评估

### 风险等级: 🟢 **LOW**

**原因**:
1. ✅ 只是架构模式迁移,业务逻辑不变
2. ✅ ContentService 完全不动
3. ✅ 所有参数验证逻辑保留
4. ✅ Rate limiting 保留
5. ✅ Handler 逻辑已存在且稳定

### 潜在问题

1. **测试文件未知**:
   - 可能无现有测试 → 需要手动验证
   - 可能有测试但需要大幅改动

2. **Result 对象不匹配**:
   - `get_stickers()` 等方法返回 Dict
   - 需要在 Handler 中转换为 Result 对象
   - 可能存在字段映射问题

3. **依赖注入变化**:
   - 从 FastAPI Depends() 改为 Container
   - 需要确保 Container 正确初始化 ContentService

### 回滚策略

如果出现问题:
```bash
git revert HEAD
git push origin main
```

所有改动在单个 commit 中,回滚干净。

---

## 后续优化 (可选)

### 1. 增加 Service 层单元测试

目前只测试 API 层,可考虑增加:
```python
# tests/domains/content/test_content_service.py
async def test_get_resources_with_access():
    service = ContentService(mock_repository)
    result = await service.get_resources_with_access(...)
    assert len(result) > 0
```

### 2. 增加 Handler 单元测试

```python
# tests/application/queries/test_content.py
async def test_get_resources_handler():
    handler = GetResourcesHandler(mock_service)
    query = GetResourcesQuery(user_tier="t2", ...)
    result = await handler.handle(query)
    assert isinstance(result, GetResourcesResult)
```

### 3. 考虑性能优化

- Resources 查询可能较大,考虑添加缓存
- 评估是否需要 pagination 优化

---

## 总结

Resources API v2.1.0 → v3.0.0 升级是一次**纯架构迁移**:
- ✅ 业务逻辑不变
- ✅ 安全验证保留
- ✅ 提升架构一致性
- ✅ 符合 DDD v3.0.0 标准

**预计工作量**: 30 分钟
**风险等级**: 🟢 LOW
**收益**: ⭐⭐⭐⭐ → ⭐⭐⭐⭐⭐

准备好后即可开始实施。
