# MagicZine AI (Make Decodables) 后台业务逻辑说明

> **当前版本**: v3.27.0
> **发布日期**: 2026-01-16
> **产品**: MagicZine AI / Make Decodables - AI 驱动的 8 页可折叠迷你书创作平台
> **架构状态**: 🟢 V3 Stable (Zero Debt)

---

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| v3.27.0 | 2026-01-16 | 🏗️ **V3 重构完成**：Zero Debt、原子积分操作 (RPC)、N+1 优化、安全加固 | - |
| v3.6.0 | 2026-01-12 | 🎨 **新增主题管理系统**：Themes v2.1 (AI 批量生成、审核工作流、主题切换、12 个 Admin API 端点) | - |
| v3.5.0 | 2026-01-12 | 🔒 **数据库安全增强**：69 表启用 RLS、视图命名规范 `v_` 前缀、field_mappings 审计修复 | - |
| v3.4.0 | 2026-01-11 | 📝 **新增文章管理系统**：Articles CMS (Manual/News/Changelog)、DDD 架构、Markdown 支持、发布/取消发布工作流 | - |
| v3.3.0 | 2026-01-10 | 🗑️ **新增统一删除机制**：BaseRepository 三阶段删除 (软删除/永久标记/物理删除)、自动过滤、Repository 模式更新 | - |
| v3.2.0 | 2026-01-09 | 📝 **新增认证系统章节**：Self-hosted auth 用户 ID 格式 (UUID)、验证规则、认证流程 | - |
| v3.1.0 | 2026-01-08 | 🧹 **全量清理**：schemas/→api/schemas/、scheduled_tasks/→application/services/、文档整理 | - |
| v3.0.0 | 2026-01-07 | 🏗️ **重大架构升级**：DDD 三层架构迁移完成、旧代码清理、完整测试覆盖 | - |
| v2.0.0 | 2026-01-06 | 🏗️ 重大更新：新增后台架构说明、代码规范、文件分类；版本号规范化为语义化版本 | - |
| v1.3.24 | 2026-01-06 | 📝 用户生成历史表 (user_generations) - 遗漏补充 | - |
| v1.3.23 | 2026-01-06 | ⚡ 任务队列化：异步图片生成、Redis Queue (RQ)、WebSocket 实时进度推送 | - |
| v1.3.22 | 2026-01-06 | 🔒 数据一致性增强：Credits 和 Marketplace 原子化事务、AI API 重试机制 | - |
| v1.3.3 | 2026-01-05 | 完善 AI 服务灰度发布配置、更新缓存策略文档 | - |
| v1.3.2 | 2026-01-03 | 新增 Universal Analytics Layer 事件追踪规范 | - |
| v1.3.1 | 2025-12-28 | 新增 A/B 测试与实验系统、统计显著性计算 | - |
| v1.3.0 | 2025-12-20 | 重构支付系统、新增 Stripe Webhook 处理流程 | - |
| v1.2.5 | 2025-12-15 | 新增 Marketplace 市场功能、审核状态机 | - |
| v1.2.4 | 2025-12-10 | 完善积分系统、月度重置规则、扣费优先级 | - |
| v1.2.3 | 2025-12-05 | 新增试用期(30天)机制、功能权限矩阵 | - |
| v1.2.2 | 2025-11-28 | 新增资源访问控制(allowed_tiers)、发布权限规则 | - |
| v1.2.1 | 2025-11-20 | 完善项目管理、两阶段删除、自动保存机制 | - |
| v1.2.0 | 2025-11-15 | 新增订阅系统(Starter/Pro)、用户等级定义 | - |
| v1.1.5 | 2025-11-01 | 新增 AI 图像生成服务、模型配置 | - |
| v1.0.0 | 2025-10-15 | 初始版本：基础用户系统、项目 CRUD | - |

**版本号规则** (语义化版本 X.Y.Z):
- **X (主版本)**: 重大架构变更、不兼容改动
- **Y (次版本)**: 新增功能、兼容性改进
- **Z (补丁版本)**: Bug 修复、文档更新

---

## 目录

### 第一部分：架构与规范
1. [产品概述](#1-产品概述)
2. [后台架构](#2-后台架构) ⭐ **v2.0 新增**
3. [代码规范](#3-代码规范) ⭐ **v2.0 新增**
4. [文件分类](#4-文件分类) ⭐ **v2.0 新增**
4.5. [认证系统 (Self-hosted Auth)](#45-认证系统-self-hosted-auth) ⚠️ **必读**

### 第二部分：业务逻辑
5. [用户等级与订阅系统](#5-用户等级与订阅系统)
6. [积分系统](#6-积分系统)
7. [权限与访问控制](#7-权限与访问控制)
8. [AI 服务](#8-ai-服务)
9. [Marketplace 市场](#9-marketplace-市场)
10. [项目管理](#10-项目管理)
11. [资源管理](#11-资源管理)
12. [导出功能](#12-导出功能)
13. [A/B 测试与实验](#13-ab-测试与实验)
14. [缓存系统](#14-缓存系统)
15. [分析与追踪](#15-分析与追踪)
16. [支付系统](#16-支付系统)
17. [文章管理系统](#17-文章管理系统) ⭐ **v3.4 新增**
18. [主题管理系统](#18-主题管理系统) ⭐ **v3.6 新增**

---

# 第一部分：架构与规范

---

## 1. 产品概述

### 1.1 产品定位

**Make Decodables** 是一款面向 K-12 教师、家长、学生的 AI 驱动可折叠迷你书创作平台。用户可以通过简单的文字提示，30秒内生成带有一致性插图的 8 页迷你书，打印后只需简单折叠即可使用。

### 1.2 核心价值

| 价值 | 说明 |
|------|------|
| 快速创作 | 30秒内生成完整 8 页故事和插图 |
| AI 驱动 | 文本生成 + 图像生成的完整 AI 工作流 |
| 打印友好 | 单页纸打印，简单折叠即可成书 |
| 教育导向 | 专为儿童阅读材料设计 |

### 1.3 技术架构

| 层级 | 技术栈 |
|------|--------|
| 前端 | Next.js 15 + React 19 + Tailwind CSS 4, Fabric.js 5.3 |
| 状态管理 | Zustand 5 |
| 认证 | Self-hosted (HS256 JWT) |
| UI组件 | Radix UI + Shadcn UI + Lucide Icons |
| 后端 | Python FastAPI + Uvicorn |
| 数据库 | Supabase (PostgreSQL) |
| 缓存 | Redis (主) + Memory (降级) |
| AI 图像 | Fal-client (Flux 模型) |
| AI 文本 | OpenAI API |
| 支付 | Stripe |
| 部署 | Frontend: Vercel, Backend: Railway |

---

## 2. 后台架构

### 2.1 分层架构 (DDD 三层架构 + 横切关注点)

> ⚠️ **架构演进说明**:
> - **v1.x - v2.x**: 传统分层架构 (routers → services → db)
> - **v3.0+**: DDD 三层架构 (api → application → domains + infrastructure)

#### 当前架构 (v3.27 Stable)

```
┌─────────────────────────────────────────────────────────────────────┐
│              API 层 (api/user + api/admin)                          │
│  HTTP 请求接收、参数验证、DTO 转换、调用 Application Layer             │
│  ⚠️ 注意: api/routers/ 已废弃，迁移至 api/user/ 和 api/admin/         │
├─────────────────────────────────────────────────────────────────────┤
│              应用层 (application/commands + queries)                │
│  用例编排、Command/Query 分离、跨 Domain 协调、事务边界                │
├─────────────────────────────────────────────────────────────────────┤
│    领域层 (domains/*)          │    基础设施层 (infrastructure/*)   │
│  ├─ billing/                  │    ├─ repositories/               │
│  │  ├─ aggregates/            │    │  ├─ credit_repository.py     │
│  │  ├─ value_objects.py       │    │  ├─ user_repository.py       │
│  │  ├─ service.py             │    │  └─ ...                      │
│  │  ├─ repository.py (IF)     │    ├─ external_services/         │
│  │  └─ exceptions.py           │    │  ├─ stripe_client.py        │
│  ├─ identity/                 │    │  └─ ...                      │
│  ├─ creation/                 │    │  └─ ...                      │
│  ├─ marketplace/               │    └─ messaging/                 │
│  └─ platform/                 │        └─ redis_queue.py          │
│  业务规则、实体、聚合根          │    技术实现、第三方集成              │
├──────────────────────────────────────────────────────────────────────┤
│               核心层 (core/) + 共享层 (shared/)                       │
│  ├─ core/: auth, cache, database, exceptions, middleware, utils     │
│  └─ shared/: ai, payment, storage (跨 domain 共享服务)               │
├──────────────────────────────────────────────────────────────────────┤
│                      横切关注点 (Cross-Cutting)                       │
│  配置管理、日志、监控、异常处理、中间件、依赖注入 (container.py)        │
└──────────────────────────────────────────────────────────────────────┘
```

#### 依赖方向规则 (DDD 核心原则)

```
api → application → domains ← infrastructure
                       ↓
                core + shared
```

**关键约束**:
- ✅ domains 可以依赖 core/shared
- ✅ infrastructure 可以依赖 domains (实现 repository 接口)
- ❌ domains **不能**依赖 infrastructure (依赖倒置原则)
- ❌ domains **不能**依赖 application
- ❌ 同级 domain 之间**不能**直接依赖

### 2.2 目录结构 (v3.1 DDD 架构 - 完整迁移版)

```
decodables/
├── 入口文件
│   ├── app.py              # FastAPI 应用入口
│   ├── config.py           # 环境配置
│   ├── container.py        # 依赖注入容器 (DI Container)
│   ├── dependencies.py     # FastAPI 依赖 (认证、授权)
│   ├── scheduler.py        # APScheduler 定时任务
│   └── worker.py           # RQ Worker 后台任务
│
├── core/                   # ✨ 核心框架层 (29 files, 3,328 lines)
│   ├── auth/               # JWT 认证
│   ├── cache/              # Redis/Memory 缓存
│   ├── database/           # Supabase 客户端、重试装饰器
│   ├── exceptions/         # 统一异常体系
│   ├── middleware/         # CORS、日志中间件
│   └── utils/              # 工具函数 (datetime, timezone, hash)
│
├── shared/                 # ✨ 共享服务层 (34 files, 7,137 lines)
│   ├── ai/                 # AI 服务 (FAL, OpenAI, Qwen)
│   │   ├── adapters/       # 多模型适配器
│   │   ├── unified_service.py
│   │   ├── model_config.py
│   │   └── canary_service.py
│   ├── payment/            # Stripe 支付
│   └── storage/            # Supabase Storage
│
├── domains/                # ✨ 领域层 (58 files, 9,691 lines)
│   ├── billing/            # 💰 积分、支付
│   ├── identity/           # 👤 用户身份
│   ├── creation/           # 📝 项目创作
│   ├── marketplace/        # 🛒 素材市场
│   ├── platform/           # ⚙️ Feature Flags、实验
│   ├── content/            # 📦 系统资源、模板
│   └── shared/             # 共享领域逻辑
│
├── application/            # ✨ 应用层 (55 files, 6,961 lines)
│   ├── commands/           # 写操作 (Command)
│   ├── queries/            # 读操作 (Query)
│   ├── handlers/           # Command/Query 处理器
│   └── services/           # 应用服务 (定时任务迁移至此)
│       ├── aggregators/    # 统计聚合任务
│       ├── campaigns/      # 营销活动调度
│       ├── experiments/    # A/B 实验服务
│       └── metrics/        # 指标 ETL
│
├── infrastructure/         # ✨ 基础设施层 (29 files, 7,018 lines)
│   ├── repositories/       # Supabase 仓储实现
│   ├── logging/            # 日志服务
│   ├── tasks/              # 后台任务
│   ├── task_queue/         # RQ 任务队列
│   ├── websocket/          # WebSocket 管理
│   └── cache/              # 缓存 key 定义
│
├── api/                    # ✨ API 层 (58 files, 11,242 lines)
│   ├── user/               # 用户端 API (27 个路由)
│   │   ├── generation_images.py
│   │   ├── generation_story.py
│   │   ├── generation_pdf.py
│   │   └── ...
│   ├── admin/              # 管理端 API (16 个路由)
│   │   └── ...
│   └── schemas/            # ✨ Pydantic 模型 (从 schemas/ 迁移)
│       ├── base.py
│       ├── user/           # 用户端 schemas
│       └── admin/          # 管理端 schemas
│
├── tests/                  # 测试 (135 files, 36,975 lines)
│   ├── api/                # API 测试
│   ├── domains/            # 领域测试
│   └── integration/        # 集成测试
│
├── scripts/                # 脚本 (6 files)
│   ├── migrations/         # 迁移脚本
│   ├── fixes/              # 修复脚本
│   └── tools/              # 开发工具
│
├── migrations/             # SQL 迁移文件
│   ├── v2/
│   │   └── refactored_schema_v2.sql  # 完整数据库 DDL (v4.0)
│   ├── v3/                 # Phase 3 软删除迁移
│   └── *.sql               # 增量迁移脚本
│
├── supabase/               # Supabase CLI 配置
│
├── docs/                   # 文档
│   ├── 后台业务逻辑说明.md      # 本文档
│   ├── BACKEND_ARCHITECTURE_GUIDE.md
│   ├── api-reference.md
│   ├── TEST_COVERAGE_PLAN.md
│   ├── shared/             # 前后端共用文档
│   └── adr/                # 架构决策记录
│
├── .github/                # GitHub Actions
├── .githooks/              # Git hooks
│
└── 配置文件
    ├── .env.example        # 环境变量模板
    ├── requirements.txt    # Python 依赖
    ├── pytest.ini          # pytest 配置
    ├── .coveragerc         # 覆盖率配置
    ├── railway.toml        # Railway 部署配置
    ├── Procfile            # 进程定义
    ├── README.md
    └── CHANGELOG.md
```

### 2.3 代码统计

| 层级 | 文件数 | 代码行数 | 说明 |
|------|--------|----------|------|
| api/ | 58 | 11,242 | API 路由、schemas |
| application/ | 55 | 6,961 | 用例编排、定时任务 |
| domains/ | 58 | 9,691 | 业务核心 |
| infrastructure/ | 29 | 7,018 | 技术实现 |
| core/ | 29 | 3,328 | 框架组件 |
| shared/ | 34 | 7,137 | 跨域服务 |
| tests/ | 135 | 36,975 | 测试文件 |
| **总计** | **404** | **~85,000** | - |

### 2.4 复用统计

| 分类 | 文件数量 | 说明 |
|------|----------|------|
| 🔷 框架层 | ~25 个 | 可直接复制，零修改或仅改导入 |
| 🔸 混合层 | ~15 个 | 结构/骨架复用，配置/内容需调整 |
| 🔶 业务层 | ~60 个 | 需要根据新业务重写 |

**快速判断规则**:
- 如果文件名包含具体业务词汇 (user, project, credit, marketplace) → 🔶 业务层
- 如果文件处理通用功能 (cache, log, db, auth) → 🔷 框架层
- 如果文件是第三方集成 (stripe, openai) → 🔸 混合层

### 2.5 数据访问模式 (DDD Repository Pattern)

> ⚠️ **架构演进说明**:
> - **v1.x - v2.x**: 服务层直接访问数据库
> - **v3.0+**: Repository 模式 + Domain Services

**当前采用: Repository 模式 (v3.0+)**

```python
# infrastructure/repositories/user_repository.py
from infrastructure.repositories.base_repository import BaseRepository
from domains.identity.aggregates.user_profile import UserProfile

class SupabaseUserRepository(BaseRepository[UserProfile], IUserRepository):
    @property
    def table_name(self) -> str:
        return "profiles"

    def _map_to_entity(self, row: dict) -> UserProfile:
        # 数据库行 → 领域实体
        return UserProfile(user_id=row["id"], email=row["email"], ...)

# domains/identity/service.py
from domains.identity.repository import IUserRepository

class IdentityService:
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        return await self.user_repo.get_by_id(user_id)
```

**设计原则**:
- **依赖倒置**: Domain Service 依赖 Repository 接口,不依赖具体实现
- **统一删除**: 所有 Repository 继承 `BaseRepository`,提供统一的软删除/硬删除机制
- **领域对象**: Repository 返回领域实体 (`UserProfile`, `Project`),不是 `dict`
- **原子事务**: 使用 PostgreSQL RPC 函数实现复杂事务

**原子化事务示例** (积分操作):
```sql
-- PostgreSQL RPC 函数
CREATE OR REPLACE FUNCTION deduct_credits_atomic(
    p_user_id UUID,
    p_amount INT,
    p_operation VARCHAR,
    p_related_id UUID DEFAULT NULL
) RETURNS TABLE(success BOOLEAN, new_balance INT, error_code VARCHAR) AS $$
BEGIN
    -- 原子化扣费逻辑
    -- 先扣月度，再扣永久
    -- 余额不足时回滚
END;
$$ LANGUAGE plpgsql;
```

### 2.6 统一删除机制 (Soft Delete & Hard Delete)

> ✨ **v3.3 新增**: 统一的三阶段删除系统，支持软删除、永久标记删除和物理删除

#### 2.6.1 删除策略概述

Make Decodables 使用**三阶段删除策略**,平衡数据安全和存储成本:

| 阶段 | 标识 | 数据库字段 | 可恢复性 | 适用场景 |
|------|------|-----------|---------|----------|
| **Stage 1: 软删除** | Soft Delete | `is_deleted = true` | ✅ 可恢复 | 用户主动删除 (30天内可恢复) |
| **Stage 2: 永久标记** | Permanent Flag | `is_permanently_deleted = true` | ❌ 不可恢复 | 30天后自动 + 数据保留 (合规/审计) |
| **Stage 3: 物理删除** | Physical Delete | 从数据库删除 | ❌ 不可恢复 | 管理员强制删除 (释放存储) |

#### 2.6.2 BaseRepository 抽象类

所有 Repository 实现继承自 `BaseRepository[T]`,提供统一的删除接口:

```python
# infrastructure/repositories/base_repository.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional

T = TypeVar('T')  # 领域实体类型

class BaseRepository(ABC, Generic[T]):
    """
    抽象基类,提供统一的 CRUD 和删除操作。

    子类必须实现:
    - table_name: str property
    - _map_to_entity(row: dict) -> T
    - _map_to_row(entity: T) -> dict
    """

    # === Stage 1: Soft Delete ===
    async def soft_delete(self, id: str, user_id: Optional[str] = None) -> bool:
        """软删除记录 (is_deleted = true)"""

    async def restore(self, id: str, user_id: Optional[str] = None) -> bool:
        """恢复软删除的记录 (is_deleted = false)"""

    # === Stage 2/3: Hard Delete ===
    async def hard_delete(
        self,
        id: str,
        user_id: Optional[str] = None,
        permanent_delete: bool = False
    ) -> bool:
        """
        硬删除记录:
        - permanent_delete=False → Stage 2 (is_permanently_deleted = true)
        - permanent_delete=True → Stage 3 (物理删除)
        """

    # === Query Helpers ===
    def _query_active_only(self, select: str = "*"):
        """自动过滤已删除记录 (is_deleted = false)"""

    def _query_deleted_only(self, select: str = "*"):
        """只查询软删除记录 (is_deleted = true)"""

    def _query_all(self, select: str = "*"):
        """查询所有记录 (包括已删除)"""
```

#### 2.6.3 数据库表结构

所有支持软删除的表必须包含以下字段:

```sql
-- 必需字段 (Stage 1)
is_deleted BOOLEAN DEFAULT false,
deleted_at TIMESTAMPTZ,

-- 可选字段 (Stage 2, 用于需要长期保留数据的表)
is_permanently_deleted BOOLEAN DEFAULT false,

-- 索引优化
CREATE INDEX idx_tablename_active ON tablename(user_id, created_at DESC)
WHERE is_deleted = false;

CREATE INDEX idx_tablename_deleted ON tablename(deleted_at DESC)
WHERE is_deleted = true AND is_permanently_deleted = false;
```

#### 2.6.4 支持删除的表

**支持软删除的表** (有 `is_deleted`, `deleted_at`, `recovery_expires_at`):

| 表名 | Stage 1 | Stage 2 | 说明 |
|------|---------|---------|------|
| `profiles` | ✅ | ❌ | 用户账号 (GDPR 删除使用物理删除) |
| `projects` | ✅ | ✅ | 项目 (保留创作数据用于分析) |
| `marketplace_listings` | ✅ | ✅ | 市场商品 (保留交易历史) |
| `assets` | ✅ | ✅ | 用户资源 (保留使用统计) |
| `asset_categories` | ✅ | ❌ | 素材分类 (LTREE 层级结构) |
| `user_asset_prompt_templates` | ✅ | ❌ | 用户 AI 素材提示词模板 |
| `marketplace_favorites` | ✅ | ❌ | 用户收藏 |
| `marketplace_reviews` | ✅ | ❌ | 商品评价 |
| `campaigns` | ✅ | ✅ | 营销活动 |
| `daily_themes` | ✅ | ❌ | 每日主题 |
| `holidays` | ✅ | ❌ | 节日配置 |
| `support_tickets` | ✅ | ❌ | 工单 |
| `support_replies` | ✅ | ❌ | 工单回复 |

**不支持软删除的表** (只增不删或物理删除):

| 表名 | 原因 |
|------|------|
| `credit_transactions` | 积分交易 (只增不删，审计要求) |
| `marketplace_purchases` | 购买记录 (只增不删，财务要求) |
| `user_events` | 用户事件 (append-only 日志表) |
| `content_reports` | 内容举报 (保留完整记录) |
| `error_logs` | 错误日志 (只增不删) |
| `api_logs` | API 日志 (只增不删) |
| `admin_operations` | 管理操作 (审计要求) |

#### 2.6.5 使用示例

**用户删除项目** (Soft Delete):

```python
# domains/creation/service.py
class ProjectService:
    def __init__(self, project_repo: IProjectRepository):
        self.project_repo = project_repo

    async def delete_project(self, project_id: str, user_id: str) -> bool:
        """用户主动删除项目 → Stage 1 软删除"""
        return await self.project_repo.soft_delete(project_id, user_id)

    async def restore_project(self, project_id: str, user_id: str) -> bool:
        """30天内恢复删除的项目"""
        return await self.project_repo.restore(project_id, user_id)
```

**定时任务清理** (Permanent Flag):

```python
# application/services/cleanup_service.py
async def cleanup_old_deletions():
    """每天运行: 将 30 天前的软删除记录标记为永久删除"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

    # 查询 30 天前的软删除记录
    projects = await project_repo._query_deleted_only().execute()

    for project in projects:
        if project["deleted_at"] <= cutoff_date:
            # Stage 2: 永久标记删除
            await project_repo.hard_delete(project["id"], permanent_delete=False)
```

**管理员强制删除** (Physical Delete):

```python
# api/admin/projects.py
@router.delete("/projects/{project_id}/force")
async def force_delete_project(project_id: str, admin: Admin = Depends(require_admin)):
    """管理员强制物理删除 (释放存储空间)"""
    return await project_repo.hard_delete(project_id, permanent_delete=True)
```

#### 2.6.6 自动过滤机制

使用 `_query_active_only()` 查询时,**自动排除已删除记录**:

```python
# infrastructure/repositories/project_repository.py
class SupabaseProjectRepository(BaseRepository[Project]):
    async def get_user_projects(self, user_id: str) -> List[Project]:
        # 自动过滤 is_deleted = false
        result = self._query_active_only().eq("user_id", user_id).execute()
        return [self._map_to_entity(row) for row in result.data]
```

#### 2.6.7 迁移清单

如需迁移旧代码到新的删除机制:

| 旧模式 | 新模式 | 说明 |
|--------|--------|------|
| `status = "deleted"` | `is_deleted = true` | 使用布尔标志 |
| `.delete().eq("id", id)` | `.soft_delete(id)` | 使用 BaseRepository 方法 |
| `.eq("status", "active")` | `._query_active_only()` | 使用自动过滤 |
| 手动退款逻辑 | BaseRepository 事务 | 统一异常处理 |

**相关文档**:
- 完整实施细节: [`docs/tmp/PHASE-2-COMPLETION-SUMMARY.md`](../tmp/PHASE-2-COMPLETION-SUMMARY.md)
- 数据库 Schema: [`migrations/v2/refactored_schema_v2.sql`](../../migrations/v2/refactored_schema_v2.sql)

---

### 2.6.1 数据库安全: RLS 与视图规范 (v3.5.0)

> ✨ **v3.5 新增**: 统一的数据库安全策略

#### Row Level Security (RLS)

所有 69 个表已启用 RLS (无策略):
- `service_role` key (后端) → ✅ 绕过 RLS，正常访问
- `anon` key (泄露风险) → ❌ 拒绝所有访问

```sql
-- 03_infrastructure.sql:1834-1917
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
-- ... 其他 67 个表
```

#### 视图命名规范

所有视图统一使用 `v_` 前缀:

| 视图 | 基础表 | 用途 |
|------|--------|------|
| `v_projects` | projects | owner_id 别名 |
| `v_marketplace_reports` | content_reports | Repository 兼容 |
| `v_ai_usage_last_30_days` | ai_usage_daily | AI 使用统计 |

```python
# ✅ 使用统一命名
result = self.client.table("v_marketplace_reports").select("*").execute()
```

**详见**: [`database-guide.md` Part 3](database-guide.md#part-3-数据库视图与安全)

---

### 2.7 服务组织模式

| 模式 | 适用场景 | 示例 |
|------|----------|------|
| 单文件服务 | 简单业务、<500 行 | `user_service.py`, `project_service.py` |
| 目录模块 | 复杂业务、多子组件 | `services/ai/` (含 adapters, canary 等) |

**目录模块结构**:
```
services/ai/
├── __init__.py              # 导出公共接口
├── unified_service.py       # 统一入口 (Facade)
├── model_config.py          # 模型配置
├── canary_service.py        # 灰度发布
├── usage_tracking.py        # 使用量追踪
├── cache_service.py         # AI 结果缓存
└── adapters/                # 多模型适配器
    ├── __init__.py
    ├── base.py              # 基类
    ├── openai_adapter.py
    ├── fal_adapter.py
    └── qwen_adapter.py
```

### 2.8 Router 组织

**当前状态**: 扁平化结构，40 个 router 文件

**分组规则**:

| 分组 | 路由前缀 | 文件 |
|------|----------|------|
| 用户 | `/api/users` | `users.py`, `user_profile.py`, `user_assets.py` |
| 项目 | `/api/projects` | `projects.py` |
| 生成 | `/api/generate` | `generation.py`, `pdf_export.py` |
| 市场 | `/api/marketplace` | `marketplace.py`, `marketplace_search.py` |
| 管理 | `/api/admin/*` | `admin_users.py`, `admin_credits.py`, ... |
| 系统 | `/api/system` | `health.py`, `webhooks_stripe.py` |

**建议优化** (待实施):
- 将 `admin_*.py` 移至 `routers/admin/` 子目录
- 合并相似路由 (`user_profile.py` + `user_assets.py` → `users.py`)

### 2.9 异步 vs 同步选择

**当前策略**: 同步优先，特定场景使用异步

| 场景 | 选择 | 原因 |
|------|------|------|
| 数据库 CRUD | 同步 | Supabase 客户端为同步；操作延迟低 |
| AI API 调用 | 同步 + 任务队列 | AI 调用耗时长，使用 RQ 异步处理 |
| 文件上传 | 同步 | 单文件操作，httpx 同步足够 |
| WebSocket | 异步 | FastAPI 原生支持 |

**异步任务 (RQ)**:
```python
# 提交任务
from redis import Redis
from rq import Queue

q = Queue('high', connection=Redis())
job = q.enqueue('services.ai.generate_images', prompt=...)

# Worker 处理
# worker.py
```

---

## 3. 代码规范

### 3.1 命名约定

| 类型 | 规则 | 示例 |
|------|------|------|
| 文件名 | snake_case | `user_service.py`, `credit_service.py` |
| 类名 | PascalCase | `UserService`, `CreditTransaction` |
| 函数名 | snake_case | `get_user_credits()`, `deduct_credits()` |
| 常量 | UPPER_SNAKE | `CREDITS_PER_IMAGE`, `MAX_LISTING_PRICE` |
| 路由函数 | snake_case, 动词开头 | `get_user()`, `create_project()`, `list_items()` |
| Pydantic 模型 | PascalCase, 后缀明确 | `UserCreate`, `UserResponse`, `ProjectUpdate` |

### 3.2 函数设计原则

```python
# ✅ 好的实践
def get_user_by_id(user_id: str) -> Optional[UserProfile]:
    """获取用户信息。
    
    Args:
        user_id: 用户唯一标识
        
    Returns:
        用户档案，不存在时返回 None
        
    Raises:
        DatabaseError: 数据库连接失败
    """
    pass

# ❌ 避免
def getUserById(userId):  # 驼峰命名
    pass
    
def get_user(id):  # 参数名过于通用
    pass
```

### 3.3 错误处理

**统一异常体系**:

```python
# exceptions/base.py
class AppError(Exception):
    """应用基础异常"""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

# exceptions/billing.py
class InsufficientCreditsError(AppError):
    def __init__(self, required: int, available: int):
        super().__init__(
            code="OUT_OF_CREDITS",
            message=f"积分不足: 需要 {required}，剩余 {available}",
            status_code=402
        )
```

**Router 层处理**:
```python
@router.post("/generate")
async def generate_images(request: GenerateRequest, user: User = Depends(get_current_user)):
    try:
        result = image_service.generate(request, user)
        return {"success": True, "data": result}
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})
```

### 3.4 日志规范

```python
import logging
from middleware import get_request_id

logger = logging.getLogger(__name__)

# ✅ 结构化日志
logger.info("User action", extra={
    "request_id": get_request_id(),
    "user_id": user_id,
    "action": "generate_image",
    "credits_used": 5
})

# ❌ 避免
logger.info(f"User {user_id} generated image, used 5 credits")  # 不结构化
print(f"Debug: {data}")  # 使用 print
```

### 3.5 配置管理

```python
# config.py
import os

# === 环境 ===
ENV = os.getenv("ENV", "development")
DEBUG = ENV == "development"

# === 业务常量 (可配置化) ===
CREDITS_PER_IMAGE = int(os.getenv("CREDITS_PER_IMAGE", "5"))
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "30"))

# === 硬编码常量 (不可配置) ===
# 引用 domains/identity/constants.py 中的定义
VALID_TIERS = ["t1", "t2", "t3", "t4"]  # t4 为 Enterprise 预留
MEMBER_TIERS = ["t2", "t3", "t4"]
```

### 3.6 API 响应格式

```python
# 成功响应
{
    "success": True,
    "data": { ... },
    "meta": {
        "page": 1,
        "page_size": 20,
        "total": 100
    }
}

# 错误响应
{
    "success": False,
    "error": {
        "code": "OUT_OF_CREDITS",
        "message": "积分不足: 需要 5，剩余 0"
    }
}
```

### 3.7 测试规范

| 类型 | 位置 | 命名 | 说明 |
|------|------|------|------|
| 单元测试 | `tests/unit/` | `test_*.py` | 测试单个函数/类 |
| API 测试 | `tests/api/` | `test_*.py` | 测试端点行为 |
| 边界测试 | `tests/edge_cases/` | `test_*_boundaries.py` | 边界条件 |
| 业务规则 | `tests/business_rules/` | `test_*_rules.py` | 业务逻辑正确性 |

---

## 4. 文件分类

**图例说明**:
- 🔷 **框架层** - 业务无关，可直接复用到任何 FastAPI 项目
- 🔶 **业务层** - 业务相关，新项目需要重写
- 🔸 **混合层** - 结构/模式可复用，具体内容需调整

### 4.1 框架层 🔷 (可直接复用)

这些文件与具体业务完全无关，可直接复制到其他项目：

| 文件/目录 | 说明 | 复用率 | 复用方式 |
|-----------|------|--------|----------|
| `middleware.py` | Request ID、结构化日志中间件 | **100%** | 直接复制 |
| `timezone_utils.py` | 时区处理工具 | **100%** | 直接复制 |
| `Procfile` | Railway 部署配置 | **100%** | 直接复制 |
| `exceptions/base.py` | 应用异常基类 | **100%** | 直接复制 |
| `exceptions/auth.py` | 认证异常 (401/403) | **100%** | 直接复制 |
| `exceptions/general.py` | 通用异常 (404/500) | **100%** | 直接复制 |
| `exceptions/validation.py` | 验证异常 (400) | **100%** | 直接复制 |
| `exceptions/resource.py` | 资源异常 (404/409) | **100%** | 直接复制 |
| `schemas/base.py` | 通用 API 响应模型 | **100%** | 直接复制 |
| `services/db/core.py` | 数据库连接、重试逻辑 | **100%** | 改连接串即可 |
| `services/cache_service.py` | Redis 缓存封装 | **100%** | 直接复制 |
| `services/ai/adapters/*.py` | 多模型适配器 | **100%** | 直接复制 |
| `services/ai/canary_service.py` | 灰度发布服务 | **100%** | 直接复制 |
| `services/ai/usage_tracking.py` | AI 使用量追踪 | **100%** | 直接复制 |
| `services/ai/cache_service.py` | AI 结果缓存 | **100%** | 直接复制 |
| `scheduled_tasks/task_logger.py` | 定时任务日志 | **100%** | 直接复制 |
| `scheduled_tasks/storage_cleanup.py` | 存储清理任务 | **100%** | 直接复制 |
| `scripts/run_tests.sh` | 测试运行脚本 | **100%** | 直接复制 |
| `scripts/backup/` | 备份脚本 | **100%** | 直接复制 |
| `routers/health.py` | 健康检查端点 | **100%** | 直接复制 |
| `app.py` | FastAPI 应用入口 | **80%** | 修改 router 导入 |
| `worker.py` | RQ Worker 入口 | **80%** | 修改任务导入 |

### 4.2 业务层 🔶 (需重写)

这些文件包含具体业务逻辑，新项目需要重写：

| 文件/目录 | 说明 | 新项目处理 |
|-----------|------|------------|
| `routers/users.py` | 用户 API | 按新业务设计 |
| `routers/projects.py` | 项目 API | 按新业务设计 |
| `routers/generation.py` | AI 生成 API | 按新业务设计 |
| `routers/marketplace.py` | 市场 API | 按新业务设计 |
| `routers/admin_*.py` | 管理后台 API (8个) | 按新业务设计 |
| `services/user_service.py` | 用户业务逻辑 | 全部重写 |
| `services/project_service.py` | 项目业务逻辑 | 全部重写 |
| `services/credit_service.py` | 积分业务逻辑 | 全部重写 |
| `services/marketplace_service.py` | 市场业务逻辑 | 全部重写 |
| `schemas/users.py` | 用户数据模型 | 按新数据结构定义 |
| `schemas/projects.py` | 项目数据模型 | 按新数据结构定义 |
| `schemas/marketplace.py` | 市场数据模型 | 按新数据结构定义 |
| `schemas/generation.py` | 生成数据模型 | 按新数据结构定义 |
| `exceptions/billing.py` | 计费异常 | 按新业务定义 |
| `exceptions/marketplace.py` | 市场异常 | 按新业务定义 |
| `scheduled_tasks/aggregators/` | 业务数据聚合 | 按新指标设计 |
| `scheduled_tasks/campaign_scheduler/` | 活动调度 | 按新活动设计 |
| `migrations/` | 数据库迁移脚本 | 全部重写 |
| `tests/unit/` | 单元测试 | 全部重写 |
| `tests/api/` | API 测试 | 全部重写 |
| `tests/business_rules/` | 业务规则测试 | 全部重写 |
| `docs/` | 业务文档 | 全部重写 |

### 4.3 混合层 🔸 (结构可复用)

这些文件的架构和模式可复用，但具体内容需要根据业务调整：

| 文件/目录 | 可复用部分 | 需调整部分 |
|-----------|------------|------------|
| `config.py` | 环境变量读取结构、日志配置 | 业务常量 (积分、等级、限额) |
| `dependencies.py` | 依赖注入框架、认证装饰器结构 | 具体权限规则、等级检查 |
| `scheduler.py` | 调度器初始化、任务注册机制 | 任务列表、执行时间 |
| `services/ai/unified_service.py` | 统一入口模式、Facade 设计 | Prompt 模板、业务参数 |
| `services/ai/model_config.py` | 模型配置结构 | 具体模型选择、参数 |
| `services/payment/stripe_service.py` | Stripe 集成骨架、Webhook 处理 | 产品定义、价格 ID |
| `routers/webhooks_stripe.py` | Stripe Webhook 处理结构 | 订阅/支付处理逻辑 |
| `exceptions/ai.py` | AI 异常结构 | 错误码、消息 |
| `scheduled_tasks/metrics_etl/` | ETL 框架结构 | 指标定义、聚合逻辑 |
| `tests/conftest.py` | 测试 fixtures 结构 | 测试数据 |

### 4.4 复用指南

**快速启动新项目** (5 步):

```bash
# Step 1: 复制框架层文件
mkdir -p new_project/{services/db,services/ai/adapters,exceptions,schemas,scripts}
cp decodables/middleware.py new_project/
cp decodables/timezone_utils.py new_project/
cp decodables/Procfile new_project/
cp decodables/exceptions/{base,auth,general,validation,resource}.py new_project/exceptions/
cp decodables/schemas/base.py new_project/schemas/
cp decodables/services/db/core.py new_project/services/db/
cp decodables/services/cache_service.py new_project/services/
cp -r decodables/services/ai/adapters new_project/services/ai/
cp decodables/services/ai/{canary_service,usage_tracking,cache_service}.py new_project/services/ai/

# Step 2: 复制并修改混合层文件
cp decodables/app.py new_project/       # 修改 router 导入
cp decodables/config.py new_project/    # 修改业务常量
cp decodables/dependencies.py new_project/  # 修改权限规则
cp decodables/worker.py new_project/    # 修改任务导入

# Step 3: 定义业务 schemas
# new_project/schemas/your_business.py

# Step 4: 实现业务 services
# new_project/services/your_service.py

# Step 5: 创建 routers
# new_project/routers/your_api.py
```

**配置化扩展点** (便于快速调整):

```python
# config.py - 业务配置示例 (建议独立为 business_config.py)
PRODUCT_CONFIG = {
    # 用户等级定义
    "tiers": ["t1", "t2", "t3"],
    
    # 积分/配额配置
    "credits": {
        "t1": 50,
        "t2": 500,
        "t3": 1000
    },

    # 功能权限矩阵
    "features": {
        "ai_generation": ["t1", "t2", "t3"],
        "sticker_library": ["t2", "t3"],
        "zip_export": ["t3"]
    },

    # 限额配置
    "limits": {
        "project_count": {"t1": 1, "t2": 20, "t3": 200},
        "upload_size_mb": {"t1": 5, "t2": 20, "t3": 100}
    }
}
```

### 4.5 新项目工作量估算

| 工作内容 | 预计时间 | 说明 |
|----------|----------|------|
| 复制框架层 | 0.5 天 | 复制 + 验证 |
| 调整混合层 | 1 天 | 修改配置、权限规则 |
| 设计数据模型 | 1-2 天 | schemas + migrations |
| 实现核心服务 | 3-5 天 | 取决于业务复杂度 |
| 实现 API 端点 | 2-3 天 | routers |
| 编写测试 | 2-3 天 | 关键路径测试 |
| **总计** | **10-15 天** | 基础功能可用 |

---

# 第二部分：业务逻辑

---

## 4.5 认证系统 (Self-hosted Auth)

> ⚠️ **重要**: 本节包含关键的业务知识，请务必阅读！

### 4.5.1 用户 ID 格式

**user_id 使用标准 UUID 格式。**

| 格式类型 | 示例 | 用途 |
|----------|------|------|
| ✅ UUID | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` | 用户标识、数据库主键 |

**用户 ID 特征**:
- 格式: 标准 UUID v4
- 总长度: 36 个字符
- 示例: `12345678-1234-1234-1234-123456789abc`

### 4.5.2 验证规则

```python
# UUID 用户 ID 验证
UUID_USER_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)
```

### 4.5.3 认证流程

```
前端 → lib/auth → BFF Proxy → 后端 /auth/login
                                      ↓
                              HS256 JWT (Access Token 15min)
                              + Refresh Token (httpOnly cookie, 7d)
                                      ↓
                              API 请求: Bearer <access_token>
                                      ↓
                              dependencies.py → get_current_user()
                                      ↓
                              jwt.decode(token, AUTH_JWT_SECRET, algorithms=["HS256"])
                                      ↓
                              user_id = payload["sub"]  # UUID 格式
```

**相关文件**:
- `domains/auth/`: 认证领域 (注册/登录/Token/密码/会话)
- `api/auth/router.py`: Auth API 端点
- `dependencies.py`: `get_current_user()` 从 JWT 的 `sub` 字段获取用户 ID
- `api/user/billing.py`: `UUID_USER_ID_PATTERN` 用于验证管理员添加积分时的目标用户 ID

---

## 5. 用户等级与订阅系统

### 5.1 用户等级定义

| 系统代码 (tier) | 简称 | 显示名称 (可配置) | 是否会员 | 订阅状态要求 |
|-----------------|------|------------------|----------|--------------|
| `t1` | First Tier | Free Plan | ❌ 否 | 无 |
| `t2` | Second Tier | Starter Plan | ✅ 是 | `active` |
| `t3` | Third Tier | Pro Plan | ✅ 是 | `active` |

**业务规则**:
- 只有 `t2` 和 `t3` 是"会员"(Member)
- 会员身份需要 `tier in ['t2', 't3']` **且** `subscription_status = 'active'`
- 订阅过期后,用户降级为 `t1`

**命名说明**:
- **系统代码** (`t1`/`t2`/`t3`) - 数据库字段值,永不改变
- **简称** (First Tier/Second Tier/Third Tier) - 固定的描述性名称
- **显示名称** (Free Plan/Starter Plan/Pro Plan) - 前端展示,可通过 system_configs 配置

### 5.2 订阅计划

| 系统代码 | 简称 | 显示名称 | 原价 (USD) | 现价 (USD) | 月度积分 | 核心功能 |
|---------|------|---------|-----------|-----------|----------|----------|
| `t1` | First Tier | Free Plan | $0 | $0 | 50 (注册赠送永久积分) | 基础生成 + 30天试用 |
| `t2` | Second Tier | Starter Plan | **$14.9** | **$9.9** | 200 | 贴纸库、发布免费资源 |
| `t3` | Third Tier | Pro Plan | **$29.9** | **$19.9** | 500 | 全部功能、OCR、ZIP导出、发布项目、商业授权 |

> ⚠️ **注意**: 原价用于展示划线价格。所有价格通过配置管理（Stripe Price ID），不硬编码在代码中。

### 5.3 试用期 (30天)

**核心规则**:
- 试用期时长：**30 天**（从注册日期开始）
- 试用期内：Free 用户可以体验**所有**功能（等同 Pro）
- 试用期结束后：
  - 不属于 Free 的功能权益会"上锁"
  - 已使用 Pro 功能创建的内容无法继续编辑（只读）
  - 需要升级才能解锁

**判断逻辑**:
```python
def is_in_trial(user):
    if user.tier != "t1":
        return False
    registration_date = user.created_at
    days_since_registration = (now - registration_date).days
    return days_since_registration <= 30
```

### 5.4 订阅生命周期

```
注册 → First Tier (t1, 赠送 50 永久积分) → 30天试用期开始
  ↓
升级 → Second Tier (t2) / Third Tier (t3) (立即生效)
  ↓
续费成功 → 重置月度积分为等级配额
  ↓
续费失败 → past_due → 宽限期 → 降级为 First Tier (t1)
  ↓
取消 → 当前周期结束后降级为 First Tier (t1) (不退费则继续有效)
```

### 5.5 匿名用户 (游客)

**核心规则**: 游客 (`visitor_xxx`) **什么功能都用不了**
- 无法创建项目
- 无法生成图像
- 无法访问编辑器
- 无法购买市场商品
- 只能浏览公开的市场列表

---

## 6. 积分系统

### 6.1 积分类型

| 类型 | 字段 | 有效期 | 来源 |
|------|------|--------|------|
| 月度积分 | `credits_monthly` | 每30天重置 | 订阅发放 |
| 永久积分 | `credits_permanent` | 永不过期 | 购买、市场收入、注册赠送 |

### 6.2 扣费优先级

**核心规则**: 扣费时**先扣月度积分，再扣永久积分**

```python
# 扣费逻辑
deduct_monthly = min(monthly_balance, amount)
deduct_permanent = amount - deduct_monthly
```

**示例**:
- 用户有 月度=30, 永久=100, 需要扣 50 积分
- 扣 月度 30 + 永久 20 = 50
- 结果: 月度=0, 永久=80

### 6.3 积分消耗

| 操作 | 消耗积分 | 特殊规则 |
|------|----------|----------|
| AI 图像生成 | **5 积分/张** | 无特殊 |
| AI 文本生成 | **0 积分/次** (免费) | 当前免费，可由 Admin 调整 |
| Smart Scan / OCR | **10 积分/次** | 仅 Pro 或试用期可用 |
| 市场购买 | 0-500 积分 | 取决于商品定价 |
| PDF 导出 | 0 | 免费 |
| ZIP 导出 | 0 | 免费但仅限 Pro |

#### 6.3.1 积分消耗配置管理

**配置来源** (v3.23 新增):
- **主要来源**: `system_configs` 表（Admin 可动态修改）
- **备用来源**: 代码中的 Emergency Fallback（仅数据库不可用时）

**配置项**:

| 配置 Key | 默认值 | 说明 | 数据库字段 |
|---------|--------|------|-----------|
| `credits.cost.image_generation` | 5 | AI 图像生成每张消耗 | `system_configs.value` |
| `credits.cost.text_generation` | 1 | AI 文字生成每次消耗 | `system_configs.value` |
| `credits.cost.smart_scan` | 10 | Smart Scan 每次消耗 | `system_configs.value` |
| `credits.cost.ocr` | 2 | OCR 识别每次消耗 | `system_configs.value` |

**架构设计**:
```
BillingService.get_operation_cost()
    ↓
ConfigService (60s缓存)
    ↓
system_configs 表 (主要来源)
    ↓ (失败)
EMERGENCY_FALLBACK_COSTS (备用来源 + WARNING日志)
```

**优势**:
- ✅ Admin 可实时调整积分消耗，无需重启服务
- ✅ 支持 A/B 测试不同定价策略
- ✅ 数据库是唯一真实来源 (Single Source of Truth)
- ✅ 优雅降级：数据库不可用时使用 fallback

**Admin 修改配置**:
```sql
-- 方式1: 直接 SQL
UPDATE system_configs
SET value = '8', updated_by = 'admin@example.com'
WHERE key = 'credits.cost.image_generation';

-- 方式2: Admin API (待实现)
POST /api/v2/admin/configs
{
  "key": "credits.cost.image_generation",
  "value": "8"
}
```

**相关文档**: [ADR-0002: 数据库驱动的积分配置系统](adr/0002-database-driven-config.md)

### 6.4 积分获取

| 来源 | 数量 | 积分类型 |
|------|------|----------|
| 注册赠送 | 50 | **永久** |
| Second Tier (t2) 月度配额 | 200 | 月度 |
| Third Tier (t3) 月度配额 | 500 | 月度 |
| 市场销售收入 | 售价×90% | **永久** |
| 充值购买 (Credits Booster) | 见下表 | **永久** |

#### 6.4.1 Credits 购买档位

| 档位 | 积分数量 | 原价 (USD) | 现价 (USD) | 折扣 |
|------|----------|-----------|-----------|------|
| 小包 | 100 | $2.99 | $2.99 | - |
| 中包 | 500 | $14.99 | $13.49 | 9折 |
| 大包 | 2000 | $60.00 | $48.00 | 8折 |

> ⚠️ **配置说明**:
> - 所有价格通过 Stripe Price ID 配置，不硬编码在代码中
> - 原价用于展示划线价格
> - 折扣信息在前端配置展示

### 6.5 月度重置规则

- **重置时机**: 根据用户**订阅日期**计算，每 **30 天 UTC 0点** 重置
- **重置方式**: 月度积分**覆盖重置**为等级配额（不是累加）
- **不结转**: 未使用的月度积分**不结转**到下月
- **触发机制**: Stripe Webhook `invoice.payment_succeeded` 触发

```python
# 订阅周期锚点
monthly_credits_cycle_anchor = subscription_start_date

# 重置检查
if (now - cycle_anchor).days % 30 == 0 and now.hour == 0:
    user.credits_monthly = TIER_CREDITS[user.tier]
```

---

## 7. 权限与访问控制

### 7.1 功能权限矩阵

| 功能 | First Tier (t1) | t1 (试用期) | Second Tier (t2) | Third Tier (t3) |
|------|-----------------|-------------|------------------|-----------------|
| AI 图像生成 | ✅ (付费) | ✅ | ✅ | ✅ |
| 贴纸库 | ❌ | ✅ | ✅ | ✅ |
| OCR/Smart Scan | ❌ | ✅ | ❌ | ✅ |
| 项目模板 | ❌ | ✅ | ❌ | ✅ |
| PDF 导出 | ⚠️ 水印 | ✅ | ✅ | ✅ |
| ZIP 导出 | ❌ | ❌ | ❌ | ✅ |
| 个人资源上传 | ❌ | ❌ | ❌ | ✅ |
| 发布 Asset | ❌ | ❌ | ✅ (仅免费) | ✅ |
| 发布 Project | ❌ | ❌ | ❌ | ✅ |
| 购买 Asset | ✅ | ✅ | ✅ | ✅ |
| 购买 Project | ❌ | ❌ | ❌ | ✅ |
| 项目数量上限 | 1 | 1 | 20 | 200 |
| 商业授权 | ❌ | ❌ | ❌ | ✅ |
| 积分充值折扣 | 无 | 无 | 无 | 20% |

### 7.2 资源访问控制 (allowed_tiers)

资源(Resource/Listing)通过 `allowed_tiers` 字段控制访问：

| allowed_tiers | 可访问用户 |
|---------------|-----------|
| `['t1']` | 所有登录用户 |
| `['t2', 't3']` | 会员用户 |
| `['t3']` | 仅 Third Tier 用户 |

**有效的 allowed_tiers 组合** (白名单):
- `['t1']`
- `['t2', 't3']`
- `['t3']`

**访问检查逻辑**:
```python
def can_access_resource(user, allowed_tiers):
    if 't1' in allowed_tiers:
        return True  # 免费资源所有人可访问
    if not is_member(user):
        return False
    return user.tier in allowed_tiers
```

### 7.3 发布权限

| 用户等级 | 简称 | 可发布类型 | 定价限制 |
|----------|------|-----------|----------|
| `t1` | First Tier | ❌ 无法发布 | - |
| `t2` | Second Tier | Asset 仅 | **必须为 0 积分** |
| `t3` | Third Tier | Asset + Project | 0-500 积分 |

**业务规则**:
- 发布需要 **活跃订阅**（subscription_status = 'active'）
- Second Tier (t2) 只能发布**免费资源**
- Third Tier (t3) 可以自由定价 (0-500 积分)
- 定价上限 **500 积分** (硬编码)

### 7.4 锁定元素 (Locked Elements)

当用户降级时，之前使用的高级素材会被"锁定"：

```python
# 画布保存时检查
if contains_locked_elements(canvas_data, user):
    # 方案1: 阻止保存，提示升级或删除锁定元素
    # 方案2: 项目变为只读
```

---

## 8. AI 服务

### 8.1 模型配置

**文本推理模型**:

| 场景 | Provider | Model | 用途 |
|------|----------|-------|------|
| 用户文本 | openai | gpt-4o-mini | 故事生成、提示词增强 |
| Admin 分析 | openai | gpt-4o | 业务报表分析 |

**图像生成模型** (基于用户等级):

| 用户等级 | 简称 | Provider | Model | 特点 |
|----------|------|----------|-------|------|
| `t1` | First Tier | fal | flux-schnell | 快速 (4步) |
| `t2` | Second Tier | fal | flux-schnell | 快速 (4步) |
| `t3` | Third Tier | fal | flux-dev | 高质量 (28+步) |

### 8.2 生成模式

| 模式 | 标识 | 特点 | 参数 |
|------|------|------|------|
| 精准 | `guided` | 严格遵循提示词 | 高 guidance_scale (3.5-4.5) |
| 自由 | `flexible` | 允许艺术创作 | 低 guidance_scale (1.5-2.5) |

**创意度滑块** (仅 flexible 模式):
- 0.0 = 精准，guidance_scale = 4.0
- 1.0 = 非常创意，guidance_scale = 1.5

### 8.3 灰度发布 (Canary Release)

**分流规则**:
- 基于 `MD5(user_id + model_type)` 的确定性哈希
- 哈希值 0-99，低于 `traffic_percent` 进入灰度
- 同一用户在同一实验中始终获得相同分配

**灰度配置示例**:
```json
{
  "enabled": false,
  "text_reasoning": {
    "canary_provider": "qwen",
    "canary_model": "qwen-plus",
    "traffic_percent": 10,
    "target_tiers": ["pro"]
  }
}
```

### 8.4 AI 缓存策略

| 类型 | TTL | 说明 |
|------|-----|------|
| 文本结果 | **24 小时** | 相同 prompt+model+参数 |
| 图像结果 | **不缓存** | 每次生成唯一 |

### 8.5 Fallback 机制

当主模型失败时，自动切换到备用模型：
```
主模型失败 → 检查 fallback 配置 → 调用备用模型 → 记录使用量
```

### 8.6 任务队列化

**架构概述**:
- 图片生成采用异步任务队列，避免长连接超时
- 使用 Redis Queue (RQ) 实现优先级队列
- WebSocket 实时推送生成进度
- Worker 进程独立部署，可水平扩展

**优先级队列**:

| 用户等级 | 简称 | 队列 | 说明 |
|----------|------|------|------|
| `t3` | Third Tier | `high` | 最高优先级，优先处理 |
| `t2` | Second Tier | `default` | 正常优先级 |
| `t1` | First Tier | `low` | 低优先级，排队处理 |

**API 端点**:

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/generate/images/async` | POST | 异步生成，返回 task_id |
| `/api/tasks/{task_id}` | GET | 查询任务状态 |
| `/api/tasks/{task_id}/cancel` | POST | 取消任务 (仅 pending/queued) |
| `/ws/task/{task_id}` | WebSocket | 实时进度推送 |

**任务状态流转**:
```
pending → queued → processing → completed / failed / cancelled
```

**进度推送消息** (WebSocket):
```json
{
  "type": "progress",
  "task_id": "gen_xxx",
  "status": "processing",
  "progress": 50,
  "current_step": 4,
  "total_steps": 8,
  "message": "Generating 4/8 images..."
}
```

**完成消息**:
```json
{
  "type": "completed",
  "task_id": "gen_xxx",
  "result": {
    "image_urls": ["https://..."],
    "total_generated": 8
  }
}
```

**Credits 处理**:
- 先扣款，后入队 (保证一致性)
- 任务失败/取消时自动退款
- 幂等性：重复提交不会重复扣款

**Worker 部署**:
- Procfile: `worker: python worker.py`
- Railway: 单独服务实例运行 worker
- 自动重试：失败任务最多重试 3 次
- 任务超时：5 分钟

### 8.7 重试与超时

**AI API 重试策略**:
- 最大重试次数：3
- 退避策略：指数退避 (1s → 2s → 4s)
- 可重试错误：Rate Limit, Timeout, 5xx
- 不可重试错误：认证失败、参数错误

**超时配置**:

| 场景 | 连接超时 | 读取超时 |
|------|----------|----------|
| OpenAI | 10s | 60s |
| FAL 图像 | 10s | 120s |

---

## 9. Marketplace 市场

### 9.1 资源类型

| 类型 | 标识 | 可发布者 | 可购买者 |
|------|------|----------|----------|
| Asset (素材) | `asset` | Starter, Pro | 所有用户 |
| Project (项目模板) | `project` | Pro | Pro |

### 9.2 购买流程

```
1. 验证 listing 状态 (approved, public, not deleted)
2. 检查 allowed_tiers 权限
3. 检查 resource_type 权限 (project 仅 Pro)
4. 检查是否已购买 (去重)
5. 扣除买家积分 (monthly first)
6. 添加卖家收入 (90% → permanent)
7. 记录交易
8. 增加 sales_count
```

### 9.3 收益分成

| 角色 | 比例 |
|------|------|
| 卖家 | **90%** → 永久积分 |
| 平台 | **10%** |

**示例**: 定价 100 积分，卖家获得 90 永久积分

### 9.4 审核状态机

```
draft → pending → approved / rejected
              ↑              ↓ (编辑关键字段)
              └──────────────┘
```

| 状态 | 标识 | 说明 | 市场可见性 |
|------|------|------|-----------|
| 草稿 | `draft` | 未提交 | ❌ |
| 待审核 | `pending` | 已提交等待审核 | ❌ |
| 已通过 | `approved` | 审核通过 | ✅ (需 is_public=true) |
| 已拒绝 | `rejected` | 审核驳回 | ❌ |

**市场可见条件**: `moderation_status='approved' AND is_public=true AND is_deleted=false`

### 9.5 排行榜

- 排序依据: `usage_count` (使用次数)
- 筛选条件: approved + public + not deleted
- 周期: monthly / all_time
- 类型: all / project / asset

---

## 10. 项目管理

### 10.1 项目限额

| 系统代码 | 简称 | 最大项目数 |
|---------|------|-----------|
| `t1` | First Tier | 1 |
| `t2` | Second Tier | 20 |
| `t3` | Third Tier | 200 |

### 10.2 项目数据结构

```javascript
{
  pages: [
    {
      canvasJson: { /* Fabric.js JSON */ },
      previewImage: "data:image/png;base64,...",
      isLocked: false,
      prompt: "..."
    },
    // ... 8 pages total
  ],
  paperSize: "Letter"  // "Letter" | "A4"
}
```

### 10.3 两阶段删除

**软删除规则**:

| 项目状态 | 删除操作 | 结果 |
|----------|----------|------|
| 自己的未上架项目 | 删除 | 软删除 (30天内可恢复) |
| 30天后 | 自动 | 从删除历史移除 (仍是软删除) |
| 已上架项目 | 删除 | Marketplace 不可见 |
| 购买者的副本 | 原项目删除 | **不受影响**，正常使用 |

**核心规则**: 
- 用户购买后，获得的是独立副本
- 原项目/素材是否删除，**不影响**已购买用户的使用

### 10.4 自动保存

- 防抖延迟: **3 秒**
- 触发条件: 任意页面标记为 `isDirty`
- 保存时检查: 试用期过期、项目超限、锁定元素

### 10.5 幂等性创建 (v1.1.0)

> 业界最佳实践 (Stripe/PayPal/AWS) 防止重复创建

**问题背景**:
- DB 写入成功但响应失败（网络中断、服务器 500 等）
- 客户端以为创建失败，重试后创建了重复项目
- 用户看到"创建失败"但项目数已增加，触发配额限制

**解决方案**:

```
POST /api/v2/user/projects
{
  "title": "My Project",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"  // UUID v4
}
```

**后端处理流程**:

```python
# application/commands/creation.py
class CreateProjectHandler:
    async def handle(self, command: CreateProjectCommand) -> CreateProjectResult:
        # 1. 幂等性检查
        if command.idempotency_key:
            existing = await self._creation_service.get_by_idempotency_key(
                user_id=command.user_id,
                idempotency_key=command.idempotency_key,
            )
            if existing:
                return CreateProjectResult(success=True, project=existing)

        # 2. 创建项目
        project = await self._creation_service.create_project(...)

        # 3. 序列化验证 (防止 Pydantic 错误)
        try:
            project_dict = project.to_dict()
        except Exception:
            # 4. 回滚 - 删除刚创建的项目
            await self._creation_service.delete_project(project.project_id, hard_delete=True)
            raise SerializationError(...)

        return CreateProjectResult(success=True, project=project)
```

**数据库索引**:

```sql
-- 唯一索引: (user_id, idempotency_key)
CREATE UNIQUE INDEX idx_projects_user_idempotency_key
ON projects(user_id, idempotency_key)
WHERE idempotency_key IS NOT NULL AND is_deleted = false;
```

**前端重试逻辑**:

```typescript
// services/projectService.ts
export const createProject = async (token, data, options = {}) => {
  const { maxRetries = 2, retryDelay = 500 } = options;

  // 生成幂等键 (同一逻辑操作使用相同 key)
  const idempotencyKey = data.idempotency_key || generateIdempotencyKey();

  let attempts = 0;
  while (attempts <= maxRetries) {
    try {
      return await apiRequest('/api/v2/user/projects', {
        method: 'POST',
        body: JSON.stringify({ ...data, idempotency_key: idempotencyKey }),
        token,
      });
    } catch (error) {
      if (isRetryableError(error) && attempts < maxRetries) {
        await sleep(retryDelay * ++attempts);  // 指数退避
        continue;
      }
      throw error;
    }
  }
};
```

**相关文件**:
- 后端 Handler: `application/commands/creation.py`
- 后端 Repository: `infrastructure/repositories/project_repository.py`
- 前端 Service: `services/projectService.ts`
- 前端工具: `lib/idempotency.ts`

---

## 11. 资源管理

### 11.1 资源类型

| 类型 | 标识 | 说明 |
|------|------|------|
| 项目模板 | `template` | 完整 8 页项目 |
| 贴纸 | `sticker` | 可添加到画布的图片 |
| 图片 | `image` | 通用图片素材 |
| 背景 | `background` | 页面背景 |
| 边框 | `frame` | 装饰边框 |
| 表情 | `emoji` | 表情图标 |
| 图案 | `pattern` | 重复图案/纹理 |

### 11.2 资源分类

**模板分类**:
- `story` - 📖 故事类
- `educational` - 🎓 教育类
- `seasonal` - 🌸 季节/节日
- `blank` - 📄 空白模板

**贴纸分类**:
- `animals` - 🐾 动物
- `nature` - 🌿 自然
- `people` - 👥 人物
- `food` - 🍎 食物
- `objects` - 📦 物品
- `emotions` - 😊 表情/情绪
- `education` - 📚 教育
- `holiday` - 🎄 节日

### 11.3 Storage Bucket

| Bucket 名称 | 用途 | 目录结构 |
|-------------|------|----------|
| `make-decodables-s` | 系统素材 (Admin 管理) | `stickers/{category}/`, `templates/{type}/`, `backgrounds/` |
| `make-decodables-u` | 用户内容 | `{user_id}/temp/{YYYY-MM-DD}/` (AI生成), `{user_id}/uploads/`, `{user_id}/scans/` |

---

## 12. 导出功能

### 12.1 导出类型

| 类型 | 格式 | 权限 | 积分消耗 |
|------|------|------|----------|
| PDF | .pdf | 所有用户 (Free 有水印) | 0 |
| ZIP | .zip (含高清图片) | **仅 Pro** | 0 |
| 打印 | 直接打印 | 所有用户 | 0 |

### 12.2 PDF 水印规则

| 系统代码 | 简称 | 试用期内 | 试用期后 |
|---------|------|----------|----------|
| `t1` | First Tier | 无水印 | 有水印 |
| `t2` | Second Tier | 无水印 | 无水印 |
| `t3` | Third Tier | 无水印 | 无水印 |

---

## 13. A/B 测试与实验

### 13.1 实验类型

| 类型 | 标识 | 说明 |
|------|------|------|
| A/B 测试 | `ab` | 两个变体对比 |
| 多变体 | `multivariate` | 多个变体 |
| 功能标志 | `feature_flag` | 开关控制 |

### 13.2 变体分配

**确定性哈希分配**:
- 使用 `SHA256(experiment_key:user_identifier)` 
- 哈希值 0-99
- 同一用户在同一实验中始终获得相同变体
- 支持权重分配

**变体配置示例**:
```json
[
  {"key": "control", "name": "对照组", "weight": 50},
  {"key": "variant_a", "name": "变体A", "weight": 50}
]
```

### 13.3 流量分配

- `traffic_allocation`: 0-100，控制参与实验的流量比例
- 100 = 全部流量参与
- 50 = 50% 流量参与，其余不进入实验

### 13.4 目标群体 (Targeting)

```json
{
  "include_anonymous": true,  // 是否包含匿名用户
  "tiers": ["t3"]             // 限定用户等级
}
```

### 13.5 统计显著性

使用 Z-Test 计算：
- p-value < 0.05 = 显著
- 置信度 = (1 - p_value) × 100

---

## 14. 缓存系统

### 14.1 架构

双层存储：Redis (主) → Memory (降级)

- **自动故障转移**: Redis 不可用时自动切换内存缓存
- **定期重连**: 每 30 秒检测 Redis 恢复
- **命名空间隔离**: 按业务域划分缓存键前缀

### 14.2 缓存 TTL

| 类型 | 键前缀 | TTL | 说明 |
|------|--------|-----|------|
| 配置 | `md:config:` | 60s | 配置可能频繁更新 |
| 实验 | `md:experiment:` | 60s | 实验状态需快速生效 |
| AI 文本 | `md:ai:` | 24h | 文本结果稳定 |
| AI 图像 | - | 不缓存 | 每次生成唯一 |
| 统计 | `md:stats:` | 5min | 统计聚合有延迟 |
| 限流 | `md:rl:` | 60s | 窗口周期 |

---

## 15. 分析与追踪

### 15.1 Universal Analytics Layer

所有事件使用 `md_` 前缀，推送到 GTM dataLayer：

| 事件 | 类别 | 触发场景 |
|------|------|---------|
| `md_user_registered` | conversion | 用户注册完成 |
| `md_subscription_started` | conversion | 订阅开始 |
| `md_subscription_upgraded` | conversion | 订阅升级 |
| `md_credits_purchased` | conversion | 积分购买 |
| `md_ai_generation_completed` | engagement | AI 生成完成 |
| `md_project_created` | engagement | 项目创建 |
| `md_project_exported` | conversion | 项目导出 |
| `md_marketplace_purchased` | conversion | 市场购买 |
| `md_experiment_viewed` | system | 实验曝光 |
| `md_experiment_converted` | system | 实验转化 |

### 15.2 平台映射

| 通用事件 | GA4 | Facebook | TikTok |
|---------|-----|----------|--------|
| `md_user_registered` | `sign_up` | `CompleteRegistration` | `CompleteRegistration` |
| `md_subscription_started` | `purchase` | `Subscribe` | `Subscribe` |
| `md_credits_purchased` | `purchase` | `Purchase` | `Purchase` |
| `md_marketplace_purchased` | `purchase` | `Purchase` | `Purchase` |

### 15.3 CAPI 服务

支持服务端事件追踪：
- Facebook Conversions API
- TikTok Events API
- Server-Side GTM

---

## 16. 支付系统

### 16.1 支付方式

| 方式 | 用途 | 模式 |
|------|------|------|
| Stripe | 订阅、充值 | subscription / payment |
| PayPal | 备用 (计划中) | - |

### 16.2 定价配置系统 (Pricing Configuration)

> **重要变更**: 从 v2.0 开始，所有价格配置从硬编码迁移到数据库驱动系统，详见 [PRICING-SYSTEM-DESIGN.md](shared/PRICING-SYSTEM-DESIGN.md)

**订阅计划** (存储在 `pricing_plans` 表):

| Plan Code | Tier | 显示名称 | 原价 (USD) | 现价 (USD) | 月度积分 | 标签 |
|-----------|------|---------|-----------|-----------|----------|------|
| `tier_t1_monthly` | t1 | Free Plan | - | $0 | 0 | FREE |
| `tier_t2_monthly` | t2 | Starter Plan | $14.9 | $9.9 | 200 | - |
| `tier_t3_monthly` | t3 | Pro Plan | $29.9 | $19.9 | 500 | RECOMMENDED |

**积分充值包** (永久有效):

| Plan Code | 积分数量 | 原价 (USD) | 现价 (USD) | 折扣 | 标签 |
|-----------|----------|-----------|-----------|------|------|
| `credits_100` | 100 | - | $2.99 | - | - |
| `credits_500` | 500 | $14.99 | $13.49 | 10% | POPULAR |
| `credits_2000` | 2000 | $60.00 | $48.00 | 20% | BEST VALUE |

**技术实现**:
- 价格存储在 `pricing_plans` 表，支持灵活调整
- Stripe Price ID 区分生产/开发环境 (`stripe_price_id_prod` / `stripe_price_id_dev`)
- 支持用户专属定价 (通过 `user_price_overrides` 表)
- 自动审计追踪 (通过 `pricing_history` 表和触发器)
- PricingService 提供统一的价格查询接口

### 16.3 Webhook 事件

| 事件 | 处理 |
|------|------|
| `checkout.session.completed` | 支付成功，发放积分/更新等级 |
| `invoice.paid` | 订阅续期，重置月度积分 |
| `customer.subscription.deleted` | 订阅取消，降级为 Free |
| `customer.subscription.updated` | 订阅变更 |

### 16.4 订阅取消规则

- **不退费取消**: 当月订阅继续有效，直到有效期结束
- **立即取消 + 退费**: 立即降级为 Free
- **周期结束取消**: 设置 `cancel_at_period_end=true`

---

## 17. 文章管理系统

> **版本**: v3.4.0 (2026-01-11 新增)

文章管理系统用于管理帮助文档 (Manual)、新闻公告 (News) 和更新日志 (Changelog)。采用 DDD 架构，支持 Markdown 内容。

### 17.1 架构设计

**DDD 分层**:
```
api/user/articles.py        → Public API (无需认证)
api/admin/articles.py       → Admin API (require_admin)
domains/articles/           → 领域层
  ├── entities.py           → Article, ArticleSummary, ArticleCategory
  ├── repository.py         → 接口定义 (ArticleRepository)
  └── service.py            → ArticleService (业务逻辑)
infrastructure/repositories/
  └── article_repository.py → SupabaseArticleRepository (实现)
```

**调用链**: API → ArticleService → ArticleRepository

### 17.2 文章分类

| Category | 用途 | 前端路由 |
|----------|------|----------|
| `manual` | 帮助文档/FAQ | `/manual`, `/manual/[slug]` |
| `news` | 新闻/公告 | `/news`, `/news/[slug]` |
| `changelog` | 更新日志 | `/changelog` |

### 17.3 数据模型

**articles 表**:
```sql
CREATE TABLE articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug VARCHAR(200) UNIQUE NOT NULL,     -- URL 友好标识
  title VARCHAR(500) NOT NULL,
  content TEXT NOT NULL,                  -- Markdown 内容
  summary TEXT,                           -- 摘要 (列表展示)
  category VARCHAR(50) NOT NULL,          -- 'manual' | 'news' | 'changelog'
  tags JSONB DEFAULT '[]',                -- 标签数组
  cover_image VARCHAR(500),               -- 封面图 URL
  is_published BOOLEAN DEFAULT false,     -- 发布状态
  published_at TIMESTAMPTZ,               -- 发布时间
  author_id UUID,                          -- user_id (UUID)
  sort_order INTEGER DEFAULT 0,           -- 排序权重
  view_count INTEGER DEFAULT 0,           -- 阅读量
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 17.4 API 端点

**Public API** (无认证, 60 req/min):

| 端点 | 方法 | 用途 |
|------|------|------|
| `/articles` | GET | 列表 (分页、分类筛选) |
| `/articles/categories` | GET | 分类及文章数 |
| `/articles/search` | GET | 搜索 (30 req/min) |
| `/articles/{slug}` | GET | 详情 (自动增加阅读量) |

**Admin API** (require_admin, 10 req/min):

| 端点 | 方法 | 用途 |
|------|------|------|
| `/articles` | GET | 列表 (含草稿) |
| `/articles/{id}` | GET | 详情 (by ID) |
| `/articles` | POST | 创建 |
| `/articles/{id}` | PUT | 更新 |
| `/articles/{id}` | DELETE | 删除 |
| `/articles/{id}/publish` | POST | 发布 |
| `/articles/{id}/unpublish` | POST | 取消发布 |

### 17.5 业务规则

**Slug 生成**:
- 自动从标题生成 (slugify)
- 唯一性检查，冲突时追加序号
- 更新时支持自定义 slug

**发布/取消发布**:
- 发布时设置 `published_at = now()`
- 取消发布时清空 `published_at`
- Public API 只返回 `is_published=true` 的文章

**搜索**:
- 模糊匹配: title, content, summary
- 大小写不敏感 (ilike)
- 支持分类筛选

**阅读量**:
- 访问 `/articles/{slug}` 时自动 +1
- 非原子操作 (read-modify-write)

### 17.6 相关文档

- API 详情: [admin-api-review.md](shared/admin-api-review.md) § 3. Articles
- 设计文档: [articles-system-design.md](shared/articles-system-design.md)

---

## 18. 主题管理系统

> **版本**: v3.6.0 (2026-01-12 新增)

主题管理系统 (Themes v2.1) 为平台提供每日主题管理功能，支持 AI 批量预生成、人工审核、主题切换等能力，用于首页展示和用户创作灵感激发。

### 18.1 架构设计

**DDD 分层**:
```
api/admin/themes.py           → Admin API (require_admin)
domains/themes/               → 领域层
  ├── entities.py             → DailyTheme, ThemeCategory, ReviewStatus
  ├── repository.py           → 接口定义 (ThemesRepository)
  └── themes_service.py       → ThemesService (业务逻辑)
infrastructure/repositories/
  └── themes_repository.py    → SupabaseThemesRepository (实现)
```

**调用链**: API → ThemesService → ThemesRepository

### 18.2 核心概念

**主题分类 (ThemeCategory)**:

| 分类 | 说明 | 示例 |
|------|------|------|
| `holiday` | 节日主题 | 圣诞节、复活节 |
| `notable` | 纪念日/名人日 | 世界读书日、地球日 |
| `seasonal` | 季节主题 | 春季、夏季开学 |
| `special` | 特别活动 | 开学季、毕业季 |
| `evergreen` | 常青主题 | 友谊、家庭、冒险 |

**审核状态 (ReviewStatus)**:

| 状态 | 说明 | 触发条件 |
|------|------|----------|
| `pending` | 待审核 | AI 生成后默认状态 |
| `auto_approved` | 自动批准 | priority ≥ 80 自动批准 |
| `reviewed` | 已审核 | 管理员手动批准 |
| `rejected` | 已拒绝 | 管理员拒绝 |

### 18.3 数据模型

**daily_themes 表**:
```sql
CREATE TABLE daily_themes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL,                          -- 主题日期
  name VARCHAR(200) NOT NULL,                  -- 主题名称
  slogan VARCHAR(500),                         -- 标语
  description TEXT,                            -- 描述
  category VARCHAR(50) DEFAULT 'evergreen',    -- 分类
  priority INTEGER DEFAULT 50,                 -- 优先级 (0-100)
  is_active BOOLEAN DEFAULT true,              -- 是否激活
  is_deleted BOOLEAN DEFAULT false,            -- 软删除标记
  deleted_at TIMESTAMPTZ,                      -- 删除时间

  -- AI 生成相关
  ai_generated BOOLEAN DEFAULT false,          -- 是否 AI 生成
  ai_alternatives JSONB DEFAULT '[]',          -- AI 备选方案
  selected_alternative_id VARCHAR(50),         -- 选中的方案 ID

  -- 审核相关
  review_status VARCHAR(50) DEFAULT 'pending', -- 审核状态
  reviewed_by VARCHAR(50),                     -- 审核人 user_id
  reviewed_at TIMESTAMPTZ,                     -- 审核时间

  -- 时间戳
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 索引
CREATE UNIQUE INDEX idx_daily_themes_date_active
  ON daily_themes(date) WHERE is_deleted = false AND is_active = true;
CREATE INDEX idx_daily_themes_review_status
  ON daily_themes(review_status) WHERE is_deleted = false;
```

### 18.4 API 端点

**Admin API** (require_admin):

| 端点 | 方法 | 用途 |
|------|------|------|
| `/themes` | GET | 列表 (分页、筛选) |
| `/themes` | POST | 创建单个主题 |
| `/themes/{theme_id}` | GET | 获取详情 |
| `/themes/{theme_id}` | PUT | 更新主题 |
| `/themes/{theme_id}` | DELETE | 删除主题 (软删除) |
| `/themes/by-date/{date}` | GET | 按日期查询 |
| `/themes/date-range` | GET | 批量查询日期范围 |
| `/themes/ai/batch-generate` | POST | AI 批量生成 |
| `/themes/{theme_id}/review` | POST | 审核 (approve/reject/switch) |
| `/themes/batch-review` | POST | 批量审核 |
| `/themes/review-queue` | GET | 审核队列 |
| `/themes/stats` | GET | 统计信息 |

### 18.5 业务规则

**AI 批量生成**:
1. 指定日期范围和生成数量
2. 跳过已有主题的日期 (可配置是否覆盖)
3. 每个日期生成多个备选方案 (ai_alternatives)
4. 自动选择最佳方案作为默认 (selected_alternative_id)
5. priority ≥ 80 的主题自动批准

**审核工作流**:
```
AI 生成 → pending
         ↓
   ┌─────┼─────┐
   ↓     ↓     ↓
approve reject switch
   ↓     ↓     ↓
reviewed rejected reviewed (切换方案)
```

**主题切换 (switch)**:
- 从 ai_alternatives 中选择另一个方案
- 更新 name, slogan, description 等字段
- 更新 selected_alternative_id
- 状态变为 reviewed

**优先级规则**:
- 同一日期多个主题时，使用最高优先级的
- priority ≥ 80: 自动批准
- priority < 80: 需要人工审核

### 18.6 公共 API

**Public API** (无认证):

| 端点 | 方法 | 用途 |
|------|------|------|
| `/themes/today` | GET | 获取今日主题 |
| `/themes/upcoming` | GET | 获取即将到来的主题列表 |

### 18.7 相关文档

- API 详情: [admin-api-review.md](shared/admin-api-review.md) § 19. Themes
- 设计文档: [shared/theme-system-design.md](shared/theme-system-design.md)

---

## 附录

### A. 配置常量

```python
# config.py
CREDITS_PER_IMAGE = 5
CREDITS_PER_OCR = 5
CREDITS_SIGNUP_BONUS = 50
CREDITS_MONTHLY_T2 = 500
CREDITS_MONTHLY_T3 = 1000
MAX_LISTING_PRICE = 500
SELLER_REVENUE_PERCENT = 90
VALID_TIERS = ["t1", "t2", "t3", "t4"]  # t4 为 Enterprise 预留
MEMBER_TIERS = ["t2", "t3", "t4"]
TRIAL_DAYS = 30
```

### B. 数据库关键表

| 表名 | 用途 |
|------|------|
| `profiles` | 用户档案、积分余额、订阅状态 |
| `projects` | 用户项目 |
| `credit_transactions` | 积分交易记录 |
| `marketplace_listings` | 市场商品 |
| `user_purchases` | 用户购买记录 |
| `listing_usage` | 商品使用记录 (去重) |
| `experiments` | A/B 实验配置 |
| `experiment_assignments` | 实验分配记录 |
| `analytics_events` | 事件追踪 |
| `system_configs` | 系统配置 |
| `system_resources` | 系统资源 (贴纸/模板等) |
| `notifications` | 用户通知 |
| `user_generations` | 用户生成历史 |
| `articles` | 文章 (Manual/News/Changelog) |
| `daily_themes` | 每日主题 (AI 生成、审核) |

### C. API 端点汇总

| 模块 | 路由前缀 | 主要端点 |
|------|----------|----------|
| 用户 | `/api/users` | `/me`, `/credits/history`, `/assets`, `/notifications` |
| 项目 | `/api/projects` | CRUD, `/dashboard`, `/seller-stats` |
| 生成 | `/api/generate` | `/story`, `/images`, `/pdf` |
| 市场 | `/api/marketplace` | `/items`, `/purchase`, `/publish`, `/leaderboard` |
| 资源 | `/api/resources` | `/stickers`, `/backgrounds`, `/templates` |
| 文章 | `/api/articles` | 列表, 详情, 搜索, 分类 (Public) |
| 主题 | `/api/themes` | `/today`, `/upcoming` (Public) |
| 实验 | `/api/experiments` | `/variant`, `/track` |
| 管理 | `/api/admin` | `/users`, `/credits/adjust`, `/marketplace/moderation`, `/configs`, `/metrics`, `/articles`, `/themes` |

### D. 错误代码

| 代码 | HTTP Status | 描述 |
|------|-------------|------|
| `OUT_OF_CREDITS` | 402 | 积分不足 |
| `FORBIDDEN` | 403 | 无访问权限 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `TRIAL_EXPIRED` | 403 | 试用期已过期 |
| `PROJECT_LIMIT_REACHED` | 403 | 项目数量已达上限 |
| `CONTENT_POLICY_VIOLATION` | 400 | 内容违规 |
| `ALREADY_PURCHASED` | 200 | 已购买 (返回成功但 already_owned=true) |

### E. 监控与日志

**Sentry 错误监控**:
- 集成 `sentry-sdk[fastapi]`
- 自动捕获未处理异常
- 性能追踪 (traces)
- 敏感信息脱敏 (Authorization, API Key 等)

**配置**:
```python
sentry_sdk.init(
    dsn=SENTRY_DSN,
    environment=ENV,  # development / production
    traces_sample_rate=0.1,  # 10% 性能追踪采样
    send_default_pii=False,
)
```

**日志级别**:
| 级别 | 场景 |
|------|------|
| INFO | 正常业务流程 |
| WARNING | 可恢复的异常 |
| ERROR | 需要关注的错误 (自动上报 Sentry) |

### F. 环境变量配置

**必须配置**:

| 变量 | 说明 | 示例 |
|------|------|------|
| `SUPABASE_URL` | Supabase 项目 URL | `https://xxx.supabase.co/` |
| `SUPABASE_KEY` | Supabase Service Role Key | `eyJxxx...` |
| `REDIS_URL` | Redis 连接 URL | `redis://xxx:6379` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-xxx` |
| `FAL_KEY` | FAL AI API Key | `xxx` |
| `STRIPE_SECRET_KEY` | Stripe 密钥 | `sk_live_xxx` |
| `STRIPE_WEBHOOK_SECRET` | Stripe Webhook 签名密钥 | `whsec_xxx` |
| `AUTH_JWT_SECRET` | Auth JWT 签名密钥 (256-bit) | `<random-base64>` |

**推荐配置**:

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ENV` | 环境标识 | `development` |
| `SENTRY_DSN` | Sentry DSN | 无 (不启用) |
| `SENTRY_TRACES_SAMPLE_RATE` | 性能追踪采样率 | `0.1` |
| `WORKER_QUEUES` | Worker 监听队列 | `high,default,low` |

**生产环境推荐值**:
```bash
ENV=production
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_TRACES_SAMPLE_RATE=0.1
```

**开发环境推荐值**:
```bash
ENV=development
SENTRY_DSN=<同生产环境>
SENTRY_TRACES_SAMPLE_RATE=0.5
```

### G. 部署架构

**Railway 服务结构**:

```
Railway Project
├── 🌐 Web Service (main)
│   └── Command: uvicorn app:app --host 0.0.0.0 --port $PORT
│
├── 👷 Worker Service
│   └── Command: python worker.py
│
└── 🔴 Redis
    └── 用于缓存、限流、任务队列
```

**服务职责**:

| 服务 | 职责 |
|------|------|
| Web | API 请求处理、WebSocket 连接 |
| Worker | 后台任务执行 (图片生成等) |
| Redis | 缓存、Rate Limiting、任务队列、进度追踪 |

**扩展建议**:
- Web 服务：根据 API 请求量水平扩展
- Worker 服务：根据任务队列深度水平扩展
- Redis：单实例通常足够，大流量可考虑 Redis Cluster

---

*文档版本: v2.0.0 | 发布日期: 2026-01-06*

---
---

## 附录 A: 价格配置系统设计

> 来源: `PRICING-SYSTEM-DESIGN.md`
> 添加日期: 2026-01-10

### A.1 当前问题分析

#### 现状

当前系统的价格配置存在以下问题:

**硬编码问题**:
```python
# domains/identity/constants.py (硬编码)
TIER_MONTHLY_PRICES = {
    TIER_T1: 0.0,
    TIER_T2: 14.9,  # 硬编码,修改需要改代码+重新部署
    TIER_T3: 29.9,
}

# domains/billing/payment_service.py (环境变量)
PRICE_MAP = {
    "credits_100": os.environ.get("STRIPE_PRICE_CREDITS_100"),  # Stripe Price ID
    "starter": os.environ.get("STRIPE_PRICE_SUB_STARTER"),
    "pro": os.environ.get("STRIPE_PRICE_SUB_PRO")
}
```

**问题列表**:
1. ❌ **价格硬编码**: 修改价格需要改代码 + 重新部署
2. ❌ **现价/原价分离**: 原价用于展示划线价,但没有统一管理
3. ❌ **Stripe Price ID 散落**: 环境变量维护,不同环境需要同步
4. ❌ **历史价格无追踪**: 无法查询历史价格变化记录
5. ❌ **新增档位困难**: 增加新的订阅/积分档位需要多处修改
6. ❌ **价格不一致风险**: 代码、数据库、Stripe 三处不同步

#### 业界最佳实践

参考 Stripe、Shopify、AWS Pricing 等成熟系统:

**核心原则**:
- ✅ **配置驱动**: 所有价格存储在数据库,动态读取
- ✅ **版本管理**: 价格修改不删除旧记录,新增版本
- ✅ **审计追踪**: 记录每次价格变更的时间、原因、操作人
- ✅ **环境隔离**: Dev/Staging/Prod 各自维护 Stripe Price ID 映射
- ✅ **灰度发布**: 支持 A/B 测试,不同用户看到不同价格
- ✅ **向后兼容**: 老用户保持原价,新用户使用新价

### A.2 数据库设计

详见完整文档: [PRICING-SYSTEM-DESIGN.md](PRICING-SYSTEM-DESIGN.md)

核心表结构:
- `pricing_plans` - 定价方案主表
- `pricing_history` - 价格变更历史
- `user_price_overrides` - 用户级价格覆盖

---
---

## 附录 B: 软删除系统

> 来源: `SOFT-DELETE-SYSTEM.md`
> 添加日期: 2026-01-10

### B.1 系统概述

**核心理念**: "逻辑删除"而非"物理删除"

**核心特性**:
- ✅ 用户误删可恢复 (30天恢复期，可配置)
- ✅ 数据合规性 (GDPR 要求保留删除记录)
- ✅ 审计追踪 (保留完整操作历史)
- ✅ 系统稳定性 (避免级联删除引发的数据一致性问题)

### B.2 软删除三件套

```
┌─────────────────────────────────────────────────┐
│           软删除三件套 (Soft Delete)             │
├─────────────────────────────────────────────────┤
│  is_deleted           BOOLEAN                   │  标记: 是否已删除
│  deleted_at           TIMESTAMPTZ               │  时间: 何时删除
│  recovery_expires_at  TIMESTAMPTZ               │  过期: 何时不可恢复
└─────────────────────────────────────────────────┘
```

### B.3 状态转换

```
Active (is_deleted = false)
  ↓ soft_delete()
Recoverable (is_deleted = true, recovery_expires_at > NOW())
  ↓ auto-expire
Expired (is_deleted = true, recovery_expires_at < NOW())
  ↓ cleanup (90 days later)
Deleted (physical deletion)
```

详见完整文档: [SOFT-DELETE-SYSTEM.md](SOFT-DELETE-SYSTEM.md)

---
---

## 附录 C: V3.0.0 升级路线图

> 来源: `V3-UPGRADE-ROADMAP.md`
> 添加日期: 2026-01-10

### C.1 V3.0.0 标准

V3.0.0 引入了 **Container Pattern** 统一依赖注入:

```python
# ❌ V2.x (Inline Handler)
handler = GetResourcesHandler(content_service)  # Inline 创建
result = await handler.handle(query)

# ✅ V3.0.0 (Container Pattern)
container = get_container()
handler = container.get_resources_handler  # 从 Container 获取
result = await handler.handle(query)
```

### C.2 核心改进

| 改进点 | V2.x | V3.0.0 | 收益 |
|--------|------|--------|------|
| **依赖注入** | FastAPI Depends() | Container Property | 统一管理 |
| **Handler 创建** | Inline 创建 | Container 注册 | 可测试性 |
| **Result 对象** | 部分有 | 完整 | 类型安全 |
| **Service 层** | 直接注入 | Container 管理 | 解耦 |

### C.3 升级状态

**已升级模块** (✅ V3.0.0):
- Experiments (v3.31)
- Generations (v3.0.0)
- Export (v3.0.0)
- Marketplace (v3.0.0)
- Resources (v3.0.0)
- User Assets (v3.0.0)
- Templates (v3.0.0)
- System Resources (v3.0.0)

**待升级模块**: 无 - 所有核心模块已升级到 V3.0.0 ✅

详见完整文档: [V3-UPGRADE-ROADMAP.md](V3-UPGRADE-ROADMAP.md)

---

*最后更新: 2026-01-10*
*维护者: Make Decodables 后端团队*
