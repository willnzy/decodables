# Make Decodables 后端 API 参考文档

> 版本: 3.33
> 更新时间: 2026-01-28
> 供前端重构参考

---

## 目录

1. [RESTful 设计规范](#1-restful-设计规范)
2. [基础信息](#2-基础信息)
3. [健康检查 API](#3-健康检查-api)
4. [Webhooks](#4-webhooks)
5. [API 总览](#5-api-总览)
   - [User API](#user-api-123个端点)
   - [Admin API](#admin-api-178个端点)
6. [附录 A: 认证系统](#附录-a-认证系统)
7. [附录 B: Tier 命名规范](#附录-b-tier-命名规范)
8. [附录 C: 积分系统](#附录-c-积分系统)
9. [附录 D: 速率限制](#附录-d-速率限制)
10. [附录 E: 端点文档补充说明](#附录-e-端点文档补充说明)

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
- ✅ 带过滤条件的列表: `GET /api/v2/projects?status=active&offset=0&limit=20`
- ✅ 获取统计数据: `GET /api/v2/admin/stats/dashboard`
- ❌ 不要用 GET 执行任何修改操作

**示例**:
```
GET /api/v2/user/profile/me       # 获取当前用户资料
GET /api/v2/user/billing/credits  # 获取积分余额
GET /api/v2/user/projects          # 获取项目列表
GET /api/v2/user/projects/{id}     # 获取单个项目
GET /api/v2/admin/users?search=john&offset=0&limit=20  # 搜索用户
```

#### POST - 创建/执行操作

**用途**: 创建新资源，或执行非幂等操作

**规则**:
- ✅ 创建新资源: `POST /api/v2/user/projects`
- ✅ 执行操作/触发任务: `POST /api/v2/user/generate/images`
- ✅ 批量操作: `POST /api/v2/user/analytics/events`
- ✅ 登录/认证: `POST /api/v2/auth/login`
- ✅ 复杂搜索 (请求体过大): `POST /api/v2/search`
- ❌ 不要用 POST 获取资源 (除非 GET 参数过长)

**示例**:
```
POST /api/v2/user/projects             # 创建新项目
POST /api/v2/user/generate/images      # 生成 AI 图片
POST /api/v2/user/payment/checkout     # 创建支付会话
POST /api/v2/user/support/ticket       # 提交工单
POST /api/v2/admin/notifications/broadcast  # 发送广播通知
POST /api/v2/user/experiments/{key}/exposure  # 记录曝光事件
```

#### PUT - 完整替换

**用途**: 用请求体完整替换目标资源

**规则**:
- ✅ 替换整个资源: `PUT /api/v2/user/projects/{id}`
- ✅ 更新资源状态: `PUT /api/v2/admin/experiments/{key}/status`
- ❌ 不要用 PUT 部分更新 (用 PATCH)
- ❌ 不要用 PUT 创建资源 (用 POST)

**示例**:
```
PUT /api/v2/user/projects/{id}              # 更新整个项目
PUT /api/v2/user/profile/timezone           # 更新时区
PUT /api/v2/admin/config/{key}              # 更新系统配置
PUT /api/v2/admin/experiments/{key}/status  # 更新实验状态
```

#### PATCH - 部分更新

**用途**: 部分修改资源的某些字段

**规则**:
- ✅ 更新单个字段: `PATCH /api/v2/user/generations/{id}`
- ✅ 更新多个字段 (非全部): 请求体只包含要更新的字段
- ❌ 不要用 PATCH 替换整个资源 (用 PUT)

**示例**:
```
PATCH /api/v2/user/projects/{id}       # 部分更新项目
PATCH /api/v2/user/generations/{id}    # 更新生成记录
PATCH /api/v2/user/marketplace/listings/{id}  # 部分更新商品
PATCH /api/v2/admin/feature-flags/{key}       # 部分更新功能开关
```

#### DELETE - 删除

**用途**: 删除资源

**规则**:
- ✅ 删除单个资源: `DELETE /api/v2/user/projects/{id}`
- ✅ 删除可以是逻辑删除 (soft delete)
- ❌ 不要在请求体中传递数据
- ⚠️ 批量删除推荐用 POST: `POST /api/v2/user/generations/batch-delete`

**示例**:
```
DELETE /api/v2/user/projects/{id}      # 删除项目
DELETE /api/v2/user/assets/{id}        # 删除素材
DELETE /api/v2/user/generations/{id}   # 删除生成记录
DELETE /api/v2/admin/experiments/{key} # 删除实验
```

### 1.4 特殊场景处理

#### 操作型 API (RPC 风格)

某些操作不适合 REST 资源模型，使用 POST 动词:

```
POST /api/v2/user/billing/credits/add       # 添加积分 (Admin Only)
POST /api/v2/admin/subscriptions/refund     # 执行退款
POST /api/v2/admin/events/aggregation/run   # 触发聚合任务
POST /api/v2/admin/system/cache/clear-all   # 清空缓存
```

#### 批量操作

```
POST /api/v2/user/analytics/events              # 批量记录事件
POST /api/v2/user/generations/batch-delete      # 批量删除
POST /api/v2/admin/notifications/notification/batch  # 批量发送通知
```

#### 复杂查询

当 GET 参数过长或过于复杂时，可用 POST:

```
POST /api/v2/search                    # 复杂搜索
POST /api/v2/admin/logs/operations/export  # 导出日志数据 (带筛选条件)
```

#### 文件上传

```
POST /api/v2/user/assets/upload        # 上传素材
POST /api/v2/user/tools/ocr            # 上传图片进行 OCR
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
| 402 | Payment Required | 积分不足 |
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
/api/v2/user/*             # 用户相关
/api/v2/user/billing/*     # 积分相关
/api/v2/user/projects/*    # 项目相关
/api/v2/user/generate/*    # AI 生成
/api/v2/user/assets/*      # 素材相关
/api/v2/user/marketplace/* # 市场相关
/api/v2/user/payment/*     # 支付相关
/api/v2/user/experiments/* # A/B 测试 (公开端点)
```

#### 公开 API (无需认证)

```
/api/v2/user/config/*      # 公开配置
/api/v2/user/logs/*        # 错误上报
/api/v2/user/themes/*      # 节日主题
/api/v2/user/resources/*   # 系统资源
```

#### Admin API (需管理员权限)

```
/api/v2/admin/users/*         # 用户管理
/api/v2/admin/stats/*         # 统计数据
/api/v2/admin/config/*        # 系统配置
/api/v2/admin/tiers/*         # Tier 配置管理 (v3.41 NEW)
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
/api/v2/user/webhooks/stripe    # Stripe 支付回调
/api/v2/user/webhooks/clerk     # Clerk 用户回调
/api/webhooks/fal               # FAL AI 回调
```

> **注意**: Webhook 路径不能随意修改，需要在第三方平台配置

### 1.8 检查清单

新增 API 前，请确认:

- [ ] HTTP 方法选择正确 (GET/POST/PUT/PATCH/DELETE)
- [ ] 路径命名符合规范 (名词、复数、小写)
- [ ] 响应状态码使用正确
- [ ] 需要认证的 API 添加了 `Depends(get_current_user)` 或 `Depends(require_admin)`
- [ ] 添加了适当的限流 (`@limiter.limit`)
- [ ] 更新了 API 文档

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

**DDD 标准分页** (2026-01-10 统一):

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `offset` | int | 0 | 偏移量 |
| `limit` | int | 20 | 每页数量 (最大 100) |

**返回格式**:
```json
{
  "items": [...],
  "total": 100,
  "offset": 0,
  "limit": 20
}
```

---

## 3. 健康检查 API

### GET `/health`

基础健康检查

**响应**:
```json
{
  "status": "healthy",
  "version": "3.27",
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
- `charge.refunded` - 退款完成

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
| `charge.refunded` | 退款处理: 扣除相应积分 |

**Metadata 说明**:

checkout.session 需要携带的 metadata:
```json
{
  "user_id": "clerk_user_id",
  "plan": "t2|t3|credits_100|credits_500|credits_2000"
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

## 5. API 总览

### User API (158个端点)

| 模块 | 基础路径 | 端点数 | 说明 |
|------|----------|--------|------|
| **用户档案** | `/api/v2/user/profile` | 7 | 用户信息、通知、时区 |
| **工作区** | `/api/v2/user/workspaces` | 6 | Workspace CRUD、统计 (v3.33) |
| **标签系统** | `/api/v2/user/tags` | 6 | Tag CRUD、预设、分组 (v3.33) |
| **文件夹** | `/api/v2/user/folders` | 6 | Folder CRUD、重排序 (v3.33) |
| **项目标签** | `/api/v2/user/projects/{id}/tags` | 4 | 项目-标签关联 (v3.33) |
| **素材标签** | `/api/v2/user/assets/{id}/tags` | 4 | 素材-标签关联 (v3.33) |
| **项目管理** | `/api/v2/user/projects` | 14 | CRUD、恢复、复制、移动、收藏 (v3.33) |
| **计费管理** | `/api/v2/user/billing` | 4 | 积分余额、交易历史 |
| **支付** | `/api/v2/user/payment` | 2 | Checkout、Portal |
| **AI 生成 - 图片** | `/api/v2/user/generate/images` | 2 | 同步/异步生成 |
| **AI 生成 - PDF** | `/api/v2/user/generate/pdf` | 1 | 折叠式迷你书 |
| **AI 生成 - 故事** | `/api/v2/user/generate/story` | 2 | 故事/灵感生成 |
| **生成历史** | `/api/v2/user/generations` | 6 | 历史、收藏、删除 |
| **市场** | `/api/v2/user/marketplace` | 11 | 商品、购买、举报 |
| **系统资源** | `/api/v2/user/resources` | 7 | 贴纸、背景、模板 |
| **用户资源** | `/api/v2/user/assets` | 10 | 上传、删除、恢复 |
| **用户资源** | `/api/v2/user/user_assets` | 14 | 资产管理、移动、收藏 (v3.33) |
| **系统资源** | `/api/v2/user/system_resources` | 9 | 系统资源管理 |
| **模板** | `/api/v2/user/templates` | 10 | Asset/Page 模板 |
| **分析** | `/api/v2/user/analytics` | 1 | 事件上报 |
| **配置** | `/api/v2/user/config` | 3 | 系统配置查询 |
| **主题** | `/api/v2/user/themes` | 1 | 节日主题 |
| **活动** | `/api/v2/user/campaigns` | 3 | 领取、关闭 |
| **导出** | `/api/v2/user/export` | 6 | PDF/ZIP 导出 |
| **任务** | `/api/v2/user/tasks` | 2 | 任务状态、取消 |
| **支持** | `/api/v2/user/support` | 4 | 工单、客服、反馈 |
| **实验** | `/api/v2/user/experiments` | 4 | 分配、曝光、转化 |
| **新手引导** | `/api/v2/user/onboarding` | 6 | 步骤、进度 |
| **推荐系统** | `/api/v2/user/referrals` | 6 | 推荐码、奖励 |
| **工具** | `/api/v2/user/tools` | 2 | PDF预览、OCR |
| **日志** | `/api/v2/user/logs` | 2 | 错误上报 |
| **Webhooks** | `/api/v2/user/webhooks` | 2 | Clerk、Stripe |

**详细文档**: 完整的 158 个 User API 端点详细文档见 [docs/shared/user-api-review.md](../shared/user-api-review.md)

> **v3.33 新增**: Workspace (6个) + Tags (6个) + Folders (6个) + Project Tags (4个) + Asset Tags (4个) + Project move/star (4个) + Asset move/star (4个) = 34 个新端点

---

### Admin API (183个端点)

> **版本**: v3.42 (2026-01-20) - 完整评审 183 个端点

| 模块 | 基础路径 | 端点数 | 说明 |
|------|----------|--------|------|
| **用户管理** | `/api/v2/admin/users` | 13 | 搜索、审计、积分调整 |
| **订阅管理** | `/api/v2/admin/subscriptions` | 3 | 退款、取消、降级 |
| **统计仪表板** | `/api/v2/admin/stats` | 18 | KPI、增长、转化 |
| **AI 洞察** | `/api/v2/admin/ai` | 5 | 洞察、推荐、报告 |
| **AI Models** | `/api/v2/admin/ai/models` | 8 | 模型配置、使用统计 |
| **内容审核** | `/api/v2/admin/moderation` | 10 | Marketplace 审核、举报 |
| **通知管理** | `/api/v2/admin/notifications` | 5 | 广播、批量发送 |
| **系统配置** | `/api/v2/admin/config` | 8 | 配置 CRUD、限流预设 |
| **Tier 配置** | `/api/v2/admin/tiers` | 3 | Tier 权益配置管理 |
| **系统管理** | `/api/v2/admin/system` | 12 | 缓存、系统配置 |
| **实验管理** | `/api/v2/admin/experiments` | 14 | AB 测试、AI 分析 |
| **Feature Flags** | `/api/v2/admin/feature-flags` | 15 | 功能开关管理 (v1.2 含 Tier 分层筛选) |
| **事件管理** | `/api/v2/admin/events` | 5 | 事件、聚合 |
| **日志与审计** | `/api/v2/admin/logs` | 5 | 错误日志、操作日志 |
| **指标** | `/api/v2/admin/metrics` | 7 | 日/月指标、留存 |
| **任务管理** | `/api/v2/admin/tasks/management` | 4 | 任务状态、手动触发 |
| **营销活动** | `/api/v2/admin/campaigns` | 8 | 活动 CRUD、统计 |
| **文章管理** | `/api/v2/admin/articles` | 7 | 文章 CMS CRUD |
| **素材分类** | `/api/v2/admin/asset-categories` | 7 | 分类 CRUD、树结构 |
| **主题管理** | `/api/v2/admin/themes` | 13 | 主题 CRUD、AI 批量生成、审核 |
| **静态页面** | `/api/v2/admin/static-pages` | 7 | 静态页面 CMS CRUD |
| **用户创建监控** | `/api/v2/admin/monitoring/user-creation` | 5 | 仪表板统计、趋势、最近用户 **v3.42 扩展** |
| **Webhooks** | `/api/v2/admin/webhooks` | 2 | Webhook 重试 |

**详细文档**: 完整的 183 个 Admin API 端点详细文档见 [docs/shared/admin-api-review.md](../shared/admin-api-review.md)

> **说明**: admin-api-review.md v3.42 记录了全部 183 个端点。v3.42 扩展 User Creation Monitoring (3→5个)。v3.41 新增 Tiers (3个)。v3.40 新增 Static Pages (7个)。

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

**📍 详细文档**: 完整的 user_code 生成逻辑、数据分析应用等详见 [docs/shared/USER-ID-SYSTEM.md](../shared/USER-ID-SYSTEM.md)

---

## 附录 B: 业务规则参考

> 📍 **Tier 命名系统和积分系统的完整文档已迁移到专用文档，避免重复维护**

### Tier 命名规范

详见: [backend-business-logic.md](backend-business-logic.md) 第 5 章

**快速参考**:
| 系统代码 | 显示名称 | 月度积分 |
|----------|----------|----------|
| `t1` | Free Plan | 0 |
| `t2` | Starter Plan | 100 |
| `t3` | Pro Plan | 200 |
| `t4` | Enterprise (预留) | 500 |

### 积分系统

详见: [backend-business-logic.md](backend-business-logic.md) 第 6 章

**快速参考**:
- **扣费顺序**: 先月度积分 → 后永久积分
- **注册赠送**: 100 永久积分
- **AI 消耗**: 5 积分/图片

### 相关文档

- [TIER-NAMING-SYSTEM.md](../shared/tier-naming-system.md) - Tier 命名系统详解
- [tier-permissions.md](../shared/tier-permissions.md) - 会员权益汇总表
- [backend-business-logic.md](backend-business-logic.md) - 完整业务规则

---

## 附录 C: 速率限制

### User API 限流

| 端点 | 限制 | 说明 |
|------|------|------|
| `/user/payment/checkout` | 5/分钟 | 防止恶意创建订单 |
| `/user/payment/portal` | 10/分钟 | Billing Portal 访问 |
| `/user/generate/images` | 10/分钟 | AI 图片生成 |
| `/user/generate/story` | 5/分钟 | AI 故事生成 |
| `/user/projects` (POST) | 20/分钟 | 创建项目 |
| `/user/assets` (POST) | 20/分钟 | 上传素材 |
| `/user/marketplace/purchase` | 10/分钟 | 购买商品 |
| `/user/analytics/events` | 60/分钟 | 分析事件上报 |

### Admin API 限流

| 端点 | 限制 | 说明 |
|------|------|------|
| 查询操作 (GET) | 30/分钟 | 大部分查询端点 |
| 创建/更新 (POST/PUT/PATCH) | 10-20/分钟 | 修改操作 |
| 删除操作 (DELETE) | 10/分钟 | 危险操作 |
| 系统操作 (聚合/缓存) | 5/分钟 | 重负载操作 |
| 缓存清空 (clear-all) | 1/10分钟 | 极危险操作 |

---

## 附录 D: 端点文档补充说明

### 文档现状

本文档当前记录了 **User API 123 个端点** 和 **Admin API 178 个端点** (v3.40 已全部评审)。

### 详细端点文档

**User API 详细文档**: [docs/shared/user-api-review.md](../shared/user-api-review.md)
- ✅ 123 个 User API 端点完整文档
- ✅ 每个端点的请求参数、请求体示例、响应示例
- ✅ 验证规则、限流配置、错误码说明
- ✅ DDD 架构合规性验证
- ✅ 测试覆盖率: 65%+

**Admin API 详细文档**: [docs/shared/admin-api-review.md](../shared/admin-api-review.md)
- ✅ 143 个 Admin API 端点（142 个已有完整文档，1 个待补充：PUT /config/admin 占位符）
- ✅ 18 个模块分类组织（AI Insights、AI Models、Asset Categories、Campaigns、Config、Events、Experiments、Feature Flags、Logs、Metrics、Moderation、Notifications、Stats、Subscriptions、System、Tasks、Users、Webhooks）
- ✅ 每个端点的请求参数、请求体示例、响应示例
- ✅ 验证规则、限流配置、错误码说明
- ✅ DDD 架构合规性验证

### DDD 架构合规性

**所有 API (User + Admin) 已完成 DDD 架构迁移** (2026-01-11):

- ✅ **统一分页**: `offset` + `limit` (非 `page` + `limit`)
- ✅ **统一返回类型**: `List[Entity]` (非 `List[dict]`)
- ✅ **安全防护**: DoS/SSRF 防护覆盖率 95%+
- ✅ **审计日志**: 所有删除操作记录到 `admin_operations`
- ✅ **异步任务**: PDF/ZIP 导出异步化 (5.3x 性能提升)
- ✅ **测试覆盖率**: ≥ 60% (实际: 65%+)

**参考文档**:
- `API-REVIEW-USER.md` (User API 审查报告)
- `API-REVIEW-ADMIN.md` (Admin API 审查报告)
- `API-DB-Fix-Progress.md` (数据库一致性修复进度)

---

*文档版本: v3.33*
*最后更新: 2026-01-27*
*更新内容:
- v3.33: user_assets/dashboard 端点重构 - 新增视图过滤 (all/bought/selling)、搜索、分页
- v3.32: User Creation Monitoring 模块扩展 (3→5 端点) - 新增 /recent 和 /trends 端点
- v3.31: 新增 Tiers API (3个端点) - Tier 配置管理
- v3.30: 精简附录 B/C，Tier 和积分系统详细内容移至 backend-business-logic.md
- v3.29: Feature Flags v1.2 Tier 分层筛选支持 (allowed_tiers 字段, 规则级 tiers)
- v3.28: Feature Flags v1.1 树状结构支持 (Admin 15 个端点, User 4 个端点)
- v3.27: 重构 API 文档结构,分离 User/Admin API 详细文档
- v3.26: 新增完整的 Admin API 文档 (15个模块), 包含 DDD 架构说明和审计日志机制
- v3.25: 补充 9 个缺失的 User API 端点章节, 添加 Clerk ID 格式说明*
