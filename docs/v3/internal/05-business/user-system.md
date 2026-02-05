# 用户体系

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [fullstack]
> **对应代码**: `domains/identity/`

---

## 概述

用户体系定义，包括双 ID 系统和用户生命周期。

---

## 双用户标识符

| 标识符 | 格式 | 用途 |
|--------|------|------|
| **user_id** | UUID v4 | 系统内部、数据库主键 |
| **user_code** | 26位数字 | 用户可见、客服查询 |

### user_code 格式

```
YYMMDD + HHMMSS + mmmm + UUUUUUU + RRR
  6位     6位     4位     7位      3位
 日期    时间    毫秒    序号     随机
```

---

## 详细文档

- [双 ID 系统](./user-id-system.md)
- [用户生命周期](./user-system/user-lifecycle.md)

---

## 相关文档

- [Tier 体系](./tier-system.md)
- [认证功能规格](../02-product/features/auth.md)
