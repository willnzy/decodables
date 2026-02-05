# API 参考文档模板

> **版本**: 1.0.0
> **创建日期**: 2026-02-05

---

## 使用说明

此模板用于创建 `04-engineering/api/{module}.md` 文件。

---

## 模板

```markdown
# {模块名称} API 参考

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证 / 🟡 待验证
> **Base Path**: `/api/v1/{module}`
> **最后更新**: YYYY-MM-DD

---

## 概述

简要描述此模块 API 的用途（1-2 句话）。

### 认证要求

| 端点 | 认证 | 权限 |
|------|------|------|
| GET /xxx | 可选 | - |
| POST /xxx | 必需 | t2+ |

### 通用响应格式

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

---

## 端点列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/xxx` | 获取列表 |
| GET | `/xxx/{id}` | 获取详情 |
| POST | `/xxx` | 创建 |
| PATCH | `/xxx/{id}` | 更新 |
| DELETE | `/xxx/{id}` | 删除 |

---

## 端点详情

### GET /xxx - 获取列表

获取 xxx 列表，支持分页和筛选。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| offset | int | 否 | 偏移量 | 0 |
| limit | int | 否 | 每页数量 | 20 |
| sort | string | 否 | 排序字段 | created_at |
| order | string | 否 | 排序方向 | desc |

#### 请求示例

```bash
curl -X GET "https://api.example.com/api/v1/xxx?offset=0&limit=10" \
  -H "Authorization: Bearer {token}"
```

#### 响应示例

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "示例",
        "created_at": "2026-01-01T00:00:00Z"
      }
    ],
    "total": 100,
    "offset": 0,
    "limit": 10
  }
}
```

#### 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| AUTH_REQUIRED | 401 | 需要认证 |
| INVALID_PARAMS | 400 | 参数错误 |

---

### GET /xxx/{id} - 获取详情

获取单个 xxx 的详细信息。

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| id | uuid | xxx 的 ID |

#### 请求示例

```bash
curl -X GET "https://api.example.com/api/v1/xxx/{id}" \
  -H "Authorization: Bearer {token}"
```

#### 响应示例

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "示例",
    "description": "详细描述",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
}
```

#### 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| NOT_FOUND | 404 | 资源不存在 |

---

### POST /xxx - 创建

创建新的 xxx。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 名称，1-100 字符 |
| description | string | 否 | 描述 |

#### 请求示例

```bash
curl -X POST "https://api.example.com/api/v1/xxx" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "新建项目",
    "description": "描述内容"
  }'
```

#### 响应示例

```json
{
  "success": true,
  "data": {
    "id": "new-uuid",
    "name": "新建项目",
    "created_at": "2026-01-01T00:00:00Z"
  },
  "message": "创建成功"
}
```

#### 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| VALIDATION_ERROR | 400 | 验证失败 |
| DUPLICATE_NAME | 409 | 名称已存在 |

---

## 数据模型

### Xxx

| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid | 唯一标识 |
| name | string | 名称 |
| description | string | 描述 |
| status | enum | 状态: active, archived |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

---

## 速率限制

| 端点 | 限制 |
|------|------|
| GET 端点 | 100 次/分钟 |
| POST/PATCH/DELETE | 30 次/分钟 |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1 | 2026-01-01 | 初始版本 |
```
