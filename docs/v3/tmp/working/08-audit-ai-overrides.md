# 08 - AI Insights + AI Models + Feature Overrides 审计

> 审计时间: 2026-02-12 | 审计维度: 后端API ↔ 前端页面 ↔ 文档覆盖

---

## A. AI Insights (ai.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /ai/insights | AI 洞察 (growth/engagement/revenue) | ✅ | ✅ | ✅ |
| 2 | GET | /ai/recommendations | AI 推荐 (growth/retention/monetization) | ✅ | ✅ | ✅ |
| 3 | GET | /ai/behavior-analysis | 用户行为分析 (限50K记录) | ✅ | ✅ | ✅ |
| 4 | POST | /ai/generate-report | AI 商业报告 (5类型×4时间维度) | ✅ | ✅ | ✅ |
| 5 | GET | /ai/quick-insights | 快速洞察 (规则型, 无AI调用) | ✅ | ✅ | ✅ |

### 关键发现

- 🟢 **三维度 100% 对齐**: 5/5 端点 API→Frontend→文档 全部完整
- 🟢 **DDD 合规**: v3.27 完成迁移，API → Service (domains.stats.ai_insights)
- 🟢 **安全**: 差异化限流 (insights 30/min, report 5/min, quick 60/min)
- 🟡 **潜在问题**: generate_report 实现在 application.services.ai_reports，需验证服务层完整性

---

## B. AI Models (ai_models.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /ai/models/config | 获取所有AI模型配置 | ✅ | ✅ | ❌ |
| 2 | PUT | /ai/models/config/text | 更新文本生成模型 | ✅ | ❌ | ❌ |
| 3 | PUT | /ai/models/config/image | 更新图像生成模型 | ✅ | ❌ | ❌ |
| 4 | PUT | /ai/models/config/admin | 更新管理员模型 (占位符) | ⚠️ 未实现 | ❌ | ❌ |
| 5 | PUT | /ai/models/config/canary | 更新金丝雀发布配置 | ✅ | ❌ | ❌ |
| 6 | PUT | /ai/models/providers/toggle | 启用/禁用AI提供商 | ✅ | ❌ | ❌ |
| 7 | GET | /ai/models/usage | AI使用统计 (1-365天) | ✅ | ❌ | ❌ |
| 8 | POST | /ai/models/cache/clear | 清空AI缓存 | ✅ | ❌ | ❌ |

### 关键发现

- 🟡 **前端覆盖率 88% (7/8)**: update_admin_config 端点为 TODO 占位符
- 🔴 **文档严重不足**: v2仅记录1个, v3零记录, 7个端点无文档
- 🟢 **DDD 合规**: v3.30 完成迁移
- 🟢 **参数验证完整**: Temperature 0-2, MaxTokens 1-32K, Canary 0-100%
- 🔴 **占位符端点**: update_admin_config 未实现但路由已注册

---

## C. Feature Overrides (overrides.py)

### API 端点清单

| # | Method | Path | 功能 | 前端调用 | v2文档 | v3文档 |
|---|--------|------|------|----------|--------|--------|
| 1 | GET | /feature-overrides/{user_id} | 获取用户功能覆盖 | ❌ | ✅ | ❌ |
| 2 | POST | /feature-overrides/{user_id} | 设置功能覆盖 | ❌ | ✅ | ❌ |
| 3 | DELETE | /feature-overrides/{user_id}/{flag_key} | 删除功能覆盖 | ❌ | ✅ | ❌ |

### 关键发现

- 🔴 **前端覆盖率 0%**: 3个端点完全无前端调用
- 🔴 **DDD 违规**: 直接调用 Supabase client，未通过 Service/Repository
- 🔴 **缺少安全措施**: 无参数验证、无速率限制
- 🟡 **POST/DELETE 实现不完整**: GET 已实现，写入操作需验证
- 🟡 **PII 风险**: events 端点可能返回未脱敏用户数据

---

## D. 总评

| 指标 | AI Insights | AI Models | Overrides | **合计** |
|------|:---:|:---:|:---:|:---:|
| 端点数 | 5 | 8 | 3 | **16** |
| 前端调用 | 5 | 7 | 0 | **12 (75%)** |
| 文档(v2) | 5 | 1 | 3 | **9 (56%)** |
| 文档(v3) | 5 | 0 | 0 | **5 (31%)** |

### 严重问题

| 优先级 | 问题 | 模块 |
|--------|------|------|
| 🔴 P0 | Feature Overrides 完全无前端集成 | overrides.py |
| 🔴 P0 | Feature Overrides 违反 DDD 架构标准 | overrides.py |
| 🔴 P0 | AI Models update_admin_config 占位符 | ai_models.py |
| 🟡 P1 | AI Models 7/8 端点无文档 | ai_models.py |
| 🟡 P1 | Feature Overrides 缺少速率限制和参数验证 | overrides.py |
