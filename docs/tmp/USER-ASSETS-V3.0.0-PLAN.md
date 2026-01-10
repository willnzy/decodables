# User Assets API v3.0.0 DDD 重构计划

**创建时间**: 2026-01-10
**目标**: 将 User Assets API 从 v3.25 (⭐⭐⭐ 3星) 升级到 v3.0.0 (⭐⭐⭐⭐⭐ 5星)

---

## 背景

User Assets API v3.25 存在**架构不完整**问题:
- ✅ 已有 Repository 层 (`SupabaseAssetRepository`)
- ❌ **缺少 Service 层** (业务逻辑散落在 API 层)
- ❌ **缺少 Handler 层** (无 CQRS 分离)
- ❌ API 直接调用 Repository (绕过 Service 层)
- ❌ API 层有直接数据库调用 (`supabase.table()`)

**当前评分**: ⭐⭐⭐ (3星) - 架构不完整
**目标评分**: ⭐⭐⭐⭐⭐ (5星) - 完整 DDD 架构

---

## 架构对比

### 现状 (v3.25 - 架构不完整)

```python
# ❌ API 直接调用 Repository (绕过 Service)
@router.get("")
async def my_assets(...):
    assets_repo = SupabaseAssetRepository()
    return await assets_repo.get_assets(user["id"], target_proj)

# ❌ API 直接调用数据库 (绕过所有层)
@router.get("/dashboard")
async def get_asset_dashboard(...):
    supabase = get_supabase_client()
    assets = supabase.table("assets").select("*").eq("user_id", user["id"]).execute()
```

### 目标 (v3.0.0 - 完整 DDD)

```python
# ✅ 完整 DDD 调用链
@router.get("")
async def my_assets(...):
    container = get_container()
    handler = container.get_user_assets_handler

    query = GetUserAssetsQuery(user_id=user["id"], project_id=project_id)
    result = await handler.handle(query)

    return result.assets
```

**调用链**:
```
v3.25: API → Repository (❌ 绕过 Service)
       API → Database (❌ 绕过所有层)

v3.0.0: API → Handler → Service → Repository → Database (✅ 完整 DDD)
```

---

## 10 个 Endpoints 分析

| # | Endpoint | Method | 类型 | 复杂度 | 当前问题 |
|---|----------|--------|------|--------|----------|
| 1 | `GET /assets` | List | Query | 🟢 简单 | 直接调用 Repository |
| 2 | `POST /assets` | Upload | Command | 🔴 复杂 (文件上传) | 直接调用 Repository + Storage |
| 3 | `DELETE /assets/{id}` | Delete | Command | 🟡 中等 (软删除/永久) | 直接调用 Repository |
| 4 | `POST /assets/from-url` | FromURL | Command | 🔴 复杂 (URL验证+SSRF) | 直接调用 Repository |
| 5 | `GET /assets/check-url` | CheckURL | Query | 🟡 中等 (URL验证) | 无 Repository 调用 |
| 6 | `POST /assets/{id}/increment-usage` | IncrementUsage | Command | 🟢 简单 | 直接调用 Repository |
| 7 | `GET /assets/dashboard` | Dashboard | Query | 🟡 中等 (统计) | **直接调用 Database** ❌ |
| 8 | `GET /assets/seller-stats` | SellerStats | Query | 🟡 中等 (统计) | **直接调用 Database** ❌ |
| 9 | `GET /assets/deleted` | ListDeleted | Query | 🟢 简单 | 直接调用 Repository |
| 10 | `POST /assets/{id}/restore` | Restore | Command | 🟢 简单 | 直接调用 Repository |

**分类**:
- **Query Handlers**: 5 个 (Get, CheckURL, Dashboard, SellerStats, ListDeleted)
- **Command Handlers**: 5 个 (Upload, Delete, FromURL, IncrementUsage, Restore)

**关键业务逻辑**:
1. **文件上传**: Pro 权限检查、文件类型验证、大小限制 (5MB)
2. **SSRF 防护**: 私有 IP 过滤、URL 长度限制 (2048)
3. **软删除/永久删除**: 双模式删除
4. **统计聚合**: Dashboard + SellerStats 需要聚合逻辑

---

## 重构方案

### Phase 1: 完善 Repository

**文件**: `infrastructure/repositories/asset_repository.py` (已存在，需完善)

**现状**:
- ✅ 已有基础 CRUD 方法
- ❌ 缺少 Dashboard 统计方法
- ❌ 缺少 SellerStats 统计方法

**新增方法** (2 个):
```python
class SupabaseAssetRepository:
    # 现有方法 (8 个) - 保留
    async def save_asset(...)
    async def get_assets(...)
    async def soft_delete_asset(...)
    async def permanently_hide_asset(...)
    async def increment_asset_usage(...)
    async def get_deleted_assets(...)
    async def restore_asset(...)

    # 新增方法 (2 个)
    async def get_dashboard_stats(user_id: str) -> Dict[str, Any]:
        """Get asset dashboard statistics."""
        # 聚合: total_assets, total_usage, by_source, recent

    async def get_seller_stats(user_id: str) -> Dict[str, Any]:
        """Get seller marketplace statistics."""
        # 聚合: total_listings, total_sales, total_revenue
```

### Phase 2: 创建 Service

**文件**: `domains/assets/assets_service.py` (新建)

**职责**:
- 业务逻辑封装
- 权限检查 (Pro tier for upload)
- 文件验证 (类型、大小)
- SSRF 防护 (URL 安全检查)
- 文件上传到 Storage
- 统计逻辑

**核心方法** (10 个):
```python
class AssetsService:
    def __init__(self, repository: SupabaseAssetRepository, storage_client):
        self.repository = repository
        self.storage = storage_client

    # Query Methods (5)
    async def get_user_assets(user_id: str, project_id: Optional[str]) -> List[Dict]:
        """Get user assets with filters."""

    async def check_url_validity(url: str) -> Dict[str, Any]:
        """Check if URL is valid and points to image."""
        # SSRF check + httpx validation

    async def get_dashboard_stats(user_id: str) -> Dict[str, Any]:
        """Get asset dashboard statistics."""

    async def get_seller_stats(user_id: str) -> Dict[str, Any]:
        """Get seller marketplace statistics."""

    async def get_deleted_assets(user_id: str) -> List[Dict]:
        """Get soft-deleted assets."""

    # Command Methods (5)
    async def upload_asset(
        user_id: str,
        user_tier: str,
        file: UploadFile,
        project_id: Optional[str]
    ) -> Dict[str, Any]:
        """Upload asset with Pro check and file validation."""
        # 1. Check Pro tier
        # 2. Validate file type + size
        # 3. Upload to Storage
        # 4. Save to database

    async def add_asset_from_url(
        user_id: str,
        url: str,
        project_id: Optional[str]
    ) -> Dict[str, Any]:
        """Add asset from external URL with SSRF protection."""
        # 1. Validate URL safety (SSRF)
        # 2. Check URL accessibility
        # 3. Verify content type
        # 4. Save to database

    async def delete_asset(
        asset_id: str,
        user_id: str,
        permanent: bool = False
    ) -> Dict[str, str]:
        """Delete asset (soft or permanent)."""

    async def increment_asset_usage(asset_id: str, user_id: str) -> int:
        """Increment asset usage count."""

    async def restore_asset(asset_id: str, user_id: str) -> Dict[str, Any]:
        """Restore soft-deleted asset."""
```

### Phase 3: 创建 Application Layer

**文件 1**: `application/queries/assets.py` (新建)

5 个 Query Handlers:
```python
# 1. GetUserAssetsQuery/Handler/Result
@dataclass
class GetUserAssetsQuery:
    user_id: str
    project_id: Optional[str] = None
    scope: Optional[str] = None

@dataclass
class GetUserAssetsResult:
    assets: List[Dict[str, Any]]

class GetUserAssetsHandler:
    def __init__(self, service: AssetsService):
        self._service = service

    async def handle(self, query) -> GetUserAssetsResult:
        assets = await self._service.get_user_assets(
            query.user_id,
            query.project_id
        )
        return GetUserAssetsResult(assets=assets)

# 2. CheckURLQuery/Handler/Result
# 3. GetDashboardStatsQuery/Handler/Result
# 4. GetSellerStatsQuery/Handler/Result
# 5. GetDeletedAssetsQuery/Handler/Result
```

**文件 2**: `application/commands/assets.py` (新建)

5 个 Command Handlers:
```python
# Asset Commands (5)
# 1. UploadAssetCommand/Handler/Result
# 2. AddAssetFromURLCommand/Handler/Result
# 3. DeleteAssetCommand/Handler/Result
# 4. IncrementAssetUsageCommand/Handler/Result
# 5. RestoreAssetCommand/Handler/Result
```

### Phase 4: Container 注册

**文件**: `container.py`

11 个注册 (1 Service + 10 Handlers):
```python
# Service
@property
def assets_service(self):
    from domains.assets.assets_service import AssetsService
    from infrastructure.repositories.asset_repository import SupabaseAssetRepository
    from core.database import get_supabase_client
    if 'assets' not in self._services:
        repository = SupabaseAssetRepository(get_database_client())
        storage_client = get_supabase_client()
        self._services['assets'] = AssetsService(repository, storage_client)
    return self._services['assets']

# Query Handlers (5)
@property
def get_user_assets_handler(self): ...

# Command Handlers (5)
@property
def upload_asset_handler(self): ...
```

### Phase 5: API 层重构

**文件**: `api/user/user_assets.py`

重构 10 个 endpoints:
- 移除所有 `SupabaseAssetRepository()` 直接实例化
- 移除所有 `supabase.table()` 直接调用
- 使用 Container + Handler 模式
- 保留所有 v3.25 安全验证 (UUID validation, SSRF protection, rate limiting)
- 版本: v3.25 → v3.0.0
- Router tag: user-assets-v2 → user-assets-v3

---

## 预计工作量

| Phase | 文件 | 改动 | 时间 |
|-------|------|------|------|
| 1 | `infrastructure/repositories/asset_repository.py` | +60 lines (新增2方法) | 15 min |
| 2 | `domains/assets/assets_service.py` | ~400 lines (新建) | 60 min |
| 3 | `application/queries/assets.py` | ~150 lines (新建) | 20 min |
| 3 | `application/commands/assets.py` | ~200 lines (新建) | 25 min |
| 4 | `container.py` | +130 lines | 15 min |
| 5 | `api/user/user_assets.py` | ~250 lines 重构 | 40 min |

**总计**: ~1190 lines, **预计 2.5-3 小时**

---

## 风险评估

**风险等级**: 🟡 **MEDIUM**

**原因**:
1. ❌ 涉及文件上传 (Storage 操作)
2. ❌ 涉及外部 HTTP 请求 (SSRF 风险)
3. ❌ 有直接数据库调用需要迁移
4. ✅ 有现成 Repository 可复用

**降低风险策略**:
1. 保留所有 v3.25 安全验证逻辑
2. Storage 逻辑迁移到 Service 层但保持不变
3. SSRF 防护函数迁移到 Service 层
4. 分阶段重构,每个 Phase 独立测试

---

## 成功标准

✅ 所有 10 个 endpoints 使用 Handler pattern
✅ 完整 DDD 调用链 (API → Handler → Service → Repository)
✅ 消除所有 `supabase.table()` 直接调用
✅ 业务逻辑封装在 Service 层
✅ 所有 v3.25 安全验证保留 (SSRF, UUID, rate limiting)
✅ 无 Breaking Changes (API 接口兼容)

---

## 完成后成果

**进度**: 24/24 modules (100%) 🎉🎉🎉
**评级**: 所有 24 个模块全部达到 ⭐⭐⭐⭐⭐ 五星标准！

准备好后即可开始实施。
