# Entitlement 实现文档索引

> **版本**: v1.0
> **日期**: 2026-02-04
> **状态**: 初始化

---

## 文档说明

本目录包含 Entitlement 系统的技术实现文档，与设计文档 (01-25) 形成对应关系。

**设计文档**: 描述"是什么"和"为什么"
**实现文档**: 描述"怎么做"和"代码在哪"

---

## 实现文档列表

| 序号 | 文档 | 说明 | 状态 |
|:----:|------|------|:----:|
| 01 | [01-database-schema.md](./01-database-schema.md) | 数据库表结构、索引、RPC 函数 | 🔴 待实现 |
| 02 | [02-backend-services.md](./02-backend-services.md) | 后端 Service 层实现 | 🔴 待实现 |
| 03 | [03-backend-repositories.md](./03-backend-repositories.md) | 后端 Repository 层实现 | 🔴 待实现 |
| 04 | [04-backend-apis.md](./04-backend-apis.md) | API 端点实现 | 🔴 待实现 |
| 05 | [05-frontend-stores.md](./05-frontend-stores.md) | 前端 Zustand Store 实现 | 🔴 待实现 |
| 06 | [06-frontend-components.md](./06-frontend-components.md) | 前端组件实现 | 🔴 待实现 |
| 07 | [07-migration-scripts.md](./07-migration-scripts.md) | 数据迁移脚本 | 🔴 待实现 |

---

## 设计文档 → 实现文档映射表

### 核心配置 (01-10)

| 设计文档 | 数据库 | 后端 Service | 后端 Repo | API | 前端 Store | 前端组件 |
|----------|:------:|:------------:|:---------:|:---:|:----------:|:--------:|
| 01-permission-matrix | §2.1 | §3.1 | - | - | §2.1 | - |
| 02-tier-config | §2.2 | §3.2 | §2.1 | §2.1 | §2.2 | - |
| 03-system-design | §1 | §1 | §1 | §1 | §1 | - |
| 04-feature-flag-engine | §2.3 | §3.3 | §2.2 | §2.2 | §2.3 | - |
| 05-ui-spec | - | - | - | - | - | §2-§5 |
| 06-priority-rules | - | §3.4 | - | - | §2.4 | - |
| 07-tier-inheritance | - | §3.2 | - | - | §2.2 | - |
| 08-user-groups | §2.4 | §3.5 | §2.3 | §2.3 | §2.5 | §6 |
| 09-config-versioning | §2.5 | §3.6 | §2.4 | - | - | - |
| 10-workspace-override | §2.6 | §3.7 | §2.5 | §2.4 | §2.6 | - |

### 生命周期 (11-18)

| 设计文档 | 数据库 | 后端 Service | 后端 Repo | API | 前端 Store | 前端组件 |
|----------|:------:|:------------:|:---------:|:---:|:----------:|:--------:|
| 11-trial-expiration | §3.1 | §4.1 | §3.1 | §3.1 | §3.1 | §7 |
| 12-tier-downgrade | §3.2 | §4.2 | §3.2 | §3.2 | §3.2 | §8 |
| 13-subscription-pause | §3.3 | §4.3 | §3.3 | §3.3 | §3.3 | §9 |
| 14-billing-cycle-switch | §3.4 | §4.4 | §3.4 | §3.4 | - | - |
| 15-credits-lifecycle | §3.5 | §4.5 | §3.5 | §3.5 | §3.4 | §10 |
| 16-renewal-reminders | §3.6 | §4.6 | - | - | - | §11 |
| 17-invoice-management | §3.7 | §4.7 | §3.6 | §3.6 | - | §12 |
| 18-refund-processing | §3.8 | §4.8 | §3.7 | §3.7 | - | - |

### 营销与扩展 (19-25)

| 设计文档 | 数据库 | 后端 Service | 后端 Repo | API | 前端 Store | 前端组件 |
|----------|:------:|:------------:|:---------:|:---:|:----------:|:--------:|
| 19-promotions | §4.1 | §5.1 | §4.1 | §4.1 | §4.1 | §13 |
| 20-referral-rewards | §4.2 | §5.2 | §4.2 | §4.2 | §4.2 | §14 |
| 21-education-discount | §4.3 | §5.3 | §4.3 | §4.3 | - | §15 |
| 22-free-quota | §4.4 | §5.4 | - | - | §4.3 | - |
| 23-feature-sunset | - | §5.5 | - | - | §4.4 | §16 |
| 24-conflict-resolution | - | §5.6 | - | - | - | - |
| 25-future-scenarios | - | - | - | - | - | - |

---

## 状态说明

| 状态 | 含义 |
|:----:|------|
| 🔴 | 待实现 - 设计已完成，代码未开始 |
| 🟡 | 进行中 - 部分代码已实现 |
| 🟢 | 已完成 - 代码实现并测试通过 |
| ⚫ | 不适用 - 该设计文档无需此层实现 |

---

## 使用指南

### 1. 查找某设计文档的实现

1. 在上方映射表中找到设计文档行
2. 查看对应列的章节号
3. 跳转到对应实现文档的章节

**示例**: 查找 `15-credits-lifecycle.md` 的后端 Service 实现
- 映射表显示: §4.5
- 打开 `02-backend-services.md`，跳转到 `§4.5 积分生命周期`

### 2. 实现新功能

1. 先阅读设计文档 (01-25)
2. 查看映射表确定需要实现的层
3. 按顺序实现: 数据库 → 后端 Repo → 后端 Service → API → 前端 Store → 前端组件
4. 更新对应实现文档的状态

### 3. 代码审查

1. 根据 PR 涉及的文件，在映射表中找到对应设计文档
2. 对照设计文档检查实现是否符合规范
3. 使用 `26-audit-checklist.md` 进行合规性检查

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [../README.md](../README.md) | 设计文档导航 |
| [../26-audit-checklist.md](../26-audit-checklist.md) | 审计清单 |
| [../27-audit-report-20260204.md](../27-audit-report-20260204.md) | 审计报告 |

---

**END OF DOCUMENT**
