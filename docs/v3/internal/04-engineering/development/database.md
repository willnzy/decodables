# 数据库规范

> **版本**: 1.0.0
> **创建日期**: 2026-02-05
> **状态**: 🟡 待补充
> **同步范围**: [backend]
> **Schema 文件**: `migrations/v2/`

---

## 概述

定义数据库设计和管理规范。

---

## 命名规范

### 表命名

| 规则 | 示例 |
|------|------|
| 使用复数 | `users`, `projects` |
| 下划线分隔 | `user_profiles` |
| 小写字母 | 不使用大写 |

### 字段命名

| 规则 | 示例 |
|------|------|
| 下划线分隔 | `created_at` |
| 布尔字段 | `is_active`, `has_permission` |
| 外键 | `user_id`, `project_id` |

---

## 标准字段

### 每个表必须包含

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `created_at` | TIMESTAMPTZ | 创建时间 (UTC) |
| `updated_at` | TIMESTAMPTZ | 更新时间 (UTC) |

### 可选标准字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `deleted_at` | TIMESTAMPTZ | 软删除时间 |
| `created_by` | UUID | 创建者 |
| `version` | INT | 乐观锁版本号 |

---

## 索引规范

| 场景 | 索引类型 |
|------|----------|
| 主键 | PRIMARY KEY |
| 外键 | INDEX |
| 唯一约束 | UNIQUE |
| 常用查询字段 | INDEX |
| 复合查询 | 复合索引 |

---

## 时间处理

| 规则 | 说明 |
|------|------|
| 存储 | 始终使用 TIMESTAMPTZ (UTC) |
| 生成 | Python: `datetime.now(timezone.utc)` |
| 显示 | 前端转换为用户时区 |

---

## 迁移管理

### Schema 文件

```
migrations/v2/
├── 01_core_business.sql     # 核心业务表
├── 02_platform_services.sql # 平台服务表
└── 03_infrastructure.sql    # 基础设施表
```

### 修改流程

1. 直接修改对应的 schema 文件
2. 不创建迁移脚本
3. 提交并推送
4. 在数据库执行变更

---

## 待补充内容

- [ ] 性能优化指南
- [ ] 分区策略
- [ ] 备份恢复流程
