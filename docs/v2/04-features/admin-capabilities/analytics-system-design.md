 # Analytics 系统设计
 
 > 后台数据分析能力的系统设计与边界说明。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/analytics/`, `decodables-fe/app/admin/analytics/_lib/api.ts`, `decodables/api/admin/stats.py`, `decodables/api/admin/metrics.py`, `decodables/api/admin/events.py`, `decodables/api/admin/ai.py`
 
 ---
 
## 背景

- 需要统一后台分析能力的范围与边界
- 明确指标口径与审计要求

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一 Stats / Metrics / Events / AI 的分析入口
- 明确统计口径、时间维度与聚合策略
- 支持趋势、洞察与运营决策

## 能力清单

- Stats：Dashboard KPI、增长/收入/积分/转化漏斗
- Metrics：DAU、留存、错误、漏斗、日/月统计
- Events：事件列表、聚合统计、聚合任务触发
- AI：洞察、建议、行为分析、报告生成

## 关键流程

- 指标查询 → 过滤/聚合 → 展示
- 事件聚合 → 统计产出 → 结果回显
- AI 洞察 → 建议/报告 → 运营决策

## 规则与护栏

- 统一分页：`offset` + `limit`
- 日期格式与 period/group_by 校验
- 管理员权限与接口限流

## 接口清单（Admin）

- `GET /api/v2/admin/stats/dashboard`
- `GET /api/v2/admin/stats/user-growth`
- `GET /api/v2/admin/stats/revenue`
- `GET /api/v2/admin/stats/projects`
- `GET /api/v2/admin/stats/credits`
- `GET /api/v2/admin/stats/tier-distribution`
- `GET /api/v2/admin/stats/conversion-funnel`
- `GET /api/v2/admin/stats/exports`
- `GET /api/v2/admin/stats/assets`
- `GET /api/v2/admin/stats/tier-activity`
- `GET /api/v2/admin/stats/subscription-events`
- `GET /api/v2/admin/stats/page-views`
- `GET /api/v2/admin/stats/project-details`
- `GET /api/v2/admin/stats/returning-users`
- `GET /api/v2/admin/stats/tier-trend`
- `GET /api/v2/admin/stats/tier-conversion`
- `GET /api/v2/admin/stats/performance`
- `GET /api/v2/admin/stats/user-distribution`

- `GET /api/v2/admin/metrics/daily`
- `GET /api/v2/admin/metrics/monthly`
- `GET /api/v2/admin/metrics/retention`
- `GET /api/v2/admin/metrics/funnel`
- `GET /api/v2/admin/metrics/errors`
- `GET /api/v2/admin/metrics/dau-trend`
- `POST /api/v2/admin/metrics/refresh`

- `GET /api/v2/admin/events/events`
- `GET /api/v2/admin/events/events/stats`
- `GET /api/v2/admin/events/aggregated/{stat_type}`
- `GET /api/v2/admin/events/aggregated/{stat_type}/range`
- `POST /api/v2/admin/events/aggregation/run`

- `GET /api/v2/admin/ai/insights`
- `GET /api/v2/admin/ai/recommendations`
- `GET /api/v2/admin/ai/behavior-analysis`
- `POST /api/v2/admin/ai/generate-report`
- `GET /api/v2/admin/ai/quick-insights`

## 影响范围

- 相关模块：Analytics 系统
- 相关文档：`docs/v2/05-api/admin-endpoints.md`、`docs/v2/05-api/api-reference.md`

## 证据与验证

- 关键证据来源：`decodables/api/admin/metrics.py`、`decodables/domains/analytics/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
