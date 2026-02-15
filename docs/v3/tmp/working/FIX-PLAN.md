# Admin 审计问题修复方案 v1.0

> **基于**: FINAL-AUDIT-REPORT v2.4 (26 个问题)
> **原则**: 根源性重构 > 补丁式修复 | 项目未上线，可直接删除无用代码
> **参照模板**: `api/admin/config.py` (627 行，DDD + Container DI 全合规)
> **日期**: 2026-02-15

---

## 方法论

### 问题聚类

26 个问题按修复耦合度分为 6 个独立集群，每个集群内的问题共享修改文件或修复模式，应一起处理以避免重复修改：

| 集群 | 问题 | 核心主题 | 预计工时 |
|------|------|---------|---------|
| **A** | C7, C10, H3, H16 | DDD/DI 架构迁移 | 12h |
| **B** | C1, C2, C8, C11, H14, M7 | 前后端契约对齐 | 14h |
| **C** | H9, H11, H17, M2 | 错误处理 + 日志标准化 | 8h |
| **D** | C4, C6, H1, H2, H4, H13 | 快速修复 (独立) | 6h |
| **E** | H12, M1, M3, M5, M6 | 架构改善 | 16h |
| **F** | M4 | 文档补全 | 28h |

### 执行顺序

```
Phase 1: D (快速修复, 阻塞少) → 立即见效
Phase 2: A (DDD 迁移, C7/C10 是 P0) → 核心架构
Phase 3: B (前后端对齐, 含 4 个 P0) → 功能修复
Phase 4: C (错误处理 + 日志) → 质量提升
Phase 5: E (架构改善) → 长期健康
Phase 6: F (文档) → 持续进行
```

---

## 集群 D: 快速修复 (6 个问题)

### D-1. C6: tasks_mgmt.py 添加 await

**根因**: `service.run_task(task_name)` 调用异步方法缺 await，协程创建但未执行
**文件**: `api/admin/tasks_mgmt.py` L165
**方案**: 添加 `await` 关键字
**工作量**: 5min
**风险**: 🟢 极低

```python
# Before:
result = service.run_task(task_name)
# After:
result = await service.run_task(task_name)
```

**验证**: 运行 `pytest tests/test_app_startup.py -v` + tasks_mgmt 相关测试

---

### D-2. C4: AI Models 占位符 — 前后端死代码同时删除 ⚡ *v1.2 修正*

**根因**: `PUT /ai/models/config/admin` 端点注册但实现为 TODO 占位符
**文件**:
- 后端: `api/admin/ai_models.py` L179-184
- 前端: `app/admin/analytics/_lib/api.ts` L386-391 (`updateAdminModelConfig()`)

**v1.2 核实结论**: 前端 `updateAdminModelConfig()` 虽然存在，但在整个前端仓库中 **未被任何组件 import 或调用** (死代码)。后端占位端点也无实际功能。两侧均为死代码，可安全独立删除。

**方案**: **前后端同时删除死代码**
**工作量**: 15min

```python
# 后端: 删除以下代码块 (ai_models.py L179-184):
@router.put("/config/admin")
@limiter.limit("20/minute")
async def update_admin_config(request: Request, admin: dict = Depends(require_admin)):
    """Update admin-only AI config (placeholder)."""
    # TODO: Implement admin-specific config
    return {"status": "ok", "message": "Admin config updated"}
```

```typescript
// 前端: 删除以下代码块 (analytics/_lib/api.ts L386-391):
export async function updateAdminModelConfig(
  token: string | null,
  settings: Record<string, unknown>
): Promise<AIModelConfig> {
  return adminPut<AIModelConfig>(token, '/ai/models/config/admin', { settings });
}
```

**验证**: `pytest tests/test_app_startup.py -v` + `npm run build` (前端构建确认无断链)

---

### D-3. H1: users.py Tier 枚举标准化

**根因**: Tier 过滤同时接受 `free/starter/pro` 和 `t1/t2/t3`，应统一为系统代码
**文件**: `api/admin/users.py` L89
**方案**: 仅保留 `t1/t2/t3` 系统代码

```python
# Before:
tier: str = Field(..., pattern="^(t1|t2|t3|free|starter|pro)$")
# After:
tier: str = Field(..., pattern="^(t1|t2|t3)$")
```

同时检查:
1. 前端是否传 `free/starter/pro` — 如有，改为 `t1/t2/t3`
2. 常量引用: `from domains.identity.constants import TIER_T1, TIER_T2, TIER_T3`

**验证**: 前端 Tier 筛选功能测试

---

### D-4. H2: subscriptions VALID_TARGET_TIERS 补全 t3

**根因**: 白名单缺 `t3` (Pro Plan)，管理员无法将用户订阅切到 Pro
**文件**: `api/admin/subscriptions.py` L75
**方案**:

```python
# Before:
VALID_TARGET_TIERS = {"t1", "t2"}
# After:
VALID_TARGET_TIERS = {"t1", "t2", "t3"}
```

**验证**: 测试管理员将用户 Tier 切换到 t3

---

### D-5. H4: Themes 批量生成子端点实现

**根因**: 后端仅有 `POST /batch-generate`，缺前端已调用的 preview 和 jobId 查询端点
**文件**: `api/admin/themes.py`
**前端调用** (themes/_lib/api.ts):
- L163: `GET /themes/batch-generate/preview` — 预览生成计划
- L188: `GET /themes/batch-generate/{jobId}` — 查询单次任务状态

**方案**: 在 themes.py 新增 2 个端点

```python
@router.get("/batch-generate/preview")
@limiter.limit("30/minute")
async def preview_batch_generate(
    request: Request,
    # 从前端调用推断参数
    admin: dict = Depends(require_admin),
    theme_service: ThemeService = Depends(get_theme_service)
):
    """预览批量生成计划 — 返回待生成主题列表和预估积分消耗"""
    ...

@router.get("/batch-generate/{job_id}")
@limiter.limit("30/minute")
async def get_batch_generate_status(
    request: Request,
    job_id: str,
    admin: dict = Depends(require_admin),
    theme_service: ThemeService = Depends(get_theme_service)
):
    """查询单次批量生成任务状态"""
    ...
```

**前提**: 需确认 ThemeService 是否已有对应方法，或需要同步实现 Service 层
**工作量**: 3h (含 Service 层实现)
**验证**: 前端批量生成功能端到端测试

---

### D-6. H13: overrides 分页限制

**根因**: `GET /feature-overrides/{user_id}` 无分页参数，前端可请求任意大结果集
**文件**: `api/admin/overrides.py`
**方案**: 添加 offset/limit 参数 (与 C7 重构合并时一起处理)

```python
# 在 GET 端点添加:
offset: int = Query(0, ge=0),
limit: int = Query(50, ge=1, le=200)
```

**注意**: 此修复将在集群 A 的 C7 全面重构中一起完成，此处仅记录方案。

---

## 集群 A: DDD/DI 架构迁移 (4 个问题)

### 参照标准 (config.py 模式)

```python
# 1. Container DI 依赖函数
async def get_xxx_service() -> XxxService:
    container = get_container()
    return await container.get_xxx_service()

# 2. 端点使用 Depends 注入
@router.get("/")
@limiter.limit("30/minute")
async def list_xxx(
    request: Request,
    admin: dict = Depends(require_admin),
    service: XxxService = Depends(get_xxx_service)
):
    ...

# 3. Service 层处理业务逻辑
# 4. Repository 层处理数据访问
# 5. Container 注册 Service/Repository
```

---

### A-1. C7: overrides.py 全面重构 (P0)

**现状** (97 行):
- 🔴 直接调用 Supabase client，无 Service/Repository
- 🔴 无 Container DI
- 🔴 CRUD 不完整 (仅 GET)
- 🔴 无 rate limiter
- 🔴 无参数验证
- 🔴 无审计日志

**方案**: 完全重写 — 建立完整 DDD 三层架构

#### Step 1: 创建 Domain Entity

```
domains/admin/feature_override/
├── __init__.py
├── entity.py          # FeatureOverrideEntity
├── service.py         # FeatureOverrideService
└── constants.py       # ALLOWED_FEATURE_KEYS 白名单
```

```python
# entity.py
class FeatureOverrideEntity:
    user_id: str
    feature_key: str
    override_value: bool
    created_by: str      # admin_id
    created_at: datetime
    expires_at: Optional[datetime]

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "FeatureOverrideEntity": ...
```

#### Step 2: 创建 Repository

```
infrastructure/repositories/
└── feature_override_repository.py
```

```python
class FeatureOverrideRepository(ABC):
    @abstractmethod
    async def get_by_user(self, user_id: str, offset: int, limit: int) -> List[FeatureOverrideEntity]: ...
    @abstractmethod
    async def set_override(self, entity: FeatureOverrideEntity) -> FeatureOverrideEntity: ...
    @abstractmethod
    async def delete_override(self, user_id: str, feature_key: str) -> bool: ...

class SupabaseFeatureOverrideRepository(FeatureOverrideRepository):
    # Lazy Loading pattern
    ...
```

#### Step 3: 创建 Service

```python
# service.py
class FeatureOverrideService:
    def __init__(self, repo: FeatureOverrideRepository):
        self._repo = repo

    async def get_user_overrides(self, user_id: str, offset: int, limit: int) -> List[FeatureOverrideEntity]:
        # 验证 user_id 有效性
        ...

    async def set_override(self, user_id: str, feature_key: str, value: bool, admin_id: str) -> FeatureOverrideEntity:
        # 验证 feature_key 在白名单内
        if feature_key not in ALLOWED_FEATURE_KEYS:
            raise ValueError(f"Invalid feature key: {feature_key}")
        ...

    async def delete_override(self, user_id: str, feature_key: str) -> bool:
        ...
```

#### Step 4: 注册到 Container

```python
# container.py 添加:
async def get_feature_override_service(self) -> FeatureOverrideService:
    repo = SupabaseFeatureOverrideRepository(await self.get_db_client())
    return FeatureOverrideService(repo)
```

#### Step 5: 重写 Router

```python
# api/admin/overrides.py — 完全重写
router = APIRouter(prefix="/overrides", tags=["admin-overrides"])

async def get_override_service() -> FeatureOverrideService:
    container = get_container()
    return await container.get_feature_override_service()

# Request/Response models
class SetOverrideRequest(BaseModel):
    feature_key: str = Field(..., description="Feature key from allowed list")
    override_value: bool
    expires_at: Optional[datetime] = None

class OverrideResponse(BaseModel):
    user_id: str
    feature_key: str
    override_value: bool
    created_by: str
    created_at: datetime
    expires_at: Optional[datetime]

# CRUD 端点
@router.get("/{user_id}")
@limiter.limit("30/minute")
async def get_user_overrides(...): ...

@router.post("/{user_id}")
@limiter.limit("10/minute")
async def set_override(...): ...

@router.delete("/{user_id}/{feature_key}")
@limiter.limit("10/minute")
async def delete_override(...): ...
```

**H13 (分页限制) 在此一并解决**: GET 端点添加 `offset/limit` 参数

**修改文件清单**:
1. 新建 `domains/admin/feature_override/entity.py`
2. 新建 `domains/admin/feature_override/service.py`
3. 新建 `domains/admin/feature_override/constants.py`
4. 新建 `infrastructure/repositories/feature_override_repository.py`
5. 修改 `container.py` — 注册 Service
6. 重写 `api/admin/overrides.py`
7. 新建测试 `tests/test_admin_overrides.py`

**工作量**: 6h
**风险**: 🟡 中 (需确保现有 override 数据兼容)

---

### A-2. C10: user_creation_monitoring 全面迁移 (P0)

**现状** (262 行):
- 🔴 直接导入 `UserCreationMonitoringService` 单例 (非 Container DI)
- 🔴 无 rate limiter
- 🔴 `/events` 返回未脱敏 email

**方案**:

#### Step 1: Container DI 迁移

```python
# Before (L13):
from application.services.user_creation_monitoring import UserCreationMonitoringService

# After:
from container import get_container

async def get_monitoring_service() -> UserCreationMonitoringService:
    container = get_container()
    return await container.get_user_creation_monitoring_service()
```

确认 Container 是否已注册该 Service，如无则添加注册。

#### Step 2: 所有 5 个端点添加 rate limiter

```python
@router.get("/stats")
@limiter.limit("30/minute")    # 查询端点 30/min
async def get_stats(...): ...

@router.get("/health")
@limiter.limit("30/minute")
async def get_health(...): ...

@router.get("/events")
@limiter.limit("20/minute")    # 含 PII 的端点更严格
async def get_events(...): ...

@router.get("/recent")
@limiter.limit("30/minute")
async def get_recent(...): ...

@router.get("/trends")
@limiter.limit("30/minute")
async def get_trends(...): ...
```

#### Step 3: PII 脱敏

```python
# 在 /events 端点的 response 构造中:
def mask_email(email: str) -> str:
    """user@example.com → u***@example.com"""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"

# 或在 Service 层处理 (更好的关注点分离)
```

**修改文件清单**:
1. 修改 `api/admin/user_creation_monitoring.py` — DI + rate limit + 脱敏
2. 可能修改 `container.py` — 注册 Service
3. 修改/新建测试

**工作量**: 3h
**风险**: 🟢 低

---

### A-3. H3: feature_flags.py 全局 Service 移除

**现状** (726 行):
- 大部分端点已正确使用 Container DI ✅
- 仅 `test_evaluation` (L528/L585) 使用全局 `feature_service` 实例
- rate limiter 仅 1/9 端点有

**方案**:

#### Step 1: 移除全局导入

```python
# 删除 L35:
from core.feature_flag import feature_service  # ❌ 删除

# L585 改为:
# Before:
result = feature_service.evaluate(...)
# After:
service: FeatureFlagService = Depends(get_feature_flag_service)
result = await service.evaluate(...)
```

#### Step 2: 补全 rate limiter (8 个端点)

```python
# 所有 GET 端点: @limiter.limit("30/minute")
# 所有 POST/PATCH/DELETE 端点: @limiter.limit("10/minute")
```

**修改文件**: `api/admin/feature_flags.py`
**工作量**: 1h
**风险**: 🟢 低

---

### A-4. H16: tiers.py Container DI 迁移

**现状** (492 行): ⚡ *v1.2 修正*
- Rate limiter ✅ (3/3 端点)
- 参数验证 ✅
- 🔴 L111-119: `get_tier_service()` 直接创建 `SupabaseConfigRepository(db)` 而非从 Container 获取
- 🔴 L170-171, L265-266, L353-355: 3 处 **额外** 重复创建 Repository (绕过 `get_tier_service()`)
- **共 4 处直接实例化** (1 处在 `get_tier_service` 定义 + 3 处绕过该函数直接创建)

**方案**: 重写 `get_tier_service()` 使用 Container，并消除全部 4 处直接实例化

```python
# Before (L111-119):
async def get_tier_service() -> TierService:
    from core.database import get_async_db_client
    db = await get_async_db_client()
    config_repo = SupabaseConfigRepository(db)  # ❌ 直接创建 (第 1 处)
    return TierService(config_repo)

# After:
async def get_tier_service() -> TierService:
    container = get_container()
    return await container.get_tier_service()  # ✅ 从 Container 获取
```

消除 L170-171, L265-266, L353-355 的 3 处重复创建 (第 2-4 处) — 统一通过 `Depends(get_tier_service)` 注入。

**前提**: Container 未注册 `get_tier_service()`，需同步添加。
**修改文件**: `api/admin/tiers.py` + `container.py` (添加注册)
**工作量**: 1h
**风险**: 🟢 低

---

## 集群 B: 前后端契约对齐 (6 个问题)

### B-1. C1: asset_categories slug vs id + HTTP 方法 (P0)

**现状**:
- 后端: `@router.patch("/{slug}")`, `@router.delete("/{slug}")`, `@router.put("/{slug}/move")`
- 前端: `getCategory(token, id)` → `/asset-categories/${id}` — 传的是 id 不是 slug

**方案**: **后端改用 id 作为路径参数** (前端已有 id，修改后端更合理)

```python
# Before:
@router.patch("/{slug}", ...)
async def update_category(slug: str, ...):
    # 用 slug 查询

# After:
@router.patch("/{category_id}", ...)
async def update_category(category_id: str, ...):
    # 用 id 查询
```

同时统一 HTTP 方法:
- 前端使用 `PATCH` (部分更新) — 保持
- 后端从 `PUT` 改为 `PATCH` (如适用)

**修改文件**:
1. `api/admin/asset_categories.py` — 路由参数 slug→id + HTTP 方法
2. 前端保持不变 (前端已正确使用 id)
3. Service/Repository 层查询方式调整 (如 find_by_slug → find_by_id)

**工作量**: 3h
**风险**: 🟡 中 (需确认数据库查询是否支持 id 查询)

---

### B-2. C2: 用户 Tier 变更切到新 API (P0)

**现状**:
- 后端: `POST /users/{user_id}/tier` 返回 410 Gone，已废弃
- 后端: `PATCH /users/{user_id}` 是新的更新端点 (含 TierUpdateRequest)
- 前端: `changeUserTier()` 仍调用旧 POST 端点

**方案**: **前端删除旧函数，使用现有 updateUser()**

```typescript
// Before (users/_lib/api.ts L159-168):
// Change user tier (DEPRECATED in backend)
export async function changeUserTier(token: string, userId: string, tier: string) {
  return adminApiRequest(token, `/users/users/${userId}/tier`, {
    method: 'POST', body: JSON.stringify({ tier })
  });
}
// ❌ 删除此函数

// After — 调用方改用:
updateUser(token, userId, { tier: newTier })
```

同时:
1. 后端删除 410 占位端点 (项目未上线，无需保留)
2. 前端组件中所有 `changeUserTier` 调用改为 `updateUser`

**修改文件**:
1. 前端: `users/_lib/api.ts` — 删除 changeUserTier
2. 前端: 搜索所有调用 changeUserTier 的组件，改用 updateUser
3. 后端: `users.py` — 删除 POST /users/{user_id}/tier 端点 (L191-211)

**工作量**: 2h
**风险**: 🟢 低

---

### B-3. C8: 前后端分页参数统一 (P0)

**现状**:
- 后端: 全部使用 `offset` + `limit`
- 前端: 混用 `page/page_size` (5+ 处) 和 `offset/limit`

**受影响的前端文件** (需改 page/page_size → offset/limit):
1. `users/_lib/api.ts` — searchUsers(), getUserProjects()
2. `_lib/api.ts` — fetchOperationLogs(), fetchErrorLogs(), fetchTasks()
3. `moderation/_lib/api.ts` — getModerationList() (如存在)

**方案**: **前端统一迁移到 offset/limit**

```typescript
// Before:
export async function searchUsers(token: string, params: { page: number; page_size: number; ... }) {
  return adminApiRequest(token, '/users', { params: { page: params.page, page_size: params.page_size } });
}

// After:
export async function searchUsers(token: string, params: { offset: number; limit: number; ... }) {
  return adminApiRequest(token, '/users', { params: { offset: params.offset, limit: params.limit } });
}
```

同时需要修改:
1. 前端类型定义 (`_lib/types.ts`) — PaginationParams 统一为 offset/limit
2. 前端组件中的分页状态管理 (page state → offset state)
3. 前端分页组件的 onChange 逻辑

**修改文件**:
1. 前端 `_lib/types.ts` — PaginationParams 定义
2. 前端 5+ 个 api.ts 文件
3. 前端相关分页组件 (Pagination, table components)

**工作量**: 4h
**风险**: 🟡 中 (涉及多文件，需逐一验证)

---

### B-4. C11: Articles check-slug + stats 端点实现 (P0)

**现状**:
- 前端调用 `GET /articles/check-slug?slug=...` 和 `GET /articles/stats`
- 后端完全无这两个端点

**方案**: **后端实现这两个端点**

```python
# articles.py 新增:

@router.get("/check-slug")
@limiter.limit("30/minute")
async def check_slug_unique(
    request: Request,
    slug: str = Query(..., min_length=1),
    exclude_id: Optional[str] = Query(None),
    admin: dict = Depends(require_admin),
    service: ArticleService = Depends(get_article_service)
):
    """检查 slug 唯一性"""
    is_unique = await service.check_slug_unique(slug, exclude_id)
    return {"slug": slug, "is_unique": is_unique}

@router.get("/stats")
@limiter.limit("30/minute")
async def get_article_stats(
    request: Request,
    admin: dict = Depends(require_admin),
    service: ArticleService = Depends(get_article_service)
):
    """获取文章统计 (总数/已发布/草稿)"""
    stats = await service.get_stats()
    return stats
```

**前提**: ArticleService 需添加 `check_slug_unique()` 和 `get_stats()` 方法
**注意**: `/check-slug` 路由必须在 `/{id}` 之前注册，否则 FastAPI 会把 "check-slug" 当 id 解析

**修改文件**:
1. `api/admin/articles.py` — 新增 2 个端点
2. Service 层 — 新增 2 个方法
3. Repository 层 — 新增 2 个查询方法
4. 测试

**工作量**: 3h
**风险**: 🟢 低

---

### B-5. H14: Articles 筛选参数后端实现

**现状**:
- 前端发送: `offset, limit, category, status, search, sort_by, sort_order`
- 后端接收: `category, include_drafts, offset, limit` — 缺 status/search/sort_by/sort_order

**方案**: **后端扩展 list 端点参数**

```python
# Before (articles.py list 端点):
async def list_articles(
    category: Optional[str] = Query(None),
    include_drafts: bool = Query(True),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    ...
):

# After:
async def list_articles(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None, pattern="^(draft|published|archived)$"),
    search: Optional[str] = Query(None, min_length=1, max_length=200),
    sort_by: Optional[str] = Query("created_at", pattern="^(created_at|updated_at|title|status)$"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    ...
):
```

**注意**: 删除 `include_drafts` 参数，用 `status` 替代 (更灵活)
**修改文件**: `api/admin/articles.py`, ArticleService, ArticleRepository
**工作量**: 2h

---

### B-6. M7: tasks_mgmt 前端 stub 删除

**现状**:
- 前端: `cancelTask()` 和 `retryTask()` 是 stub 函数 (仅 console.warn)
- 后端: 无 cancel/retry 端点
- 项目未上线

**方案**: **前后端都不需要，直接删除前端 stub**

```typescript
// 删除 _lib/api.ts L156-170:
// cancelTask() — stub
// retryTask() — stub
```

同时检查前端组件中是否有调用这两个函数的按钮/UI，如有则一并删除。

**修改文件**: 前端 `_lib/api.ts`, 相关组件
**工作量**: 30min

---

## 集群 C: 错误处理 + 日志标准化 (4 个问题)

### C-1. H17: 建立 Admin 错误码系统

**现状**:
- 后端各模块直接抛 `HTTPException(status_code, detail=技术错误信息)`
- 前端 `adminApiClient.ts` 捕获后直接 throw，组件层用 `message.apiError(err)` 显示
- `getUserFriendlyMessage()` 函数已存在但未在 adminApiClient 层使用

**方案**: 三层标准化

#### Layer 1: 后端统一错误响应格式

```python
# core/errors.py (新建或扩展):
class AdminErrorCode(str, Enum):
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class AdminAPIError(HTTPException):
    def __init__(self, code: AdminErrorCode, message: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            detail={"code": code.value, "message": message}
        )
```

所有 admin router 中的 `HTTPException` 替换为 `AdminAPIError`。

#### Layer 2: 前端 adminApiClient 错误转换

```typescript
// adminApiClient.ts — catch 块中:
catch (error) {
    const apiError = parseAdminError(error);
    // 自动转换为用户友好消息
    throw new AdminApiError(
        apiError.code,
        getUserFriendlyMessage(apiError.code, apiError.status),
        apiError.originalMessage
    );
}
```

#### Layer 3: 前端组件统一使用

```typescript
// 组件中:
try {
    await updateConfig(...);
} catch (error) {
    if (error instanceof AdminApiError) {
        message.error(error.userMessage);  // 已转换好的友好消息
    }
}
```

**修改文件**:
1. 后端: 新建 `core/admin_errors.py`
2. 后端: 各 admin router 替换 HTTPException
3. 前端: `adminApiClient.ts` — 添加错误转换层
4. 前端: 新建 `_lib/adminErrors.ts` — 错误码定义 + 友好消息映射

**工作量**: 4h
**风险**: 🟡 中 (涉及多文件，但不改变业务逻辑)

---

### C-2. H9: 前端 catch 块规范化

**代码验证修正**: 原审计称 "~40 个空 catch 块"，实际只有 **15 个 catch 块分布在 8 个文件**，且**无真正的空 catch** — 都有 console.warn 或 message.apiError 处理。

**实际问题**: 部分 catch 块使用 `console.warn + return 默认值` (静默降级)，不通知用户

**方案**: 分类处理

```
Type A: catch → message.apiError(err) — ✅ 保持不变
Type B: catch → console.warn + return default — 需评估是否应通知用户
```

对 Type B (约 5 处，在 `_lib/api.ts` 中):
- 如果是可选功能降级 (如 health check 失败) → 保持 console.warn，但替换为 Logger
- 如果是用户操作结果 → 改为 Logger.warn + toast 通知

**与 M2 合并处理**: 所有 console.warn/console.error 统一替换为 Logger

**工作量**: 2h (与 C-3 合并)

---

### C-3. M2: console.log 替换为 Logger

**现状**: 4 个文件残留 console.* 调用，Logger 类已存在 (`lib/logger.ts`)

**方案**: 逐文件替换

```typescript
// Before:
console.error('[Admin API] Error:', { endpoint, error });
console.warn('[Admin API] Task health endpoint failed');

// After:
import { Logger } from '@/lib/logger';
const logger = new Logger('AdminAPI');

logger.error('API request failed', { endpoint, error });
logger.warn('Task health endpoint failed, using defaults');
```

**修改文件**:
1. `adminApiClient.ts` — 2 处
2. `_lib/api.ts` — 3 处
3. `analytics/_components/ai/AIInsightsPanel.tsx`
4. `configs/_lib/api.ts`

**工作量**: 1h

---

### C-4. H11: 后端日志格式标准化

**现状**:
- tasks_mgmt.py: `f"[Admin {id}] message"` — 无 `event` 字段，无 `extra`
- overrides.py: 有 `extra` 但无 `event` 字段
- config.py: 有 `f"[Admin {id}]"` 但无 `extra`

**规范格式** (per coding-rules.md):
```python
logger.info(
    "admin.config.updated",
    extra={
        "event": "admin.config.updated",
        "admin_id": admin.get("id"),
        "config_key": key,
        "duration_ms": elapsed
    }
)
```

**方案**: 统一 3 个文件的日志格式

| 文件 | 改动量 |
|------|--------|
| tasks_mgmt.py | ~5 处日志调用 |
| overrides.py | ~3 处 (C7 重构时一并处理) |
| config.py | ~8 处日志调用 |

**工作量**: 2h (overrides 在 A-1 重构时处理)

---

## 集群 E: 架构改善 (5 个问题)

### E-1. H12: RBAC 设计 (方案阶段)

**现状**: 所有 admin 模块仅有 `require_admin` 单一权限检查，无角色区分

**方案**: 设计 RBAC 方案文档 (此阶段不实现)

```
角色定义:
- super_admin: 全部权限 (overrides, billing, system)
- content_admin: 内容管理 (articles, themes, static_pages, moderation)
- support_admin: 用户管理 (users, subscriptions) — 不含 overrides
- analytics_admin: 只读 (stats, metrics, events, logs)

实现方式:
1. admin_roles 表 (admin_user_id, role)
2. @require_role("super_admin") decorator
3. 前端 sidebar 按角色过滤可见菜单
```

**此次输出**: RBAC 设计文档 (存放于 `docs/v3/internal/`)
**工作量**: 4h (设计) — 实现另排期

---

### E-2. M1: 超大前端文件拆分

**Top 5 文件**:
| 文件 | 行数 | 拆分方案 |
|------|------|---------|
| AssetCategoriesPanel.tsx (985) | 3.3x | → Table + Form + Dialog + Hooks |
| MarketplaceModerationPanel.tsx (823) | 2.7x | → List + Detail + Actions + Hooks |
| StaticPagesPanel.tsx (812) | 2.7x | → Table + Editor + Preview + Hooks |
| ArticleEditorDialog.tsx (579) | 1.9x | → Form + Preview + Toolbar + Hooks |
| NotificationCenterPanel.tsx (544) | 1.8x | → List + Form + Preview + Hooks |

**通用拆分模式**:
```
XxxPanel.tsx (800+ lines)
  → _components/xxx/
      ├── XxxPanel.tsx        (组装层, <100 行)
      ├── XxxTable.tsx         (列表/表格)
      ├── XxxForm.tsx          (表单)
      ├── XxxDialog.tsx        (弹窗)
      └── useXxx.ts            (状态/逻辑 Hook)
```

**工作量**: 8h (5 个文件)
**风险**: 🟢 低 (纯前端拆分，不改变功能)

---

### E-3. M3: 乐观锁机制完善

**现状**: Schema 已为 4 张表添加 version 字段 (projects, marketplace_listings, system_configs, experiments)，且有 `p_update_project_with_version` RPC

**方案**:
1. 确认哪些表的 version 字段已在业务代码中使用
2. 对 system_configs 的 batch_update 启用 version 检查 (与 E-4 合并)
3. 关键表 (积分/Tier 相关) 评估是否需要 version

**工作量**: 4h
**依赖**: E-4 (config batch_update)

---

### E-4. M5: config.py batch_update 事务保护

**现状**: `batch_update_configs` 逐个更新，无事务保护，部分失败时数据不一致

**方案**: 使用 Supabase RPC 实现原子操作

```python
# 方案 A: 创建 RPC 函数
CREATE OR REPLACE FUNCTION p_batch_update_configs(
    p_updates jsonb,
    p_admin_id text
) RETURNS jsonb AS $$
BEGIN
    -- 在单个事务中执行所有更新
    FOR item IN SELECT * FROM jsonb_array_elements(p_updates)
    LOOP
        UPDATE system_configs
        SET value = item->>'value',
            updated_by = p_admin_id,
            updated_at = now()
        WHERE config_key = item->>'config_key';
    END LOOP;
    RETURN '{"status": "ok"}'::jsonb;
END;
$$ LANGUAGE plpgsql;
```

```python
# Service 层:
async def batch_update_configs(self, updates: list, admin_id: str) -> dict:
    result = await self._repo.rpc(
        "p_batch_update_configs",
        {"p_updates": updates, "p_admin_id": admin_id}
    )
    return result
```

**修改文件**:
1. Schema: `migrations/v2/01_core_business.sql` — 新增 RPC
2. `domains/platform/config_service.py` — 使用 RPC
3. 测试

**工作量**: 2h

---

### E-5. M6: Stats vs Metrics 功能重叠整理

**重叠点**: `stats/conversion-funnel` 和 `metrics/funnel` 功能相似

**方案**: 明确职责边界 + 文档化 (不删除端点)

```
stats: 聚合仪表板数据 (累计值、快照) — 用于 KPI Dashboard
metrics: 时间序列趋势数据 (日/月粒度) — 用于趋势分析

conversion-funnel (stats): 总体转化率快照
funnel (metrics): 按日期分解的转化趋势
```

**输出**: 在 M4 文档中明确两者职责
**工作量**: 1h (文档) — 如确认完全重复则合并端点

---

## 集群 F: 文档补全

### F-1. M4: 文档覆盖率提升

**需新建 8 份**:
1. campaigns
2. experiments
3. notifications
4. stats + metrics + events (可合并为 analytics)
5. ai_models
6. tasks_mgmt
7. webhooks_retry
8. user_creation_monitoring

**需扩展 6 份**:
1. users (v2→v3)
2. config/tiers/flags (v2→v3)
3. system (v2→v3)
4. themes (v2→v3)
5. articles (v2→v3)
6. static_pages (v2→v3)

**工作量**: 28h (可分散到各模块修复后一起补)

---

## 审计问题修正 (代码验证新发现)

在分析代码过程中发现以下审计问题需要修正:

### H9 描述不准确

**原描述**: "前端约 40 个空 catch 块 — catch (error) {} 或 catch (e) { /* empty */ }"
**实际**: admin 目录仅 15 个 catch 块分布在 8 个文件，**无一是真正的空 catch** (都有 console.warn 或 message.apiError)
**建议**: 修正为 "部分 catch 块仅 console.warn + 静默降级，应改为 Logger + 评估是否通知用户"

### H4 实际范围确认

**原描述中**: "POST /batch-generate 和 GET /generation-status 后端已实现" — 已验证 ✅
**缺失端点确认**: 仅 `GET /batch-generate/preview` 和 `GET /batch-generate/{jobId}` 缺失 — 已验证 ✅

### M3 Schema 已部分实现

**原描述**: "后端更新操作无 version/etag 字段"
**实际**: Schema 已为 projects, marketplace_listings, system_configs, experiments 添加 version 字段
**建议**: 修正为 "version 字段已添加但业务代码未启用乐观锁检查"

---

## 执行检查清单

### Phase 1: 快速修复 (D 集群, ~1 天)
- [ ] D-1: C6 tasks_mgmt await
- [ ] D-2: C4 AI Models 删除占位符
- [ ] D-3: H1 Tier 枚举标准化
- [ ] D-4: H2 subscriptions 补 t3
- [ ] D-5: H4 Themes 子端点实现
- [ ] D-6: H13 在 A-1 中处理
- [ ] `pytest tests/test_app_startup.py -v` 通过
- [ ] `npm run build` 通过

### Phase 2: DDD 迁移 (A 集群, ~3 天)
- [ ] A-1: C7 overrides 全面重构
- [ ] A-2: C10 monitoring DI+限流+脱敏
- [ ] A-3: H3 feature_flags 移除全局
- [ ] A-4: H16 tiers DI 迁移
- [ ] 所有新增代码有测试

### Phase 3: 前后端对齐 (B 集群, ~3 天)
- [ ] B-1: C1 asset_categories slug→id
- [ ] B-2: C2 删除废弃 Tier API
- [ ] B-3: C8 分页参数统一
- [ ] B-4: C11 Articles 新端点
- [ ] B-5: H14 Articles 筛选参数
- [ ] B-6: M7 删除前端 stub
- [ ] 前后端联调通过

### Phase 4: 错误+日志 (C 集群, ~2 天)
- [ ] C-1: H17 错误码系统
- [ ] C-2: H9 catch 块规范化
- [ ] C-3: M2 console→Logger
- [ ] C-4: H11 日志格式统一

### Phase 5: 架构改善 (E 集群, ~1 周)
- [ ] E-1: H12 RBAC 设计文档
- [ ] E-2: M1 文件拆分
- [ ] E-3: M3 乐观锁启用
- [ ] E-4: M5 batch 事务
- [ ] E-5: M6 Stats/Metrics 职责边界

### Phase 6: 文档 (F 集群, 持续)
- [ ] F-1: M4 新建 8 + 扩展 6 份文档

---

**总工作量预估**: ~84h (约 2-3 周)
**文档版本**: v1.2 (二次核实修订)
**日期**: 2026-02-15

**v1.2 更新**:
- D-2 (C4): 前端 `updateAdminModelConfig()` 确认为死代码 (未被任何组件调用)，方案从 ❌ 改为 ⚠️
- A-4 (H16): 恢复 4 处直接实例化 (`get_tier_service` 定义处 + 3 处绕过)，v1.1 改为 3 处有误
- 准确性统计: 13 ✅ / 12 ⚠️ / 0 ❌ (v1.1: 12 ✅ / 12 ⚠️ / 1 ❌)

---

## 附录: 代码核实勘误表 (v1.0 → v1.1 → v1.2)

> 以下修正基于逐文件代码验证，每项标注 ✅ 准确 / ⚠️ 需修正 / ❌ 方案错误

### 集群 D 核实结果

#### D-1 (C6): ✅ 完全准确
L165 `result = service.run_task(task_name)` 确认缺 await，方案无需修改。

#### D-2 (C4): ⚠️ 方案已修正 — 前后端均为死代码 ⚡ *v1.2 再核实*

**v1.1 判断**: ❌ 认为"不能直接删除后端，因前端有调用"
**v1.2 再核实**: 前端 `updateAdminModelConfig()` (api.ts L386-391) 虽然存在，但在整个前端仓库中 **未被任何组件 import 或调用** — 是死代码。后端占位端点同样无实际功能。

**修正方案**: 前后端死代码同时删除 (已更新到主方案 D-2)
1. 后端: 删除 `ai_models.py` L179-184 占位端点
2. 前端: 删除 `analytics/_lib/api.ts` L386-391 的 `updateAdminModelConfig()` 函数
3. ~~前端: 搜索并删除所有调用 `updateAdminModelConfig` 的组件代码~~ → 无调用方，此步无需执行

#### D-3 (H1): ✅ 完全准确
L89 `pattern="^(t1|t2|t3|free|starter|pro)$"` 确认存在，前端已使用系统代码 t1/t2/t3。

#### D-4 (H2): ✅ 完全准确
L75 `VALID_TARGET_TIERS = {"t1", "t2"}` 确认，t4 为预留不需添加。

#### D-5 (H4): ⚠️ 需补充实现细节

方案方向正确，但需补充:
- 需确认 `POST /batch-generate` 返回的 response 是否包含 jobId
- preview 端点需接收参数: `start_date`, `end_date`, `skip_existing` (从前端 api.ts L157-169 推断)
- ThemeService 需新增 `preview_batch_generate()` 和 `get_batch_generate_job_status()` 方法

#### D-6 (H13): ⚠️ 需修正合并策略

**发现**: overrides.py **已使用 Container DI** (`get_container()` L66)，但调用了不存在的 `container.get_supabase_client()` 方法 (Container 只有 `get_async_db_client()`)。

**修正**: H13 分页限制可独立处理，不必等 C7 重构。但需注意:
- 当前 overrides.py L67 的 `container.get_supabase_client()` 是运行时 bug
- 此 bug 应在 C7 重构中一并修复（将直接 DB 访问改为 Repository 层）

---

### 集群 A 核实结果

#### A-1 (C7): ⚠️ 需修正多处描述

**修正 1**: overrides.py 已使用 Container（`from container import get_container`, L18），但绕过 Service/Repository 直接查 DB。方案描述"完全绕过 DDD 架构"仍然成立，但应改为"使用 Container 获取 DB 客户端，但绕过 Service/Repository 层"。

**修正 2**: L67 调用 `container.get_supabase_client()` — Container 中**不存在此方法**（仅有 `get_async_db_client()`）。这是一个**运行时 bug**，端点目前无法正常工作。

**修正 3**: Docstring (L8-9) 声称有 POST 和 DELETE 端点，但代码中完全未实现。重构时需决定: 实现完整 CRUD 还是仅保留实际需要的端点。

**修正 4**: `user_feature_overrides` 表确认存在于 `02_platform_services.sql`，含审计表 `user_feature_override_logs`。重构时应复用现有表结构。

#### A-2 (C10): ✅ 方案准确，补充细节

- L13 `from application.services.user_creation_monitoring import UserCreationMonitoringService` 确认直接导入 ✅
- **0/5** 端点有 rate limiter ✅ (全部无保护)
- `/events` 端点确认返回未脱敏 email ✅
- Container 中**未注册**该 Service — 需同步添加注册

#### A-3 (H3): ⚠️ Rate limiter 数字修正

**修正**: 方案说 "rate limiter 仅 1/9 端点有"，实际是 **0/9**。feature_flags.py 所有 9 个端点均无 rate limiter。方案需补充全部 9 个端点的限流配置。

- 8/9 端点已使用 Container DI ✅ (仅 test_evaluation 用全局 service)
- 全局 `feature_service` 仅用于 test_evaluation (L585)，影响范围有限

#### A-4 (H16): ⚠️ 实例化次数修正 ⚡ *v1.2 再核实*

**v1.1 判断**: "实际 3 处非 4 处，L111-119 是定义函数不算直接实例化"
**v1.2 再核实**: `get_tier_service()` (L111-119) 虽然是函数定义，但其内部 **直接创建** `SupabaseConfigRepository(db)` — 这正是需要修复的目标 (改为从 Container 获取)。因此应算作第 1 处直接实例化，加上 L170-171/L265-266/L353-355 三处绕过该函数的重复创建，**共 4 处直接实例化** — 恢复原方案 v1.0 的计数。

Container **未注册** `get_tier_service()` — 需同步添加。

---

### 集群 B 核实结果

#### B-1 (C1): ⚠️ 需深入调查后确定方向

**核实发现**:
- 后端: `PATCH /{slug}`, `PUT /{slug}/move`, `DELETE /{slug}` — 使用 **slug** 作为路径参数 ✅
- 前端: `updateCategory(token, id, ...)` → `PATCH /asset-categories/${id}` — 传的是变量名叫 "id"
- **额外发现**: 前端 HTTP 方法也有不一致:
  - `updateCategory` 用 **PUT** (前端) vs **PATCH** (后端)
  - `moveCategory` 用 **POST** (前端) vs **PUT** (后端)

**关键问题**: 前端传的 `id` 变量的实际值是什么？如果 category 列表返回中 id 字段就是 slug，那可能只是命名不一致；如果是 UUID，则是功能性 bug。需检查:
1. `GET /asset-categories` 返回的 CategoryResponse 中 id 和 slug 分别是什么
2. 前端从列表中取的是哪个字段

**修正方案**: 暂保留方案方向（后端改 slug→id），但需先确认数据模型中 id 和 slug 的关系，再决定修改方向。同时必须修正 HTTP 方法不一致。

#### B-2 (C2): ✅ 完全准确

补充调用位置: `useUserDetail.ts` L122 调用 `changeUserTier`，需同步修改。

#### B-3 (C8): ⚠️ 数量修正

实际混用 **6+ 处** (方案说 5+):
1. `_lib/api.ts` L42 fetchOperationLogs
2. `_lib/api.ts` L64 fetchErrorLogs
3. `_lib/api.ts` L96 fetchTasks
4. `users/_lib/api.ts` L56 searchUsers
5. `users/_lib/api.ts` L124 getUserProjects
6. `_components/panels/TaskMonitorPanel.tsx` L70-71 (组件状态)

方案方向正确但需确认: 后端这些端点是否真的已统一为 offset/limit？

#### B-4 (C11): ✅ 完全准确

前端调用确认: `checkSlugUnique()` L123, `getArticleStats()` L139。后端无此端点。路由顺序提醒准确。

#### B-5 (H14): ✅ 方向准确，补充细节

- 后端接收: `category, include_drafts, offset, limit` — 确认缺 status/search/sort_by/sort_order
- `include_drafts` 替换为 `status` 合理 ✅
- 补充: search 实现需注意 SQL 注入防护（应用参数化查询）

#### B-6 (M7): ✅ 完全准确

`cancelTask()` L156-162, `retryTask()` L164-170 确认为 stub (仅 console.warn)。需同步检查 UI 是否有绑定按钮。

---

### 集群 C 核实结果

#### C-1 (H17): ⚠️ 需修正 — 现有基础设施已更完善

**发现**:
- `getUserFriendlyMessage()` 已存在于 `lib/errorMessages.ts` L156
- `useMessage` hook L219 **已使用** getUserFriendlyMessage 进行转换
- 组件层通过 `message.apiError(err)` 调用时**已自动转换**

**修正**: 方案中说"getUserFriendlyMessage 未在 adminApiClient 层使用"，但实际上组件层的 `message.apiError()` 已集成了错误转换。方案应调整为:
1. 后端: 仍需建立 `AdminErrorCode` 枚举 (统一错误码)
2. 前端: adminApiClient 层的 catch 可保持现状 (组件层已处理)
3. 主要工作: 后端统一错误码 + 前端错误码映射表扩展

#### C-2 (H9): ✅ 准确

15 个 catch 块，无空 catch。约 6 处仅 console.warn 需改为 Logger。

#### C-3 (M2): ✅ 准确

**精确数量**: 4 个文件 ~13 处 console 调用。Logger 类已存在 (`lib/logger.ts`)。
补充: `adminApiClient.ts` 的 3 处 console 包在 `NODE_ENV === 'development'` 条件中，可选改为 Logger.debug。

#### C-4 (H11): ⚠️ 数字修正

- tasks_mgmt.py: **5 处**日志 ✅ (方案准确)
- config.py: **~18-20 处**日志 ❌ (方案说 8 处，严重低估)
- overrides.py: 2 处日志 (在 A-1 重构中处理)

---

### 集群 E 核实结果

#### E-1 (H12): ⚠️ 已有基础可复用

**发现**:
- `domains/identity/value_objects.py` 已定义 `UserRole` 枚举 (USER/ADMIN)
- `dependencies.py` 的 `require_admin()` 检查 `role == 'admin'`
- 无 `admin_roles` 表或细粒度权限结构

方案补充: 设计时应复用现有 `UserRole` 枚举，扩展为 super_admin/content_admin 等子角色。

#### E-2 (M1): ✅ 完全准确

5 个文件行数全部匹配 (985/823/812/579/544)。

#### E-3 (M3): ⚠️ 需修正描述

Schema 已实现 4 张表的 version 字段 + 1 个 RPC 函数 ✅
**但业务代码完全未启用** — api/admin/ 中无任何调用 version 参数的代码。
修正: "version 字段已添加但业务代码未启用乐观锁检查"

#### E-4 (M5): ⚠️ 需修正实现细节

当前 `batch_update_configs` 确认为**逐条顺序更新，无事务保护** ✅
RPC `p_batch_update_configs` **不存在** — 需新建。
修正: 方案中"使用 Supabase RPC 实现原子操作"方向正确，但需强调 RPC 需从零创建。

#### E-5 (M6): ✅ 准确

- stats 17 个端点, metrics 7 个端点 (含 /refresh)
- 主要重叠: `/stats/conversion-funnel` vs `/metrics/funnel`
- 建议: 明确职责边界或合并其一

---

### 核实总结

| 方案 | 准确性 | 核心修正 |
|------|:---:|---------|
| D-1 C6 | ✅ | — |
| D-2 C4 | ⚠️ | 前端函数存在但为死代码 (未被调用)，前后端同时删除 |
| D-3 H1 | ✅ | — |
| D-4 H2 | ✅ | — |
| D-5 H4 | ⚠️ | 补充前端参数和 Service 方法 |
| D-6 H13 | ⚠️ | 可独立处理，overrides.py 有运行时 bug |
| A-1 C7 | ⚠️ | get_supabase_client 不存在 (运行时 bug)，已部分使用 Container |
| A-2 C10 | ✅ | Container 需添加注册 |
| A-3 H3 | ⚠️ | Rate limiter 0/9 非 1/9 |
| A-4 H16 | ⚠️ | 恢复 4 处 (含 get_tier_service 定义处)，Container 需添加注册 |
| B-1 C1 | ⚠️ | 需先确认 id/slug 关系，HTTP 方法也不一致 |
| B-2 C2 | ✅ | — |
| B-3 C8 | ⚠️ | 6+ 处非 5+ |
| B-4 C11 | ✅ | — |
| B-5 H14 | ✅ | — |
| B-6 M7 | ✅ | — |
| C-1 H17 | ⚠️ | getUserFriendlyMessage 已集成在 useMessage 中 |
| C-2 H9 | ✅ | — |
| C-3 M2 | ✅ | — |
| C-4 H11 | ⚠️ | config.py ~18-20 处非 8 处 |
| E-1 H12 | ⚠️ | 已有 UserRole 枚举可复用 |
| E-2 M1 | ✅ | — |
| E-3 M3 | ⚠️ | Schema 已实现但业务代码未启用 |
| E-4 M5 | ⚠️ | RPC 不存在需新建 |
| E-5 M6 | ✅ | — |

**准确率**: 12/25 完全准确 (48%)，12/25 需小幅修正 (48%)，1/25 方案错误 (4%)
