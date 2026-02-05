# 权限系统 - 重构规划

> **同步范围**: [fullstack]
> **状态**: 🟡 规划中
> **内容来源**: v1 设计文档

---

## 目录说明

保留权限系统的完整设计文档，作为重构实现的指南。

## 源文档

来自 `decodables-fe/docs/v1/shared/entitlement/`（28 个文档）

## 计划文档

| 文档 | 用途 | 对应 v1 | 状态 |
|------|------|---------|------|
| `design.md` | 完整系统设计 | 03-system-design.md | 📋 待整理 |
| `feature-flag-engine.md` | Flag 引擎设计 | 04-feature-flag-engine.md | 📋 待整理 |
| `priority-rules.md` | 优先级规则 | 06-priority-rules.md | 📋 待整理 |
| `scenarios/` | 各场景设计 | 11-25 | 📁 目录 |

## 重构优先级

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 完整权限评估引擎 | 核心功能 |
| P0 | Tier 降级处理 | 边界情况 |
| P1 | 用户 Override | 特殊权限 |
| P2 | 用户组权限 | 批量授权 |
| P2 | Workspace 权限 | 多租户 |

## 参考

- 原始设计：`decodables-fe/docs/v1/shared/entitlement/README.md`
