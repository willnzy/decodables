# 后端 API 参考文档

**状态**: active  
**版本**: 3.44.0  
**版本日期**: 2026-01-29  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 背景

- 问题或机会: API 规范分散，缺少统一的引用入口与口径
- 目标与非目标: 目标是统一 REST 规范、认证与通用返回格式；非目标是替代具体业务流程说明

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- RESTful 设计规范与通用约束
- User/Admin API 的统一参考入口

## 影响范围

- 相关模块: API 设计与路由
- 相关文档: `docs/v2/05-api/user-endpoints.md`

## 证据与验证

- 关键证据来源：`decodables/api/`、`decodables-fe/app/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 3.44.0 | 结构对齐与信息补齐 | Docs Working Group |

## 1. RESTful 设计规范

### 1.1 HTTP 方法速查

| 方法 | 用途 | 幂等性 | 安全性 | 请求体 | 典型响应码 |
|------|------|--------|--------|--------|------------|
| GET | 获取资源 | ✅ | ✅ | ❌ | 200, 404 |
| POST | 创建/操作 | ❌ | ❌ | ✅ | 201, 200, 400 |
| PUT | 完整替换 | ✅ | ❌ | ✅ | 200, 201 |
| PATCH | 部分更新 | ❌ | ❌ | ✅ | 200 |
| DELETE | 删除 | ✅ | ❌ | ❌ | 200, 204 |

### 1.2 状态码规范

**成功响应**: 200, 201, 204  
**客户端错误**: 400, 401, 402, 403, 404, 409, 422, 429  
**服务端错误**: 500, 502, 503

### 1.3 路径命名规范

- 名词复数、小写、连字符  
- 资源嵌套不超过 2 层  
- 版本号 `/api/v2/...` 为当前版本

### 1.4 API 分类

**公开 API (需认证)**:

```
/api/v2/user/*
/api/v2/user/billing/*
/api/v2/user/projects/*
/api/v2/user/generate/*
/api/v2/user/assets/*
/api/v2/user/marketplace/*
/api/v2/user/payment/*
/api/v2/user/experiments/*
```

**公开 API (无需认证)**:

```
/api/v2/user/config/*
/api/v2/user/logs/*
/api/v2/user/themes/*
/api/v2/user/resources/*
```

**Admin API**:

```
/api/v2/admin/users/*
/api/v2/admin/config/*
/api/v2/admin/tiers/*
/api/v2/admin/experiments/*
```

---

## 2. 基础信息

### 2.1 基础 URL

| 环境 | 基础 URL |
|------|----------|
| 生产 | `https://api.foliaz.com` |
| 开发 | `http://localhost:8000` |

### 2.2 认证方式

```
Authorization: Bearer <access_token>
```

### 2.3 通用响应格式

成功:

```json
{
  "status": "success",
  "data": {}
}
```

错误:

```json
{
  "detail": "错误描述",
  "error_code": "ERROR_CODE"
}
```

### 2.4 分页参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| offset | int | 0 | 偏移量 |
| limit | int | 20 | 每页数量 (最大 100) |

---

## 3. 健康检查 API

### GET `/health`

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

```json
{
  "status": "healthy",
  "services": {},
  "queues": { "high": 0, "default": 5, "low": 12 },
  "workers": { "active": 3, "idle": 1 },
  "warnings": []
}
```

---

## 4. Webhooks

### 4.1 Auth API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/register` | POST | 用户注册 |
| `/auth/login` | POST | 用户登录 |
| `/auth/refresh` | POST | 刷新 token |
| `/auth/logout` | POST | 登出 |
| `/auth/verify-email` | POST | 邮箱验证 |
| `/auth/forgot-password` | POST | 忘记密码 |
| `/auth/reset-password` | POST | 重置密码 |

### 4.2 Stripe Webhook

**URL**: `POST /api/v2/user/webhooks/stripe`  
**Header**: `Stripe-Signature`

事件:
- `checkout.session.completed`
- `invoice.payment_succeeded`
- `customer.subscription.deleted`
- `customer.subscription.updated`
- `charge.refunded`

---

## 5. API 总览

### 5.1 User API

详见 `docs/v2/05-api/user-endpoints.md`

### 5.2 Admin API

详见 `docs/v2/05-api/admin-endpoints.md`

---

## 附录

### A. 认证与用户 ID

详见 `docs/v2/03-business/user-id-system.md`

### B. Tier 命名

详见 `docs/v2/03-business/tier-naming-system.md`

### C. 积分系统

详见 `docs/v2/03-business/entitlement/credits-lifecycle.md`

