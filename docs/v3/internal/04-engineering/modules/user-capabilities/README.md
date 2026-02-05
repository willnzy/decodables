# 用户能力模块

> User Capabilities - 用户侧功能系统设计

> **同步范围**: [fullstack]
> **状态**: 🟢 已验证
> **最后更新**: 2026-02-05

---

## 一、模块概述

用户能力模块涵盖用户日常使用中的核心功能，包括资产管理、主题系统、推荐系统等。

---

## 二、模块清单

| 模块 | 文档 | 状态 | 描述 |
|------|------|------|------|
| 资产系统 | [assets-system.md](./assets-system.md) | 🟢 Active | 用户资产上传、管理、收藏夹 |
| 主题系统 | [theme-system.md](./theme-system.md) | 🟢 Active | 主题/Daily Doodle 展示 |
| 推荐系统 | [referrals-system.md](./referrals-system.md) | 🟢 Active | 用户推荐与返利 |
| 分析系统 | [analytics-system.md](./analytics-system.md) | 🟢 Active | 用户行为追踪与分析 |
| 支持系统 | [support-system.md](./support-system.md) | 🟡 Draft | 客服工单与反馈 |

---

## 三、快速导航

### 资产系统
- 上传: 支持图片、SVG、PDF，带 SSRF 保护
- 存储: Supabase Storage
- 文件夹: 分类管理
- 收藏: 星标功能

### 主题系统
- Daily Doodle: 每日主题
- 主题列表: 分类展示
- 模板关联: 主题与模板关联

### 推荐系统
- 推荐码: 用户专属
- 奖励: 积分发放
- 统计: 推荐数据

---

## 四、相关文档

- [Dashboard 架构](../dashboard/architecture.md)
- [Marketplace 架构](../marketplace/architecture.md)
