# Config Module Deep Review (v3.25)

**审查日期**: 2026-01-09
**审查范围**: Config 模块 8 个接口 (api/admin/config.py)
**当前版本**: v3.25

---

## 📋 总结

### 模块概览
Config 模块负责系统配置管理和动态限流控制，共 8 个端点:

1. `GET /config` - 获取所有配置
2. `GET /config/{config_key}` - 获取单个配置
3. `PUT /config` - 更新单个配置
4. `PUT /config/batch` - 批量更新配置
5. `GET /rate-limits` - 获取当前限流配置
6. `POST /rate-limits/preset` - 应用限流预设
7. `GET /rate-limits/presets` - 获取可用预设列表
8. `POST /config/cache/clear` - 清除配置缓存

### 架构模式
**特殊设计**: Config 模块采用 **Domain Service 直接访问数据库** 模式:
- API Layer → `domains/platform/config_service.py` (Domain Service)
- Domain Service → **直接使用 Supabase Client** (不通过 Repository)
- 存在 `infrastructure/repositories/config_repository.py` **但未被使用**

### 关键发现

#### 🔴 CRITICAL (2个)
1. **CFG-CRITICAL-1**: Domain Service 直接访问数据库，绕过 Repository 层
2. **CFG-CRITICAL-2**: ConfigRepository 存在但未被使用，造成架构不一致

#### 🟠 HIGH (4个)
3. **CFG-HIGH-1**: 缺少 Pydantic Response Models
4. **CFG-HIGH-2**: 缺少查询 limit，存在 OOM 风险
5. **CFG-HIGH-3**: Domain Service 使用模块级 `supabase` 实例，不符合依赖注入
6. **CFG-HIGH-4**: 缺少统一的错误处理

#### 🟡 MEDIUM (3个)
7. **CFG-MEDIUM-1**: 双重缓存机制（Redis + Domain Service 内存缓存）
8. **CFG-MEDIUM-2**: Domain Service 混合使用同步方法，但 Repository 是异步
9. **CFG-MEDIUM-3**: 部分端点缺少审计日志

#### 🔵 LOW (2个)
10. **CFG-LOW-1**: 测试文件重复（test_config.py + test_config_api.py）
11. **CFG-LOW-2**: 部分端点限流配置过于宽松（60/minute）

---

## 🏗️ 架构分析

### 当前架构 (v3.25)

```
API Layer (api/admin/config.py)
    ↓
Domain Service (domains/platform/config_service.py)
    ↓ [直接访问]
Supabase Client (模块级实例)
    ↓
Database (system_configs 表)

[未使用] ConfigRepository (infrastructure/repositories/config_repository.py)
```

**问题**:
- Domain Service 直接创建 Supabase Client: `supabase = create_client(SUPABASE_URL, SUPABASE_KEY)`
- ConfigRepository 存在完整实现（341 行），但从未被调用
- 违反 DDD 原则: Domain Layer 不应该依赖 Infrastructure Layer

### DDD 标准架构

```
API Layer
    ↓
Domain Service (业务逻辑编排)
    ↓
Repository Interface (domains/platform/config_repository.py)
    ↓
Repository Implementation (infrastructure/repositories/config_repository.py)
    ↓
Database
```

---

## 🔍 详细问题清单

### 🔴 CRITICAL Issues

#### CFG-CRITICAL-1: Domain Service 直接访问数据库

**位置**: `domains/platform/config_service.py:16-32`

**问题**:
```python
# Domain Service 直接创建数据库连接
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_config(config_key: str):
    # 直接访问数据库
    result = supabase.table("system_configs").select("value, is_active")...
```

**违反原则**:
- Domain Layer 依赖 Infrastructure (Supabase SDK)
- 模块级实例，无法注入 mock 进行测试
- 缺少重试机制和错误处理

**影响**:
- 测试困难（需要真实数据库）
- 无法复用 Repository 的重试机制
- 架构不一致

#### CFG-CRITICAL-2: ConfigRepository 存在但未被使用

**位置**: `infrastructure/repositories/config_repository.py` (341 lines)

**问题**:
- 完整的 Repository 实现已存在：
  - `get_by_key()` - 获取单个配置
  - `get_all()` - 获取所有配置
  - `update()` - 更新配置
  - `get_audit_logs()` - 审计日志
  - 完整的缓存机制
  - `@retry_on_network_error()` 装饰器
- **但从未被 Domain Service 或 API Layer 调用**

**影响**:
- 代码冗余（341 行未使用代码）
- 架构混乱（有 Repository 但不用）
- 维护成本高（两套实现需要同步维护）

---

### 🟠 HIGH Issues

#### CFG-HIGH-1: 缺少 Pydantic Response Models

**位置**: `api/admin/config.py` (所有 8 个端点)

**问题**:
```python
@router.get("/config")  # ❌ 没有 response_model
async def get_all_configs(...):
    configs = get_all_configs(category)
    return {"configs": configs, "total": len(configs)}  # 返回原始 dict
```

**对比其他模块** (Logs/Events 已修复):
```python
@router.get("/events", response_model=UserEventsResponse)  # ✅ 有 response_model
async def adm_get_user_events(...):
    return result  # 类型安全
```

**影响**:
- 无类型验证
- OpenAPI 文档不完整
- 运行时错误难以捕获

**需要创建**:
- `AllConfigsResponse`
- `SingleConfigResponse`
- `ConfigUpdateResponse`
- `BatchConfigUpdateResponse`
- `RateLimitsResponse`
- `RateLimitPresetsResponse`
- `CacheClearResponse`

#### CFG-HIGH-2: 缺少查询 limit，存在 OOM 风险

**位置**: `domains/platform/config_service.py:183-191`

**问题**:
```python
def get_all_configs(category: str = None):
    query = supabase.table("system_configs").select("*")  # ❌ 无 limit
    if category:
        query = query.eq("config_group", category)
    result = query.order("key").execute()
    return result.data or []
```

**对比**:
- Logs module: `.limit(100000)`
- Events module: `.limit(100000)`
- Config module: **无限制**

**风险**:
- 如果配置表有上千条记录，可能 OOM
- 查询性能下降

**修复方案**:
```python
result = query.order("key").limit(10000).execute()
```

#### CFG-HIGH-3: 使用模块级 Supabase 实例

**位置**: `domains/platform/config_service.py:30-32`

**问题**:
```python
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)  # 模块级实例
```

**标准做法** (其他模块):
```python
# 使用依赖注入
db_client = get_database_client()
config_repo = SupabaseConfigRepository(db_client)
```

**影响**:
- 无法 mock 测试
- 违反依赖注入原则
- 难以替换数据库实现

#### CFG-HIGH-4: 缺少统一的错误处理

**位置**: `api/admin/config.py` (多个端点)

**当前**:
```python
@router.put("/config")
async def update_config(data: ConfigUpdateRequest, admin: dict = Depends(require_admin)):
    success = set_config(data.config_key, data.config_value, admin.get("id"))
    if not success:
        raise HTTPException(500, "Failed to update config")  # ❌ 泛化错误
    return {"success": True, "message": "Config updated successfully"}
```

**标准做法** (Logs/Events 模块):
```python
try:
    result = await repo.update_config(...)
    return result
except Exception as e:
    logger.error(f"[Admin {admin.get('id')}] Update config failed: {type(e).__name__} - {e}")
    raise HTTPException(500, "Failed to update configuration")
```

**缺失**:
- try-except 块
- 详细日志记录（错误类型、上下文）
- 错误信息清理（防止泄露敏感信息）

---

### 🟡 MEDIUM Issues

#### CFG-MEDIUM-1: 双重缓存机制

**位置**:
- `domains/platform/config_service.py` - 使用 `core.cache.cache_service` (Redis)
- `infrastructure/repositories/config_repository.py` - 使用内存字典 `self._config_cache`

**问题**:
```python
# Domain Service 缓存
cache_service.get_json(f"config:{config_key}")  # Redis/内存

# Repository 缓存（未使用）
self._config_cache: Dict[str, tuple] = {}  # 内存字典
```

**影响**:
- Repository 的缓存永远不会被使用
- 两套缓存逻辑需要维护
- 潜在的缓存不一致风险

**决策**:
- 如果使用 Repository: 移除 Domain Service 的缓存逻辑
- 如果保留 Domain Service: 删除 Repository 的缓存代码

#### CFG-MEDIUM-2: 同步/异步混用

**问题**:
- **Domain Service**: 所有方法都是同步 `def get_config()`, `def set_config()`
- **Repository**: 所有方法都是异步 `async def get_by_key()`, `async def update()`
- **API Layer**: 端点是异步 `async def get_all_configs()`

**当前调用链**:
```python
# API (async) → Domain Service (sync)
async def get_all_configs(...):
    configs = get_all_configs(category)  # ❌ 同步调用
```

**如果迁移到 Repository**:
```python
# API (async) → Domain Service (async) → Repository (async)
async def get_all_configs(...):
    configs = await config_service.get_all_configs(category)  # ✅ async/await
    # config_service 调用:
    result = await config_repo.get_all(group=category)
```

**影响**:
- 同步调用阻塞事件循环
- 迁移到 Repository 需要改所有方法签名

#### CFG-MEDIUM-3: 部分端点缺少审计日志

**问题**:
- ✅ `update_config()` - 有审计（通过 `updated_by` 参数）
- ✅ `batch_update_configs()` - 有审计
- ✅ `apply_rate_limit_preset()` - 有审计
- ❌ `clear_config_cache()` - **无审计**

**示例**:
```python
@router.post("/config/cache/clear")
async def clear_cache(admin: dict = Depends(require_admin)):
    clear_config_cache()  # ❌ 没有记录谁清除了缓存
    return {"success": True, "message": "Config cache cleared"}
```

**标准做法**:
```python
logger.info(f"[Admin {admin.get('id')}] Cleared config cache")
```

---

### 🔵 LOW Issues

#### CFG-LOW-1: 测试文件重复

**位置**:
- `tests/api/admin/test_config.py` (203 lines) - 完整的测试套件
- `tests/api/admin/test_config_api.py` (64 lines) - 基础认证测试

**问题**:
- `test_config_api.py` 的测试与 `test_config.py` 重复
- 两个文件测试相同的端点认证逻辑

**建议**:
- 合并到 `test_config.py`，删除 `test_config_api.py`

#### CFG-LOW-2: 部分端点限流配置过于宽松

**位置**: `api/admin/config.py`

**当前配置**:
```python
@router.get("/config")
@limiter.limit("60/minute")  # 60 次/分钟
async def get_all_configs(...):
```

**对比其他 Admin 端点**:
- 大部分 Admin 端点: `30/minute`
- 危险操作（退款、订阅）: `10/minute`
- Config 查询: `60/minute` ← 可能过高

**风险**:
- Admin 端点应该更严格限流
- 60/min 相当于每秒 1 次，可能被滥用

**建议**:
- 查询端点: `30/minute`
- 写入端点: `10/minute`（当前已经是）

---

## 📊 测试覆盖分析

### 测试文件

| 文件 | 行数 | 测试类 | 测试方法数 | 用途 |
|------|------|--------|-----------|------|
| test_config.py | 203 | 4 classes | 21+ tests | 完整测试套件 |
| test_config_api.py | 64 | 1 class | 3 tests | 认证测试（重复） |

### 测试覆盖

#### ✅ 已覆盖
- 所有端点的认证要求
- Pydantic 请求模型验证
- 参数边界测试（长度、数量）
- 常量定义测试
- 预设值有效性测试

#### ❌ 缺失
- **Repository 方法测试** - Repository 完全未被测试（因为未被使用）
- **Domain Service 单元测试** - 没有针对 config_service.py 的独立测试
- **错误场景测试** - 数据库连接失败、配置不存在等
- **缓存失效测试** - 更新后缓存是否正确清除
- **审计日志测试** - 是否正确记录操作日志
- **异步测试** - 没有异步执行相关的测试

---

## 🔧 修复计划

### Phase 1: 架构重构（解决 CRITICAL 问题）

#### 1.1 迁移到 Repository 模式

**目标**: 让 Domain Service 使用已存在的 ConfigRepository

**步骤**:

1. **创建 Repository 接口** (domains/platform/config_repository.py):
```python
from abc import ABC, abstractmethod

class ConfigRepository(ABC):
    """Abstract interface for config data access."""

    @abstractmethod
    async def get_by_key(self, key: str, default_value=None) -> Optional[str]:
        pass

    @abstractmethod
    async def get_all(self, group: Optional[str] = None) -> List[Dict]:
        pass

    @abstractmethod
    async def update(self, key: str, value: str, admin_id: str) -> Optional[Dict]:
        pass
```

2. **重构 Domain Service** (domains/platform/config_service.py):
```python
# BEFORE:
supabase = create_client(...)  # 模块级实例

def get_config(config_key: str):
    result = supabase.table("system_configs").select(...)

# AFTER:
class ConfigService:
    def __init__(self, config_repo: ConfigRepository):
        self.config_repo = config_repo

    async def get_config(self, config_key: str):
        return await self.config_repo.get_by_key(config_key)
```

3. **更新 API Layer** (api/admin/config.py):
```python
# BEFORE:
from domains.platform.config_service import get_config

async def get_all_configs(...):
    configs = get_all_configs(category)

# AFTER:
from infrastructure.repositories.config_repository import SupabaseConfigRepository
from core.dependencies import get_database_client

async def get_all_configs(...):
    db_client = get_database_client()
    config_repo = SupabaseConfigRepository(db_client)
    config_service = ConfigService(config_repo)
    configs = await config_service.get_all_configs(category)
```

4. **清理未使用代码**:
- 移除 Domain Service 中的直接数据库访问代码
- 保留 DEFAULT_RATE_LIMITS 常量
- 保留 RATE_LIMIT_PRESETS 常量

**预期结果**:
- ✅ Domain Service 通过 Repository 访问数据
- ✅ 架构符合 DDD 规范
- ✅ 可测试性提高（可注入 mock Repository）
- ✅ 复用 Repository 的重试机制

#### 1.2 统一缓存策略

**决策**: 保留 Domain Service 层缓存，移除 Repository 层缓存

**理由**:
- 配置读取频繁，Domain Service 层缓存更高效
- Repository 应专注数据访问，不应包含业务缓存逻辑
- 避免双重缓存的复杂性

**修改**:
```python
# infrastructure/repositories/config_repository.py
# 删除:
self._config_cache: Dict[str, tuple] = {}
self._get_cached_config()
self._set_cached_config()
```

---

### Phase 2: 添加 Response Models（解决 HIGH 问题）

**创建**: `api/admin/config_models.py` (v1.0.0)

```python
"""
Config Management API Models - Request/Response schemas.

@module api.admin.config_models
@version 1.0.0
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ConfigEntry(BaseModel):
    """Single configuration entry."""
    key: str = Field(..., description="Configuration key")
    value: str = Field(..., description="Configuration value (JSON string)")
    config_group: str = Field(..., description="Configuration group")
    description: Optional[str] = Field(None, description="Configuration description")
    is_active: bool = Field(..., description="Whether config is active")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class AllConfigsResponse(BaseModel):
    """Response for GET /config."""
    configs: List[ConfigEntry] = Field(..., description="List of configurations")
    total: int = Field(..., description="Total number of configs")


class SingleConfigResponse(BaseModel):
    """Response for GET /config/{config_key}."""
    key: str = Field(..., description="Configuration key")
    value: Dict[str, Any] = Field(..., description="Configuration value")
    is_active: bool = Field(..., description="Whether config is active")


class ConfigUpdateResponse(BaseModel):
    """Response for PUT /config."""
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Response message")
    config: Optional[ConfigEntry] = Field(None, description="Updated config")


class BatchConfigUpdateResponse(BaseModel):
    """Response for PUT /config/batch."""
    success: bool = Field(..., description="Overall success status")
    results: Dict[str, bool] = Field(..., description="Per-config update results")
    updated_count: int = Field(..., description="Number of successfully updated configs")
    failed_count: int = Field(..., description="Number of failed updates")


class RateLimitConfig(BaseModel):
    """Single rate limit configuration."""
    key: str = Field(..., description="Rate limit key")
    limit: int = Field(..., description="Request limit")
    window: str = Field(..., description="Time window (minute, hour, day)")
    enabled: bool = Field(..., description="Whether rate limit is enabled")


class RateLimitsResponse(BaseModel):
    """Response for GET /rate-limits."""
    rate_limits: List[RateLimitConfig] = Field(..., description="List of rate limit configs")
    global_enabled: bool = Field(..., description="Whether rate limiting is globally enabled")


class RateLimitPresetInfo(BaseModel):
    """Single rate limit preset information."""
    name: str = Field(..., description="Preset name")
    description: str = Field(..., description="Preset description")
    multiplier: Optional[float] = Field(None, description="Multiplier for limits")
    enabled: Optional[bool] = Field(None, description="Whether to enable rate limiting")


class RateLimitPresetsResponse(BaseModel):
    """Response for GET /rate-limits/presets."""
    presets: List[RateLimitPresetInfo] = Field(..., description="Available presets")


class RateLimitPresetApplyResponse(BaseModel):
    """Response for POST /rate-limits/preset."""
    success: bool = Field(..., description="Apply success status")
    message: str = Field(..., description="Response message")
    preset: str = Field(..., description="Applied preset name")


class CacheClearResponse(BaseModel):
    """Response for POST /config/cache/clear."""
    success: bool = Field(..., description="Clear success status")
    message: str = Field(..., description="Response message")
```

**更新 API 端点**:
```python
from api.admin.config_models import (
    AllConfigsResponse, SingleConfigResponse, ConfigUpdateResponse,
    BatchConfigUpdateResponse, RateLimitsResponse, RateLimitPresetsResponse,
    RateLimitPresetApplyResponse, CacheClearResponse
)

@router.get("/config", response_model=AllConfigsResponse)
async def get_all_configs(...):
    ...

@router.get("/config/{config_key}", response_model=SingleConfigResponse)
async def get_config(...):
    ...

# ... 其余端点类似
```

---

### Phase 3: 添加安全防护（解决 HIGH 问题）

#### 3.1 添加查询 limit

**修改**: Repository 方法

```python
@retry_on_network_error()
async def get_all(self, group: Optional[str] = None) -> List[Dict]:
    query = self.client.table("system_configs").select("*")
    if group:
        query = query.eq("config_group", group)

    # 添加 limit 防止 OOM
    result = query.order("config_group").order("key").limit(10000).execute()
    return result.data or []
```

#### 3.2 统一错误处理

**更新所有端点**:
```python
@router.put("/config", response_model=ConfigUpdateResponse)
async def update_config(
    data: ConfigUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Update single system configuration."""
    try:
        db_client = get_database_client()
        config_repo = SupabaseConfigRepository(db_client)
        config_service = ConfigService(config_repo)

        logger.info(f"[Admin {admin.get('id')}] Updating config: {data.config_key}")

        updated = await config_service.set_config(
            data.config_key,
            data.config_value,
            admin.get("id")
        )

        if not updated:
            raise HTTPException(404, "Configuration not found")

        return ConfigUpdateResponse(
            success=True,
            message="Configuration updated successfully",
            config=updated
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Admin {admin.get('id')}] Update config failed: "
            f"{type(e).__name__} - {e}"
        )
        raise HTTPException(500, "Failed to update configuration")
```

---

### Phase 4: 完善审计和测试

#### 4.1 添加完整审计日志

**所有修改操作添加日志**:
```python
# 示例: clear_config_cache
@router.post("/config/cache/clear", response_model=CacheClearResponse)
async def clear_cache(admin: dict = Depends(require_admin)):
    try:
        logger.info(f"[Admin {admin.get('id')}] Clearing config cache")
        clear_config_cache()
        logger.info(f"[Admin {admin.get('id')}] Config cache cleared successfully")
        return CacheClearResponse(success=True, message="Config cache cleared")
    except Exception as e:
        logger.error(f"[Admin {admin.get('id')}] Clear cache failed: {e}")
        raise HTTPException(500, "Failed to clear config cache")
```

#### 4.2 测试清理

**删除重复测试**:
```bash
rm tests/api/admin/test_config_api.py
```

**添加新测试** (test_config.py):
```python
# 添加 Repository 测试
class TestConfigRepository:
    """Tests for ConfigRepository."""

    async def test_get_by_key_with_cache(self):
        # 测试缓存功能
        pass

    async def test_update_invalidates_cache(self):
        # 测试缓存失效
        pass

# 添加错误场景测试
class TestConfigErrorHandling:
    """Tests for error handling."""

    async def test_get_config_db_error(self):
        # Mock 数据库错误
        pass

    async def test_update_config_not_found(self):
        # 配置不存在
        pass
```

---

## 📈 预期改进效果

### 架构层面
- ✅ **100% DDD 合规** - 完全符合三层架构
- ✅ **Repository 得到使用** - 341 行代码被激活
- ✅ **依赖注入** - 可测试性提升

### 性能层面
- ✅ **OOM 防护** - 添加查询 limit
- ✅ **缓存优化** - 移除冗余缓存逻辑

### 安全层面
- ✅ **错误处理** - 统一 try-except，防止信息泄露
- ✅ **审计完整** - 所有操作均记录日志
- ✅ **限流优化** - 调整过松的限流配置

### 代码质量
- ✅ **类型安全** - 所有端点添加 response_model
- ✅ **测试覆盖** - 新增 Repository 和错误场景测试
- ✅ **代码清理** - 删除重复测试文件

---

## 🎯 修复优先级

### P0 - 立即修复（架构合规）
1. **CFG-CRITICAL-1**: 迁移到 Repository 模式
2. **CFG-CRITICAL-2**: 激活 ConfigRepository
3. **CFG-HIGH-3**: 移除模块级 Supabase 实例

### P1 - 高优先级（安全性）
4. **CFG-HIGH-2**: 添加查询 limit
5. **CFG-HIGH-4**: 统一错误处理
6. **CFG-HIGH-1**: 添加 Response Models

### P2 - 中优先级（优化）
7. **CFG-MEDIUM-1**: 清理双重缓存
8. **CFG-MEDIUM-2**: 统一异步模式
9. **CFG-MEDIUM-3**: 完善审计日志

### P3 - 低优先级（清理）
10. **CFG-LOW-1**: 合并测试文件
11. **CFG-LOW-2**: 调整限流配置

---

## 📝 待决策问题

### 1. 是否保留 Domain Service 的缓存逻辑？

**选项 A**: Domain Service 缓存 + Repository 无缓存（推荐）
- ✅ 业务层缓存更灵活
- ✅ Repository 职责单一
- ❌ Domain Service 稍微复杂

**选项 B**: Repository 缓存 + Domain Service 无缓存
- ✅ Repository 自包含缓存逻辑
- ❌ 缓存逻辑与数据访问混合
- ❌ 难以控制缓存策略

**建议**: 选项 A

### 2. 是否需要迁移到完全异步？

**当前**: Domain Service 同步，Repository 异步

**选项 A**: 全部改为异步（推荐）
- ✅ 符合 FastAPI 最佳实践
- ✅ 不阻塞事件循环
- ❌ 需要改所有方法签名

**选项 B**: 保持同步
- ✅ 改动最小
- ❌ 阻塞调用
- ❌ 不符合异步框架最佳实践

**建议**: 选项 A（全部异步）

---

## 🔗 相关文件

### 需要修改的文件
1. `api/admin/config.py` (v3.25 → v3.26)
2. `domains/platform/config_service.py` (重构为 Service 类)
3. `infrastructure/repositories/config_repository.py` (清理缓存代码)

### 需要创建的文件
1. `api/admin/config_models.py` (v1.0.0) - Response Models
2. `domains/platform/config_repository.py` (v1.0.0) - Repository Interface

### 需要删除的文件
1. `tests/api/admin/test_config_api.py` (与 test_config.py 重复)

---

## ✅ 验收标准

### 架构验收
- [ ] Domain Service 通过 Repository 访问数据库
- [ ] ConfigRepository 被所有 Config 操作使用
- [ ] 无模块级数据库客户端实例
- [ ] 所有方法使用依赖注入

### 功能验收
- [ ] 所有 8 个端点正常工作
- [ ] 缓存正确工作（更新后失效）
- [ ] 限流配置可动态调整
- [ ] 预设应用生效

### 测试验收
- [ ] 所有现有测试通过 (21+ tests)
- [ ] 新增 Repository 单元测试
- [ ] 新增错误场景测试
- [ ] 测试覆盖率 ≥ 70%

### 安全验收
- [ ] 所有查询有 limit 限制
- [ ] 所有端点有错误处理
- [ ] 所有修改操作有审计日志
- [ ] 敏感信息不泄露

---

**审查完成时间**: 2026-01-09
**下一步**: 根据用户指令 "现在就全部修复，不要自作聪明"，立即开始修复所有问题
