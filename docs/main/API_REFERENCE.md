# Make Decodables 后端 API 参考文档

> 版本: 3.26
> 更新时间: 2026-01-11
> 供前端重构参考

---

## 目录

1. [RESTful 设计规范](#1-restful-设计规范)
2. [基础信息](#2-基础信息)
3. [健康检查 API](#3-健康检查-api)
4. [Webhooks](#4-webhooks)
5. [用户 API](#5-用户-api)
6. [管理员 API](#6-管理员-api)
7. [业务规则速查](#7-业务规则速查)
8. [错误码说明](#8-错误码说明)

---

## 1. RESTful 设计规范

> 来源: `API-HTTP-METHODS-GUIDELINES.md`

### 1.1 概述

本节定义了 Make Decodables 后端 API 的 HTTP 方法使用标准，遵循 RESTful 设计原则和行业最佳实践。

### 1.2 HTTP 方法速查表

| 方法 | 用途 | 幂等性 | 安全性 | 请求体 | 典型响应码 |
|------|------|--------|--------|--------|------------|
| GET | 获取资源 | ✅ 是 | ✅ 是 | ❌ 无 | 200, 404 |
| POST | 创建资源/执行操作 | ❌ 否 | ❌ 否 | ✅ 有 | 201, 200, 400 |
| PUT | 完整替换资源 | ✅ 是 | ❌ 否 | ✅ 有 | 200, 201, 404 |
| PATCH | 部分更新资源 | ❌ 否 | ❌ 否 | ✅ 有 | 200, 404 |
| DELETE | 删除资源 | ✅ 是 | ❌ 否 | ❌ 无 | 200, 204, 404 |

**关键概念**:
- **幂等性 (Idempotent)**: 多次执行相同请求，结果一致
- **安全性 (Safe)**: 不会修改服务器状态

### 1.3 详细使用规范

#### GET - 查询/获取

**用途**: 获取资源，不修改任何状态

**规则**:
- ✅ 获取单个资源: `GET /api/v2/projects/{id}`
- ✅ 获取资源列表: `GET /api/v2/projects`
- ✅ 带过滤条件的列表: `GET /api/v2/projects?status=active&page=1`
- ✅ 获取统计数据: `GET /api/v2/admin/stats/dashboard`
- ❌ 不要用 GET 执行任何修改操作

**示例**:
```
GET /api/v2/user/profile          # 获取当前用户资料
GET /api/v2/credits/balance       # 获取积分余额
GET /api/v2/projects              # 获取项目列表
GET /api/v2/projects/{id}         # 获取单个项目
GET /api/v2/admin/users?search=john&page=1  # 搜索用户
```

#### POST - 创建/执行操作

**用途**: 创建新资源，或执行非幂等操作

**规则**:
- ✅ 创建新资源: `POST /api/v2/projects`
- ✅ 执行操作/触发任务: `POST /api/v2/generate/image`
- ✅ 批量操作: `POST /api/v2/analytics/events`
- ✅ 登录/认证: `POST /api/v2/auth/login`
- ✅ 复杂搜索 (请求体过大): `POST /api/v2/search`
- ❌ 不要用 POST 获取资源 (除非 GET 参数过长)

**示例**:
```
POST /api/v2/projects             # 创建新项目
POST /api/v2/generate/image       # 生成 AI 图片
POST /api/v2/payment/checkout     # 创建支付会话
POST /api/v2/support/ticket       # 提交工单
POST /api/v2/admin/broadcast      # 发送广播通知
POST /api/v2/experiments/{key}/exposure  # 记录曝光事件
```

#### PUT - 完整替换

**用途**: 用请求体完整替换目标资源

**规则**:
- ✅ 替换整个资源: `PUT /api/v2/projects/{id}`
- ✅ 更新资源状态: `PUT /api/v2/admin/experiments/{key}/status`
- ❌ 不要用 PUT 部分更新 (用 PATCH)
- ❌ 不要用 PUT 创建资源 (用 POST)

**示例**:
```
PUT /api/v2/projects/{id}         # 更新整个项目
PUT /api/v2/user/profile          # 更新用户资料
PUT /api/v2/admin/config/{key}    # 更新系统配置
PUT /api/v2/admin/experiments/{key}/status  # 更新实验状态
```

#### PATCH - 部分更新

**用途**: 部分修改资源的某些字段

**规则**:
- ✅ 更新单个字段: `PATCH /api/v2/user/profile`
- ✅ 更新多个字段 (非全部): 请求体只包含要更新的字段
- ❌ 不要用 PATCH 替换整个资源 (用 PUT)

**示例**:
```
PATCH /api/v2/projects/{id}       # 部分更新项目
PATCH /api/v2/user/settings       # 更新部分设置
PATCH /api/v2/marketplace/listings/{id}  # 部分更新商品
```

#### DELETE - 删除

**用途**: 删除资源

**规则**:
- ✅ 删除单个资源: `DELETE /api/v2/projects/{id}`
- ✅ 删除可以是逻辑删除 (soft delete)
- ❌ 不要在请求体中传递数据
- ⚠️ 批量删除推荐用 POST: `POST /api/v2/generations/batch-delete`

**示例**:
```
DELETE /api/v2/projects/{id}      # 删除项目
DELETE /api/v2/assets/{id}        # 删除素材
DELETE /api/v2/generations/{id}   # 删除生成记录
DELETE /api/v2/admin/experiments/{key}  # 删除实验
```

### 1.4 特殊场景处理

#### 操作型 API (RPC 风格)

某些操作不适合 REST 资源模型，使用 POST 动词:

```
POST /api/v2/credits/deduct       # 扣除积分
POST /api/v2/admin/refund         # 执行退款
POST /api/v2/admin/aggregation/run  # 触发聚合任务
POST /api/v2/admin/cache/clear    # 清空缓存
```

#### 批量操作

```
POST /api/v2/analytics/events     # 批量记录事件
POST /api/v2/generations/batch-delete  # 批量删除
POST /api/v2/admin/notification/batch  # 批量发送通知
```

#### 复杂查询

当 GET 参数过长或过于复杂时，可用 POST:

```
POST /api/v2/search               # 复杂搜索
POST /api/v2/admin/users/export   # 导出用户数据 (带筛选条件)
```

#### 文件上传

```
POST /api/v2/assets/upload        # 上传素材
POST /api/v2/tools/ocr            # 上传图片进行 OCR
```

### 1.5 响应状态码规范

#### 成功响应

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | GET/PUT/PATCH/DELETE 成功 |
| 201 | Created | POST 创建成功 |
| 204 | No Content | DELETE 成功，无返回内容 |

#### 客户端错误

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未登录/Token 无效 |
| 403 | Forbidden | 无权限访问 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 (如重复创建) |
| 422 | Unprocessable Entity | 业务校验失败 |
| 429 | Too Many Requests | 限流 |

#### 服务端错误

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 500 | Internal Server Error | 服务器内部错误 |
| 502 | Bad Gateway | 上游服务错误 |
| 503 | Service Unavailable | 服务暂时不可用 |

### 1.6 API 路径命名规范

#### 基本规则

1. **使用名词，不用动词**: `/projects` 而非 `/getProjects`
2. **使用复数形式**: `/projects` 而非 `/project`
3. **使用小写和连字符**: `/user-settings` 而非 `/userSettings`
4. **资源嵌套不超过 2 层**: `/projects/{id}/pages` 而非 `/projects/{id}/pages/{pageId}/elements`

#### 版本控制

```
/api/v2/...   # 当前版本
/api/v1/...   # 遗留版本 (逐步废弃)
```

### 1.7 Make Decodables API 分类

#### 公开 API (需认证)

```
/api/v2/user/*        # 用户相关
/api/v2/credits/*     # 积分相关
/api/v2/projects/*    # 项目相关
/api/v2/generate/*    # AI 生成
/api/v2/assets/*      # 素材相关
/api/v2/marketplace/* # 市场相关
/api/v2/payment/*     # 支付相关
/api/v2/experiments/* # A/B 测试 (公开端点)
```

#### 公开 API (无需认证)

```
/api/v2/configs/*     # 公开配置
/api/v2/logs/*        # 错误上报
/api/v2/themes/*      # 节日主题
/api/v2/resources/*   # 系统资源
```

#### Admin API (需管理员权限)

```
/api/v2/admin/users/*         # 用户管理
/api/v2/admin/stats/*         # 统计数据
/api/v2/admin/config/*        # 系统配置
/api/v2/admin/campaigns/*     # 营销活动
/api/v2/admin/moderation/*    # 内容审核
/api/v2/admin/notifications/* # 通知管理
/api/v2/admin/subscriptions/* # 订阅管理
/api/v2/admin/ai/*            # AI 配置
/api/v2/admin/logs/*          # 日志查看
/api/v2/admin/metrics/*       # 系统指标
/api/v2/admin/events/*        # 事件管理
/api/v2/admin/experiments/*   # 实验管理
```

#### Webhook API (第三方回调)

```
/api/webhooks/stripe    # Stripe 支付回调
/api/webhooks/clerk     # Clerk 用户回调
/api/webhooks/fal       # FAL AI 回调
```

> **注意**: Webhook 路径不能随意修改，需要在第三方平台配置

### 1.8 检查清单

新增 API 前，请确认:

- [ ] HTTP 方法选择正确 (GET/POST/PUT/PATCH/DELETE)
- [ ] 路径命名符合规范 (名词、复数、小写)
- [ ] 响应状态码使用正确
- [ ] 需要认证的 API 添加了 `Depends(get_current_user)` 或 `Depends(require_admin)`
- [ ] 添加了适当的限流 (`@limiter.limit`)
- [ ] 更新了 API 文档 (`__init__.py` 中的 docstring)

---

## 1.9 DDD 架构合规性 & API质量标准

> **重要提示**: 所有 API (User + Admin) 均已完成 DDD 架构迁移和质量审查
>
> **审查完成**: 2026-01-11 (User API: 123个端点, Admin API: 135个端点)
>
> **参考文档**:
> - `API-REVIEW-USER.md` (User API 审查报告)
> - `API-REVIEW-ADMIN.md` (Admin API 审查报告)
> - `API-DB-Fix-Progress.md` (数据库一致性修复进度)

### DDD 架构模式

所有 API 端点遵循统一的 **CQRS (Command Query Responsibility Segregation)** 模式:

```
API Layer (FastAPI Router)
    ↓
Handler Layer (Command/Query Handlers)
    ↓
Domain Service Layer
    ↓
Repository Layer (Interface)
    ↓
Infrastructure Layer (Supabase Implementation)
```

**架构优势**:
- ✅ **关注点分离**: API层只负责HTTP协议,业务逻辑在Domain层
- ✅ **可测试性**: 每层独立测试,Mock外部依赖
- ✅ **可维护性**: 清晰的调用链,易于定位问题
- ✅ **可扩展性**: 更换数据库只需修改Infrastructure层

### API 质量标准 (已达标)

#### ✅ 1. 统一分页模式

**标准参数**: `offset` + `limit` (NOT `page` + `limit`)

```python
# ✅ 正确 (DDD 风格)
GET /projects?offset=0&limit=20

# ❌ 旧式 (已迁移)
GET /projects?page=1&limit=20
```

**返回格式**:
```json
{
  "items": [...],
  "total": 100,
  "offset": 0,
  "limit": 20
}
```

**已完成迁移** (2026-01-10):
- `/user/projects` (6个接口)
- `/user/marketplace/listings` (3个接口)
- `/admin/*` (所有分页接口)

#### ✅ 2. 统一返回类型

**标准**: 返回 `List[Entity]` 领域对象 (NOT `List[dict]`)

```python
# ✅ 正确 (DDD 风格)
async def list_projects(...) -> List[Project]:
    return await project_service.list_projects(...)

# ❌ 旧式 (已迁移)
async def list_projects(...) -> List[dict]:
    return await repository.query()
```

**Pydantic Response Models** (v2.0):
- `ProjectResponse`
- `ListingResponse`
- `ResourceResponse`
- `ConfigResponse`

**已完成迁移** (2026-01-11):
- Marketplace API (11个端点) → `ListingResponse`
- Projects API (10个端点) → `ProjectResponse`
- Resources API (7个端点) → `ResourceResponse`
- Config API (3个端点) → `ConfigResponse`

#### ✅ 3. 安全防护 (P2-030 / P2-047)

**DoS 防护**: 所有字符串输入字段强制长度限制

```python
# ✅ 已实施 (Field validators)
title: str = Field(max_length=200)
description: str = Field(max_length=2000)
tag: str = Field(max_length=50)
```

**SSRF 防护**: URL 白名单验证

```python
# ✅ 已实施 (Marketplace API)
ALLOWED_DOMAINS = [
    "storage.googleapis.com",
    "supabase.co",
    "makedecodables.com"
]
```

**已覆盖模块**:
- Marketplace API (17个参数添加长度限制)
- Support API (工单/反馈表单)
- Logs API (错误上报)

#### ✅ 4. 审计日志 (Task 9.2)

所有 **删除操作** 记录到 `admin_operations` 表:

```python
# ✅ 已实施
@router.delete("/{campaign_id}")
async def delete_campaign(...):
    await campaign_service.delete(campaign_id)
    await audit_log_service.log_admin_operation(
        admin_id=current_user.user_id,
        operation_type="campaign_delete",
        target_id=campaign_id,
        ip_address=request.client.host
    )
```

**已覆盖端点**:
- Campaigns (删除活动)
- Events (删除事件)
- Experiments (删除实验)
- Generations (删除生成记录/批量删除)
- System Resources (删除资源)
- Templates (删除模板)

#### ✅ 5. 异步任务队列 (P2-015/016)

**长耗时操作** 使用异步任务 + 立即返回:

```python
# ✅ 已实施 (Export API)
@router.post("/projects/{project_id}/pdf/async")
async def export_pdf_async(...) -> TaskResponse:
    task_id = await task_queue.submit(
        task_type="pdf_export",
        project_id=project_id,
        user_id=current_user.user_id,
        priority=get_user_priority(current_user.tier)
    )
    return TaskResponse(task_id=task_id, status="pending")
```

**已实施**:
- PDF 导出 (`/export/projects/{id}/pdf/async`)
- ZIP 导出 (`/export/projects/{id}/zip/async`)
- 性能提升: 5.3x 响应速度 (5s → 0.95s)

#### ✅ 6. Graceful Fallback 模式

**数据库 RPC 函数** 失败时自动回退到直接查询:

```python
# ✅ 已实施 (Marketplace API)
try:
    # 优先使用 RPC (性能优化)
    result = await supabase.rpc("p_get_marketplace_listings", params)
except Exception as e:
    logger.warning(f"RPC failed, falling back to direct query: {e}")
    # Graceful fallback
    result = await repository.search_with_filters_legacy(params)
```

**性能提升**: 5x-10x (RPC vs 多次查询)

**已实施**:
- Marketplace Listings RPC (`p_get_marketplace_listings`)

#### ✅ 7. 测试覆盖率标准

**目标**: ≥ 60% (实际: 65%+)

**测试类型分布**:
- Unit Tests (Service + Handler): 70%
- Integration Tests (API Endpoints): 25%
- E2E Tests: 5%

**已完成测试**:
- Billing API (4个端点, 7 tests)
- Generation Images API (2个端点, 13 tests)
- Generation Story API (2个端点, 9 tests)
- Marketplace API (11个端点, 8 RPC tests)
- Payment API (2个端点, 8 tests)
- Projects API (10个端点, 19 tests)
- User Profile API (7个端点, 11 tests)
- Webhooks API (2个端点, 13 tests)

### 已修复的关键问题

#### P0 (CRITICAL) - 100% 完成

| 问题 | 状态 | 修复日期 | Commit |
|------|------|----------|--------|
| P0-010 Stripe 退款 Webhook | ✅ 已修复 | 2026-01-10 | `3ad688d`, `f528710` |
| P0-013 Cache Clear All 安全防护 | ✅ 已修复 | 2026-01-10 | `57526fa` |
| P0-014 Marketplace Category 约束 | ✅ 已验证 | 2026-01-10 | - |
| P0-015 Marketplace allowed_tiers 默认值 | ✅ 已修复 | 2026-01-10 | `37ddc5c` |
| M-P0-001 购买流程事务保护 | ✅ 已验证 | 2026-01-10 | (代码已完善) |

#### P1 (HIGH) - 100% 完成

| 问题 | 状态 | 修复日期 | Commit |
|------|------|----------|--------|
| Tier 命名统一 (t1/t2/t3) | ✅ 已完成 | 2026-01-10 | `c0906a2` |
| 分页模式迁移 (offset+limit) | ✅ 已完成 | 2026-01-10 | `d750fed` |
| 性能索引创建 (5个) | ✅ 已完成 | 2026-01-10 | `28e4c0a` |
| Marketplace RPC 函数 | ✅ 已完成 | 2026-01-10 | `11350d2`, `96efba4` |
| seller_id CHECK 约束 | ✅ 已完成 | 2026-01-10 | `52d4704` |
| contains_locked_elements 逻辑 | ✅ 已完成 | 2026-01-10 | `558bfd5` |

#### P2 (MEDIUM) - 100% 完成

| 问题 | 状态 | 修复日期 |
|------|------|----------|
| AI Insights DDD 迁移 | ✅ 已完成 | 2026-01-11 |
| JSONB Schema 定义 | ✅ 已完成 | 2026-01-11 |
| Tier Naming 统一 | ✅ 已完成 | 2026-01-11 |
| Marketplace SSRF 防护 | ✅ 已完成 | 2026-01-11 |
| 返回类型迁移 (4模块) | ✅ 已完成 | 2026-01-11 |
| PDF/ZIP 异步导出 | ✅ 已完成 | 2026-01-11 |

### 架构改进统计

**代码质量提升**:
- 总API端点数: 258 (User: 123 + Admin: 135)
- DDD架构合规: 100%
- 测试覆盖率: 65%+ (目标: 60%)
- 安全防护覆盖: 95%+

**性能优化**:
- Marketplace Listings: 5x-10x (RPC 函数)
- PDF Export: 5.3x (异步队列)
- 数据库索引: 5个性能索引 (部分索引优化)

**安全加固**:
- DoS防护: 17+ 参数长度限制
- SSRF防护: URL白名单验证
- Cache Clear: 两步确认 + 一次性token
- 审计日志: 所有删除操作记录

---

## 2. 基础信息

### 2.1 API 基础路径

| 环境 | 基础 URL |
|------|----------|
| 生产 | `https://api.makedecodables.com` |
| 开发 | `http://localhost:8000` |

### 2.2 认证方式

所有用户端点需要 Clerk JWT Token:

```http
Authorization: Bearer <clerk_jwt_token>
```

### 2.3 通用响应格式

**成功响应**:
```json
{
  "status": "success",
  "data": { ... }
}
```

**错误响应**:
```json
{
  "detail": "错误描述",
  "error_code": "ERROR_CODE"
}
```

### 2.4 分页参数

大部分列表接口支持分页:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `limit` | int | 20 | 每页数量 (最大 100) |

---

## 3. 健康检查 API

### GET `/health`

基础健康检查

**响应**:
```json
{
  "status": "healthy",
  "version": "3.24",
  "environment": "production",
  "services": {
    "database": "connected",
    "redis": "connected",
    "stripe": "configured"
  }
}
```

### GET `/health/detailed`

详细健康检查（含队列信息）

**响应**:
```json
{
  "status": "healthy",
  "services": { ... },
  "queues": {
    "high": 0,
    "default": 5,
    "low": 12
  },
  "workers": {
    "active": 3,
    "idle": 1
  },
  "warnings": []
}
```

---

## 4. Webhooks

> ⚠️ **重要**: Webhooks 用于第三方平台回调，需在对应平台配置正确的 URL

### 4.1 Clerk Webhook

**URL**: `POST /api/v2/user/webhooks/clerk`

**配置位置**: Clerk Dashboard → Webhooks

**需要订阅的事件**:
- `user.created` - 用户注册
- `user.updated` - 用户信息更新
- `session.created` - 用户登录
- `session.ended` - 用户登出
- `session.removed` - 会话移除
- `session.revoked` - 会话撤销

**请求头**:
```http
svix-id: <event_id>
svix-timestamp: <timestamp>
svix-signature: <signature>
```

**处理逻辑**:

| 事件 | 处理动作 |
|------|----------|
| `user.created` | 创建用户档案、赠送 50 永久积分 |
| `user.updated` | 更新头像/用户名/姓名 |
| `session.created` | 记录登录活动 |
| `session.*` (结束) | 记录登出活动 |

**响应**:
```json
{
  "status": "success",
  "reason": "user_created"
}
```

---

### 4.2 Stripe Webhook

**URL**: `POST /api/v2/user/webhooks/stripe`

**配置位置**: Stripe Dashboard → Developers → Webhooks

**需要订阅的事件**:
- `checkout.session.completed` - 结账完成
- `invoice.payment_succeeded` - 发票支付成功
- `customer.subscription.deleted` - 订阅删除
- `customer.subscription.updated` - 订阅更新

**请求头**:
```http
Stripe-Signature: <signature>
```

**处理逻辑**:

| 事件 | 处理动作 |
|------|----------|
| `checkout.session.completed` | 积分购买: +100/500/2000 永久积分<br>订阅启动: Starter +200 / Pro +500 月度积分 |
| `invoice.payment_succeeded` | 订阅续费: 重置月度积分（不累积） |
| `customer.subscription.deleted` | 降级为 Free 等级 |
| `customer.subscription.updated` | 更新订阅状态 |

**Metadata 说明**:

checkout.session 需要携带的 metadata:
```json
{
  "user_id": "clerk_user_id",
  "plan": "t2|t3|credits_100"
}
```

**响应**:
```json
{
  "status": "processed",
  "action": "subscription_started",
  "user_id": "user_xxx"
}
```

---

## 5. 用户 API

前缀: `/api/v2/user`

### 7.1 用户档案 `/profile`

#### GET `/profile/me`

获取当前用户信息

**响应**:
```json
{
  "id": "user_xxx",
  "email": "user@example.com",
  "username": "username",
  "avatar_url": "https://...",
  "first_name": "John",
  "last_name": "Doe",
  "tier": "t2",
  "credits_monthly": 450,
  "credits_permanent": 50,
  "credits_total": 500,
  "is_member": true,
  "subscription_status": "active",
  "timezone": "America/New_York",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### GET `/profile/history`

获取积分交易历史

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | int | 1 | 页码 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "items": [
    {
      "id": "tx_xxx",
      "amount": -5,
      "bucket": "monthly",
      "type": "ai_generation",
      "description": "AI 图像生成",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 100,
  "page": 1
}
```

#### GET `/profile/purchases`

获取市场购买记录

**响应**:
```json
{
  "purchases": [
    {
      "id": "purchase_xxx",
      "listing_id": "listing_xxx",
      "listing_title": "可爱动物贴纸包",
      "price_credits": 50,
      "purchased_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### GET `/profile/notifications`

获取用户通知

**响应**:
```json
{
  "notifications": [
    {
      "id": "notif_xxx",
      "title": "欢迎加入",
      "content": "您已获得 50 积分",
      "type": "system",
      "is_read": false,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### POST `/profile/notifications/{id}/read`

标记通知为已读

**响应**:
```json
{
  "status": "success"
}
```

#### POST `/profile/notifications/read-all`

标记所有通知为已读

**响应**:
```json
{
  "status": "success"
}
```

#### PUT `/profile/timezone`

更新时区偏好

**请求体**:
```json
{
  "timezone": "Asia/Shanghai"
}
```

**响应**:
```json
{
  "status": "success",
  "timezone": "Asia/Shanghai"
}
```

---

### 4.2 项目管理 `/projects`

#### GET `/projects`

获取用户项目列表

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | int | 1 | 页码 |
| `limit` | int | 20 | 每页数量 |
| `search` | string | - | 搜索关键词 |
| `include_canvas_data` | bool | true | 是否包含画布数据 |

**响应**:
```json
{
  "items": [
    {
      "id": "proj_xxx",
      "title": "我的迷你书",
      "thumbnail_url": "https://...",
      "canvas_data": { ... },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-02T00:00:00Z"
    }
  ],
  "total": 15,
  "page": 1
}
```

#### GET `/projects/dashboard`

仪表板项目视图

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `view` | string | "all" | 视图类型: `all`, `bought`, `selling` |
| `page` | int | 1 | 页码 |
| `limit` | int | 20 | 每页数量 |
| `search` | string | - | 搜索关键词 |

**响应**:
```json
{
  "items": [ ... ],
  "total_count": 50
}
```

#### GET `/projects/deleted`

获取已删除项目（垃圾箱）

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | int | 1 | 页码 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "deleted_projects": [
    {
      "id": "proj_xxx",
      "title": "已删除项目",
      "deleted_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### GET `/projects/seller-stats`

获取卖家统计

**响应**:
```json
{
  "total_selling": 5,
  "total_sales": 120,
  "unique_buyers": 45
}
```

#### POST `/projects`

创建新项目

**请求体**:
```json
{
  "title": "我的新迷你书",
  "canvas_data": { ... }
}
```

**响应**:
```json
{
  "id": "proj_xxx",
  "title": "我的新迷你书",
  "canvas_data": { ... },
  "created_at": "2024-01-01T00:00:00Z"
}
```

**错误**:
- `403`: 超出项目限制 (Free=1, Starter=20, Pro=200)

#### GET `/projects/{project_id}`

获取项目详情

**响应**:
```json
{
  "id": "proj_xxx",
  "title": "我的迷你书",
  "canvas_data": { ... },
  "thumbnail_url": "https://...",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T00:00:00Z"
}
```

#### PUT `/projects/{project_id}`

更新项目

**请求体**:
```json
{
  "title": "更新后的标题",
  "canvas_data": { ... },
  "thumbnail_url": "https://...",
  "used_listing_ids": ["listing_1", "listing_2"]
}
```

**响应**:
```json
{
  "status": "success",
  "locked_elements": []
}
```

#### DELETE `/projects/{project_id}`

删除项目

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `permanent` | bool | false | 是否永久删除 |

**响应**:
```json
{
  "status": "success",
  "stage": 1
}
```

> **删除阶段**: Stage 1 = 软删（可恢复），Stage 2 = 永久隐藏

#### POST `/projects/{project_id}/restore`

恢复已删除项目

**响应**:
```json
{
  "status": "success",
  "project": { ... }
}
```

#### POST `/projects/{project_id}/duplicate`

复制项目

**响应**:
```json
{
  "id": "proj_new_xxx",
  "title": "我的迷你书 (副本)",
  ...
}
```

---

### 4.3 计费管理 `/billing`

#### GET `/billing/credits`

获取积分余额

**响应**:
```json
{
  "monthly_credits": 450,
  "permanent_credits": 50,
  "total_credits": 500,
  "tier": "starter"
}
```

#### GET `/billing/transactions`

获取交易历史

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 20 | 每页数量 |
| `offset` | int | 0 | 偏移量 |
| `tx_type` | string | - | 交易类型筛选 |
| `start_date` | string | - | 开始日期 |
| `end_date` | string | - | 结束日期 |

**响应**:
```json
{
  "transactions": [ ... ],
  "total_count": 100
}
```

#### GET `/billing/can-afford`

检查是否能负担操作

**参数** (二选一):
| 参数 | 类型 | 说明 |
|------|------|------|
| `amount` | int | 直接指定积分数量 |
| `operation` | string | 操作类型: `ai_image`, `ai_text`, `smart_scan` |

**响应**:
```json
{
  "can_afford": true,
  "current_balance": 500,
  "required_amount": 5
}
```

---

### 4.4 支付 `/payment`

#### POST `/payment/checkout`

创建 Stripe 结账会话

**请求体**:
```json
{
  "plan_type": "t2"
}
```

> `plan_type`: `t2`, `t3`

**响应**:
```json
{
  "url": "https://checkout.stripe.com/...",
  "discount_applied": false
}
```

**限流**: 5 次/分钟

#### POST `/payment/portal`

获取 Stripe 账单门户

**响应**:
```json
{
  "url": "https://billing.stripe.com/..."
}
```

**限流**: 10 次/分钟

---

### 4.5 AI 生成 `/generate`

#### POST `/generate/images`

同步生成图像

**请求体**:
```json
{
  "prompts": ["一只可爱的猫咪"],
  "num_images": 1,
  "image_size": "square_hd",
  "reference_image": null,
  "generation_mode": "fast",
  "creativity_level": 0.7
}
```

**参数说明**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `prompts` | array | 必填 | 提示词数组 |
| `num_images` | int | 1 | 生成数量 (1-4) |
| `image_size` | string | "square_hd" | 尺寸: `square`, `square_hd`, `portrait_4_3`, `landscape_4_3`, `portrait_16_9`, `landscape_16_9` |
| `reference_image` | string | null | 参考图像 URL |
| `generation_mode` | string | "fast" | 模式: `fast`, `quality` |
| `creativity_level` | float | 0.7 | 创意程度 (0-1) |

**响应**:
```json
{
  "image_urls": ["https://..."],
  "balance": {
    "monthly": 445,
    "permanent": 50,
    "total": 495
  },
  "model_used": "flux-schnell",
  "prompt_enhanced": "一只可爱的猫咪, 高清, 细节丰富",
  "generation_id": "gen_xxx"
}
```

**积分消耗**:
- 基础生成: 5 积分/张
- 带参考图: 7 积分/张

**模型选择**:
- Free/Starter: `flux-schnell`
- Pro: `flux-dev`

#### POST `/generate/images/async`

异步生成图像（推荐用于大批量）

**请求体**: 同上

**响应**:
```json
{
  "task_id": "task_xxx",
  "status": "pending",
  "credits_charged": 5,
  "poll_url": "/api/v2/user/tasks/task_xxx",
  "websocket_url": "ws://..."
}
```

#### POST `/generate/story`

生成故事结构

**请求体**:
```json
{
  "topic": "小兔子学勇气"
}
```

**响应**:
```json
{
  "pages": [
    {
      "page_number": 1,
      "text": "从前有一只小兔子...",
      "image_prompt": "一只可爱的小兔子在森林里"
    },
    ...
  ]
}
```

**积分消耗**: 1 积分

#### POST `/generate/inspiration`

获取创意灵感（免费）

**请求体**:
```json
{
  "category": "character"
}
```

> `category`: `all`, `character`, `scene`, `story`

**响应**:
```json
{
  "suggestions": [
    "一只穿着太空服的小猫",
    "一个会说话的魔法南瓜",
    ...
  ],
  "category": "character",
  "fallback": false
}
```

#### POST `/generate/pdf`

生成折叠式迷你书 PDF（免费）

**请求体**:
```json
{
  "project_id": "proj_xxx",
  "image_urls": ["https://...", ...],
  "texts": ["封面文字", "第一页...", ...],
  "current_hash": "abc123"
}
```

**响应**: PDF 文件流

**Headers**:
```http
Content-Type: application/pdf
Content-Disposition: attachment; filename="minibook.pdf"
```

---

### 4.6 生成历史 `/generations`

#### GET `/generations/history`

获取生成历史

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 20 | 每页数量 |
| `offset` | int | 0 | 偏移量 |
| `favorites_only` | bool | false | 仅显示收藏 |

**响应**:
```json
{
  "generations": [
    {
      "id": "gen_xxx",
      "prompt": "一只猫咪",
      "image_url": "https://...",
      "is_favorited": false,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

#### PATCH `/generations/{generation_id}`

更新生成属性（推荐）

**请求体**:
```json
{
  "is_favorited": true
}
```

**响应**:
```json
{
  "success": true,
  "is_favorited": true
}
```

#### DELETE `/generations/{generation_id}`

删除生成记录

**响应**:
```json
{
  "success": true,
  "deleted": true
}
```

#### POST `/generations/batch-delete`

批量删除（推荐）

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `keep_favorites` | bool | true | 保留收藏 |

**响应**:
```json
{
  "success": true,
  "deleted_count": 45
}
```

---

### 4.7 市场 `/marketplace`

#### GET `/marketplace/listings`

获取市场商品列表

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `featured` | bool | false | 仅精选 |
| `resource_type` | string | - | 资源类型筛选 |
| `sort` | string | "latest" | 排序: `latest`, `popular`, `price_low`, `price_high` |
| `tier` | string | - | 等级筛选: `t1`, `t2`, `t3` |
| `price` | string | - | 价格筛选: `t1`, `paid` |
| `page` | int | 1 | 页码 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "items": [
    {
      "id": "listing_xxx",
      "title": "可爱动物贴纸包",
      "description": "包含 20 个可爱动物贴纸",
      "thumbnail_url": "https://...",
      "resource_type": "sticker",
      "price_credits": 50,
      "allowed_tiers": ["t2", "t3"],
      "seller": {
        "id": "user_xxx",
        "username": "creator",
        "avatar_url": "https://..."
      },
      "download_count": 120,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 500,
  "page": 1
}
```

#### GET `/marketplace/listings/{listing_id}`

获取商品详情

**响应**:
```json
{
  "id": "listing_xxx",
  "title": "可爱动物贴纸包",
  "description": "包含 20 个可爱动物贴纸...",
  "thumbnail_url": "https://...",
  "resource_url": "https://...",
  "resource_type": "sticker",
  "price_credits": 50,
  "allowed_tiers": ["t2", "t3"],
  "seller": { ... },
  "is_purchased": false,
  "can_purchase": true,
  "download_count": 120,
  "version": "1.0",
  "changelog": "",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### POST `/marketplace/listings`

发布商品到市场

**请求体**:
```json
{
  "title": "我的贴纸包",
  "description": "精心设计的贴纸",
  "thumbnail_url": "https://...",
  "resource_url": "https://...",
  "resource_type": "sticker",
  "price_credits": 30,
  "allowed_tiers": ["t2", "t3"],
  "submit_for_review": true
}
```

**响应**:
```json
{
  "listing_id": "listing_xxx",
  "moderation_status": "pending",
  "message": "商品已提交审核"
}
```

**权限**:
- Second Tier (t2): 仅能发布免费资源（allowed_tiers 包含 t2）
- Third Tier (t3): 可发布任意价格资源

#### PUT `/marketplace/listings/{listing_id}`

更新商品

**请求体**:
```json
{
  "title": "更新后的标题",
  "description": "更新后的描述",
  "price_credits": 40,
  "allowed_tiers": ["t3"]
}
```

**响应**:
```json
{
  "status": "success",
  "listing_id": "listing_xxx",
  "requires_resubmit": true
}
```

> 如果修改了关键字段，需要重新审核

#### DELETE `/marketplace/listings/{listing_id}`

下架商品

**响应**:
```json
{
  "status": "success"
}
```

#### POST `/marketplace/purchase`

购买商品

**请求体**:
```json
{
  "listing_id": "listing_xxx",
  "idempotency_key": "unique_key_xxx",
  "utm_source": "homepage",
  "utm_medium": "featured"
}
```

**响应**:
```json
{
  "success": true,
  "listing_id": "listing_xxx",
  "project_id": "proj_xxx",
  "credits_deducted": 50
}
```

**错误**:
- `400`: 积分不足
- `400`: 已购买过
- `403`: 等级不满足

#### GET `/marketplace/my-listings`

获取我的商品列表

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | int | 1 | 页码 |
| `limit` | int | 20 | 每页数量 |

**响应**:
```json
{
  "items": [ ... ],
  "total": 5,
  "page": 1
}
```

#### GET `/marketplace/seller/stats`

获取卖家统计

**响应**:
```json
{
  "total_earned_credits": 5000,
  "listings_count": 10,
  "total_sales": 120,
  "total_usage": 350
}
```

#### GET `/marketplace/leaderboard`

获取排行榜

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `period` | string | "monthly" | 周期: `monthly`, `all_time` |
| `type` | string | "all" | 类型: `all`, `sticker`, `template` |

**响应**:
```json
{
  "items": [
    {
      "rank": 1,
      "seller": { ... },
      "total_sales": 500,
      "total_earnings": 25000
    }
  ],
  "period": "monthly",
  "type": "all"
}
```

#### POST `/marketplace/report`

举报商品

**请求体**:
```json
{
  "listing_id": "listing_xxx",
  "reason": "侵权内容"
}
```

**响应**:
```json
{
  "success": true,
  "report_id": "report_xxx",
  "message": "举报已提交"
}
```

---

### 4.8 系统资源 `/resources`

#### GET `/resources`

获取系统资源列表

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `type` | string | - | 资源类型 |
| `category` | string | - | 分类 |
| `tier` | string | - | 等级筛选 |
| `search` | string | - | 搜索关键词 |
| `page` | int | 1 | 页码 |
| `limit` | int | 20 | 每页数量 |
| `include_locked` | bool | true | 是否包含锁定资源 |

**响应**:
```json
{
  "items": [
    {
      "id": "res_xxx",
      "name": "可爱猫咪贴纸",
      "type": "sticker",
      "category": "animals",
      "thumbnail_url": "https://...",
      "resource_url": "https://...",
      "is_locked": false,
      "required_tier": "t1"
    }
  ],
  "total": 200,
  "page": 1,
  "has_more": true
}
```

#### GET `/resources/types`

获取所有资源类型

**响应**:
```json
{
  "types": ["sticker", "background", "template", "clipart", "frame", "pattern"]
}
```

#### GET `/resources/categories/{resource_type}`

获取资源类型的分类

**响应**:
```json
{
  "categories": ["animals", "food", "nature", "characters", "objects"]
}
```

#### GET `/resources/stickers`

获取贴纸（便捷端点）

**参数**: 同 `/resources`

#### GET `/resources/backgrounds`

获取背景（便捷端点）

#### GET `/resources/templates`

获取模板（便捷端点）

---

### 4.9 用户资源 `/assets`

#### GET `/assets`

获取用户资源

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `project_id` | string | - | 项目 ID（可选） |
| `scope` | string | "project" | 范围: `project`, `all`（Pro 可用） |

**响应**:
```json
{
  "assets": [
    {
      "id": "asset_xxx",
      "url": "https://...",
      "type": "image",
      "filename": "my_image.png",
      "project_id": "proj_xxx",
      "usage_count": 5,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### POST `/assets`

上传资源（Pro 专属）

**请求**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | file | 文件（≤5MB） |

**支持格式**: JPEG, PNG, GIF, WebP, SVG

**响应**:
```json
{
  "url": "https://...",
  "filename": "uploaded_image.png"
}
```

#### DELETE `/assets/{asset_id}`

删除资源

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `permanent` | bool | false | 是否永久删除 |

**响应**:
```json
{
  "status": "success",
  "action": "soft_deleted",
  "asset_id": "asset_xxx"
}
```

#### POST `/assets/from-url`

从 URL 添加资源

**请求体**:
```json
{
  "url": "https://example.com/image.png",
  "project_id": "proj_xxx"
}
```

**响应**:
```json
{
  "status": "success",
  "asset": { ... }
}
```

#### GET `/assets/check-url`

验证 URL 有效性

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | string | 要验证的 URL |

**响应**:
```json
{
  "valid": true,
  "content_type": "image/png",
  "status_code": 200
}
```

#### GET `/assets/deleted`

获取已删除资源（垃圾箱）

**响应**:
```json
{
  "deleted_assets": [ ... ]
}
```

#### POST `/assets/{asset_id}/restore`

恢复资源

**响应**:
```json
{
  "status": "success",
  "asset": { ... }
}
```

---

### 4.10 模板 `/templates`

#### 资源模板 (5W1H)

##### GET `/templates/asset`

获取资源提示词模板列表

**响应**:
```json
{
  "templates": [
    {
      "id": "tpl_xxx",
      "name": "可爱动物风格",
      "who_subject": "小猫",
      "who_appearance": "橙色条纹",
      "what_action": "睡觉",
      "what_expression": "安详",
      "where_setting": "窗台上",
      "where_time": "下午",
      "style": "卡通",
      "moods": ["温馨", "可爱"],
      "creativity_level": 0.7,
      "use_count": 15,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

##### POST `/templates/asset`

创建资源模板

**请求体**:
```json
{
  "name": "我的模板",
  "who_subject": "小狗",
  "who_appearance": "金毛",
  "what_action": "奔跑",
  "what_expression": "开心",
  "where_setting": "草地",
  "where_time": "清晨",
  "style": "水彩",
  "moods": ["活泼", "快乐"],
  "creativity_level": 0.8
}
```

**响应**:
```json
{
  "success": true,
  "template": { ... }
}
```

**限制**: 每用户最多 20 个模板

##### PUT `/templates/asset/{template_id}`

更新模板

##### DELETE `/templates/asset/{template_id}`

删除模板

##### POST `/templates/asset/{template_id}/use`

标记使用

**响应**:
```json
{
  "success": true,
  "use_count": 16
}
```

#### 页面模板

##### GET `/templates/page`

获取页面模板列表

##### POST `/templates/page`

创建页面模板

**请求体**:
```json
{
  "name": "童话故事模板",
  "layout": "story_page",
  "story_theme": "冒险",
  "main_character": "小勇士",
  "style": "童话插画",
  "creativity_level": 0.6
}
```

##### PUT `/templates/page/{template_id}`

更新页面模板

##### DELETE `/templates/page/{template_id}`

删除页面模板

---

### 4.11 分析 `/analytics`

#### POST `/analytics/events`

批量记录分析事件

**请求体**:
```json
{
  "events": [
    {
      "event_type": "project_create_complete",
      "properties": {
        "project_id": "proj_xxx",
        "pages_count": 8
      },
      "env": {
        "browser": "Chrome",
        "os": "MacOS"
      },
      "user_properties": {
        "tier": "t2"
      }
    }
  ]
}
```

**响应**:
```json
{
  "status": "success",
  "count": 1,
  "ip": "xxx.xxx.xxx.xxx",
  "country": "US"
}
```

**支持的事件类型**:
- `project_create_complete`
- `project_print`
- `project_export_pdf`
- `project_delete`
- `ai_generation_complete`
- `marketplace_purchase`
- `template_use`
- `feature_use`

---

### 4.12 配置 `/config`

#### GET `/config`

获取所有公开配置

**响应**:
```json
{
  "configs": {
    "feature_flags": {
      "new_editor": true,
      "ai_v2": false
    },
    "limits": {
      "max_file_size": 5242880,
      "max_projects_t1": 1
    }
  }
}
```

#### GET `/config/{key}`

获取单个配置

**响应**:
```json
{
  "key": "feature_flags.new_editor",
  "value": true
}
```

#### GET `/config/group/{group_name}`

获取配置组

**响应**:
```json
{
  "group": "feature_flags",
  "configs": {
    "new_editor": true,
    "ai_v2": false
  }
}
```

---

### 4.13 主题 `/themes`

#### GET `/themes/active`

获取当前激活主题

**响应**:
```json
{
  "theme": {
    "id": "theme_xxx",
    "name": "春季主题",
    "colors": { ... },
    "assets": { ... }
  }
}
```

#### GET `/themes/list`

获取所有主题

**响应**:
```json
{
  "themes": [ ... ]
}
```

#### POST `/themes/select`

选择主题

**请求体**:
```json
{
  "theme_id": "theme_xxx"
}
```

---

### 4.14 活动 `/campaigns`

#### GET `/campaigns/active`

获取活跃活动

**响应**:
```json
{
  "campaigns": [
    {
      "id": "camp_xxx",
      "name": "新年活动",
      "type": "bonus",
      "reward": {
        "credits": 100
      },
      "ends_at": "2024-02-01T00:00:00Z",
      "is_claimed": false
    }
  ]
}
```

#### POST `/campaigns/{id}/claim`

领取奖励

**响应**:
```json
{
  "success": true,
  "reward": {
    "credits": 100
  }
}
```

#### POST `/campaigns/{id}/dismiss`

关闭活动通知

---

### 4.15 导出 `/export`

#### GET `/export/projects/{project_id}/pdf`

导出项目 PDF

**响应**: PDF 文件流

#### GET `/export/projects/{project_id}/preview`

生成预览图

**响应**: 图片文件流

#### POST `/export/zip`

生成 ZIP 包

**请求体**:
```json
{
  "project_ids": ["proj_1", "proj_2"],
  "include_canvas_data": true
}
```

**响应**: ZIP 文件流

---

### 4.16 任务 `/tasks`

#### GET `/tasks/{task_id}`

获取任务状态

**响应**:
```json
{
  "task_id": "task_xxx",
  "status": "completed",
  "progress": 100,
  "result": {
    "image_urls": ["https://..."]
  },
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:00:30Z"
}
```

**状态**: `pending`, `processing`, `completed`, `failed`, `cancelled`

#### POST `/tasks/{task_id}/cancel`

取消任务

**响应**:
```json
{
  "success": true,
  "status": "cancelled"
}
```

---

### 4.17 支持 `/support`

#### POST `/support/ticket`

创建支持工单

**请求体**:
```json
{
  "subject": "功能建议",
  "message": "希望能增加...",
  "type": "feature_request"
}
```

#### POST `/support/feedback`

提交反馈

**请求体**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `message` | string | 反馈内容 |
| `images` | file[] | 截图（可选） |

---

### 4.18 实验 `/experiments`

#### GET `/experiments/active`

获取用户参与的实验

**响应**:
```json
{
  "experiments": [
    {
      "id": "exp_xxx",
      "name": "new_pricing_page",
      "variant": "control"
    }
  ]
}
```

#### POST `/experiments/{id}/expose`

记录实验曝光

---

## 6. 管理员 API

前缀: `/api/v2/admin`

> ⚠️ 需要管理员权限

### 7.1 用户管理

#### GET `/users`

搜索用户

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | string | 搜索关键词（邮箱/用户名） |

#### GET `/users/by-tier/{tier}`

按等级获取用户

#### GET `/users/{uid}`

获取用户详情（审计）

**响应**:
```json
{
  "profile": { ... },
  "credits": {
    "monthly": 450,
    "permanent": 50,
    "total": 500
  },
  "subscriptions": [ ... ],
  "activity": [ ... ]
}
```

#### POST `/users/{uid}/credits`

调整用户积分

**请求体**:
```json
{
  "amount": 100,
  "bucket": "permanent",
  "reason": "补偿用户问题"
}
```

#### POST `/users/{uid}/tier`

更新用户等级

**请求体**:
```json
{
  "tier": "t3"
}
```

#### POST `/users/{uid}/discount`

创建用户折扣

**请求体**:
```json
{
  "discount_percent": 20,
  "valid_days": 7,
  "target_plan": "t3"
}
```

---

### 7.2 订阅管理 `/subscriptions`

#### POST `/subscriptions/refund`

处理退款

**请求体**:
```json
{
  "user_id": "user_xxx",
  "user_code": "ABC123",
  "payment_intent_id": "pi_xxx",
  "amount_cents": 1490,
  "reason": "用户要求退款"
}
```

> `user_code` 用于二次确认，防止误操作

#### POST `/subscriptions/cancel`

取消订阅

**请求体**:
```json
{
  "user_id": "user_xxx",
  "user_code": "ABC123",
  "subscription_id": "sub_xxx",
  "immediate": false,
  "reason": "用户要求取消"
}
```

#### POST `/subscriptions/downgrade`

降级订阅

**请求体**:
```json
{
  "user_id": "user_xxx",
  "user_code": "ABC123",
  "user_email": "user@example.com",
  "target_tier": "t2",
  "immediate": false,
  "reason": "用户要求降级"
}
```

---

### 7.3 统计仪表板

#### GET `/stats/dashboard`

获取仪表板汇总

#### GET `/stats/revenue`

获取收入统计

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `start_date` | string | 开始日期 |
| `end_date` | string | 结束日期 |

#### GET `/stats/users`

获取用户统计

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `period` | string | "month" | 周期: `today`, `week`, `month` |

#### GET `/stats/projects`

获取项目统计

---

### 7.4 AI 洞察 `/ai`

#### GET `/ai/insights`

获取 AI 洞察

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `type` | string | "all" | 类型筛选 |

#### GET `/ai/recommendations`

获取优化建议

**参数**:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `area` | string | "all" | 领域: `ux`, `pricing`, `marketing`, `retention` |

#### GET `/ai/behavior-analysis`

获取用户行为分析

#### POST `/ai/generate-report`

生成商业智能报告

---

### 7.5 内容审核 `/moderation`

#### GET `/moderation/pending`

获取待审核列表

#### POST `/moderation/approve/{listing_id}`

批准商品

#### POST `/moderation/reject/{listing_id}`

拒绝商品

**请求体**:
```json
{
  "reason": "内容不符合规范"
}
```

#### GET `/moderation/reports`

获取举报列表

#### POST `/moderation/reports/{report_id}/action`

处理举报

**请求体**:
```json
{
  "action": "remove_listing",
  "reason": "确认违规"
}
```

---

### 7.6 通知管理 `/notifications`

#### GET `/notifications`

获取通知列表

#### POST `/notifications/send`

发送通知

**请求体**:
```json
{
  "type": "broadcast",
  "target": "all",
  "title": "系统公告",
  "content": "我们更新了新功能..."
}
```

---

### 7.7 系统配置 `/config`

#### GET `/config`

获取系统配置

#### PUT `/config/{key}`

更新配置

**请求体**:
```json
{
  "value": "new_value"
}
```

---

### 6.8 实验管理 `/experiments`

#### GET `/experiments`

获取所有实验

#### POST `/experiments`

创建 A/B 实验

**请求体**:
```json
{
  "name": "new_pricing_page",
  "description": "测试新定价页面",
  "variants": [
    {"name": "control", "weight": 50},
    {"name": "treatment", "weight": 50}
  ],
  "target_users": "all"
}
```

#### PUT `/experiments/{id}`

更新实验

#### POST `/experiments/{id}/results`

获取实验结果

---

## 7. 业务规则速查

### 7.1 用户等级

| 系统代码 | 简称 | 显示名称 | 原价 | 现价 | 月度积分 | 项目限制 | AI 模型 |
|---------|------|---------|------|------|----------|----------|---------|
| `t1` | First Tier | Free Plan | $0 | $0 | 0 | 1 | flux-schnell |
| `t2` | Second Tier | Starter Plan | $14.9 | $9.9 | 200 | 20 | flux-schnell |
| `t3` | Third Tier | Pro Plan | $29.9 | $19.9 | 500 | 200 | flux-dev |

> **价格配置说明**:
> - 所有价格存储在 `pricing_plans` 表中，支持灵活调整
> - Stripe Price ID 区分生产/开发环境
> - 支持用户专属定价 (通过 `user_price_overrides` 表)
> - 详见: [PRICING-SYSTEM-DESIGN.md](shared/PRICING-SYSTEM-DESIGN.md)

### 7.2 积分购买档位

| 档位 | 积分 | 原价 | 现价 | 折扣 | Plan Code |
|------|------|------|------|------|-----------|
| 小包 | 100 | $2.99 | $2.99 | - | `credits_100` |
| 中包 | 500 | $14.99 | $13.49 | 10% off | `credits_500` |
| 大包 | 2000 | $60.00 | $48.00 | 20% off | `credits_2000` |

> **重要**: 充值积分**永久有效**，不会过期

### 7.3 积分消耗

| 操作 | 积分 |
|------|------|
| AI 图像生成（基础） | 5 |
| AI 图像生成（带参考图） | 7 |
| AI 文字生成 | 1 |
| Smart Scan | 10 |
| PDF 导出 | 免费 |
| 灵感生成 | 免费 |

### 7.4 积分扣费顺序

```
月度积分 (credits_monthly) → 永久积分 (credits_permanent)
```

### 7.5 市场收益分配

- 卖家: 90%
- 平台: 10%

### 7.6 发布权限

| 系统代码 | 简称 | 可发布资源 |
|---------|------|------------|
| `t1` | First Tier | 不可发布 |
| `t2` | Second Tier | 仅免费资源 |
| `t3` | Third Tier | 任意价格资源 |

### 7.7 删除流程

| 阶段 | 操作 | 可恢复 |
|------|------|--------|
| Stage 1 | 软删除 | ✅ |
| Stage 2 | 永久隐藏 | ❌ |

---

## 8. 错误码说明

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 冲突（如重复购买） |
| 422 | 数据验证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

### 常见业务错误码

| 错误码 | 说明 |
|--------|------|
| `INSUFFICIENT_CREDITS` | 积分不足 |
| `PROJECT_LIMIT_REACHED` | 项目数量达到上限 |
| `ALREADY_PURCHASED` | 已购买过该商品 |
| `TIER_NOT_ALLOWED` | 等级不满足要求 |
| `INVALID_SIGNATURE` | Webhook 签名验证失败 |
| `DUPLICATE_EVENT` | 重复的 Webhook 事件 |

---

### 4.19 新手引导 `/onboarding`

#### GET `/onboarding/steps`

获取新手引导步骤

**响应**:
```json
{
  "steps": [
    {
      "id": "create_first_project",
      "title": "创建你的第一个项目",
      "description": "体验 Make Decodables 强大的编辑器",
      "completed": false,
      "order": 1
    }
  ]
}
```

#### POST `/onboarding/steps/{step_id}/complete`

标记步骤为已完成

**响应**:
```json
{
  "success": true,
  "next_step_id": "upload_first_asset"
}
```

---

### 4.20 推荐系统 `/referrals`

#### GET `/referrals/code`

获取用户推荐码

**响应**:
```json
{
  "referral_code": "ABC123",
  "referral_count": 5,
  "bonus_credits_earned": 250
}
```

#### GET `/referrals/stats`

获取推荐统计

**响应**:
```json
{
  "total_referrals": 5,
  "successful_conversions": 3,
  "pending_referrals": 2,
  "total_credits_earned": 250
}
```

---

### 4.21 工具 `/tools`

#### POST `/tools/color-picker`

颜色选择器工具

**请求**:
```json
{
  "image_url": "https://...",
  "x": 100,
  "y": 150
}
```

**响应**:
```json
{
  "hex": "#FF5733",
  "rgb": {"r": 255, "g": 87, "b": 51}
}
```

---

### 4.22 日志 `/logs`

#### GET `/logs/activities`

获取用户活动日志

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `limit` | int | 返回数量 (默认: 20) |
| `offset` | int | 偏移量 (默认: 0) |
| `activity_type` | string | 活动类型过滤 |

**响应**:
```json
{
  "logs": [
    {
      "id": "log_xxx",
      "activity_type": "project_created",
      "description": "创建项目: 我的第一本书",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 100
}
```

---

### 4.23 用户档案 `/user_profile`

#### GET `/user_profile/settings`

获取用户设置

**响应**:
```json
{
  "language": "en",
  "timezone": "America/New_York",
  "email_notifications": true,
  "auto_save": true
}
```

#### PATCH `/user_profile/settings`

更新用户设置

**请求**:
```json
{
  "language": "zh-CN",
  "auto_save": false
}
```

---

### 4.24 用户资源 `/user_assets`

#### GET `/user_assets`

获取用户上传的资源列表

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `type` | string | 资源类型 (image/sticker/background) |
| `limit` | int | 返回数量 |
| `offset` | int | 偏移量 |

**响应**:
```json
{
  "assets": [
    {
      "id": "asset_xxx",
      "type": "sticker",
      "url": "https://...",
      "filename": "my_sticker.png",
      "uploaded_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 50
}
```

---

### 4.25 AI 图片生成 `/generation_images`

#### POST `/generation_images/generate`

生成 AI 图片

**请求**:
```json
{
  "prompt": "A cute cat sitting on a windowsill",
  "style": "cartoon",
  "model": "flux-schnell"
}
```

**响应**:
```json
{
  "task_id": "task_xxx",
  "status": "processing",
  "estimated_time": 10
}
```

#### GET `/generation_images/status/{task_id}`

查询生成状态

**响应**:
```json
{
  "status": "completed",
  "image_url": "https://...",
  "credits_used": 5
}
```

---

### 4.26 PDF 生成 `/generation_pdf`

#### POST `/generation_pdf/export`

导出项目为 PDF

**请求**:
```json
{
  "project_id": "proj_xxx",
  "quality": "high"
}
```

**响应**:
```json
{
  "pdf_url": "https://...",
  "download_expires_at": "2024-01-02T00:00:00Z"
}
```

---

### 4.27 故事生成 `/generation_story`

#### POST `/generation_story/create`

生成 AI 故事

**请求**:
```json
{
  "theme": "adventure",
  "characters": ["a brave knight", "a wise dragon"],
  "pages": 8
}
```

**响应**:
```json
{
  "story_id": "story_xxx",
  "status": "processing"
}
```

---

### 4.28 系统资源 `/system_resources`

#### GET `/system_resources/backgrounds`

获取系统背景库

**响应**:
```json
{
  "backgrounds": [
    {
      "id": "bg_xxx",
      "url": "https://...",
      "category": "nature",
      "tier_required": "t1"
    }
  ]
}
```

#### GET `/system_resources/stickers`

获取系统贴纸库

**响应**:
```json
{
  "stickers": [
    {
      "id": "sticker_xxx",
      "url": "https://...",
      "category": "animals",
      "tier_required": "t2"
    }
  ]
}
```

---

## 5. Admin API Reference (管理员接口)

> **重要提示**: 所有 Admin API 需要 Admin 权限认证 (Authorization: Bearer `<admin_token>`)
>
> **DDD 架构合规**: 所有 Admin API 均采用 CQRS 模式 (API → Handler → Service → Repository)
>
> **审计日志**: 所有修改类操作 (创建/更新/删除) 都会记录到 `admin_operations` 表

### 5.1 AI Management (AI 管理) - 4个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/config` | 获取 AI 模型配置 | 30/分钟 | `get_model_configs` |
| POST | `/config` | 更新 AI 模型配置 | 10/分钟 | `update_model_config` |
| GET | `/models` | 获取可用模型列表 | 30/分钟 | `list_available_models` |
| POST | `/models` | 添加新 AI 模型 | 5/分钟 | `add_ai_model` |

#### GET `/admin/ai/config`
**响应**:
```json
{
  "models": [
    {
      "provider": "fal",
      "model_id": "fal-ai/flux-schnell",
      "tier": "t1",
      "enabled": true,
      "cost_multiplier": 1.0
    },
    {
      "provider": "fal",
      "model_id": "fal-ai/flux-dev",
      "tier": "t3",
      "enabled": true,
      "cost_multiplier": 1.5
    }
  ]
}
```

#### POST `/admin/ai/config`
**请求体**:
```json
{
  "provider": "fal",
  "model_id": "fal-ai/flux-pro",
  "tier": "t3",
  "enabled": true,
  "cost_multiplier": 2.0
}
```

---

### 5.2 System Config (系统配置) - 6个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/` | 获取配置列表 | 30/分钟 | `list_configs` |
| GET | `/{key}` | 获取单个配置 | 30/分钟 | `get_config` |
| POST | `/` | 创建配置项 | 10/分钟 | `create_config` |
| PUT | `/{key}` | 更新配置项 | 10/分钟 | `update_config` |
| DELETE | `/{key}` | 删除配置项 | 5/分钟 | `delete_config` |
| POST | `/bulk-update` | 批量更新配置 | 5/分钟 | `bulk_update_configs` |

**配置组 (group)**:
- `credits`: 积分相关 (ai_image_cost, ai_text_cost, ocr_cost)
- `features`: 功能开关 (new_editor_enabled, marketplace_enabled)
- `limits`: 限制配置 (max_project_count, max_asset_size)
- `pricing`: 价格配置 (starter_price, pro_price)

#### GET `/admin/config`
**查询参数**:
- `group` (可选): 按组筛选

**响应**:
```json
{
  "configs": [
    {
      "key": "ai_image_cost",
      "value": "5",
      "group": "credits",
      "description": "AI图片生成成本 (积分)",
      "last_modified": "2026-01-11T10:00:00Z",
      "modified_by": "admin_user_123"
    }
  ],
  "total": 25
}
```

---

### 5.3 Events Management (活动管理) - 5个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/` | 获取活动列表 | 30/分钟 | `list_events` |
| GET | `/{event_id}` | 获取活动详情 | 30/分钟 | `get_event` |
| POST | `/` | 创建新活动 | 5/分钟 | `create_event` |
| PATCH | `/{event_id}` | 更新活动 | 10/分钟 | `update_event` |
| DELETE | `/{event_id}` | 删除活动 | 5/分钟 | `delete_event` |

**活动类型 (type)**:
- `campaign`: 营销活动
- `daily_theme`: 每日主题
- `holiday`: 节日活动
- `special`: 特殊事件

#### POST `/admin/events`
**请求体**:
```json
{
  "title": "春节特别活动",
  "description": "春节期间订阅可获得额外奖励",
  "type": "holiday",
  "start_date": "2026-02-01T00:00:00Z",
  "end_date": "2026-02-15T23:59:59Z",
  "bonus_credits": 200,
  "tier_restriction": ["t2", "t3"],
  "auto_claim": false
}
```

**响应**:
```json
{
  "id": "event_123",
  "title": "春节特别活动",
  "status": "scheduled",
  "created_at": "2026-01-11T10:00:00Z"
}
```

---

### 5.4 Feature Flags (功能开关) - 5个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/` | 获取功能开关列表 | 30/分钟 | `list_feature_flags` |
| GET | `/{key}` | 获取单个功能开关 | 30/分钟 | `get_feature_flag` |
| POST | `/` | 创建功能开关 | 5/分钟 | `create_feature_flag` |
| PUT | `/{key}` | 更新功能开关 | 10/分钟 | `update_feature_flag` |
| DELETE | `/{key}` | 删除功能开关 | 5/分钟 | `delete_feature_flag` |

#### GET `/admin/feature-flags`
**响应**:
```json
{
  "flags": [
    {
      "key": "new_canvas_editor",
      "enabled": true,
      "rollout_percentage": 50,
      "target_tiers": ["t3"],
      "target_user_ids": ["user_2abc...", "user_3def..."],
      "description": "新版画布编辑器",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-11T10:00:00Z"
    }
  ],
  "total": 15
}
```

#### POST `/admin/feature-flags`
**请求体**:
```json
{
  "key": "ai_story_v2",
  "enabled": false,
  "rollout_percentage": 0,
  "target_tiers": [],
  "target_user_ids": [],
  "description": "AI故事生成V2版本"
}
```

---

### 5.5 User Management (用户管理) - 7个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/` | 获取用户列表 | 30/分钟 | `list_users` |
| GET | `/{user_id}` | 获取用户详情 | 30/分钟 | `get_user_detail` |
| PATCH | `/{user_id}` | 更新用户信息 | 10/分钟 | `update_user` |
| POST | `/{user_id}/credits` | 调整积分 | 10/分钟 | `adjust_credits` |
| POST | `/{user_id}/ban` | 封禁用户 | 5/分钟 | `ban_user` |
| POST | `/{user_id}/unban` | 解封用户 | 5/分钟 | `unban_user` |
| DELETE | `/{user_id}` | 删除用户 | 1/分钟 | `delete_user` |

#### GET `/admin/users`
**查询参数**:
- `tier` (可选): t1/t2/t3
- `search` (可选): 搜索 username/email/user_code
- `status` (可选): active/banned/deleted
- `offset` (默认: 0): 分页偏移
- `limit` (默认: 50, 最大: 200): 每页数量

**响应**:
```json
{
  "users": [
    {
      "user_id": "user_2abc...",
      "user_code": "26010914305278900123456789",
      "username": "john_doe",
      "email": "john@example.com",
      "tier": "t2",
      "credits_monthly": 200,
      "credits_permanent": 150,
      "total_projects": 25,
      "total_assets": 10,
      "status": "active",
      "created_at": "2026-01-09T14:30:52Z",
      "last_login_at": "2026-01-11T09:00:00Z"
    }
  ],
  "total": 1000,
  "offset": 0,
  "limit": 50
}
```

#### POST `/admin/users/{user_id}/credits`
**请求体**:
```json
{
  "amount": 100,
  "credit_type": "permanent",
  "reason": "Compensation for service issue",
  "transaction_type": "admin_adjustment",
  "note": "Manual credit adjustment by admin"
}
```

**响应**:
```json
{
  "success": true,
  "new_balance": {
    "credits_monthly": 200,
    "credits_permanent": 250
  },
  "transaction_id": "tx_123"
}
```

---

### 5.6 Stats & Analytics (统计分析) - 12个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/overview` | 系统概览统计 | 30/分钟 | `get_overview_stats` |
| GET | `/revenue` | 收入统计 | 30/分钟 | `get_revenue_stats` |
| GET | `/users` | 用户增长统计 | 30/分钟 | `get_user_growth_stats` |
| GET | `/engagement` | 用户活跃度 | 30/分钟 | `get_engagement_stats` |
| GET | `/ai-usage` | AI使用统计 | 30/分钟 | `get_ai_usage_stats` |
| GET | `/marketplace` | 市场统计 | 30/分钟 | `get_marketplace_stats` |
| GET | `/projects` | 项目统计 | 30/分钟 | `get_project_stats` |
| GET | `/credits` | 积分流水统计 | 30/分钟 | `get_credits_stats` |
| GET | `/subscriptions` | 订阅统计 | 30/分钟 | `get_subscription_stats` |
| GET | `/retention` | 用户留存率 | 30/分钟 | `get_retention_stats` |
| GET | `/conversion` | 转化率统计 | 30/分钟 | `get_conversion_stats` |
| GET | `/experiments` | 实验结果统计 | 30/分钟 | `get_experiment_stats` |

#### GET `/admin/stats/overview`
**响应**:
```json
{
  "users": {
    "total": 10000,
    "t1": 8000,
    "t2": 1500,
    "t3": 500,
    "new_today": 50,
    "new_this_week": 350,
    "new_this_month": 1200,
    "active_today": 2500,
    "active_this_month": 6000
  },
  "projects": {
    "total": 50000,
    "created_today": 200,
    "created_this_week": 1400,
    "created_this_month": 5000
  },
  "marketplace": {
    "total_listings": 1000,
    "active_listings": 800,
    "total_sales": 5000,
    "sales_today": 25
  },
  "revenue": {
    "mrr": 25000,
    "total_this_month": 18000,
    "total_all_time": 250000
  },
  "ai": {
    "images_generated_today": 500,
    "images_generated_this_month": 15000,
    "stories_generated_today": 100,
    "stories_generated_this_month": 3000
  }
}
```

#### GET `/admin/stats/revenue`
**查询参数**:
- `start_date` (必需): YYYY-MM-DD
- `end_date` (必需): YYYY-MM-DD
- `granularity` (可选): day/week/month (默认: day)

**响应**:
```json
{
  "data_points": [
    {
      "date": "2026-01-01",
      "subscriptions": 500,
      "credits": 200,
      "total": 700
    },
    {
      "date": "2026-01-02",
      "subscriptions": 600,
      "credits": 150,
      "total": 750
    }
  ],
  "summary": {
    "total_revenue": 15000,
    "subscription_revenue": 12000,
    "credit_revenue": 3000,
    "avg_daily": 500
  }
}
```

---

### 5.7 Moderation (内容审核) - 6个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/queue` | 获取审核队列 | 30/分钟 | `get_moderation_queue` |
| GET | `/{item_id}` | 获取审核项详情 | 30/分钟 | `get_moderation_item` |
| POST | `/{item_id}/approve` | 批准内容 | 10/分钟 | `approve_item` |
| POST | `/{item_id}/reject` | 拒绝内容 | 10/分钟 | `reject_item` |
| POST | `/{item_id}/flag` | 标记问题内容 | 10/分钟 | `flag_item` |
| GET | `/reports` | 获取用户举报 | 30/分钟 | `get_user_reports` |

#### GET `/admin/moderation/queue`
**查询参数**:
- `type` (可选): listing/project/asset
- `status` (可选): pending/approved/rejected/flagged
- `offset` (默认: 0)
- `limit` (默认: 20)

**响应**:
```json
{
  "items": [
    {
      "id": "mod_123",
      "type": "listing",
      "content_id": "listing_456",
      "title": "Educational Template",
      "creator_id": "user_2abc...",
      "creator_username": "john_doe",
      "status": "pending",
      "submitted_at": "2026-01-11T10:00:00Z",
      "preview_url": "https://...",
      "flags": []
    }
  ],
  "total": 50,
  "offset": 0,
  "limit": 20
}
```

#### POST `/admin/moderation/{item_id}/reject`
**请求体**:
```json
{
  "reason": "violation_copyright",
  "reviewer_notes": "包含未授权的品牌LOGO",
  "notify_user": true,
  "ban_duration_hours": 72
}
```

**拒绝原因 (reason)**:
- `violation_copyright`: 侵犯版权
- `violation_nsfw`: 不适宜内容
- `violation_spam`: 垃圾内容
- `violation_quality`: 质量不达标
- `violation_other`: 其他原因

---

### 5.8 Notifications (通知管理) - 4个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| POST | `/broadcast` | 发送广播通知 | 5/分钟 | `send_broadcast` |
| POST | `/targeted` | 发送定向通知 | 10/分钟 | `send_targeted` |
| GET | `/history` | 通知历史记录 | 30/分钟 | `get_notification_history` |
| GET | `/stats` | 通知统计 | 30/分钟 | `get_notification_stats` |

#### POST `/admin/notifications/broadcast`
**请求体**:
```json
{
  "title": "系统维护通知",
  "message": "系统将于今晚22:00-23:00进行维护，请提前保存工作",
  "type": "system",
  "priority": "high",
  "target_tiers": ["t1", "t2", "t3"],
  "exclude_user_ids": [],
  "action_url": "https://makedecodables.com/status",
  "expires_at": "2026-01-12T00:00:00Z"
}
```

**通知类型 (type)**:
- `system`: 系统通知
- `feature`: 新功能通知
- `promotion`: 促销通知
- `warning`: 警告通知

**优先级 (priority)**:
- `low`: 低优先级 (不推送，仅站内显示)
- `normal`: 普通 (站内显示)
- `high`: 高优先级 (站内 + 可选邮件)
- `urgent`: 紧急 (站内 + 邮件 + 可选短信)

---

### 5.9 Subscriptions (订阅管理) - 6个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/` | 获取订阅列表 | 30/分钟 | `list_subscriptions` |
| GET | `/{subscription_id}` | 获取订阅详情 | 30/分钟 | `get_subscription` |
| POST | `/{subscription_id}/cancel` | 取消订阅 | 5/分钟 | `cancel_subscription` |
| POST | `/{subscription_id}/refund` | 退款 | 5/分钟 | `refund_subscription` |
| POST | `/{subscription_id}/pause` | 暂停订阅 | 5/分钟 | `pause_subscription` |
| POST | `/{subscription_id}/resume` | 恢复订阅 | 5/分钟 | `resume_subscription` |

#### GET `/admin/subscriptions`
**查询参数**:
- `status` (可选): active/canceled/past_due/paused
- `tier` (可选): t2/t3
- `offset` (默认: 0)
- `limit` (默认: 50)

**响应**:
```json
{
  "subscriptions": [
    {
      "id": "sub_123",
      "user_id": "user_2abc...",
      "user_email": "john@example.com",
      "tier": "t2",
      "status": "active",
      "current_period_start": "2026-01-01T00:00:00Z",
      "current_period_end": "2026-02-01T00:00:00Z",
      "stripe_subscription_id": "sub_stripe_123",
      "plan_amount": 990,
      "currency": "usd",
      "created_at": "2025-12-01T00:00:00Z"
    }
  ],
  "total": 2000,
  "offset": 0,
  "limit": 50
}
```

#### POST `/admin/subscriptions/{subscription_id}/refund`
**请求体**:
```json
{
  "amount": 990,
  "reason": "Service issue compensation",
  "notify_user": true,
  "cancel_subscription": true
}
```

---

### 5.10 System Operations (系统操作) - 9个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/health` | 系统健康检查 | 60/分钟 | `check_system_health` |
| GET | `/metrics` | 系统性能指标 | 30/分钟 | `get_system_metrics` |
| POST | `/cache/clear` | 清除特定缓存 | 10/分钟 | `clear_cache` |
| POST | `/cache/clear-all/confirm` | 请求清除全部缓存token | 1/10分钟 | `request_cache_clear_token` |
| POST | `/cache/clear-all` | 清除全部缓存 | 1/10分钟 | `clear_all_cache` |
| POST | `/maintenance/enable` | 启用维护模式 | 1/10分钟 | `enable_maintenance` |
| POST | `/maintenance/disable` | 禁用维护模式 | 1/10分钟 | `disable_maintenance` |
| GET | `/jobs` | 获取后台任务状态 | 30/分钟 | `get_background_jobs` |
| POST | `/jobs/{job_id}/cancel` | 取消后台任务 | 10/分钟 | `cancel_background_job` |

#### GET `/admin/system/health`
**响应**:
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "connected",
      "latency_ms": 5
    },
    "redis": {
      "status": "connected",
      "latency_ms": 2
    },
    "storage": {
      "status": "available",
      "used_percent": 45
    },
    "stripe": {
      "status": "operational"
    },
    "clerk": {
      "status": "operational"
    }
  },
  "uptime_seconds": 864000,
  "version": "v3.25",
  "last_deployment": "2026-01-11T08:00:00Z"
}
```

#### POST `/admin/system/cache/clear-all/confirm`
**响应**:
```json
{
  "token": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "expires_in": 120,
  "warning": "清除所有缓存会导致数据库查询压力骤增，请确认!"
}
```

#### POST `/admin/system/cache/clear-all`
**查询参数**:
- `confirm_token` (必需): 从 confirm 端点获取的 token

**安全机制**:
- Token 一次性使用 (验证后立即删除)
- Token 2分钟过期
- 记录 CRITICAL 级别审计日志

---

### 5.11 Task Management (任务管理) - 5个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/` | 获取任务列表 | 30/分钟 | `list_tasks` |
| GET | `/{task_id}` | 获取任务详情 | 30/分钟 | `get_task` |
| POST | `/{task_id}/retry` | 重试失败任务 | 10/分钟 | `retry_task` |
| POST | `/{task_id}/cancel` | 取消任务 | 10/分钟 | `cancel_task` |
| DELETE | `/{task_id}` | 删除任务记录 | 10/分钟 | `delete_task` |

#### GET `/admin/tasks`
**查询参数**:
- `status` (可选): pending/running/completed/failed/canceled
- `task_type` (可选): pdf_export/zip_export/ai_image_generation/ai_story_generation
- `user_id` (可选): 按用户筛选
- `offset` (默认: 0)
- `limit` (默认: 50)

**响应**:
```json
{
  "tasks": [
    {
      "id": "task_123",
      "type": "pdf_export",
      "status": "completed",
      "user_id": "user_2abc...",
      "priority": "normal",
      "created_at": "2026-01-11T10:00:00Z",
      "started_at": "2026-01-11T10:00:05Z",
      "completed_at": "2026-01-11T10:01:30Z",
      "result_url": "https://storage.../export.pdf",
      "error_message": null,
      "retry_count": 0
    }
  ],
  "total": 5000,
  "offset": 0,
  "limit": 50
}
```

---

### 5.12 Webhooks (Webhook 管理) - 5个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/retry-queue` | 获取重试队列 | 30/分钟 | `get_retry_queue` |
| GET | `/{webhook_id}` | 获取webhook详情 | 30/分钟 | `get_webhook` |
| POST | `/{webhook_id}/retry` | 手动重试 | 10/分钟 | `retry_webhook` |
| DELETE | `/{webhook_id}` | 从队列移除 | 10/分钟 | `remove_from_queue` |
| GET | `/logs` | Webhook执行日志 | 30/分钟 | `get_webhook_logs` |

#### GET `/admin/webhooks/retry-queue`
**响应**:
```json
{
  "webhooks": [
    {
      "id": "webhook_123",
      "event_type": "checkout.session.completed",
      "event_id": "evt_stripe_123",
      "retry_count": 2,
      "max_retries": 3,
      "next_retry_at": "2026-01-11T11:00:00Z",
      "error": "Connection timeout after 30s",
      "payload_preview": "{\"type\": \"checkout.session.completed\", ...}",
      "created_at": "2026-01-11T10:00:00Z"
    }
  ],
  "total": 5
}
```

---

### 5.13 Experiments (实验管理) - 6个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/` | 获取实验列表 | 30/分钟 | `list_experiments` |
| GET | `/{experiment_key}` | 获取实验详情 | 30/分钟 | `get_experiment` |
| POST | `/` | 创建新实验 | 5/分钟 | `create_experiment` |
| PATCH | `/{experiment_key}` | 更新实验 | 10/分钟 | `update_experiment` |
| DELETE | `/{experiment_key}` | 删除实验 | 5/分钟 | `delete_experiment` |
| GET | `/{experiment_key}/results` | 获取实验结果 | 30/分钟 | `get_experiment_results` |

#### GET `/admin/experiments`
**响应**:
```json
{
  "experiments": [
    {
      "key": "new_pricing_page",
      "name": "新定价页实验",
      "description": "测试新定价页面的转化率",
      "status": "running",
      "variants": [
        {
          "name": "control",
          "weight": 50,
          "users_assigned": 500,
          "conversions": 50,
          "conversion_rate": 0.10
        },
        {
          "name": "variant_a",
          "weight": 50,
          "users_assigned": 480,
          "conversions": 60,
          "conversion_rate": 0.125
        }
      ],
      "start_date": "2026-01-01T00:00:00Z",
      "end_date": "2026-01-31T23:59:59Z",
      "created_at": "2025-12-20T00:00:00Z"
    }
  ],
  "total": 10
}
```

#### POST `/admin/experiments`
**请求体**:
```json
{
  "key": "checkout_flow_v2",
  "name": "结账流程优化",
  "description": "简化结账流程,减少步骤",
  "variants": [
    {"name": "control", "weight": 50},
    {"name": "simplified", "weight": 50}
  ],
  "target_tiers": ["t2", "t3"],
  "target_user_ids": [],
  "conversion_goal": "subscription_purchase",
  "start_date": "2026-01-15T00:00:00Z",
  "end_date": "2026-02-15T00:00:00Z"
}
```

---

### 5.14 Logs & Audit (日志与审计) - 4个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/errors` | 获取错误日志 | 30/分钟 | `get_error_logs` |
| GET | `/audit` | 获取审计日志 | 30/分钟 | `get_audit_logs` |
| GET | `/metrics` | 获取性能指标 | 30/分钟 | `get_performance_metrics` |
| GET | `/access` | 获取访问日志 | 30/分钟 | `get_access_logs` |

#### GET `/admin/logs/audit`
**查询参数**:
- `admin_id` (可选): 管理员 user_id
- `operation_type` (可选): 操作类型
- `start_date` (可选): YYYY-MM-DD HH:MM:SS
- `end_date` (可选): YYYY-MM-DD HH:MM:SS
- `offset` (默认: 0)
- `limit` (默认: 50)

**响应**:
```json
{
  "logs": [
    {
      "id": "audit_123",
      "admin_id": "user_admin_123",
      "admin_username": "admin_john",
      "operation_type": "user_tier_update",
      "target_type": "user",
      "target_id": "user_2abc...",
      "details": {
        "old_tier": "t1",
        "new_tier": "t2",
        "reason": "Manual upgrade"
      },
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
      "timestamp": "2026-01-11T10:00:00Z"
    }
  ],
  "total": 500,
  "offset": 0,
  "limit": 50
}
```

**operation_type 类型**:
- `user_tier_update`: 用户等级变更
- `user_credits_adjustment`: 积分调整
- `user_ban`: 用户封禁
- `user_delete`: 用户删除
- `listing_approve`: Listing 审核通过
- `listing_reject`: Listing 审核拒绝
- `event_create`: 活动创建
- `event_delete`: 活动删除
- `config_update`: 配置更新
- `cache_clear_all`: 清除全部缓存
- `system_maintenance`: 系统维护
- `subscription_refund`: 订阅退款

#### GET `/admin/logs/errors`
**查询参数**:
- `severity` (可选): error/warning/critical
- `source` (可选): api/worker/scheduler
- `start_date` (可选)
- `end_date` (可选)
- `offset` (默认: 0)
- `limit` (默认: 50)

**响应**:
```json
{
  "logs": [
    {
      "id": "error_123",
      "severity": "error",
      "source": "api",
      "message": "Database connection timeout",
      "stack_trace": "Traceback (most recent call last):\n  File ...",
      "user_id": "user_2abc...",
      "endpoint": "/api/user/projects",
      "request_id": "req_456",
      "timestamp": "2026-01-11T10:30:00Z"
    }
  ],
  "total": 100,
  "offset": 0,
  "limit": 50
}
```

---

### 5.15 Campaigns (营销活动管理) - 5个端点

| 方法 | 端点 | 描述 | Rate Limit | Service |
|---|---|---|---|---|
| GET | `/` | 获取营销活动列表 | 30/分钟 | `list_campaigns` |
| GET | `/{campaign_id}` | 获取活动详情 | 30/分钟 | `get_campaign` |
| POST | `/` | 创建营销活动 | 5/分钟 | `create_campaign` |
| PATCH | `/{campaign_id}` | 更新营销活动 | 10/分钟 | `update_campaign` |
| DELETE | `/{campaign_id}` | 删除营销活动 | 5/分钟 | `delete_campaign` |

#### GET `/admin/campaigns`
**响应**:
```json
{
  "campaigns": [
    {
      "id": "campaign_123",
      "title": "新年促销",
      "type": "discount",
      "status": "active",
      "start_date": "2026-01-01T00:00:00Z",
      "end_date": "2026-01-31T23:59:59Z",
      "bonus_credits": 100,
      "discount_percentage": 20,
      "target_tiers": ["t2", "t3"],
      "claimed_count": 500,
      "max_claims": 1000,
      "created_at": "2025-12-15T00:00:00Z"
    }
  ],
  "total": 25
}
```

#### POST `/admin/campaigns`
**请求体**:
```json
{
  "title": "春节特惠",
  "description": "春节期间订阅享8折优惠",
  "type": "discount",
  "start_date": "2026-02-01T00:00:00Z",
  "end_date": "2026-02-15T23:59:59Z",
  "bonus_credits": 200,
  "discount_percentage": 20,
  "tier_restriction": ["t2", "t3"],
  "max_claims": 500,
  "auto_claim": false
}
```

---

## 附录 A: 认证系统

### Clerk 用户 ID 格式

Make Decodables 使用 Clerk 作为认证提供商。用户 ID 格式如下:

**格式**: `user_{base58_characters}`

**示例**: `user_2NNEqL2nrIRdJ194ndJqAHwEfxC`

**特征**:
- 前缀: 固定为 `user_`
- 字符集: 大小写字母 + 数字 (Base58)
- 长度: 总计 25-35 个字符 (前缀 5 个 + 标识符 20-30 个)

**验证规则** (Regex):
```regex
^user_[a-zA-Z0-9]{20,30}$
```

**⚠️ 重要提示**:
- Clerk user ID **不是** UUID 格式
- 不要尝试使用 UUID 验证规则验证 Clerk ID
- API 调用时必须使用完整的 `user_` 前缀

**错误示例**:
```
❌ 550e8400-e29b-41d4-a716-446655440000  (UUID 格式)
❌ 2NNEqL2nrIRdJ194ndJqAHwEfxC          (缺少前缀)
```

**正确示例**:
```
✅ user_2NNEqL2nrIRdJ194ndJqAHwEfxC
```

### 认证流程

1. 用户在前端通过 Clerk 登录
2. Clerk 返回 JWT token
3. 前端在 API 请求中携带 token (Authorization header)
4. 后端验证 token 并提取 user_id
5. 使用 user_id 执行业务逻辑

---

### 用户代码 (user_code) 格式

系统使用**双重用户标识符**机制:

| 标识符 | 格式示例 | 用途 | 来源 |
|--------|----------|------|------|
| **user_id** | `user_2abc3def...` | 系统内部使用,数据库主键 | Clerk 自动生成 |
| **user_code** | `26010914305278900123456789` | 用户反馈/管理员搜索 | 注册时生成 |

**user_code 格式** (26位):

```
260109 143052 7890 0123456 789
------+------+----+-------+---
日期  时间  毫秒 序号    随机
```

| 部分 | 位数 | 说明 | 示例 |
|------|------|------|------|
| 日期 | 6位 | YYMMDD (UTC) | `260109` = 2026-01-09 |
| 时间 | 6位 | HHMMSS (UTC) | `143052` = 14:30:52 |
| 毫秒 | 4位 | 毫秒数 | `7890` |
| 用户序号 | 7位 | 总注册人数 | `0123456` = 第123,456个用户 |
| 随机数 | 3位 | 额外唯一性保证 | `789` |

**完整示例解读**:
```
user_code: 26010914305278900123456789

解析:
- 注册日期: 2026-01-09
- 注册时间: 14:30:52.7890 (UTC)
- 用户序号: 第 123,456 个注册用户
- 随机后缀: 789
```

**使用场景**:
- ✅ 用户反馈时提供 user_code 给客服
- ✅ 管理员通过 user_code 搜索用户 (Admin API)
- ✅ 敏感操作的双因素验证 (user_id + user_code)

**API 支持**:
```bash
# Admin API - 通过 user_code 搜索用户
GET /api/v2/admin/users?search=26010914305278900123456789

# 返回匹配的用户
{
  "users": [{
    "user_id": "user_2abc...",
    "user_code": "26010914305278900123456789",
    "username": "john_doe",
    ...
  }],
  "total": 1
}
```

**📍 详细文档**: 完整的 user_code 生成逻辑、数据分析应用等详见 `docs/shared/USER-ID-SYSTEM.md`

---

## 附录 B: Tier 命名规范

### 系统代码 vs 显示名称

Make Decodables 使用**三层 Tier 命名系统**:

| 系统代码 (tier) | 固定简称 | 显示名称 (可配置) | 月度积分 | 价格 |
|-----------------|----------|------------------|----------|------|
| `t1` | First Tier | Free Plan | 0 | $0 |
| `t2` | Second Tier | Starter Plan | 200 | $9.9/月 |
| `t3` | Third Tier | Pro Plan | 500 | $19.9/月 |

**设计原则**:
- **系统代码** (`t1`/`t2`/`t3`) - 数据库字段、代码逻辑使用，**永不改变**
- **固定简称** (First/Second/Third Tier) - 描述性名称，文档使用
- **显示名称** (Free/Starter/Pro Plan) - 用户看到的名称，**可通过 Admin 配置修改**

**为什么使用 t1/t2/t3**:
- ✅ **简洁**: 比 `free`/`starter`/`pro` 更短
- ✅ **中立**: 不包含业务语义,方便未来调整名称
- ✅ **可扩展**: 未来可轻松添加 t4、t5 等更高等级
- ✅ **国际化**: 系统代码无需翻译,只需翻译显示名称

**使用规范**:

```python
# ✅ 正确: 使用系统代码
if user.tier == "t2":
    credits = TIER_MONTHLY_CREDITS["t2"]  # 200

# ✅ 正确: 获取显示名称
tier_name = await tier_service.get_tier_display_name(user.tier)
# 返回: "Starter Plan" (可能被 Admin 修改为 "Growth Plan")

# ❌ 错误: 硬编码显示名称
plan_name = "Starter Plan"  # 将来可能改名!
```

**API 返回格式**:

```json
// GET /api/v2/user/me
{
  "tier": "t2",                    // 系统代码
  "tier_label": "Second Tier",     // 固定简称
  "tier_name": "Starter Plan",     // 显示名称 (可配置)
  "credits_monthly": 200,
  "credits_permanent": 150
}
```

**Admin API - 修改显示名称**:

```bash
# 将 t2 显示名称从 "Starter Plan" 改为 "Growth Plan"
PUT /api/v2/admin/config/tier.t2.display_name
{
  "value": "Growth Plan"
}
```

**📍 实施状态**: Tier 命名统一 (t1/t2/t3) 已于 2026-01-10 完成实施 (Commit: c0906a2, 67文件/245处修改)

**📍 详细文档**: 完整的 TierService 实现、前端 Hook、迁移计划等详见 `docs/shared/TIER-NAMING-SYSTEM.md`

---

## 附录 C: 速率限制

| 端点 | 限制 |
|------|------|
| `/payment/checkout` | 5/分钟 |
| `/payment/portal` | 10/分钟 |
| `/generate/images` | 10/分钟 |
| `/generation_images/generate` | 10/分钟 |
| `/generation_story/create` | 5/分钟 |
| `/projects` (POST) | 20/分钟 |
| `/assets` (POST) | 20/分钟 |
| `/marketplace/purchase` | 10/分钟 |
| `/analytics/events` | 60/分钟 |
| 管理员操作 | 5-10/分钟 |

---

*文档版本: v3.26*
*最后更新: 2026-01-11*
*更新内容:
- v3.26: 新增完整的 Admin API 文档 (15个模块, 135个端点), 包含 DDD 架构说明和审计日志机制
- v3.25: 补充 9 个缺失的 User API 端点章节, 添加 Clerk ID 格式说明*
