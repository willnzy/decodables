 # Onboarding 系统设计
 
 > 新手引导流程与体验策略说明。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
**来源/依据**: `decodables/domains/onboarding/`, `decodables/api/user/onboarding.py`
 
 ---
 
## 背景

- 需要将新手引导的步骤、进度与清单规则统一到服务侧
- 需要让前端按统一数据结构渲染步骤与完成状态

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 目标

- 统一引导步骤与任务清单口径
- 明确步骤状态与进度计算方式
- 支持不同 tier 的引导差异

## 能力清单

- 获取可用引导步骤列表（含进度与状态）
- 步骤开始/完成/跳过
- 获取任务清单进度与完成比例

## 关键流程

- 获取步骤列表 → 展示引导 → 提交开始/完成/跳过
- 获取清单进度 → 计算必做步骤完成率

## 规则与状态

- 步骤可见性：按 `target_tiers` 与 `is_active` 过滤
- 状态值：`pending` / `completed` / `skipped`
- 列表返回：若无进度记录则视为 `not_started`
- 清单统计：仅统计 `is_required=true` 的步骤

## 数据结构

- `OnboardingStepEntity`
  - `step_key` / `step_name` / `step_order` / `is_required`
  - `target_tiers[]` / `config` / `is_active`
- `OnboardingProgressEntity`
  - `user_id` / `step_id` / `status`
  - `completed_at` / `skipped_at`

## 接口清单

- `GET /api/v2/user/onboarding/steps`
- `POST /api/v2/user/onboarding/steps/start`
- `POST /api/v2/user/onboarding/steps/complete`
- `POST /api/v2/user/onboarding/steps/skip`
- `GET /api/v2/user/onboarding/checklist`

## 影响范围

- 相关模块：Onboarding
- 相关文档：`docs/v2/10-product/user/dashboard/dashboard.md`

## 证据与验证

- 关键证据来源：`decodables/domains/onboarding/`、`decodables/api/user/onboarding.py`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 0.1.0 | 初始创建 | Docs Working Group |
