# 审核与举报系统设计

> 市场内容审核与举报处理能力的系统设计与边界说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/moderation/`, `decodables-fe/app/admin/moderation/_lib/types.ts`, `decodables-fe/app/admin/moderation/_lib/api.ts`, `decodables/api/admin/moderation.py`, `decodables/domains/moderation/constants.py`

---

## 背景

- 需要集中处理 Marketplace 内容审核
- 需要统一举报处理与反馈机制

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一 Marketplace 内容审核与举报处理入口
- 明确审核/举报的状态与流转规则
- 降低违规内容暴露与误处理风险

## 能力清单

- Marketplace 审核列表与详情
- 审核动作：通过/驳回/下架/删除
- 举报列表/统计/详情
- 举报响应与状态更新

## 关键流程

- 审核列表 → 详情 → 通过/驳回/下架/删除
- 举报列表 → 统计 → 详情 → 响应（resolve/dismiss）

## 规则与护栏

- 状态/类型枚举校验（后端常量）
- 审核/举报全链路管理员权限
- 统一分页：`offset` + `limit`
- 接口限流（30/min）

## 状态与类型

- 审核状态：`pending` / `approved` / `rejected`
- 资源类型：`sticker` / `clipart` / `template` / `font` / `all`
- 举报状态：`pending` / `reviewed` / `resolved` / `dismissed`

## 数据结构

- ModerationItem：`resource_type` / `resource_id` / `status` / `submitted_at`
- ContentReport：`reason` / `description` / `status` / `resolution_note`
- ReportStats：`total` / `pending` / `resolved` / `dismissed`

## 前端交互要点

- 审核列表与举报列表分 Tabs
- 详情页内动作触发并回写状态
- 搜索/筛选与分页保持 URL 同步

## 实现边界（现状）

- 后端分页为 `offset/limit`，前端多处仍使用 `page/page_size`
- 后端举报响应字段为 `response`，前端使用 `resolution_note`

## 接口清单（Admin）

- `GET /api/v2/admin/moderation/marketplace/moderation/list`
- `GET /api/v2/admin/moderation/marketplace/moderation/{listing_id}`
- `POST /api/v2/admin/moderation/marketplace/moderation/{listing_id}/approve`
- `POST /api/v2/admin/moderation/marketplace/moderation/{listing_id}/reject`
- `POST /api/v2/admin/moderation/marketplace/moderation/{listing_id}/delete`
- `POST /api/v2/admin/moderation/marketplace/moderation/{listing_id}/unpublish`

- `GET /api/v2/admin/moderation/reports`
- `GET /api/v2/admin/moderation/reports/stats`
- `GET /api/v2/admin/moderation/reports/{report_id}`
- `POST /api/v2/admin/moderation/reports/{report_id}/respond`

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
| 2026-02-04 | 0.2.0 | 补充审核与举报设计细节 | Docs Working Group |
