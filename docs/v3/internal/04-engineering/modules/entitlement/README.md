# Entitlement 模块

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证

---

## 概述

权益系统的技术实现文档。

## 文档清单

| 文档 | 描述 | 状态 |
|------|------|------|
| [implementation-guide.md](./implementation-guide.md) | 开发实现指南 | 🟢 |

## 业务规则

业务规则文档位于 `05-business/entitlement/`：
- [权限矩阵](../../../05-business/entitlement/permission-matrix.md)
- [策略规则](../../../05-business/entitlement/policy-rules.md)
- [系统设计](../../../05-business/entitlement/system-design.md)

## 代码位置

```
后端: domains/entitlement/, application/use_cases/entitlement/
前端: @business/hooks/useEntitlement.ts, @business/stores/entitlement/
```
