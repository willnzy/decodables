# 审核与举报系统设计

> 市场内容审核与举报处理能力的系统设计与边界说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/moderation/`, `decodables/api/admin/moderation.py`

---

## 背景

- 需要集中处理 Marketplace 内容审核
- 需要统一举报处理与反馈机制

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 提供内容审核与举报处理的统一入口
- 支持审核决策与状态追踪
- 降低违规内容暴露风险

## 能力清单

- 内容审核（上架/下架/驳回）
- 举报列表与详情
- 举报响应与状态更新

## 关键流程

- 审核列表 → 详情 → 审核决策
- 举报列表 → 详情 → 处理反馈

## 影响范围

- 相关模块：审核与举报
- 相关文档：`docs/v2/10-product/admin/admin-dashboard/moderation.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/admin/moderation/`、`decodables/api/admin/moderation.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
