# Make Decodables 后端 API 参考文档

> 版本: 3.24
> 更新时间: 2026-01-10
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

## 附录 B: 速率限制

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

*文档版本: v3.25*
*最后更新: 2026-01-11*
*更新内容: 补充 9 个缺失的 API 端点章节, 添加 Clerk ID 格式说明*
