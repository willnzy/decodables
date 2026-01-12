# Supabase AsyncClient 完全迁移计划 (方案 B)

> **目标**: 将所有同步 Supabase 调用迁移到原生异步 AsyncClient
> **预计时间**: 2-3 天
> **状态**: 📋 规划中
> **创建日期**: 2026-01-13

---

## 📊 当前状态分析

### 影响范围统计

| 类型 | 数量 | 说明 |
|------|------|------|
| Repository 文件 | 31 个 | 所有数据访问层需要重构 |
| Supabase 调用点 | 326+ 处 | 需要移除 `run_in_threadpool` |
| 客户端初始化 | 7 处 | 需要改用 `acreate_client` |
| API 路由文件 | ~50 个 | 需要使用依赖注入 |
| 已修复文件 | 1 个 | `user_repository.py` (已包装 threadpool) |

### 当前问题

1. **同步客户端**: 使用 `create_client()` 创建同步客户端
2. **线程池包装**: 每个 DB 调用需要 `run_in_threadpool()` 包装
3. **代码臃肿**: 326+ 处需要 lambda 包装
4. **性能开销**: 频繁线程切换影响性能
5. **易错**: 新代码容易忘记包装

### 目标收益

| 指标 | 当前 | 目标 | 改善 |
|------|------|------|------|
| 代码行数 | +30% (lambda 包装) | 基准 | 减少 30% |
| 性能 | 有线程池开销 | 原生异步 | 提升 20-50% |
| 可维护性 | 易错、臃肿 | 简洁、安全 | ⭐⭐⭐⭐⭐ |
| 符合最佳实践 | ❌ | ✅ | ✅ |

---

## 🎯 执行计划

### Phase 1: 创建异步客户端基础设施 (1-2 小时)

#### 1.1 升级 `core/database/client.py`

**文件**: `core/database/client.py`

**变更点**:

1. **添加 AsyncClient 类型支持** (Line 11-18)
   ```python
   from typing import Union
   if TYPE_CHECKING:
       from supabase import Client as SupabaseClient
       from supabase._async.client import AsyncClient
       DatabaseClient = Union[SupabaseClient, AsyncClient]
   ```

2. **创建异步客户端函数** (新增，Line 87+)
   ```python
   _async_db_client: Optional[Any] = None

   async def get_async_db_client(config: DatabaseConfig = None) -> Optional[Any]:
       """Get async database client."""
       global _async_db_client, _config

       if _async_db_client is not None:
           return _async_db_client

       cfg = config or DatabaseConfig.from_env()
       if not cfg.is_valid:
           logger.warning("[DB] Database not initialized")
           return None

       try:
           from supabase import acreate_client
           _async_db_client = await acreate_client(cfg.url, cfg.key)
           _config = cfg
           logger.info("[DB] Async database client initialized")
           return _async_db_client
       except Exception as e:
           logger.error(f"[DB] Failed to initialize async client: {e}")
           return None
   ```

3. **添加清理函数** (新增)
   ```python
   async def close_async_db_client():
       """Close async database client (for graceful shutdown)."""
       global _async_db_client
       _async_db_client = None
       logger.info("[DB] Async database client closed")
   ```

**影响文件**: 1 个
**新增代码**: ~50 行
**删除代码**: 0 行

#### 1.2 更新 `core/database/__init__.py`

**文件**: `core/database/__init__.py`

**变更点**:

1. **导出异步客户端函数** (Line 25-30)
   ```python
   from .client import (
       get_db_client,
       get_async_db_client,      # 新增
       close_async_db_client,    # 新增
       # ... 其他
   )
   ```

2. **更新 __all__** (Line 50-58)
   ```python
   __all__ = [
       'get_db_client',
       'get_async_db_client',    # 新增
       'close_async_db_client',  # 新增
       # ... 其他
   ]
   ```

**影响文件**: 1 个
**新增代码**: ~5 行
**删除代码**: 0 行

**✅ Phase 1 完成标志**:
- `get_async_db_client()` 可以成功创建 AsyncClient
- 运行测试脚本验证功能

---

### Phase 2: 创建 FastAPI 依赖注入模块 (30 分钟)

#### 2.1 创建 `core/database/dependencies.py`

**新文件**: `core/database/dependencies.py`

**完整内容**:

```python
"""
FastAPI Dependencies for Database Access.

Provides dependency injection for async Supabase client.
Following FastAPI best practices for database connections.

@module core.database.dependencies
@version 1.0.0
"""

from typing import AsyncGenerator
from fastapi import Depends

from .client import get_async_db_client, DatabaseClient

# ============================================================================
# Global Async Client (Application-Level)
# ============================================================================

_global_async_client: DatabaseClient = None

async def init_global_async_client():
    """
    Initialize global async client at application startup.

    This should be called in FastAPI's lifespan event:

    ```python
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_global_async_client()
        yield
        await close_global_async_client()
    ```
    """
    global _global_async_client
    if _global_async_client is None:
        _global_async_client = await get_async_db_client()
    return _global_async_client

async def close_global_async_client():
    """Close global async client at application shutdown."""
    global _global_async_client
    # Supabase AsyncClient doesn't need explicit cleanup
    _global_async_client = None

# ============================================================================
# FastAPI Dependency Functions
# ============================================================================

async def get_async_db() -> DatabaseClient:
    """
    FastAPI dependency for async database client.

    Returns the global async client (recommended for most cases).

    Usage:
        @router.get("/users")
        async def list_users(db: DatabaseClient = Depends(get_async_db)):
            result = await db.table("users").select("*").execute()
            return result.data

    Performance:
        - Reuses global client (no overhead per request)
        - Native async operations (no threadpool)
    """
    if _global_async_client is None:
        await init_global_async_client()
    return _global_async_client

# ============================================================================
# Optional: Per-Request Client (Advanced Use Cases)
# ============================================================================

async def get_async_db_per_request() -> AsyncGenerator[DatabaseClient, None]:
    """
    Per-request async client (creates new client for each request).

    Only use this if you need user-specific RLS tokens or per-request isolation.
    For most cases, use get_async_db() instead (better performance).

    Usage:
        @router.get("/private-data")
        async def get_private_data(
            db: DatabaseClient = Depends(get_async_db_per_request),
            user: dict = Depends(get_current_user)
        ):
            # Use db with user-specific token
            result = await db.table("private").select("*").execute()
            return result.data
    """
    client = await get_async_db_client()
    try:
        yield client
    finally:
        # Cleanup if needed (Supabase client doesn't need explicit cleanup)
        pass
```

**影响文件**: 1 个 (新建)
**新增代码**: ~100 行

#### 2.2 更新 `core/database/__init__.py` (补充)

**新增导出**:

```python
from .dependencies import (
    get_async_db,
    init_global_async_client,
    close_global_async_client,
)

__all__ = [
    # ... 已有的
    'get_async_db',
    'init_global_async_client',
    'close_global_async_client',
]
```

**✅ Phase 2 完成标志**:
- `get_async_db()` 依赖注入可用
- 在 API endpoint 中可以成功注入

---

### Phase 3: 修改应用启动配置 (15 分钟)

#### 3.1 更新 `main.py`

**文件**: `main.py`

**变更点**:

1. **导入依赖** (顶部)
   ```python
   from contextlib import asynccontextmanager
   from core.database.dependencies import (
       init_global_async_client,
       close_global_async_client
   )
   ```

2. **创建 lifespan 管理** (替换现有 startup/shutdown)
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       """
       Application lifespan events.

       Startup:
           - Initialize async database client

       Shutdown:
           - Close async database client
       """
       # Startup
       logger.info("🚀 Application starting up...")

       # Initialize async DB client
       await init_global_async_client()
       logger.info("✅ Async database client initialized")

       yield

       # Shutdown
       logger.info("🔄 Application shutting down...")
       await close_global_async_client()
       logger.info("✅ Async database client closed")
   ```

3. **应用 lifespan** (修改 FastAPI 初始化)
   ```python
   app = FastAPI(
       title="Decodables API",
       version="2.0.0",
       lifespan=lifespan  # 新增
   )
   ```

**影响文件**: 1 个
**新增代码**: ~20 行
**删除代码**: ~10 行 (旧的 startup/shutdown events)

**✅ Phase 3 完成标志**:
- 应用启动时日志显示 "Async database client initialized"
- 应用关闭时正常清理

---

### Phase 4: 重构 BaseRepository (30 分钟)

#### 4.1 修改 `infrastructure/repositories/base_repository.py`

**文件**: `infrastructure/repositories/base_repository.py`

**当前代码** (Line 40-55):
```python
from core.database import get_supabase_client

class BaseRepository:
    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()  # 同步
        return self._client
```

**重构为**:
```python
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from supabase._async.client import AsyncClient

class BaseRepository:
    """
    Base repository for data access.

    Now uses AsyncClient exclusively. Repositories MUST be initialized
    with an async client (typically via dependency injection).
    """

    def __init__(self, client: Optional['AsyncClient'] = None):
        """
        Initialize repository with async Supabase client.

        Args:
            client: AsyncClient instance (should be injected via FastAPI Depends)

        Raises:
            RuntimeError: If client is None and accessed via property
        """
        self._client = client

    @property
    def client(self) -> 'AsyncClient':
        """
        Get async Supabase client.

        Raises:
            RuntimeError: If client was not injected (not initialized properly)
        """
        if self._client is None:
            raise RuntimeError(
                "Repository not initialized with async client. "
                "Repositories should be created via dependency injection:\n"
                "  repo = Depends(get_user_repo)\n"
                "See: core/database/dependencies.py"
            )
        return self._client

    # ... 其他方法保持不变 (exists, soft_delete, hard_delete 等)
```

**影响文件**: 1 个
**新增代码**: ~15 行
**修改代码**: ~10 行

**⚠️ 重要**: 这会导致所有 Repository 必须通过依赖注入创建

**✅ Phase 4 完成标志**:
- BaseRepository 只接受 AsyncClient
- 直接实例化 Repository 会抛出明确错误

---

### Phase 5: 重构 user_repository.py (1 小时)

#### 5.1 移除所有 `run_in_threadpool` 包装

**文件**: `infrastructure/repositories/user_repository.py`

**重构策略**: 批量替换

**查找模式**:
```python
result = await run_in_threadpool(
    lambda: self.client.table(...).execute()
)
```

**替换为**:
```python
result = await self.client.table(...).execute()
```

**具体修改点** (20+ 处):

1. **Line 43-45**: `get_by_id()`
   ```python
   # Before
   result = await run_in_threadpool(
       lambda: self.client.table("profiles").select("*").eq("id", user_id).single().execute()
   )

   # After
   result = await self.client.table("profiles").select("*").eq("id", user_id).single().execute()
   ```

2. **Line 59-61**: `get_by_email()`
   ```python
   # Before
   result = await run_in_threadpool(
       lambda: self.client.table("profiles").select("*").eq("email", email).single().execute()
   )

   # After
   result = await self.client.table("profiles").select("*").eq("email", email).single().execute()
   ```

3. **Line 76-78**: `save()`
4. **Line 94-96**: `create()`
5. **Line 110-112**: `update()`
6. **Line 142-144**: `get_by_tier()`
7. **Line 158-160**: `get_users_needing_onboarding()`
8. **Line 183-185**: `update_tier()`
9. **Line 205-210**: `update_onboarding_step()`
10. **Line 270-272**: `get_profile()`
11. **Line 370-372**: `create_profile()`
12. **Line 405-407**: `update_subscription_tier()`
13. **Line 447-449**: `update_profile()`
14. **Line 464-466**: `update_timezone()`
15. **Line 482-484**: `get_timezone()`
16. **Line 500-504**: `search_users()`
17. **Line 521-523**: `get_users_by_tier()`
18. **Line 541-551**: `get_user_discount()` (使用辅助函数)
19. **Line 576-583**: `create_user_discount()`
20. **Line 597-602**: `mark_discount_used()`
21. **Line 618-622**: `update_monthly_credits()`

#### 5.2 移除 `run_in_threadpool` 导入

**Line 15**: 删除
```python
from fastapi.concurrency import run_in_threadpool  # 删除这行
```

**影响文件**: 1 个
**新增代码**: 0 行
**删除代码**: ~30 行 (所有 lambda 包装)
**净减少**: 30 行

**✅ Phase 5 完成标志**:
- `user_repository.py` 不再包含 `run_in_threadpool`
- 所有方法直接 await Supabase 调用
- 代码更简洁（减少 30 行）

---

### Phase 6: 重构其他核心 Repositories (2-3 小时)

#### 6.1 优先级排序

**P0 - 核心业务** (必须完成):
1. `project_repository.py` - 项目管理
2. `asset_repository.py` - 素材管理
3. `credit_repository.py` - 积分系统
4. `article_repository.py` - 文章系统

**P1 - 重要功能** (高优先级):
5. `listing_repository.py` - 商品列表
6. `feature_flag_repository.py` - Feature Flag
7. `notification_repository.py` - 通知
8. `experiment_repository.py` - 实验系统

**P2 - 辅助功能** (中优先级):
9. `category_repository_impl.py` - 分类管理
10. `templates_repository.py` - 模板管理
11. `campaign_repository.py` - 活动管理
12. `themes_repository.py` - 主题管理
13. `support_repository.py` - 客服系统
14. `admin_repository.py` - 管理员功能

**P3 - 其他** (低优先级):
15-31. 其余 17 个 repositories

#### 6.2 重构模式

**每个 Repository 的标准流程**:

1. **查找所有 Supabase 调用**
   ```bash
   grep -n "self.client.table\|self.supabase.table\|self.db.table" <file>
   ```

2. **移除 threadpool 包装**
   - 查找: `await run_in_threadpool(`
   - 替换: 移除包装，保留内部调用

3. **更新导入**
   - 移除: `from fastapi.concurrency import run_in_threadpool`
   - 检查是否需要添加类型提示

4. **测试验证**
   - 运行相关测试
   - 检查是否有遗漏

**预估时间**:
- P0 repositories (4个): 1 小时
- P1 repositories (4个): 45 分钟
- P2 repositories (6个): 45 分钟
- P3 repositories (17个): 30 分钟

**批量处理脚本** (可选):

```python
# scripts/tools/migrate_to_async_client.py
import re
from pathlib import Path

def remove_threadpool_wrapper(content: str) -> str:
    """Remove run_in_threadpool wrapper from code."""
    # Pattern: await run_in_threadpool(lambda: ...)
    pattern = r'await run_in_threadpool\(\s*lambda:\s*([^)]+)\)'
    replacement = r'await \1'
    return re.sub(pattern, replacement, content)

def process_repository(file_path: Path):
    """Process single repository file."""
    content = file_path.read_text()

    # Remove threadpool wrappers
    new_content = remove_threadpool_wrapper(content)

    # Remove import if no longer used
    if 'run_in_threadpool' not in new_content:
        new_content = re.sub(
            r'from fastapi\.concurrency import run_in_threadpool\n',
            '',
            new_content
        )

    # Write back
    if new_content != content:
        file_path.write_text(new_content)
        print(f"✅ Updated: {file_path.name}")
        return True
    return False

# Usage
repos_dir = Path("infrastructure/repositories")
for py_file in repos_dir.glob("*_repository.py"):
    process_repository(py_file)
```

**✅ Phase 6 完成标志**:
- 所有 P0-P2 repositories 完成迁移
- P3 repositories 可以逐步迁移
- 无 `run_in_threadpool` 残留

---

### Phase 7: 创建 Repository 依赖注入 (1 小时)

#### 7.1 创建 `infrastructure/repositories/dependencies.py`

**新文件**: `infrastructure/repositories/dependencies.py`

**完整内容**:

```python
"""
Repository Dependency Injection for FastAPI.

Provides dependency injection functions for all repositories.
All repositories are initialized with async Supabase client.

@module infrastructure.repositories.dependencies
@version 1.0.0
"""

from fastapi import Depends

from core.database.dependencies import get_async_db
from core.database.client import DatabaseClient

# Import all repositories
from .user_repository import SupabaseUserRepository
from .project_repository import SupabaseProjectRepository
from .asset_repository import SupabaseAssetRepository
from .credit_repository import SupabaseCreditRepository
from .article_repository import SupabaseArticleRepository
from .listing_repository import SupabaseListingRepository
from .feature_flag_repository import SupabaseFeatureFlagRepository
from .notification_repository import SupabaseNotificationRepository
from .experiment_repository import SupabaseExperimentRepository
# ... 其他 repositories

# ============================================================================
# Core Business Repositories
# ============================================================================

async def get_user_repo(
    db: DatabaseClient = Depends(get_async_db)
) -> SupabaseUserRepository:
    """Get user repository with async client."""
    return SupabaseUserRepository(client=db)

async def get_project_repo(
    db: DatabaseClient = Depends(get_async_db)
) -> SupabaseProjectRepository:
    """Get project repository with async client."""
    return SupabaseProjectRepository(client=db)

async def get_asset_repo(
    db: DatabaseClient = Depends(get_async_db)
) -> SupabaseAssetRepository:
    """Get asset repository with async client."""
    return SupabaseAssetRepository(client=db)

async def get_credit_repo(
    db: DatabaseClient = Depends(get_async_db)
) -> SupabaseCreditRepository:
    """Get credit repository with async client."""
    return SupabaseCreditRepository(client=db)

async def get_article_repo(
    db: DatabaseClient = Depends(get_async_db)
) -> SupabaseArticleRepository:
    """Get article repository with async client."""
    return SupabaseArticleRepository(client=db)

# ============================================================================
# Platform Service Repositories
# ============================================================================

async def get_listing_repo(
    db: DatabaseClient = Depends(get_async_db)
) -> SupabaseListingRepository:
    """Get listing repository with async client."""
    return SupabaseListingRepository(client=db)

async def get_feature_flag_repo(
    db: DatabaseClient = Depends(get_async_db)
) -> SupabaseFeatureFlagRepository:
    """Get feature flag repository with async client."""
    return SupabaseFeatureFlagRepository(client=db)

async def get_notification_repo(
    db: DatabaseClient = Depends(get_async_db)
) -> SupabaseNotificationRepository:
    """Get notification repository with async client."""
    return SupabaseNotificationRepository(client=db)

async def get_experiment_repo(
    db: DatabaseClient = Depends(get_async_db)
) -> SupabaseExperimentRepository:
    """Get experiment repository with async client."""
    return SupabaseExperimentRepository(client=db)

# ... 其他 repositories
```

**影响文件**: 1 个 (新建)
**新增代码**: ~150 行

#### 7.2 更新 API 路由层

**示例**: `api/user/users.py`

**Before**:
```python
from domains.identity.user_service import UserService
from infrastructure.repositories.user_repository import SupabaseUserRepository

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    # 创建 repository (使用全局同步客户端)
    repo = SupabaseUserRepository()
    service = UserService(repo)
    profile = await service.get_user_profile(current_user["id"])
    return profile
```

**After**:
```python
from domains.identity.user_service import UserService
from infrastructure.repositories.dependencies import get_user_repo
from infrastructure.repositories.user_repository import SupabaseUserRepository

@router.get("/profile")
async def get_profile(
    current_user: dict = Depends(get_current_user),
    user_repo: SupabaseUserRepository = Depends(get_user_repo)  # 依赖注入
):
    service = UserService(user_repo)
    profile = await service.get_user_profile(current_user["id"])
    return profile
```

**需要更新的 API 文件** (~50 个):

**User API**:
- `api/user/users.py`
- `api/user/projects.py`
- `api/user/assets.py`
- `api/user/credits.py`
- `api/user/articles.py`
- `api/user/marketplace.py`
- ... (15+ 个)

**Admin API**:
- `api/admin/users.py`
- `api/admin/projects.py`
- `api/admin/feature_flags.py`
- `api/admin/experiments.py`
- ... (20+ 个)

**Webhooks**:
- `api/user/webhooks.py` (Stripe/Clerk webhooks)

**预估时间**: 1-1.5 小时

**✅ Phase 7 完成标志**:
- 所有 API endpoint 使用依赖注入
- 无直接实例化 Repository

---

### Phase 8: 全面测试 + 部署验证 (2 小时)

#### 8.1 单元测试

**更新测试 fixtures**:

**文件**: `tests/conftest.py`

```python
import pytest
import asyncio
from supabase import acreate_client

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_db_client():
    """Create async Supabase client for testing."""
    from core.database.client import DatabaseConfig

    config = DatabaseConfig.from_env()
    client = await acreate_client(config.url, config.key)

    yield client

    # Cleanup (Supabase client doesn't need explicit cleanup)

@pytest.fixture
async def user_repo(async_db_client):
    """Create user repository with async client."""
    from infrastructure.repositories.user_repository import SupabaseUserRepository
    return SupabaseUserRepository(client=async_db_client)
```

**运行测试**:
```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块
pytest tests/domains/identity/test_user_repository.py -v
pytest tests/api/user/test_users.py -v
```

#### 8.2 集成测试

**关键测试场景**:

1. **用户认证流程**
   - [ ] 用户注册
   - [ ] 用户登录
   - [ ] 获取用户信息

2. **项目管理**
   - [ ] 创建项目
   - [ ] 更新项目
   - [ ] 删除项目

3. **积分系统**
   - [ ] 扣除积分
   - [ ] 充值积分
   - [ ] 查询积分余额

4. **文章系统**
   - [ ] 获取文章列表
   - [ ] 获取文章详情
   - [ ] 获取相关文章

#### 8.3 性能基准测试

**创建性能测试脚本**:

**文件**: `scripts/benchmark_async_vs_sync.py`

```python
import asyncio
import time
from supabase import create_client, acreate_client
from core.database.client import DatabaseConfig
from fastapi.concurrency import run_in_threadpool

async def benchmark():
    config = DatabaseConfig.from_env()

    # Sync client (old way)
    sync_client = create_client(config.url, config.key)

    # Async client (new way)
    async_client = await acreate_client(config.url, config.key)

    # Test 1: Simple select (100 queries)
    print("\n📊 Test 1: Simple Select (100 queries)")

    # Sync + threadpool
    start = time.time()
    for _ in range(100):
        await run_in_threadpool(
            lambda: sync_client.table("profiles").select("id").limit(1).execute()
        )
    sync_time = time.time() - start
    print(f"  Sync + threadpool: {sync_time:.3f}s")

    # Async
    start = time.time()
    for _ in range(100):
        await async_client.table("profiles").select("id").limit(1).execute()
    async_time = time.time() - start
    print(f"  Pure async:        {async_time:.3f}s")
    print(f"  ⚡ Speedup:        {sync_time/async_time:.2f}x")

    # Test 2: Concurrent queries (10 parallel)
    print("\n📊 Test 2: Concurrent Queries (10 parallel)")

    # Sync + threadpool
    start = time.time()
    await asyncio.gather(*[
        run_in_threadpool(
            lambda: sync_client.table("profiles").select("id").limit(10).execute()
        ) for _ in range(10)
    ])
    sync_time = time.time() - start
    print(f"  Sync + threadpool: {sync_time:.3f}s")

    # Async
    start = time.time()
    await asyncio.gather(*[
        async_client.table("profiles").select("id").limit(10).execute()
        for _ in range(10)
    ])
    async_time = time.time() - start
    print(f"  Pure async:        {async_time:.3f}s")
    print(f"  ⚡ Speedup:        {sync_time/async_time:.2f}x")

if __name__ == "__main__":
    asyncio.run(benchmark())
```

**运行基准测试**:
```bash
python scripts/benchmark_async_vs_sync.py
```

**预期结果**:
- Simple select: 1.5-2x 加速
- Concurrent queries: 2-3x 加速

#### 8.4 Staging 部署验证

1. **本地验证**
   ```bash
   # 启动开发服务器
   uvicorn main:app --reload

   # 测试关键 endpoints
   curl http://localhost:8000/api/v2/user/profile
   curl http://localhost:8000/api/v2/user/articles
   curl http://localhost:8000/api/v2/user/projects
   ```

2. **部署到 Railway Staging**
   ```bash
   git add .
   git commit -m "refactor: migrate to Supabase AsyncClient (complete)"
   git push origin develop
   ```

3. **监控日志**
   - 检查启动日志："Async database client initialized"
   - 确认无错误
   - 监控性能指标

4. **功能回归测试**
   - Manual 页面显示文章
   - 用户登录/注册
   - 项目创建/编辑
   - 积分扣除/充值

**✅ Phase 8 完成标志**:
- 所有测试通过
- Staging 环境稳定运行
- 性能提升符合预期

---

## 📋 文件清单

### 需要修改的文件 (6个)

| 文件 | 类型 | 变更 | 行数变化 |
|------|------|------|----------|
| `core/database/client.py` | 修改 | 新增异步客户端 | +50 |
| `core/database/__init__.py` | 修改 | 导出异步函数 | +5 |
| `infrastructure/repositories/base_repository.py` | 修改 | AsyncClient only | +15/-10 |
| `main.py` | 修改 | lifespan 管理 | +20/-10 |
| `tests/conftest.py` | 修改 | 异步 fixtures | +15 |
| `requirements.txt` | 修改 | 确保版本 | +0 |

### 需要创建的文件 (2个)

| 文件 | 类型 | 说明 | 行数 |
|------|------|------|------|
| `core/database/dependencies.py` | 新建 | FastAPI 依赖注入 | ~100 |
| `infrastructure/repositories/dependencies.py` | 新建 | Repository 工厂 | ~150 |

### 需要重构的文件 (31个)

**所有 Repository 文件** (`infrastructure/repositories/*_repository.py`):
- 移除 `run_in_threadpool` 包装
- 直接 await Supabase 调用
- 净减少 ~30-50% 代码量

**所有 API 路由文件** (`api/user/*.py`, `api/admin/*.py`):
- 使用依赖注入
- 替换直接实例化

### 需要删除的代码模式

**全局查找并替换**:
```bash
# 查找所有需要修改的地方
grep -r "await run_in_threadpool(" infrastructure/repositories/

# 查找所有直接实例化 Repository 的地方
grep -r "Repository()" api/

# 查找导入 run_in_threadpool
grep -r "from fastapi.concurrency import run_in_threadpool" infrastructure/
```

---

## 🎯 验收标准

### 代码质量

- [ ] 所有 Repository 使用 AsyncClient
- [ ] 无 `run_in_threadpool` 残留
- [ ] 所有 API 使用依赖注入
- [ ] 类型提示完整

### 功能完整性

- [ ] 用户认证流程正常
- [ ] 项目 CRUD 正常
- [ ] 积分系统正常
- [ ] 文章系统正常
- [ ] 商品列表正常
- [ ] Feature Flag 正常

### 性能指标

- [ ] Simple query 提升 1.5x+
- [ ] Concurrent query 提升 2x+
- [ ] 无明显性能回退

### 稳定性

- [ ] Staging 运行 24 小时无错误
- [ ] 所有测试通过
- [ ] 监控指标正常

---

## ⚠️ 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 遗漏 Repository | 运行时错误 | 中 | 全局搜索验证 |
| API 未更新依赖注入 | 运行时错误 | 中 | 逐个文件检查 |
| 测试覆盖不足 | 潜在 bug | 低 | 补充集成测试 |
| 性能回退 | 用户体验 | 低 | 基准测试验证 |
| 部署失败 | 服务中断 | 低 | 分阶段部署 |

---

## 📅 时间估算

| Phase | 任务 | 预计时间 |
|-------|------|----------|
| Phase 1 | 异步客户端基础 | 1-2 小时 |
| Phase 2 | 依赖注入模块 | 30 分钟 |
| Phase 3 | 应用启动配置 | 15 分钟 |
| Phase 4 | BaseRepository | 30 分钟 |
| Phase 5 | user_repository | 1 小时 |
| Phase 6 | 其他 repositories | 2-3 小时 |
| Phase 7 | API 依赖注入 | 1-1.5 小时 |
| Phase 8 | 测试 + 部署 | 2 小时 |
| **总计** | - | **8-11 小时** |

**建议分配**:
- Day 1: Phase 1-5 (核心重构)
- Day 2: Phase 6-7 (批量迁移)
- Day 3: Phase 8 (测试 + 部署)

---

## 🚀 开始执行

准备好后，按以下顺序执行：

1. ✅ 阅读并确认本计划
2. ✅ 备份当前代码 (git commit)
3. ✅ 创建新分支 `feature/async-client-migration`
4. 🚀 开始 Phase 1

**执行前确认**:
- [ ] 已理解完整方案
- [ ] 已备份代码
- [ ] 已创建新分支
- [ ] 准备好足够时间（2-3 天）

---

**文档版本**: 1.0
**创建日期**: 2026-01-13
**预计完成**: 2026-01-15
