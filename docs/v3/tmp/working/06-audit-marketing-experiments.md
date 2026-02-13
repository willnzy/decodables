# 06 - 营销活动 + 实验 审计报告

> 审计时间: 2026-02-12 ~ 2026-02-13 | 后端: campaigns.py, experiments.py | 前端: /admin/marketing

---

## A. Campaigns (campaigns.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | 文档 |
|---|--------|------|------|----------|------|
| 1 | GET | /campaigns | 列出所有活动 | ✅ useCampaigns | ❌ |
| 2 | GET | /campaigns/{id} | 获取活动详情 | ✅ useCampaignById | ❌ |
| 3 | POST | /campaigns | 创建活动 | ✅ useCreateCampaign | ❌ |
| 4 | PUT | /campaigns/{id} | 更新活动 | ✅ useUpdateCampaign | ❌ |
| 5 | DELETE | /campaigns/{id} | 删除活动 (软删除) | ✅ useDeleteCampaign | ❌ |
| 6 | POST | /campaigns/{id}/activate | 激活活动 | ✅ useActivateCampaign | ❌ |
| 7 | POST | /campaigns/{id}/pause | 暂停活动 | ✅ usePauseCampaign | ❌ |
| 8 | GET | /campaigns/{id}/stats | 获取活动统计 | ✅ useCampaignStats | ❌ |

**前端覆盖**: 8/8 (100%) ✅ | **DDD 合规**: ✅ v3.31 Container DI | **安全**: ✅ 差异化限流

---

## B. Experiments (experiments.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | 文档 |
|---|--------|------|------|----------|------|
| 1 | GET | /experiments | 列出所有实验 | ✅ useExperiments | ❌ |
| 2 | POST | /experiments | 创建实验 | ✅ useCreateExperiment | ❌ |
| 3 | GET | /experiments/{key} | 获取实验详情 | ✅ useExperimentByKey | ❌ |
| 4 | PUT | /experiments/{key} | 更新实验 | ✅ useUpdateExperiment | ❌ |
| 5 | PUT | /experiments/{key}/status | 更新状态 | ✅ useUpdateExperimentStatus | ❌ |
| 6 | DELETE | /experiments/{key} | 删除实验 | ✅ useDeleteExperiment | ❌ |
| 7 | GET | /experiments/{key}/results | 获取结果 | ✅ useExperimentResults | ❌ |
| 8 | POST | /experiments/{key}/aggregate | 触发数据聚合 | ✅ useTriggerAggregate | ❌ |
| 9 | POST | /experiments/aggregate-all | 全部实验聚合 | ✅ useTriggerAllAggregate | ❌ |
| 10 | POST | /experiments/cache/clear | 清除缓存 | ✅ useClearExperimentCache | ❌ |
| 11 | POST | /experiments/{key}/ai-analysis | AI 分析 | ✅ useExperimentAIAnalysis | ❌ |
| 12 | GET | /experiments/{key}/quick-recommendation | 快速建议 | ✅ useExperimentRecommendation | ❌ |
| 13 | GET | /experiments/{key}/trend | 日趋势数据 | ✅ useExperimentTrend | ❌ |
| 14 | GET | /experiments/{key}/hourly-trend | 时趋势数据 | ✅ useExperimentHourlyTrend | ❌ |

**前端覆盖**: 14/14 (100%) ✅ | **DDD 合规**: ✅ v3.32 Container DI | **安全**: ✅ 差异化限流 + 权重校验(=100)

---

## C. 问题清单

| 编号 | 优先级 | 问题 | 审计维度 |
|------|--------|------|---------|
| - | 🔴 P0 | **文档完全缺失** — 22 个端点零文档覆盖 | D2 |
| - | 🟡 P1 | **Response Model Mismatch 风险** — list_experiments 返回 tuple → Pydantic model 转换需确认 | D8 |

## D. 总评

| 指标 | Campaigns | Experiments | 合计 |
|------|:---:|:---:|:---:|
| 端点数 | 8 | 14 | **22** |
| 前端覆盖 | 100% | 100% | **100%** |
| 文档覆盖 | 0% | 0% | **0%** |
| DDD 合规 | ✅ | ✅ | **100%** |

**总体评分**: 🟢 高 — Admin 中合规度较高的模块 (100% API-Frontend 对齐, 100% DDD 合规)。主要差距在文档覆盖率 (0%)。

## E. 跨层审计 (D17-D25) 复核

✅ 无额外发现。
