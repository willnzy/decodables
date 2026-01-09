# HTTP Methods Usage Guidelines

> RESTful API 设计规范 - HTTP 方法使用标准

## 概述

本文档定义了 Make Decodables 后端 API 的 HTTP 方法使用标准，遵循 RESTful 设计原则和行业最佳实践。

---

## HTTP 方法速查表

| 方法 | 用途 | 幂等性 | 安全性 | 请求体 | 典型响应码 |
|------|------|--------|--------|--------|------------|
| GET | 获取资源 | ✅ 是 | ✅ 是 | ❌ 无 | 200, 404 |
| POST | 创建资源/执行操作 | ❌ 否 | ❌ 否 | ✅ 有 | 201, 200, 400 |
| PUT | 完整替换资源 | ✅ 是 | ❌ 否 | ✅ 有 | 200, 201, 404 |
| PATCH | 部分更新资源 | ❌ 否 | ❌ 否 | ✅ 有 | 200, 404 |
| DELETE | 删除资源 | ✅ 是 | ❌ 否 | ❌ 无 | 200, 204, 404 |

### 关键概念

- **幂等性 (Idempotent)**: 多次执行相同请求，结果一致
- **安全性 (Safe)**: 不会修改服务器状态

---

## 详细使用规范

### 1. GET - 查询/获取

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

### 2. POST - 创建/执行操作

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

### 3. PUT - 完整替换

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

### 4. PATCH - 部分更新

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

### 5. DELETE - 删除

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

---

## 特殊场景处理

### 1. 操作型 API (RPC 风格)

某些操作不适合 REST 资源模型，使用 POST 动词:

```
POST /api/v2/credits/deduct       # 扣除积分
POST /api/v2/admin/refund         # 执行退款
POST /api/v2/admin/aggregation/run  # 触发聚合任务
POST /api/v2/admin/cache/clear    # 清空缓存
```

### 2. 批量操作

```
POST /api/v2/analytics/events     # 批量记录事件
POST /api/v2/generations/batch-delete  # 批量删除
POST /api/v2/admin/notification/batch  # 批量发送通知
```

### 3. 复杂查询

当 GET 参数过长或过于复杂时，可用 POST:

```
POST /api/v2/search               # 复杂搜索
POST /api/v2/admin/users/export   # 导出用户数据 (带筛选条件)
```

### 4. 文件上传

```
POST /api/v2/assets/upload        # 上传素材
POST /api/v2/tools/ocr            # 上传图片进行 OCR
```

---

## 响应状态码规范

### 成功响应

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | GET/PUT/PATCH/DELETE 成功 |
| 201 | Created | POST 创建成功 |
| 204 | No Content | DELETE 成功，无返回内容 |

### 客户端错误

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未登录/Token 无效 |
| 403 | Forbidden | 无权限访问 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 (如重复创建) |
| 422 | Unprocessable Entity | 业务校验失败 |
| 429 | Too Many Requests | 限流 |

### 服务端错误

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 500 | Internal Server Error | 服务器内部错误 |
| 502 | Bad Gateway | 上游服务错误 |
| 503 | Service Unavailable | 服务暂时不可用 |

---

## API 路径命名规范

### 基本规则

1. **使用名词，不用动词**: `/projects` 而非 `/getProjects`
2. **使用复数形式**: `/projects` 而非 `/project`
3. **使用小写和连字符**: `/user-settings` 而非 `/userSettings`
4. **资源嵌套不超过 2 层**: `/projects/{id}/pages` 而非 `/projects/{id}/pages/{pageId}/elements`

### 版本控制

```
/api/v2/...   # 当前版本
/api/v1/...   # 遗留版本 (逐步废弃)
```

---

## Make Decodables API 分类

### 公开 API (需认证)

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

### 公开 API (无需认证)

```
/api/v2/configs/*     # 公开配置
/api/v2/logs/*        # 错误上报
/api/v2/themes/*      # 节日主题
/api/v2/resources/*   # 系统资源
```

### Admin API (需管理员权限)

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

### Webhook API (第三方回调)

```
/api/webhooks/stripe    # Stripe 支付回调
/api/webhooks/clerk     # Clerk 用户回调
/api/webhooks/fal       # FAL AI 回调
```

> **注意**: Webhook 路径不能随意修改，需要在第三方平台配置

---

## 检查清单

新增 API 前，请确认:

- [ ] HTTP 方法选择正确 (GET/POST/PUT/PATCH/DELETE)
- [ ] 路径命名符合规范 (名词、复数、小写)
- [ ] 响应状态码使用正确
- [ ] 需要认证的 API 添加了 `Depends(get_current_user)` 或 `Depends(require_admin)`
- [ ] 添加了适当的限流 (`@limiter.limit`)
- [ ] 更新了 API 文档 (`__init__.py` 中的 docstring)

---

## 参考资料

- [RESTful API 设计最佳实践](https://restfulapi.net/)
- [HTTP 方法规范 (RFC 7231)](https://tools.ietf.org/html/rfc7231)
- [Google API 设计指南](https://cloud.google.com/apis/design)
