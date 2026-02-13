# 06 - Marketing (Campaigns) + Experiments 审计

> 审计时间: 2026-02-12 | 审计维度: 后端API ↔ 前端页面 ↔ 文档覆盖

---

## A. Campaigns (campaigns.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /campaigns | 列出所有活动 | ✅ useCampaigns | ❌ | ❌ |
| 2 | GET | /campaigns/{id} | 获取活动详情 | ✅ useCampaignById | ❌ | ❌ |
| 3 | POST | /campaigns | 创建活动 | ✅ useCreateCampaign | ❌ | ❌ |
| 4 | PUT | /campaigns/{id} | 更新活动 | ✅ useUpdateCampaign | ❌ | ❌ |
| 5 | DELETE | /campaigns/{id} | 删除活动 (软删除) | ✅ useDeleteCampaign | ❌ | ❌ |
| 6 | POST | /campaigns/{id}/activate | 激活活动 | ✅ useActivateCampaign | ❌ | ❌ |
| 7 | POST | /campaigns/{id}/pause | 暂停活动 | ✅ usePauseCampaign | ❌ | ❌ |
| 8 | GET | /campaigns/{id}/stats | 获取活动统计 | ✅ useCampaignStats | ❌ | ❌ |

### 关键发现

- 🟢 **API→Frontend 100% 对齐**: 8/8 端点全部在前端实现
- 🔴 **文档完全缺失**: 无 v2/v3 专项文档
- 🟢 **DDD 架构合规**: API → Domain Service → Repository，已完成 v3.31 Container DI 迁移
- 🟢 **安全加固**: rate limiting (30/min列表, 20/min写入, 10/min删除) + 请求模型校验 + Audit logging

---

## B. Experiments (experiments.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /experiments | 列出所有实验 | ✅ useExperiments | ❌ | ❌ |
| 2 | POST | /experiments | 创建实验 | ✅ useCreateExperiment | ❌ | ❌ |
| 3 | GET | /experiments/{key} | 获取实验详情 | ✅ useExperimentByKey | ❌ | ❌ |
| 4 | PUT | /experiments/{key} | 更新实验 | ✅ useUpdateExperiment | ❌ | ❌ |
| 5 | PUT | /experiments/{key}/status | 更新状态 | ✅ useUpdateExperimentStatus | ❌ | ❌ |
| 6 | DELETE | /experiments/{key} | 删除实验 | ✅ useDeleteExperiment | ❌ | ❌ |
| 7 | GET | /experiments/{key}/results | 获取结果 | ✅ useExperimentResults | ❌ | ❌ |
| 8 | POST | /experiments/{key}/aggregate | 触发数据聚合 | ✅ useTriggerAggregate | ❌ | ❌ |
| 9 | POST | /experiments/aggregate-all | 全部实验聚合 | ✅ useTriggerAllAggregate | ❌ | ❌ |
| 10 | POST | /experiments/cache/clear | 清除缓存 | ✅ useClearExperimentCache | ❌ | ❌ |
| 11 | POST | /experiments/{key}/ai-analysis | AI 分析 | ✅ useExperimentAIAnalysis | ❌ | ❌ |
| 12 | GET | /experiments/{key}/quick-recommendation | 快速建议 | ✅ useExperimentRecommendation | ❌ | ❌ |
| 13 | GET | /experiments/{key}/trend | 日趋势数据 | ✅ useExperimentTrend | ❌ | ❌ |
| 14 | GET | /experiments/{key}/hourly-trend | 时趋势数据 | ✅ useExperimentHourlyTrend | ❌ | ❌ |

### 关键发现

- 🟢 **API→Frontend 100% 对齐**: 14/14 端点全部在前端实现
- 🔴 **文档完全缺失**: 无 v2/v3 专项文档
- 🟢 **DDD 架构合规**: 已完成 v3.32 Container DI 迁移，100% 使用 ExperimentService
- 🟢 **安全加固**: rate limiting (30/min查询, 20/min写入, 10/min聚合, 5/min全聚合) + 状态/类型枚举验证 + 权重校验(=100) + Audit logging
- 🟡 **Response Model Mismatch风险**: list_experiments 返回 tuple → Pydantic model 转换需确认

---

## C. 总评

| 指标 | 数值 | 评级 |
|------|------|------|
| 总端点数 | 22 (Campaigns 8 + Experiments 14) | - |
| API→Frontend 对齐率 | **100% (22/22)** | 🟢 |
| 文档覆盖率 | **0% (0/22)** | 🔴 |
| DDD 架构合规 | 100% | 🟢 |
| 安全加固 | 95% | 🟢 |

### 严重问题

| 优先级 | 问题 | 建议 |
|--------|------|------|
| 🔴 P0 | 文档完全缺失 (22端点) | 创建 v3 文档: marketing-campaigns.md + marketing-experiments.md |
| 🟡 P1 | Response Model Mismatch | 验证 list_experiments tuple→Pydantic 转换逻辑 |

---

## v2.0 审计复核 (2026-02-13)

**复核结论**: ✅ 无新增发现。v1.0 问题清单仍然有效。

campaigns + experiments 是 Admin 中合规度较高的模块 (100% API-Frontend 对齐, 100% DDD 合规)。
主要差距仍在文档覆盖率 (0%)，建议 Phase 4 补充。
