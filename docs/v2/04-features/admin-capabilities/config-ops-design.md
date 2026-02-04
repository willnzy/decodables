# 配置与权限系统设计

> 系统配置、等级权限与功能开关的管理能力设计。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/configs/`, `decodables/api/admin/config.py`, `decodables/api/admin/tiers.py`, `decodables/api/admin/feature_flags.py`, `decodables/api/admin/config_models.py`

---

## 背景

- 需要集中管理系统配置与权限
- 需要统一 Feature Flags 与配置缓存

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一系统配置、Tier 权限与 Feature Flags 的管理入口
- 提供审计、限流与权限校验的安全护栏
- 支持灰度/评估与回滚策略

## 能力清单

- System Config 管理（查询、更新、批量更新）
- Rate Limits 管理（查询、预设、应用）
- Tier 权限配置（展示名、权益、价格、额度）
- Feature Flags 管理（CRUD、开关、评估、审计）

## 关键流程

- 配置查询 → 更新 → 审计记录 → 缓存清理
- Rate Limit 预设 → 应用 → 生效
- Tier 配置修改 → 权限/价格更新 → 清缓存
- Flag 创建 → 灰度/规则 → 测试评估 → 开关/归档

## 规则与护栏

- 管理员权限与接口限流
- Config key 长度与类别校验
- Tier code 必须为 `t1`-`t4`
- Feature Flag 允许 `allowed_tiers` 分层过滤

## 接口清单（Admin）

- `GET /api/v2/admin/config`
- `GET /api/v2/admin/config/{config_key}`
- `PUT /api/v2/admin/config`
- `PUT /api/v2/admin/config/batch`
- `GET /api/v2/admin/config/rate-limits`
- `POST /api/v2/admin/config/rate-limits/preset`
- `GET /api/v2/admin/config/rate-limits/presets`
- `POST /api/v2/admin/config/cache/clear`

- `GET /api/v2/admin/tiers`
- `GET /api/v2/admin/tiers/{tier_code}`
- `PUT /api/v2/admin/tiers/{tier_code}`

- `GET /api/v2/admin/feature-flags`
- `POST /api/v2/admin/feature-flags`
- `GET /api/v2/admin/feature-flags/{key}`
- `PATCH /api/v2/admin/feature-flags/{key}`
- `POST /api/v2/admin/feature-flags/{key}/toggle`
- `DELETE /api/v2/admin/feature-flags/{key}`
- `POST /api/v2/admin/feature-flags/test-evaluation`
- `GET /api/v2/admin/feature-flags/{key}/audit`

## 影响范围

- 相关模块：配置与权限
- 相关文档：`docs/v2/10-product/admin/config-management/configs.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/admin/configs/`、`decodables/api/admin/config.py`、`decodables/api/admin/tiers.py`、`decodables/api/admin/feature_flags.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
