# 营销运营系统设计

> 活动、实验与内容报告的运营能力设计与边界说明。

**状态**: draft  
**版本**: 0.1.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/admin/marketing/`, `decodables/api/admin/campaigns.py`, `decodables/api/admin/experiments.py`

---

## 背景

- 需要统一管理营销活动与实验
- 需要追踪活动效果与内容报告

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 提供活动管理与投放控制能力
- 提供实验配置与结果分析能力
- 汇总内容报告与处理入口

## 能力清单

- Campaigns 管理（创建/更新/启停/统计）
- A/B Experiments 管理（配置/结果/趋势）
- Content Reports 归集与处理入口

## 关键流程

- 创建活动 → 上线/暂停 → 查看统计
- 创建实验 → 运行 → 结果评估

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
