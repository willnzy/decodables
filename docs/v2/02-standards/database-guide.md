# 数据库开发规范

**状态**: active  
**版本**: 2.1.0  
**版本日期**: 2026-01-12  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: backend  
**source_repo**: backend  
**sync_required**: no

---

## 背景

- 问题或机会: 待补充
- 目标与非目标: 待补充

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 仅使用 3 个主 Schema 文件进行变更
- 禁止创建临时迁移脚本
- 变更流程: 直接编辑主文件 → 提交代码

## 详细说明

### Schema 管理规范

### 1.1 主 Schema 文件 (仅 3 个)

```
decodables/migrations/v2/
├── 01_core_business.sql
├── 02_platform_services.sql
└── 03_infrastructure.sql
```

### 1.2 禁止事项

- 不创建 `migrations/v1.28__xxx.sql`
- 不创建 `migrations/v3/04_xxx.sql`
- 不创建任何临时迁移脚本

### 1.3 正确流程

1. 判断变更归属  
2. 直接编辑对应主文件  
3. 提交代码

---

## 2. 文件结构

```
decodables/migrations/v2/
├── 01_core_business.sql
├── 02_platform_services.sql
├── 03_infrastructure.sql
└── docs/
    ├── README.md
    ├── REFACTORING_REPORT.md
    └── MIGRATION_GUIDE.md
```

---

## 3. RPC 与索引

- RPC 放在主文件末尾
- 索引可使用部分索引
- 保持命名清晰（表名/字段前缀）

---

## 4. 视图与安全

### 4.1 视图命名

- 视图统一使用 `v_` 前缀

### 4.2 RLS

- 关键业务表默认启用 RLS
- 新增表需定义最小权限策略

---

## 5. 字段映射表 (Field Mappings)

- 用于统一字段映射与查询规范
- 涉及字段映射表时需同步文档

---

## 6. 常见问题

- Schema 变更只通过 3 个主文件
- 旧版 ddl.sql 仅保留参考

## 影响范围

- 相关模块: 数据库与存储层
- 相关文档: `docs/v2/06-operations/deployment-scaling.md`

## 证据与验证

- 关键证据来源：`decodables/migrations/v2/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 2.1.0 | 结构对齐与信息补齐 | Docs Working Group |
