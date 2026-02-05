# 埋点规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]

---

## 概述

定义数据埋点规范，确保数据采集一致性。

---

## 事件命名规范

### 命名格式

```
{module}_{action}_{object}
```

### 示例

| 事件名 | 说明 |
|--------|------|
| `editor_create_project` | 编辑器创建项目 |
| `editor_add_element` | 添加元素 |
| `billing_upgrade_plan` | 升级套餐 |
| `auth_sign_in` | 登录 |

---

## 通用属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 用户 ID |
| `session_id` | string | 会话 ID |
| `timestamp` | datetime | 事件时间 (UTC) |
| `platform` | string | web/ios/android |
| `device` | string | 设备类型 |
| `browser` | string | 浏览器 |
| `page_url` | string | 页面 URL |

---

## 核心事件清单

### 认证事件

| 事件 | 触发时机 | 属性 |
|------|----------|------|
| `auth_sign_up` | 注册成功 | method, referral_code |
| `auth_sign_in` | 登录成功 | method |
| `auth_sign_out` | 登出 | - |

### 编辑器事件

| 事件 | 触发时机 | 属性 |
|------|----------|------|
| `editor_create_project` | 创建项目 | template_id |
| `editor_add_element` | 添加元素 | element_type |
| `editor_use_ai` | 使用 AI | ai_type, credits_used |
| `editor_export` | 导出 | format |

### 计费事件

| 事件 | 触发时机 | 属性 |
|------|----------|------|
| `billing_view_plans` | 查看套餐 | - |
| `billing_start_checkout` | 开始结账 | plan_type |
| `billing_complete_purchase` | 完成购买 | plan_type, amount |

---

## 待补充内容

- [ ] 完整事件清单
- [ ] 各事件详细属性
- [ ] 埋点实现指南
