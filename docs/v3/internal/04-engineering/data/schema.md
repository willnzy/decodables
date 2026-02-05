# 数据库 Schema

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [backend]
> **对应代码**: `decodables/migrations/v2/`

---

## 概述

数据库表结构定义，使用 PostgreSQL (Supabase)。

---

## Schema 文件

主 Schema 文件（3个）：

| 文件 | 内容 |
|------|------|
| `01_core_business.sql` | 核心业务表 |
| `02_platform_services.sql` | 平台服务表 |
| `03_infrastructure.sql` | 基础设施表 |

---

## 核心业务表

### 用户相关
- `users` - 用户基本信息
- `user_profiles` - 用户扩展资料
- `user_settings` - 用户设置

### 订阅相关
- `subscriptions` - 订阅记录
- `subscription_history` - 订阅变更历史

### 积分相关
- `credit_transactions` - 积分交易记录

### 素材相关
- `assets` - 素材表
- `asset_categories` - 素材分类
- `user_assets` - 用户素材关联

---

## 平台服务表

### Feature Flag
- `feature_flags` - 功能开关
- `feature_flag_rules` - 开关规则

### 配置
- `system_configs` - 系统配置
- `tier_configs` - Tier 配置

---

## 详细定义

详见：
- [实体定义](./entities.md)
- [Canvas Schema](./canvas-schema.md)
