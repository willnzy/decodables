# 架构方案提案

> 核心架构方向、边界与演进路径的统一提案。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: backend  
**source_repo**: backend  
**sync_required**: no  
**来源/依据**: `decodables/docs/main/architecture-proposal.md`

---

## 背景

- 问题或机会: 架构演进需要统一方向与边界说明
- 目标与非目标: 目标是明确分层与演进路径；非目标是替代具体模块设计

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 关键结论与约束: 采用分层架构并保持依赖单向
- 必须遵循的规则: API → Application → Domain ← Infrastructure

## 详细说明

- 架构分层与依赖方向: 领域层为核心，应用层编排用例
- 关键能力边界: 认证/计费/积分等核心能力归领域层
- 演进路线与里程碑: 架构重构 → 测试补齐 → 性能优化 → 安全审计

## 影响范围

- 相关模块: 架构分层与核心领域
- 相关文档: `docs/v2/01-architecture/backend-architecture.md`、`docs/v2/00-governance/codebase-health-matrix.md`

## 证据与验证

- 关键证据来源：`decodables/domains/`、`decodables/api/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
