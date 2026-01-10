# System Resources API v3.0.0 DDD 重构计划

## 背景

System Resources API v3.25 存在**严重架构违规**:
- ❌ 所有 9 个 endpoints 直接调用 `supabase.table()`
- ❌ 完全绕过 DDD 架构层 (Service/Repository)
- ❌ 文件上传逻辑散落在 API 层
- ❌ Audit logging 没有标准化

**当前评分**: ⭐⭐ (2星) - 严重架构问题
**目标评分**: ⭐⭐⭐⭐⭐ (5星) - 完整 DDD 架构

---

## 架构对比

### 现状 (v3.25 - 架构违规)
```python
# ❌ API 直接操作数据库
@router.get("")
async def list_system_resources(...):
    query = supabase.table("system_resources").select("*", count="exact")
    if type:
        query = query.eq("type", type)
    result = query.execute()
    return {"items": result.data or [], ...}
```

### 目标 (v3.0.0 - DDD 架构)
```python
# ✅ 完整 DDD 调用链
@router.get("")
async def list_system_resources(..., admin: dict = Depends(require_admin)):
    container = get_container()
    handler = container.list_system_resources_handler

    command = ListSystemResourcesCommand(
        resource_type=type,
        category=category,
        is_active=is_active,
        search=search,
        page=page,
        limit=limit,
    )

    result = await handler.handle(command)
    return result.result_data
```

**调用链**:
```
v3.25: API → Database (❌ 完全绕过 DDD)
v3.0.0: API → Handler → Service → Repository → Database (✅ 完整 DDD)
```

---

## 9 个 Endpoints 分析

| # | Endpoint | Method | 类型 | 复杂度 |
|---|----------|--------|------|--------|
| 1 | `GET /` | List resources | Query | 🟢 中等 |
| 2 | `GET /stats` | Get stats | Query | 🟢 简单 |
| 3 | `GET /{id}` | Get single | Query | 🟢 简单 |
| 4 | `POST /` | Create + Upload | Command | 🔴 高 (文件上传) |
| 5 | `PATCH /{id}` | Update | Command | 🟡 中等 |
| 6 | `POST /{id}/replace` | Replace + Upload | Command | 🔴 高 (文件上传) |
| 7 | `DELETE /{id}` | Delete | Command | 🟡 中等 (需删除文件) |
| 8 | `POST /batch` | Batch ops | Command | 🟡 中等 |
| 9 | `GET /{id}/audit-log` | Audit log | Query | 🟢 简单 |

**Command Handlers**: 5 个 (Create, Update, Replace, Delete, Batch)
**Query Handlers**: 4 个 (List, GetById, Stats, AuditLog)

---

## 重构方案

### Phase 1: 创建 Domain Service

**文件**: `domains/content/system_resources_service.py` (新建)

**职责**:
1. 系统资源 CRUD 业务逻辑
2. 文件上传/删除封装 (Supabase Storage)
3. Audit logging 标准化
4. Image dimensions 计算

**核心方法** (9 个):
```python
class SystemResourcesService:
    def __init__(self, repository, storage_client):
        self.repository = repository
        self.storage = storage_client

    # Query methods
    async def list_resources(...) -> tuple[List[Dict], int]:
        """List resources with filters and pagination."""

    async def get_resource(resource_id: str) -> Optional[Dict]:
        """Get single resource by ID."""

    async def get_stats() -> Dict:
        """Get resource statistics."""

    async def get_audit_log(resource_id: str) -> List[Dict]:
        """Get audit log for resource."""

    # Command methods
    async def create_resource(
        file: UploadFile,
        resource_data: Dict,
        admin_id: str,
    ) -> Dict:
        """Create resource with file upload."""
        # 1. Validate file (type, size)
        # 2. Upload to storage
        # 3. Get image dimensions
        # 4. Save to database
        # 5. Log audit

    async def update_resource(
        resource_id: str,
        updates: Dict,
        admin_id: str,
    ) -> Dict:
        """Update resource metadata."""

    async def replace_file(
        resource_id: str,
        new_file: UploadFile,
        admin_id: str,
    ) -> Dict:
        """Replace resource file."""
        # 1. Delete old file from storage
        # 2. Upload new file
        # 3. Update database
        # 4. Log audit

    async def delete_resource(
        resource_id: str,
        admin_id: str,
    ) -> Dict:
        """Soft delete resource."""
        # 1. Mark as inactive in DB
        # 2. Optionally delete file from storage
        # 3. Log audit

    async def batch_operation(
        operation: str,
        resource_ids: List[str],
        admin_id: str,
    ) -> Dict:
        """Batch activate/deactivate/delete."""
```

### Phase 2: 创建 Repository

**文件**: `infrastructure/repositories/system_resources_repository.py` (新建)

**方法** (8 个):
```python
class SupabaseSystemResourcesRepository:
    async def list_resources(filters, limit, offset) -> tuple[List, int]
    async def get_by_id(resource_id) -> Optional[Dict]
    async def create(data) -> Dict
    async def update(resource_id, updates) -> Dict
    async def delete(resource_id) -> bool
    async def get_stats() -> Dict
    async def get_audit_log(resource_id) -> List[Dict]
    async def batch_update(resource_ids, updates) -> int
```

### Phase 3: 创建 Application Layer

**文件 1**: `application/queries/system_resources.py` (新建)

4 个 Query Handlers:
```python
# 1. ListSystemResourcesQuery/Handler/Result
@dataclass
class ListSystemResourcesQuery:
    resource_type: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None
    page: int = 1
    limit: int = 50

@dataclass
class ListSystemResourcesResult:
    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
    has_more: bool

class ListSystemResourcesHandler:
    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, query) -> ListSystemResourcesResult:
        items, total = await self._service.list_resources(...)
        return ListSystemResourcesResult(...)

# 2. GetSystemResourceQuery/Handler/Result
# 3. GetResourceStatsQuery/Handler/Result
# 4. GetAuditLogQuery/Handler/Result
```

**文件 2**: `application/commands/system_resources.py` (新建)

5 个 Command Handlers:
```python
# 1. CreateSystemResourceCommand/Handler/Result
@dataclass
class CreateSystemResourceCommand:
    file: UploadFile
    type: str
    category: Optional[str]
    name: str
    description: Optional[str]
    # ... other fields
    admin_id: str

@dataclass
class CreateSystemResourceResult:
    result_data: Dict[str, Any]

class CreateSystemResourceHandler:
    def __init__(self, service: SystemResourcesService):
        self._service = service

    async def handle(self, command) -> CreateSystemResourceResult:
        result = await self._service.create_resource(
            file=command.file,
            resource_data={...},
            admin_id=command.admin_id,
        )
        return CreateSystemResourceResult(result_data=result)

# 2. UpdateSystemResourceCommand/Handler/Result
# 3. ReplaceResourceFileCommand/Handler/Result
# 4. DeleteSystemResourceCommand/Handler/Result
# 5. BatchOperationCommand/Handler/Result
```

### Phase 4: Container 注册

**文件**: `container.py`

9 个 Handler properties:
```python
# Query Handlers
@property
def list_system_resources_handler(self):
    from application.queries.system_resources import ListSystemResourcesHandler
    if 'list_system_resources' not in self._handlers:
        self._handlers['list_system_resources'] = ListSystemResourcesHandler(
            self.system_resources_service
        )
    return self._handlers['list_system_resources']

# ... get_system_resource_handler
# ... get_resource_stats_handler
# ... get_audit_log_handler

# Command Handlers
@property
def create_system_resource_handler(self):
    from application.commands.system_resources import CreateSystemResourceHandler
    if 'create_system_resource' not in self._handlers:
        self._handlers['create_system_resource'] = CreateSystemResourceHandler(
            self.system_resources_service
        )
    return self._handlers['create_system_resource']

# ... update_system_resource_handler
# ... replace_resource_file_handler
# ... delete_system_resource_handler
# ... batch_operation_handler

# Service
@property
def system_resources_service(self):
    if 'system_resources_service' not in self._services:
        from domains.content.system_resources_service import SystemResourcesService
        from infrastructure.repositories.system_resources_repository import (
            SupabaseSystemResourcesRepository
        )
        repository = SupabaseSystemResourcesRepository(self.db_client)
        self._services['system_resources_service'] = SystemResourcesService(
            repository=repository,
            storage_client=self.db_client,  # Supabase client for storage
        )
    return self._services['system_resources_service']
```

### Phase 5: API 层重构

**文件**: `api/user/system_resources.py`

重构 9 个 endpoints:

**Query Endpoints** (4 个):
```python
# 1. GET /
@router.get("")
@limiter.limit("60/minute")
async def list_system_resources(
    request: Request,
    type: Optional[str] = Query(None, max_length=50),
    category: Optional[str] = Query(None, max_length=50),
    is_active: Optional[bool] = None,
    search: Optional[str] = Query(None, max_length=MAX_SEARCH_LENGTH),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(50, ge=1, le=200),
    admin: dict = Depends(require_admin),
):
    """v3.0.0: Now uses ListSystemResourcesHandler (Container pattern)."""
    container = get_container()
    handler = container.list_system_resources_handler

    # v3.25: SR-MEDIUM-1 - Sanitize search
    if search:
        search = sanitize_search(search)

    query = ListSystemResourcesQuery(
        resource_type=type,
        category=category,
        is_active=is_active,
        search=search,
        page=page,
        limit=limit,
    )

    result = await handler.handle(query)

    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "limit": result.limit,
        "has_more": result.has_more,
    }

# 2. GET /stats
# 3. GET /{id}
# 4. GET /{id}/audit-log
```

**Command Endpoints** (5 个):
```python
# 5. POST / (Create with file upload)
@router.post("")
@limiter.limit("30/minute")
async def create_resource(
    request: Request,
    file: UploadFile = File(...),
    type: str = Form(...),
    category: Optional[str] = Form(None),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    # ... other Form fields
    admin: dict = Depends(require_admin),
):
    """v3.0.0: Now uses CreateSystemResourceHandler (Container pattern)."""
    container = get_container()
    handler = container.create_system_resource_handler

    command = CreateSystemResourceCommand(
        file=file,
        type=type,
        category=category,
        name=name,
        description=description,
        # ...
        admin_id=admin["id"],
    )

    result = await handler.handle(command)
    return result.result_data

# 6. PATCH /{id}
# 7. POST /{id}/replace
# 8. DELETE /{id}
# 9. POST /batch
```

### Phase 6: 测试迁移

**检查**: `tests/api/user/test_system_resources.py` 是否存在

如果存在:
- 迁移到 Handler mocking 模式
- Pattern: Mock `container._handlers['handler_name']`

---

## 预计工作量

| Phase | 文件 | 改动 | 时间 |
|-------|------|------|------|
| 1 | `domains/content/system_resources_service.py` | ~400 lines (新建) | 60 min |
| 2 | `infrastructure/repositories/system_resources_repository.py` | ~200 lines (新建) | 30 min |
| 3 | `application/queries/system_resources.py` | ~150 lines (新建) | 20 min |
| 3 | `application/commands/system_resources.py` | ~250 lines (新建) | 30 min |
| 4 | `container.py` | +120 lines | 15 min |
| 5 | `api/user/system_resources.py` | ~300 lines 重构 | 40 min |
| 6 | `tests/api/user/test_system_resources.py` | 迁移 (如果有) | 20 min |

**总计**: ~1010 lines, **预计 3-3.5 小时**

---

## 风险评估

**风险等级**: 🟡 **MEDIUM**

**复杂因素**:
1. ✅ 文件上传逻辑 (Supabase Storage) - 需要仔细封装
2. ✅ Audit logging - 需要标准化
3. ✅ Batch operations - 需要事务处理
4. ✅ Admin 权限验证 - 保留 `require_admin`

**降低风险策略**:
1. 分阶段重构,每个 Phase 独立测试
2. 保留所有参数验证逻辑 (v3.25 security improvements)
3. 文件上传使用现有 helper functions
4. 先完成 Service + Repository,再重构 API

---

## 实施步骤

### Step 1: 创建 Repository (基础层)
- 新建 `infrastructure/repositories/system_resources_repository.py`
- 实现 8 个数据访问方法
- 保持与 Supabase 交互逻辑

### Step 2: 创建 Service (业务层)
- 新建 `domains/content/system_resources_service.py`
- 实现 9 个业务方法
- 封装文件上传/删除逻辑
- 标准化 audit logging

### Step 3: 创建 Application Layer
- 新建 `application/queries/system_resources.py` (4 handlers)
- 新建 `application/commands/system_resources.py` (5 handlers)

### Step 4: Container 注册
- 注册 SystemResourcesService
- 注册 9 个 Handlers

### Step 5: API 层重构
- 重构 9 个 endpoints
- 保留所有验证逻辑
- 更新版本号 v3.25 → v3.0.0

### Step 6: 测试
- 检查测试文件
- 迁移或手动测试

### Step 7: Git 提交
- 提交所有改动
- 更新进度文档

---

## 预期结果

### 架构提升

| 指标 | v3.25 | v3.0.0 | 提升 |
|------|-------|--------|------|
| 架构合规 | 20/100 | **100/100** | +80 |
| 调用链完整 | 0/100 | **100/100** | +100 |
| 代码可测试性 | 30/100 | **100/100** | +70 |
| DDD 合规性 | 0% | **100%** | +100% |

### 评分提升

**v3.25**: ⭐⭐ (2星)
- 架构: 20/100 (严重违规)
- 安全: 90/100 (有验证)
- 可维护性: 40/100

**v3.0.0**: ⭐⭐⭐⭐⭐ (5星)
- 架构: 100/100 (+80)
- 安全: 90/100 (保持)
- 可维护性: 100/100 (+60)

---

## 成功标准

✅ 所有 9 个 endpoints 使用 Handler pattern
✅ 完整 DDD 调用链 (API → Handler → Service → Repository)
✅ 文件上传逻辑封装在 Service 层
✅ Audit logging 标准化
✅ 所有测试通过 (如果有)
✅ 无 Breaking Changes (API 接口兼容)

准备好后即可开始实施。
