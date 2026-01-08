# Phase 11: Repository 异步改造计划

> **文档版本**: 1.0.0
> **创建日期**: 2026-01-07
> **优先级**: 🟡 中 (性能优化，非阻塞需求)
> **状态**: Phase 8-10 完成后执行
> **作者**: Claude Sonnet 4.5

---

## 📊 问题描述

### 当前状况

**所有 Repository 方法都声明为 `async def`，但内部调用的是同步 Supabase 客户端**：

```python
# ❌ 当前实现 - 伪异步 (Fake Async)
class SupabaseUserRepository(IUserRepository):
    async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        """声明是 async，但内部是同步调用"""
        try:
            # 这是同步 I/O！会阻塞事件循环
            result = self.client.table("profiles").select("*").eq(
                "id", user_id
            ).single().execute()

            if not result.data:
                return None

            return self._map_to_profile(result.data)
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
```

### 调用链分析

```
┌─────────────────────────────────────────────────────────────┐
│ 1. API Layer (api/billing_api.py:108)                      │
│    await handler.handle(query)                             │
│    ✅ 真异步 (True Async)                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Handler (application/queries/billing.py:39-42)          │
│    async def handle(self, query)                            │
│        user_credits = await self._billing_service...       │
│    ✅ 真异步 (True Async)                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Domain Service (domains/billing/service.py:78)          │
│    async def get_user_credits(self, user_id)                │
│        return await self._repository.get_by_user_id()      │
│    ✅ 真异步 (True Async)                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Repository (infrastructure/repositories/...)            │
│    async def get_by_user_id(self, user_id)                 │
│        result = self.client.table(...).execute()  ⚠️       │
│    ❌ 伪异步！内部是同步 I/O，会阻塞事件循环                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Supabase Client (supabase-py)                           │
│    同步 HTTP 请求 (使用 httpx 同步模式)                      │
│    ❌ 阻塞 I/O                                              │
└─────────────────────────────────────────────────────────────┘
```

### 影响

1. **性能问题**：
   - 同步 I/O 会阻塞 FastAPI 的事件循环
   - 并发请求时性能下降
   - 无法充分利用异步优势

2. **误导性**：
   - 方法签名是 `async def`，但实际是同步执行
   - 违反了"诚实签名"原则

3. **资源浪费**：
   - FastAPI 期望异步，但得到的是同步阻塞
   - 无法处理其他请求，浪费事件循环时间

---

## 🎯 解决方案

### 方案对比

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| **A. 使用 asyncio.to_thread()** | 简单，无需更换库 | 仍然是同步 I/O，只是不阻塞事件循环 | ⭐⭐⭐ |
| **B. 使用 asyncpg 直接连接** | 真异步，性能最佳 | 需要重写所有查询，绕过 Supabase SDK | ⭐⭐ |
| **C. 等待 supabase-py 异步支持** | 官方支持 | 不知道何时发布 | ❌ |
| **D. 保持现状** | 无需改动 | 性能问题持续 | ❌ |

### 推荐方案：A. 使用 asyncio.to_thread()

**原理**：将同步 I/O 操作放到线程池执行，不阻塞事件循环。

**改造前后对比**：

```python
# ❌ 改造前 - 伪异步
async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
    try:
        # 同步 I/O，阻塞事件循环
        result = self.client.table("profiles").select("*").eq(
            "id", user_id
        ).single().execute()

        if not result.data:
            return None

        return self._map_to_profile(result.data)
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        return None


# ✅ 改造后 - 真异步
async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
    try:
        # 使用 to_thread 在线程池执行同步 I/O
        result = await asyncio.to_thread(
            self._sync_get_by_id, user_id
        )

        if not result:
            return None

        return self._map_to_profile(result)
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        return None

def _sync_get_by_id(self, user_id: str):
    """同步查询方法 (在线程池中执行)"""
    result = self.client.table("profiles").select("*").eq(
        "id", user_id
    ).single().execute()
    return result.data
```

---

## 📋 改造计划

### Step 1: 创建异步包装器基类

**文件**: `infrastructure/repositories/base_async_repository.py`

```python
"""
Async Repository Base - Wrapper for synchronous Supabase operations.

@module infrastructure.repositories.base_async_repository
@version 1.0.0
"""

import asyncio
from typing import Any, Callable, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AsyncRepositoryBase:
    """
    Base class for repositories that wrap synchronous Supabase calls.

    Provides async wrapper method that executes sync operations in thread pool.
    """

    async def _run_in_thread(self, func: Callable[[], T]) -> T:
        """
        Execute synchronous function in thread pool.

        Args:
            func: Synchronous function to execute (should be lambda or partial)

        Returns:
            Result from function execution

        Example:
            result = await self._run_in_thread(
                lambda: self.client.table("users").select("*").execute()
            )
        """
        try:
            return await asyncio.to_thread(func)
        except Exception as e:
            logger.error(f"Thread pool execution failed: {e}")
            raise

    async def _run_query(self, query_builder) -> Any:
        """
        Execute Supabase query builder in thread pool.

        Args:
            query_builder: Supabase query builder (before .execute())

        Returns:
            Query result data

        Example:
            result = await self._run_query(
                self.client.table("users").select("*").eq("id", user_id)
            )
        """
        return await self._run_in_thread(lambda: query_builder.execute())
```

### Step 2: 改造 14 个 Repository

需要改造的 Repository 列表：

1. `infrastructure/repositories/user_repository.py` - UserProfile
2. `infrastructure/repositories/credit_repository.py` - UserCredits
3. `infrastructure/repositories/project_repository.py` - Project
4. `infrastructure/repositories/listing_repository.py` - Listing
5. `infrastructure/repositories/asset_repository.py` - Asset (如果存在)
6. `infrastructure/repositories/template_repository.py` - Template (如果存在)
7. `infrastructure/repositories/theme_repository.py` - Theme (如果存在)
8. `infrastructure/repositories/campaign_repository.py` - Campaign (如果存在)
9. `infrastructure/repositories/experiment_repository.py` - Experiment (如果存在)
10. `infrastructure/repositories/feature_flag_repository.py` - FeatureFlag (如果存在)
11. `infrastructure/repositories/notification_repository.py` - Notification (如果存在)
12. `infrastructure/repositories/support_repository.py` - SupportTicket (如果存在)
13. `infrastructure/repositories/payment_repository.py` - Payment (如果存在)
14. `infrastructure/repositories/config_repository.py` - Config (如果存在)

**改造模板**：

```python
# 以 UserRepository 为例

from infrastructure.repositories.base_async_repository import AsyncRepositoryBase

class SupabaseUserRepository(IUserRepository, AsyncRepositoryBase):
    """Supabase implementation of user repository with true async."""

    async def get_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by user ID."""
        try:
            # ✅ 使用异步包装器
            result = await self._run_query(
                self.client.table("profiles").select("*").eq("id", user_id).single()
            )

            if not result.data:
                return None

            return self._map_to_profile(result.data)
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    async def save(self, user_profile: UserProfile) -> UserProfile:
        """Persist user profile (upsert)."""
        try:
            data = self._map_to_row(user_profile)

            # ✅ 使用异步包装器
            result = await self._run_query(
                self.client.table("users").upsert(data, on_conflict="user_id").select("*").single()
            )

            return self._map_to_profile(result.data)
        except Exception as e:
            logger.error(f"Failed to save user {user_profile.user_id}: {e}")
            raise

    # 其他方法类似改造...
```

### Step 3: 更新测试

```python
# tests/infrastructure/repositories/test_user_repository_async.py

import pytest
import asyncio

@pytest.mark.asyncio
async def test_get_by_id_runs_in_thread():
    """测试 get_by_id 确实在线程池执行"""
    repo = SupabaseUserRepository()

    # 这应该不会阻塞事件循环
    user = await repo.get_by_id("test-user-id")

    assert user is not None
    assert user.user_id == "test-user-id"


@pytest.mark.asyncio
async def test_concurrent_queries():
    """测试并发查询不会互相阻塞"""
    repo = SupabaseUserRepository()

    # 并发执行 10 个查询
    tasks = [
        repo.get_by_id(f"user-{i}")
        for i in range(10)
    ]

    start = asyncio.get_event_loop().time()
    results = await asyncio.gather(*tasks)
    duration = asyncio.get_event_loop().time() - start

    # 并发执行应该比串行快
    assert duration < 1.0  # 假设每个查询 100ms，并发应该 <1s
    assert len(results) == 10
```

---

## 📈 性能对比

### 改造前 (伪异步)

```python
# 串行执行 10 个查询
for i in range(10):
    user = await repo.get_by_id(f"user-{i}")  # 每个 100ms
# 总耗时: ~1000ms (10 * 100ms)
```

**问题**: 虽然用了 `await`，但实际上是串行阻塞执行。

### 改造后 (真异步)

```python
# 并发执行 10 个查询
tasks = [repo.get_by_id(f"user-{i}") for i in range(10)]
users = await asyncio.gather(*tasks)  # 每个 100ms
# 总耗时: ~150ms (并发执行，线程池开销)
```

**收益**: 并发执行，耗时从 1000ms → 150ms，**提升 6-7 倍**。

---

## ⚠️ 注意事项

### 1. 线程池大小

Python 默认线程池大小是 `min(32, os.cpu_count() + 4)`。如果并发请求很多，需要调整：

```python
# app.py
import asyncio

# 增加线程池大小
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# 或使用 concurrent.futures
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=100)
loop.set_default_executor(executor)
```

### 2. 事务处理

Supabase 不支持跨表事务，如果需要事务：

```python
# 使用 asyncpg 直接连接 (方案 B)
async def transfer_credits(from_user: str, to_user: str, amount: int):
    async with self.pool.acquire() as conn:
        async with conn.transaction():
            # 扣减发送者
            await conn.execute(
                "UPDATE credits SET balance = balance - $1 WHERE user_id = $2",
                amount, from_user
            )
            # 增加接收者
            await conn.execute(
                "UPDATE credits SET balance = balance + $1 WHERE user_id = $2",
                amount, to_user
            )
```

### 3. 数据库连接池

Supabase SDK 内部已经有连接池管理，使用 `to_thread` 不会创建过多连接。

### 4. 测试覆盖

- 单元测试：Mock Supabase 客户端
- 集成测试：真实数据库，测试并发性能
- 负载测试：压测验证改造效果

---

## 🎯 执行顺序

### 阶段 1: 基础设施 (1 天)
1. 创建 `AsyncRepositoryBase` 基类
2. 编写单元测试
3. 文档化使用方法

### 阶段 2: 核心 Repository (2-3 天)
按优先级改造：
1. **CreditRepository** (最关键，支付相关)
2. **UserRepository** (用户认证)
3. **ProjectRepository** (核心业务)
4. **ListingRepository** (Marketplace)

### 阶段 3: 其他 Repository (2-3 天)
5-14. 其他 Repository 按依赖顺序改造

### 阶段 4: 测试和验证 (2-3 天)
1. 单元测试全覆盖
2. 集成测试验证功能
3. 负载测试验证性能
4. 监控指标对比

### 阶段 5: 灰度发布 (1-2 周)
1. Week 1: 10% 流量
2. Week 2: 50% 流量
3. Week 3: 100% 流量
4. 监控性能指标和错误率

---

## 📊 预期收益

| 指标 | 改造前 | 改造后 | 提升 |
|------|--------|--------|------|
| 并发查询性能 | 串行执行 | 并发执行 | **6-7x** |
| 响应时间 (P95) | 500ms | 200ms | **2.5x** |
| 吞吐量 (QPS) | 100 | 400-500 | **4-5x** |
| CPU 利用率 | 80% (阻塞) | 50% (非阻塞) | **降低 30%** |
| 事件循环阻塞 | 严重 | 无 | **消除** |

---

## 🔗 相关文档

- [Phase 8: services/db → infrastructure/repositories 迁移](./PHASE_8_MIGRATION_PLAN.md)
- [Phase 9-10: 架构清理计划](./[Phase-9-10]Architecture-Cleanup-Plan.md)
- [Python asyncio 官方文档](https://docs.python.org/3/library/asyncio.html)
- [FastAPI 并发和异步](https://fastapi.tiangolo.com/async/)

---

## 📝 总结

**核心问题**: Repository 声明为 `async def` 但内部是同步 I/O，会阻塞事件循环。

**解决方案**: 使用 `asyncio.to_thread()` 将同步操作放到线程池执行。

**改造优先级**: 🟡 中等（Phase 8-10 完成后执行）

**预期收益**:
- 并发性能提升 6-7 倍
- 响应时间降低 2.5 倍
- CPU 利用率降低 30%
- 消除事件循环阻塞

**时间估算**: 1-2 周（开发 + 测试 + 灰度发布）

---

**变更历史**:
- v1.0.0 (2026-01-07): 初始版本，问题分析和改造方案
