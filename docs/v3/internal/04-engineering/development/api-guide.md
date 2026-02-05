# API 设计规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **参考**: 见 `api/` 目录下的具体 API 文档

---

## 概述

定义 RESTful API 设计规范。

---

## URL 设计

### 命名规则

```
/{version}/{resource}/{id}/{sub-resource}
```

### 示例

| 操作 | URL | 方法 |
|------|-----|------|
| 获取项目列表 | `/v1/projects` | GET |
| 创建项目 | `/v1/projects` | POST |
| 获取单个项目 | `/v1/projects/{id}` | GET |
| 更新项目 | `/v1/projects/{id}` | PUT |
| 删除项目 | `/v1/projects/{id}` | DELETE |

---

## 请求规范

### 分页参数

| 参数 | 类型 | 默认值 |
|------|------|--------|
| `offset` | int | 0 |
| `limit` | int | 20 |

### 排序参数

```
?sort=created_at&order=desc
```

### 过滤参数

```
?status=active&tier=t2
```

---

## 响应规范

### 成功响应

```json
{
  "data": { ... },
  "meta": {
    "total": 100,
    "offset": 0,
    "limit": 20
  }
}
```

### 错误响应

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": { ... }
  }
}
```

---

## HTTP 状态码

| 状态码 | 用途 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 未找到 |
| 500 | 服务器错误 |

---

## 待补充内容

- [ ] 认证规范详细说明
- [ ] 版本管理策略
- [ ] API 变更流程
