# Templates API v3.0.0 DDD 重构计划

## 背景

Templates API v2.1.0 存在**严重架构违规**:
- ❌ 所有 10 个 endpoints 直接调用 `supabase.table()`
- ❌ 完全绕过 DDD 架构层 (Service/Repository)
- ❌ 业务逻辑散落在 API 层
- ❌ 无测试覆盖

**当前评分**: ⭐⭐ (2星) - 严重架构问题
**目标评分**: ⭐⭐⭐⭐⭐ (5星) - 完整 DDD 架构

---

## 架构对比

### 现状 (v2.1.0 - 架构违规)
```python
# ❌ API 直接操作数据库
@router.get("/asset")
async def list_asset_templates(...):
    result = supabase.table("asset_prompt_templates") \
        .select("*") \
        .eq("user_id", user["id"]) \
        .order("use_count", desc=True) \
        .execute()
    return TemplateListResponse(templates=result.data or [])
```

### 目标 (v3.0.0 - DDD 架构)
```python
# ✅ 完整 DDD 调用链
@router.get("/asset")
async def list_asset_templates(...):
    container = get_container()
    handler = container.list_asset_templates_handler

    query = ListAssetTemplatesQuery(user_id=user["id"])
    result = await handler.handle(query)

    return TemplateListResponse(templates=result.templates)
```

**调用链**:
```
v2.1.0: API → Database (❌ 完全绕过 DDD)
v3.0.0: API → Handler → Service → Repository → Database (✅ 完整 DDD)
```

---

## 10 个 Endpoints 分析

### Asset Prompt Templates (5 个)
| # | Endpoint | Method | 类型 | 复杂度 |
|---|----------|--------|------|--------|
| 1 | `GET /asset` | List | Query | 🟢 简单 |
| 2 | `POST /asset` | Create | Command | 🟡 中等 (模板限制检查) |
| 3 | `PUT /asset/{id}` | Update | Command | 🟢 简单 |
| 4 | `DELETE /asset/{id}` | Delete | Command | 🟢 简单 |
| 5 | `POST /asset/{id}/use` | Use | Command | 🟡 中等 (计数器+时间戳) |

### Page Prompt Templates (5 个)
| # | Endpoint | Method | 类型 | 复杂度 |
|---|----------|--------|------|--------|
| 6 | `GET /page` | List | Query | 🟢 简单 |
| 7 | `POST /page` | Create | Command | 🟡 中等 (模板限制检查) |
| 8 | `PUT /page/{id}` | Update | Command | 🟢 简单 |
| 9 | `DELETE /page/{id}` | Delete | Command | 🟢 简单 |
| 10 | `POST /page/{id}/use` | Use | Command | 🟡 中等 (计数器+时间戳) |

**分类**:
- **Query Handlers**: 2 个 (List Asset, List Page)
- **Command Handlers**: 8 个 (Create×2, Update×2, Delete×2, Use×2)

---

## 重构方案

### Phase 1: 创建 Repository

**文件**: `infrastructure/repositories/templates_repository.py` (新建)

**职责**:
- 数据访问层
- 两个表: `asset_prompt_templates`, `page_prompt_templates`

**核心方法** (12 个):
```python
class SupabaseTemplatesRepository:
    def __init__(self, db_client):
        self.client = db_client

    # Asset Templates (6 methods)
    async def list_asset_templates(user_id: str) -> List[Dict]
    async def get_asset_template(template_id: str, user_id: str) -> Optional[Dict]
    async def create_asset_template(data: Dict) -> Dict
    async def update_asset_template(template_id: str, user_id: str, updates: Dict) -> Optional[Dict]
    async def delete_asset_template(template_id: str, user_id: str) -> bool
    async def count_asset_templates(user_id: str) -> int

    # Page Templates (6 methods)
    async def list_page_templates(user_id: str) -> List[Dict]
    async def get_page_template(template_id: str, user_id: str) -> Optional[Dict]
    async def create_page_template(data: Dict) -> Dict
    async def update_page_template(template_id: str, user_id: str, updates: Dict) -> Optional[Dict]
    async def delete_page_template(template_id: str, user_id: str) -> bool
    async def count_page_templates(user_id: str) -> int
```

### Phase 2: 创建 Service

**文件**: `domains/templates/templates_service.py` (新建)

**职责**:
- 业务逻辑
- 模板数量限制检查 (MAX_TEMPLATES_PER_USER = 20)
- Use count 递增逻辑

**核心方法** (10 个):
```python
class TemplatesService:
    def __init__(self, repository: SupabaseTemplatesRepository):
        self.repository = repository

    # Asset Templates (5 methods)
    async def list_asset_templates(user_id: str) -> List[Dict]:
        """List user's asset templates ordered by use_count."""

    async def create_asset_template(user_id: str, template_data: Dict) -> Dict:
        """Create asset template with limit check."""
        # 1. Check count
        # 2. Create template

    async def update_asset_template(template_id: str, user_id: str, updates: Dict) -> Dict:
        """Update asset template."""

    async def delete_asset_template(template_id: str, user_id: str) -> bool:
        """Delete asset template."""

    async def use_asset_template(template_id: str, user_id: str) -> int:
        """Increment use_count and update last_used_at."""
        # 1. Get current use_count
        # 2. Update use_count + 1 and last_used_at
        # 3. Return new count

    # Page Templates (5 methods - same pattern)
    async def list_page_templates(...)
    async def create_page_template(...)
    async def update_page_template(...)
    async def delete_page_template(...)
    async def use_page_template(...)
```

### Phase 3: 创建 Application Layer

**文件 1**: `application/queries/templates.py` (新建)

2 个 Query Handlers:
```python
# 1. ListAssetTemplatesQuery/Handler/Result
@dataclass
class ListAssetTemplatesQuery:
    user_id: str

@dataclass
class ListAssetTemplatesResult:
    templates: List[Dict[str, Any]]

class ListAssetTemplatesHandler:
    def __init__(self, service: TemplatesService):
        self._service = service

    async def handle(self, query) -> ListAssetTemplatesResult:
        templates = await self._service.list_asset_templates(query.user_id)
        return ListAssetTemplatesResult(templates=templates)

# 2. ListPageTemplatesQuery/Handler/Result (同样模式)
```

**文件 2**: `application/commands/templates.py` (新建)

8 个 Command Handlers:
```python
# Asset Templates Commands (4)
# 1. CreateAssetTemplateCommand/Handler/Result
# 2. UpdateAssetTemplateCommand/Handler/Result
# 3. DeleteAssetTemplateCommand/Handler/Result
# 4. UseAssetTemplateCommand/Handler/Result

# Page Templates Commands (4 - 同样模式)
# 5. CreatePageTemplateCommand/Handler/Result
# 6. UpdatePageTemplateCommand/Handler/Result
# 7. DeletePageTemplateCommand/Handler/Result
# 8. UsePageTemplateCommand/Handler/Result
```

### Phase 4: Container 注册

**文件**: `container.py`

11 个注册 (1 Service + 10 Handlers):
```python
# Service
@property
def templates_service(self):
    from domains.templates.templates_service import TemplatesService
    from infrastructure.repositories.templates_repository import SupabaseTemplatesRepository
    if 'templates' not in self._services:
        repository = SupabaseTemplatesRepository(self.db_client)
        self._services['templates'] = TemplatesService(repository)
    return self._services['templates']

# Query Handlers (2)
@property
def list_asset_templates_handler(self): ...

@property
def list_page_templates_handler(self): ...

# Command Handlers (8)
@property
def create_asset_template_handler(self): ...
@property
def update_asset_template_handler(self): ...
@property
def delete_asset_template_handler(self): ...
@property
def use_asset_template_handler(self): ...

@property
def create_page_template_handler(self): ...
# ... (同样模式)
```

### Phase 5: API 层重构

**文件**: `api/user/templates.py`

重构 10 个 endpoints:
- 移除所有 `supabase.table()` 调用
- 使用 Container + Handler 模式
- 保留所有 v2.1.0 安全验证
- 版本: v2.1.0 → v3.0.0
- Router tag: user-templates-v2 → user-templates-v3

---

## 预计工作量

| Phase | 文件 | 改动 | 时间 |
|-------|------|------|------|
| 1 | `infrastructure/repositories/templates_repository.py` | ~250 lines (新建) | 30 min |
| 2 | `domains/templates/templates_service.py` | ~300 lines (新建) | 40 min |
| 3 | `application/queries/templates.py` | ~80 lines (新建) | 15 min |
| 3 | `application/commands/templates.py` | ~300 lines (新建) | 30 min |
| 4 | `container.py` | +120 lines | 15 min |
| 5 | `api/user/templates.py` | ~200 lines 重构 | 30 min |

**总计**: ~1250 lines, **预计 2.5-3 小时**

---

## 风险评估

**风险等级**: 🟢 **LOW**

**原因**:
1. ✅ 简单 CRUD 逻辑,无复杂业务规则
2. ✅ 无文件上传/下载
3. ✅ 无外部依赖
4. ✅ 两个独立表,互不影响

**降低风险策略**:
1. 分阶段重构,每个 Phase 独立测试
2. 保留所有 v2.1.0 参数验证逻辑
3. 先完成 Service + Repository,再重构 API

---

## 成功标准

✅ 所有 10 个 endpoints 使用 Handler pattern
✅ 完整 DDD 调用链 (API → Handler → Service → Repository)
✅ 业务逻辑封装在 Service 层
✅ 所有 v2.1.0 安全验证保留
✅ 无 Breaking Changes (API 接口兼容)

准备好后即可开始实施。
