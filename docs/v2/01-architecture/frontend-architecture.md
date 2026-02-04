# 前端架构总览（摘要版）

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-01-09  
**最后复核**: 2026-02-04  
**负责人**: Frontend Team  
**适用范围**: frontend  
**source_repo**: frontend  
**sync_required**: no

---

## 背景

- 问题或机会: 架构说明分散，缺少统一的分层与依赖边界说明
- 目标与非目标: 目标是明确分层职责与依赖方向；非目标是替代具体模块设计

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- 关键结论与约束: 前端分层与职责边界
- 必须遵循的规则: 业务逻辑下沉到 `@business`；页面只负责组合与路由

## 详细说明

- 架构分层: `@core` 框架层；`@shared` 共享层；`@business` 业务层；`app` 页面层
- 关键能力边界: 业务状态与用例在 `@business`，通用组件与工具在 `@shared`，框架与编辑器能力在 `@core`

## 影响范围

- 相关模块: 前端架构与模块依赖
- 相关文档: `docs/v2/00-governance/information-architecture.md`

## 证据与验证

- 关键证据来源：`decodables-fe/@core/`、`decodables-fe/@business/`、`decodables-fe/app/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐与信息补齐 | Docs Working Group |
