# API 参考文档

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证 (来源: v2 文档 + 代码分析)
> **版本**: 1.0.0
> **最后更新**: 2026-02-05
> **数据来源**: `api/` 目录结构

---

## 一、概述

### 1.1 API 版本

当前版本: **v2**

```
/api/v2/user/*    # 用户端 API
/api/v2/admin/*   # 管理端 API
```

### 1.2 基础 URL

| 环境 | URL |
|------|-----|
| 生产 | `https://api.foliaz.com` |
| 开发 | `http://localhost:8000` |

---

## 二、RESTful 设计规范

### 2.1 HTTP 方法

| 方法 | 用途 | 幂等性 | 请求体 | 典型响应码 |
|------|------|:------:|:------:|------------|
| GET | 获取资源 | ✅ | ❌ | 200, 404 |
| POST | 创建/操作 | ❌ | ✅ | 201, 200, 400 |
| PUT | 完整替换 | ✅ | ✅ | 200, 201 |
| PATCH | 部分更新 | ❌ | ✅ | 200 |
| DELETE | 删除 | ✅ | ❌ | 200, 204 |

### 2.2 状态码规范

| 类别 | 状态码 | 说明 |
|------|--------|------|
| 成功 | 200 | OK |
| 成功 | 201 | Created |
| 成功 | 204 | No Content |
| 客户端错误 | 400 | Bad Request |
| 客户端错误 | 401 | Unauthorized |
| 客户端错误 | 402 | Payment Required |
| 客户端错误 | 403 | Forbidden |
| 客户端错误 | 404 | Not Found |
| 客户端错误 | 409 | Conflict |
| 客户端错误 | 422 | Unprocessable Entity |
| 客户端错误 | 429 | Too Many Requests |
| 服务端错误 | 500 | Internal Server Error |
| 服务端错误 | 502 | Bad Gateway |
| 服务端错误 | 503 | Service Unavailable |

### 2.3 路径命名规范

- 名词复数、小写、连字符
- 资源嵌套不超过 2 层
- 示例: `/api/v2/user/projects/{id}/pages`

---

## 三、认证

### 3.1 认证方式

```
Authorization: Bearer <access_token>
```

### 3.2 Token 说明

| 类型 | 有效期 | 用途 |
|------|--------|------|
| Access Token | 15 分钟 | API 请求认证 |
| Refresh Token | 7 天 | 刷新 Access Token |

### 3.3 认证端点

| 端点 | 方法 | 说明 | 认证 |
|------|------|------|:----:|
| `/auth/register` | POST | 用户注册 | ❌ |
| `/auth/login` | POST | 用户登录 | ❌ |
| `/auth/refresh` | POST | 刷新 Token | ❌ |
| `/auth/logout` | POST | 登出 | ✅ |
| `/auth/verify-email` | POST | 邮箱验证 | ❌ |
| `/auth/forgot-password` | POST | 忘记密码 | ❌ |
| `/auth/reset-password` | POST | 重置密码 | ❌ |

---

## 四、通用响应格式

### 4.1 成功响应

```json
{
  "status": "success",
  "data": { ... }
}
```

### 4.2 分页响应

```json
{
  "status": "success",
  "data": {
    "items": [ ... ],
    "total": 100,
    "offset": 0,
    "limit": 20
  }
}
```

### 4.3 错误响应

```json
{
  "detail": "错误描述",
  "error_code": "ERROR_CODE"
}
```

### 4.4 分页参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|:------:|------|
| offset | int | 0 | 偏移量 |
| limit | int | 20 | 每页数量 (最大 100) |

---

## 五、API 分类

### 5.1 用户端 API (需认证)

```
/api/v2/user/profile          # 用户信息
/api/v2/user/billing          # 计费相关
/api/v2/user/projects         # 项目管理
/api/v2/user/folders          # 文件夹管理
/api/v2/user/generate         # AI 生成
/api/v2/user/assets           # 素材管理
/api/v2/user/marketplace      # 商城
/api/v2/user/payment          # 支付
/api/v2/user/notifications    # 通知
/api/v2/user/favorites        # 收藏
/api/v2/user/features         # 用户权益
```

### 5.2 用户端 API (无需认证)

```
/api/v2/user/config           # 公开配置
/api/v2/user/themes           # 主题数据
/api/v2/user/resources        # 公开资源
```

### 5.3 管理端 API

```
/api/v2/admin/users           # 用户管理
/api/v2/admin/config          # 配置管理
/api/v2/admin/tiers           # Tier 管理
/api/v2/admin/experiments     # 实验管理
/api/v2/admin/analytics       # 数据分析
```

---

## 六、健康检查

### 6.1 基础健康检查

```
GET /health
```

**Response:**

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

### 6.2 详细健康检查

```
GET /health/detailed
```

**Response:**

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

## 七、Webhooks

### 7.1 Stripe Webhook

```
POST /api/v2/user/webhooks/stripe
Header: Stripe-Signature
```

**支持的事件:**

| 事件 | 说明 |
|------|------|
| `checkout.session.completed` | 支付完成 |
| `invoice.payment_succeeded` | 发票支付成功 |
| `invoice.payment_failed` | 发票支付失败 |
| `customer.subscription.created` | 订阅创建 |
| `customer.subscription.updated` | 订阅更新 |
| `customer.subscription.deleted` | 订阅取消 |
| `charge.refunded` | 退款 |

---

## 八、常用端点速查

### 8.1 用户相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/user/profile` | GET | 获取用户信息 |
| `/api/v2/user/profile` | PATCH | 更新用户信息 |
| `/api/v2/user/profile/avatar` | PUT | 上传头像 |
| `/api/v2/user/features` | GET | 获取用户权益 |

### 8.2 项目相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/user/projects` | GET | 获取项目列表 |
| `/api/v2/user/projects` | POST | 创建项目 |
| `/api/v2/user/projects/{id}` | GET | 获取项目详情 |
| `/api/v2/user/projects/{id}` | PATCH | 更新项目 |
| `/api/v2/user/projects/{id}` | DELETE | 删除项目 |

### 8.3 计费相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/user/billing/credits` | GET | 获取积分余额 |
| `/api/v2/user/billing/subscription` | GET | 获取订阅状态 |
| `/api/v2/user/billing/history` | GET | 获取交易历史 |
| `/api/v2/user/payment/checkout` | POST | 创建支付会话 |

### 8.4 AI 生成

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v2/user/generate/image` | POST | AI 生成图片 |
| `/api/v2/user/generate/page` | POST | AI 生成页面 |
| `/api/v2/user/generate/ocr` | POST | OCR 识别 |

---

## 九、错误码列表

| 错误码 | HTTP 状态 | 说明 |
|--------|----------|------|
| `AUTH_INVALID_TOKEN` | 401 | Token 无效 |
| `AUTH_TOKEN_EXPIRED` | 401 | Token 已过期 |
| `AUTH_INSUFFICIENT_PERMISSION` | 403 | 权限不足 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `CREDITS_INSUFFICIENT` | 402 | 积分不足 |
| `QUOTA_EXCEEDED` | 403 | 配额已满 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求过于频繁 |
| `VALIDATION_ERROR` | 422 | 参数验证失败 |

---

## 十、相关文档

- [用户端点详情](./user-endpoints.md)
- [管理端点详情](./admin-endpoints.md)
- [认证模块架构](../modules/auth/architecture.md)
- [计费模块架构](../modules/billing/architecture.md)

---

**END OF DOCUMENT**
