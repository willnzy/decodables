# 营销运营系统设计

> 活动、实验与内容报告的运营能力设计与边界说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/marketing/`, `decodables-fe/app/admin/marketing/_lib/types.ts`, `decodables-fe/app/admin/marketing/_lib/api.ts`, `decodables/api/admin/campaigns.py`, `decodables/api/admin/experiments.py`

---

## 背景

- 需要统一管理营销活动与实验
- 需要追踪活动效果与内容报告

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一活动、实验与内容报告的运营入口
- 支持投放/试验/复盘的闭环运营流程
- 为内容治理提供聚合入口

## 能力清单

- Campaigns 管理（创建/更新/启停/统计）
- A/B Experiments 管理（配置/结果/趋势/AI 分析）
- Content Reports 归集、统计与处理入口

## 关键流程

- 创建活动 → 上线/暂停 → 查看统计
- 创建实验 → 运行 → 结果评估/推荐
- 内容报告 → 查看详情 → 处理/归档

## 规则与护栏

- 状态/类型枚举校验
- 统一分页：`offset` + `limit`
- 管理员权限与接口限流

## 状态与类型

- Campaign type：`discount` / `trial` / `credit_bonus` / `free_tier`
- Campaign status：`draft` / `scheduled` / `active` / `ended` / `cancelled`
- Experiment type：`ab` / `multivariate`
- Experiment status：`draft` / `running` / `paused` / `completed` / `cancelled`

## 数据结构

- Campaign：`type` / `status` / `usage_limit` / `per_user_limit` / `target_tiers`
- CampaignStats：`claimed_count` / `conversion_rate` / `by_tier`
- Experiment：`experiment_key` / `variants` / `traffic_allocation` / `results`
- ExperimentResults：`winner` / `lift` / `p_value` / `is_significant`

## 前端交互要点

- 活动与实验分面板管理，支持状态筛选与详情查看
- 实验结果提供趋势/小时趋势/推荐信息
- 内容报告与审核侧共享入口

## 实现边界（现状）

- Campaign 创建字段与后端存在命名差异（`type/target_type/usage_limit` 等）
- 实验列表/结果返回结构与后端字段不完全一致

## 接口清单（Admin）

- `GET /api/v2/admin/campaigns`
- `GET /api/v2/admin/campaigns/{id}`
- `POST /api/v2/admin/campaigns`
- `PUT /api/v2/admin/campaigns/{id}`
- `DELETE /api/v2/admin/campaigns/{id}`
- `POST /api/v2/admin/campaigns/{id}/activate`
- `POST /api/v2/admin/campaigns/{id}/pause`
- `GET /api/v2/admin/campaigns/{id}/stats`

- `GET /api/v2/admin/experiments`
- `POST /api/v2/admin/experiments`
- `GET /api/v2/admin/experiments/{key}`
- `PUT /api/v2/admin/experiments/{key}`
- `DELETE /api/v2/admin/experiments/{key}`
- `PUT /api/v2/admin/experiments/{key}/status`
- `GET /api/v2/admin/experiments/{key}/results`
- `POST /api/v2/admin/experiments/{key}/aggregate`
- `POST /api/v2/admin/experiments/aggregate-all`
- `POST /api/v2/admin/experiments/cache/clear`
- `POST /api/v2/admin/experiments/{key}/ai-analysis`
- `GET /api/v2/admin/experiments/{key}/quick-recommendation`
- `GET /api/v2/admin/experiments/{key}/trend`
- `GET /api/v2/admin/experiments/{key}/hourly-trend`

- `GET /api/v2/admin/moderation/reports`
- `GET /api/v2/admin/moderation/reports/stats`
- `GET /api/v2/admin/moderation/reports/{id}`
- `POST /api/v2/admin/moderation/reports/{id}/respond`

## 影响范围

- 相关模块：营销运营
- 相关文档：`docs/v2/10-product/admin/marketing-ops/marketing.md`

## 证据与验证

- 关键证据来源：`decodables-fe/app/admin/marketing/`、`decodables/api/admin/campaigns.py`、`decodables/api/admin/experiments.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充营销运营系统设计细节 | Docs Working Group |
