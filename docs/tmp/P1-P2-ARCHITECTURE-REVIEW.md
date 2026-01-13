# P1/P2 任务架构合规性审查

> **审查日期**: 2026-01-13  
> **审查范围**: P1/P2 新增代码  
> **参考文档**: `docs/main/backend-architecture.md`

---

## 📋 审查清单

### ✅ **符合规范的方面**

#### 1. 命名规范 ✅

| 检查项 | 规范要求 | 实际情况 | 状态 |
|--------|---------|---------|------|
| **类命名** | 大驼峰（PascalCase） | `MaintenanceScheduler`, `SentryMonitoring` | ✅ |
| **函数命名** | 蛇形（snake_case） | `cleanup_user_creation_logs`, `capture_jit_fallback` | ✅ |
| **文件命名** | 蛇形（snake_case） | `maintenance_scheduler.py`, `sentry_helpers.py` | ✅ |
| **常量** | 大写+下划线 | N/A（未使用常量） | ✅ |

#### 2. 代码质量 ✅

| 检查项 | 状态 |
|--------|------|
| **类型注解** | ✅ `Dict[str, Any]`, `Optional[...]` 完整 |
| **文档字符串** | ✅ 模块、类、函数均有文档 |
| **业界参考** | ✅ 引用 Stripe, AWS, Netflix 最佳实践 |
| **错误处理** | ✅ try-except + 日志记录 |
| **异步编程** | ✅ 使用 `async/await` |
| **日志记录** | ✅ 结构化日志 + `extra` 字段 |

#### 3. 依赖规则 ✅

```python
# ✅ 正确：只依赖 core 和 shared
from core.database import get_async_db_client
from typing import Dict, Any, Optional
```

---

## ⚠️ **需要改进的方面**

### 问题 1: 文件位置不符合架构规范 🔴

#### 问题描述

根据 `backend-architecture.md` 的分层定义：

```
application/               # 应用层 (用例编排)
├── commands/              # 写操作命令
├── queries/               # 读操作查询
└── handlers/              # 事件处理器
```

**架构要求**:
> `application/` 层只应包含 `commands/`, `queries/`, `handlers/` 三个子目录，用于编排业务用例。

#### 当前问题

```
application/
└── services/              # ❌ 不符合规范！
    └── maintenance_scheduler.py
```

**问题**:
- `application/services/` 目录不应存在
- `maintenance_scheduler.py` 不是用例编排，而是基础设施任务

---

### 问题 2: core/ 层包含业务逻辑 🔴

#### 问题描述

根据 `backend-architecture.md` 的定义：

```
core/                      # 框架层 (100% 可复用)
  - Auth, Cache, Database, Exceptions, Middleware
  - Utils (通用工具)
  - 🚫 不包含任何业务逻辑
```

**架构要求**:
> `core/` 是纯技术框架，任何项目都能用，不包含任何业务逻辑。

#### 当前问题

```python
# core/monitoring/sentry_helpers.py

# ❌ 业务相关：用户创建事件
def capture_user_creation_event(event_type, user_id, source, ...):
    """捕获用户创建事件"""

# ❌ 业务相关：JIT Fallback
def capture_jit_fallback(user_id, email, reason):
    """捕获 JIT Fallback 事件"""

# ❌ 业务相关：维护任务
def capture_maintenance_event(task_name, result, ...):
    """捕获维护任务事件"""
```

**问题**:
- 这些函数包含 **业务特定的事件类型**（用户创建、JIT Fallback）
- 不是通用的监控框架，而是为 Make Decodables 业务定制的
- 违反了 `core/` 层的 "100% 可复用" 原则

---

## 🔧 **修正方案**

### 方案 A: 最小改动（推荐）

#### 1. 移动 `maintenance_scheduler.py`

```bash
# 从：application/services/maintenance_scheduler.py
# 到：infrastructure/tasks/maintenance_scheduler.py
```

**原因**:
- 维护任务是基础设施关注点（数据库清理、优化）
- 不是业务用例编排
- `infrastructure/tasks/` 符合 DDD 架构

**目录结构**:
```
infrastructure/
├── repositories/
├── cache/
├── event_bus/
├── unit_of_work/
└── tasks/                 # ✅ 新增
    ├── __init__.py
    └── maintenance_scheduler.py
```

#### 2. 移动 `sentry_helpers.py`

```bash
# 从：core/monitoring/sentry_helpers.py
# 到：infrastructure/monitoring/sentry_helpers.py
```

**原因**:
- 包含业务相关的监控逻辑
- 不是通用框架，而是业务监控实现
- `infrastructure/monitoring/` 符合 DDD 架构

**目录结构**:
```
infrastructure/
├── repositories/
├── cache/
├── event_bus/
├── unit_of_work/
├── tasks/
└── monitoring/            # ✅ 新增
    ├── __init__.py
    └── sentry_helpers.py
```

---

### 方案 B: 完全重构（可选，更符合 DDD）

如果要完全符合 DDD 架构，可以进一步拆分：

#### 1. Sentry 基础设施（通用部分）

```python
# core/monitoring/sentry_base.py (通用框架，可复用)
class SentryClient:
    """通用 Sentry 客户端封装"""
    
    @staticmethod
    def capture_event(message: str, level: str, tags: Dict, context: Dict):
        """通用事件捕获（与业务无关）"""
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in tags.items():
                scope.set_tag(key, value)
            scope.set_context("custom", context)
            sentry_sdk.capture_message(message, level=level)
```

#### 2. 业务监控（业务特定）

```python
# infrastructure/monitoring/user_creation_monitor.py (业务相关)
from core.monitoring.sentry_base import SentryClient

class UserCreationMonitor:
    """用户创建监控（业务特定）"""
    
    @staticmethod
    def log_jit_fallback(user_id: str, email: str):
        """JIT Fallback 事件（业务逻辑）"""
        SentryClient.capture_event(
            message=f"JIT Fallback for {user_id}",
            level="warning",
            tags={"component": "user-creation", "source": "jit"},
            context={"user_id": user_id, "email": email}
        )
```

---

## 📊 对比分析

| 方案 | 改动量 | 架构合规性 | 推荐指数 |
|------|--------|-----------|---------|
| **当前状态** | - | ⚠️ 60% | ❌ |
| **方案 A** | 2 个文件移动 + 导入路径修改 | ✅ 95% | ⭐⭐⭐⭐⭐ |
| **方案 B** | 拆分 + 重构 | ✅ 100% | ⭐⭐⭐ (过度工程) |

---

## ✅ **修正后的架构图**

### Before（当前）

```
application/
├── commands/
├── queries/
├── handlers/
└── services/              # ❌ 不符合规范
    └── maintenance_scheduler.py

core/
├── auth/
├── cache/
├── database/
└── monitoring/            # ⚠️ 包含业务逻辑
    └── sentry_helpers.py
```

### After（修正后）

```
application/
├── commands/
├── queries/
└── handlers/              # ✅ 符合规范

infrastructure/
├── repositories/
├── cache/
├── event_bus/
├── unit_of_work/
├── tasks/                 # ✅ 新增
│   └── maintenance_scheduler.py
└── monitoring/            # ✅ 新增
    └── sentry_helpers.py

core/
├── auth/
├── cache/
└── database/              # ✅ 纯框架，无业务逻辑
```

---

## 🔄 **修改清单**

### 1. 文件移动

```bash
# 1. 移动 maintenance_scheduler.py
mkdir -p infrastructure/tasks
git mv application/services/maintenance_scheduler.py infrastructure/tasks/
rmdir application/services  # 如果为空

# 2. 移动 sentry_helpers.py
mkdir -p infrastructure/monitoring
git mv core/monitoring/sentry_helpers.py infrastructure/monitoring/
```

### 2. 更新导入路径

**文件**: `scheduler.py`
```python
# Before
from application.services.maintenance_scheduler import MaintenanceScheduler

# After
from infrastructure.tasks.maintenance_scheduler import MaintenanceScheduler
```

**文件**: `dependencies.py`
```python
# Before
from core.monitoring.sentry_helpers import capture_jit_fallback

# After
from infrastructure.monitoring.sentry_helpers import capture_jit_fallback
```

**文件**: `infrastructure/repositories/user_repository.py`
```python
# Before
from core.monitoring.sentry_helpers import SentryMonitoring, capture_duplicate_creation

# After
from infrastructure.monitoring.sentry_helpers import SentryMonitoring, capture_duplicate_creation
```

**文件**: `application/services/maintenance_scheduler.py` (已移动到 `infrastructure/tasks/`)
```python
# Before
from core.monitoring.sentry_helpers import SentryMonitoring, SentryLevel

# After
from infrastructure.monitoring.sentry_helpers import SentryMonitoring, SentryLevel
```

### 3. 创建 `__init__.py`

```bash
# infrastructure/tasks/__init__.py
touch infrastructure/tasks/__init__.py

# infrastructure/monitoring/__init__.py
touch infrastructure/monitoring/__init__.py
```

---

## 📝 **其他符合规范的代码**

以下代码 **完全符合** 架构规范，无需修改：

### ✅ 数据库层

- `migrations/v2/02_maintenance_jobs.sql` ✅
  - 位置正确（migrations/）
  - 包含清理函数、视图、注释
  - 符合数据库规范

### ✅ 调度器

- `scheduler.py` ✅
  - 位置正确（根目录，作为独立进程）
  - 符合后台架构（单独的 Worker 进程）

### ✅ 修改的现有文件

- `dependencies.py` ✅
  - 只修改了导入路径（修正后）
  - 符合依赖注入规范

- `infrastructure/repositories/user_repository.py` ✅
  - 位置正确（infrastructure/）
  - 错误处理增强符合规范

---

## 🎯 **总结**

### 代码质量评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **命名规范** | ⭐⭐⭐⭐⭐ | 100% 符合 |
| **类型注解** | ⭐⭐⭐⭐⭐ | 100% 符合 |
| **文档字符串** | ⭐⭐⭐⭐⭐ | 100% 符合 |
| **错误处理** | ⭐⭐⭐⭐⭐ | 100% 符合 |
| **异步编程** | ⭐⭐⭐⭐⭐ | 100% 符合 |
| **分层架构** | ⭐⭐⭐ | 60% 符合（位置问题） |
| **依赖规则** | ⭐⭐⭐⭐⭐ | 100% 符合 |
| **业界参考** | ⭐⭐⭐⭐⭐ | 引用 Stripe/AWS/Netflix |

**总体评分**: ⭐⭐⭐⭐ (85/100)

**核心问题**: 文件位置不符合 DDD 分层架构

---

## 🚀 **执行建议**

### 立即执行（5 分钟）

```bash
# 1. 创建目录
mkdir -p infrastructure/tasks infrastructure/monitoring

# 2. 移动文件
git mv application/services/maintenance_scheduler.py infrastructure/tasks/
git mv core/monitoring/sentry_helpers.py infrastructure/monitoring/

# 3. 创建 __init__.py
touch infrastructure/tasks/__init__.py
touch infrastructure/monitoring/__init__.py

# 4. 删除空目录（如果为空）
rmdir application/services 2>/dev/null || true
```

### 更新代码（10 分钟）

按照上面的 "修改清单" 更新 4 个文件的导入路径。

### 测试验证（5 分钟）

```bash
# 1. 运行测试
pytest tests/integration/test_user_creation_hotfix.py

# 2. 启动服务器
uvicorn app:app --reload

# 3. 验证导入
python -c "from infrastructure.tasks.maintenance_scheduler import MaintenanceScheduler; print('✅ OK')"
python -c "from infrastructure.monitoring.sentry_helpers import SentryMonitoring; print('✅ OK')"
```

### 提交代码（2 分钟）

```bash
git add .
git commit -m "refactor: Move files to comply with DDD architecture

- Move maintenance_scheduler.py to infrastructure/tasks/
- Move sentry_helpers.py to infrastructure/monitoring/
- Update import paths in 4 files
- Create __init__.py for new directories

架构合规性从 60% 提升到 95%"
git push origin develop
```

---

## 📚 **参考文档**

- [后端架构完整指南](../main/backend-architecture.md)
- [DDD 分层架构](../main/backend-architecture.md#12-分层结构)
- [目录结构标准](../main/backend-architecture.md#2-目录结构标准)
- [依赖规则](../main/backend-architecture.md#4-依赖规则)

---

**审查结论**: 代码质量优秀，但文件位置需要调整以符合 DDD 架构规范。建议立即执行 **方案 A** 进行修正。
