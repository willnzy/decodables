# 后台业务逻辑说明

**状态**: active  
**版本**: 3.27.0  
**版本日期**: 2026-01-16  
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

- 核心业务能力概述与边界说明
- 关键业务规则与系统约束

## 详细说明

## 1. 产品概述

Make Decodables 是 AI 驱动的 8 页可折叠迷你书创作平台。

**核心价值**:
- 30 秒内生成完整 8 页内容
- 文本 + 图像 AI 完整流程
- 打印友好、教育导向

---

## 2. 架构状态

- v3.27 Stable (Zero Debt)
- DDD 三层架构完成迁移

详见: `docs/v2/01-architecture/backend-architecture.md`

---

## 3. 业务模块总览

1. 用户等级与订阅  
2. 积分系统  
3. 权限与访问控制  
4. AI 服务  
5. Marketplace 市场  
6. 项目管理  
7. 资源管理  
8. 导出功能  
9. A/B 测试与实验  
10. 缓存系统  
11. 分析与追踪  
12. 支付系统  
13. 文章管理系统  
14. 主题管理系统

---

## 4. 用户等级与订阅

- Tier 使用 `t1/t2/t3/t4` 系统代码
- 显示名称可配置（system_configs）
- t4 预留，不对外开放

详见:
- `docs/v2/03-business/tier-naming-system.md`
- `docs/v2/03-business/entitlement/permission-matrix.md`

---

## 5. 认证系统 (Self-hosted Auth)

- JWT HS256 + Refresh Token
- Email OTP 验证
- user_id + user_code 双标识

详见:
- `docs/v2/03-business/user-id-system.md`

---

## 6. 积分系统

核心规则:

- 积分来源类型 + 有效期二维模型
- 扣费优先级 FEFO
- 退款按逆序回收

详见:
- `docs/v2/03-business/entitlement/credits-lifecycle.md`

---

## 7. 权限与访问控制

权限由 Entitlement + Feature Flag + Merge Layer 控制。

详见:
- `docs/v2/03-business/entitlement/system-design.md`
- `docs/v2/03-business/entitlement/permission-matrix.md`
- `docs/v2/03-business/entitlement/feature-flag-engine.md`

---

## 8. AI 服务

- AI 生图、AI 生 Page、OCR
- 消耗积分，支持原价/现价
- 统一由 system_configs 配置

详见:
- `docs/v2/03-business/entitlement/permission-matrix.md`

---

## 9. Marketplace

- 素材发布、审核、购买
- 付费/免费发布分级控制

详见:
- `docs/v2/03-business/entitlement/permission-matrix.md`

---

## 10. 项目与资源管理

- 项目 CRUD 与访问控制
- 资源分级与分类体系

---

## 11. 导出功能

- PDF 打印、PDF 下载、ZIP 导出
- Tier 权限控制

详见:
- `docs/v2/03-business/entitlement/permission-matrix.md`

---

## 12. 实验与 Feature Flag

- Kill Switch
- 灰度发布
- A/B 测试

详见:
- `docs/v2/03-business/entitlement/feature-flag-engine.md`

---

## 13. 支付系统

- Stripe Checkout
- 订阅与积分购买
- 退款与补偿

详见:
- `docs/v2/03-business/entitlement/billing-lifecycle.md`

---

## 14. 文章管理系统

- Manual/News/Changelog
- Markdown 内容管理
- 发布/撤回流程

---

## 15. 主题管理系统

- 主题 AI 批量生成
- 审核流与投放策略

---

## 16. 相关文档

- `docs/v2/05-api/api-reference.md`

## 影响范围

- 相关模块: 后端业务与领域层
- 相关文档: `docs/v2/03-business/entitlement/system-design.md`

## 证据与验证

- 关键证据来源：`decodables/domains/`、`decodables/api/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 3.27.0 | 结构对齐与信息补齐 | Docs Working Group |
