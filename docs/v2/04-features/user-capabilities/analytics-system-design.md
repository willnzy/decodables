# 用户分析系统设计

> 用户侧分析与事件采集能力说明。

**状态**: draft  
**版本**: 0.2.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: shared  
**source_repo**: both  
**sync_required**: yes  
**来源/依据**: `decodables/domains/events/`, `decodables/api/user/analytics.py`

---

## 背景

- 需要统一用户事件采集与分析口径
- 需要明确可见指标与使用边界

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 规范事件采集与指标计算
- 支持用户侧行为分析
- 约束数据隐私与留存

## 能力清单

- 用户事件采集
- 指标聚合与展示
- 行为趋势与统计

## 关键流程

- 事件触发 → 采集 → 聚合 → 展示

## 规则与护栏

- 事件命名与字段需统一口径
- 指标查询需权限与脱敏
- 采集上报需限频与采样

## 状态与类型

- 事件类型：`view` / `click` / `conversion`
- 指标周期：`daily` / `weekly` / `monthly`

## 数据结构

- Event：`id` / `user_id` / `name` / `payload` / `created_at`
- MetricSeries：`metric` / `points` / `period`

## 前端交互要点

- 指标卡片与趋势图一致性
- 空态/无数据提示
- 过滤器与时间范围联动

## 实现边界（现状）

- 事件与指标口径以 analytics 域定义为准

## 影响范围

- 相关模块：用户分析
- 相关文档：`docs/v2/10-product/user/dashboard/dashboard.md`

## 证据与验证

- 关键证据来源：`decodables/domains/events/`、`decodables/api/user/analytics.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
| 2026-02-04 | 0.2.0 | 补充用户分析系统设计细节 | Docs Working Group |
