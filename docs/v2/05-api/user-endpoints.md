# User API 端点清单

**状态**: needs-review  
**版本**: 1.0.0  
**版本日期**: 2026-01-18  
**最后复核**: 2026-02-04  
**负责人**: Backend Team  
**适用范围**: shared  
**source_repo**: backend  
**sync_required**: yes

---

## 背景

- 问题或机会: 待补充
- 目标与非目标: 待补充

## 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须与覆盖矩阵保持一致

## 结论/规范/方案

- User 端点清单用于分模块验证与回归
- 测试执行与认证规则需统一规范

## 影响范围

- 相关模块: User API 与测试
- 相关文档: `docs/v2/05-api/api-reference.md`

## 证据与验证

- 关键证据来源：`decodables/api/user/`、`decodables/tests/`
- 覆盖矩阵对应条目：`09-reference/feature-coverage-matrix.md`

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-04 | 1.0.0 | 结构对齐与信息补齐 | Docs Working Group |

> 说明：本清单来源于集成测试清单，用于分模块验证。

## 快速测试命令

```bash
python -m pytest tests/integration/staging/{module}/ -v --tb=short
```

## 测试状态图例

| 状态 | 说明 |
|------|------|
| ✅ | 测试通过 |
| ⏭️ | 跳过 (Free tier 限制等预期行为) |
| ❌ | 测试失败，需要修复 |
| 🔧 | 已修复代码，等待部署验证 |
| ⏳ | 待测试 |

---

## 模块清单

### 1. Profile (用户资料)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/profile/me` | GET | ✅ | ⏳ |
| `/api/v2/user/profile/history` | GET | ✅ | ⏳ |
| `/api/v2/user/profile/purchases` | GET | ✅ | ⏳ |
| `/api/v2/user/profile/notifications` | GET | ✅ | ⏳ |
| `/api/v2/user/profile/notifications/{id}/read` | POST | ✅ | ⏳ |
| `/api/v2/user/profile/notifications/read-all` | POST | ✅ | ⏳ |
| `/api/v2/user/profile/timezone` | PUT | ✅ | ⏳ |

### 2. Billing (积分账单)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/billing/credits` | GET | ✅ | ⏳ |
| `/api/v2/user/billing/transactions` | GET | ✅ | ⏳ |
| `/api/v2/user/billing/can-afford` | GET | ✅ | ⏳ |
| `/api/v2/user/billing/credits/add` | POST | Admin | ⏳ |

### 3. Projects (项目管理)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/projects` | GET | ✅ | ✅ |
| `/api/v2/user/projects` | POST | ✅ | ⏭️ Free tier |
| `/api/v2/user/projects/dashboard` | GET | ✅ | ✅ |
| `/api/v2/user/projects/deleted` | GET | ✅ | ✅ |
| `/api/v2/user/projects/{id}` | GET | ✅ | ✅ |
| `/api/v2/user/projects/{id}` | PUT | ✅ | ⏳ |
| `/api/v2/user/projects/{id}` | DELETE | ✅ | ⏭️ Free tier |
| `/api/v2/user/projects/{id}/restore` | POST | ✅ | ⏭️ Free tier |
| `/api/v2/user/projects/{id}/duplicate` | POST | ✅ | ⏭️ Free tier |

### 4. Support (客服支持)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/support/ticket` | POST | ✅ | 🔧 |
| `/api/v2/user/support/chat` | POST | ✅ | ⏳ |
| `/api/v2/user/support/contact` | POST | ✅ | ⏳ |
| `/api/v2/user/support/feedback` | POST | ✅ | ⏳ |

### 5. Marketplace (市场)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/marketplace/listings` | GET | ❌ | ⏳ |
| `/api/v2/user/marketplace/listings/{id}` | GET | ❌ | ⏳ |
| `/api/v2/user/marketplace/listings` | POST | ✅ | ⏳ |
| `/api/v2/user/marketplace/listings/{id}` | PUT | ✅ | ⏳ |
| `/api/v2/user/marketplace/listings/{id}` | DELETE | ✅ | ⏳ |
| `/api/v2/user/marketplace/purchase` | POST | ✅ | ⏳ |
| `/api/v2/user/marketplace/my-listings` | GET | ✅ | ⏳ |
| `/api/v2/user/marketplace/leaderboard` | GET | ❌ | ⏳ |
| `/api/v2/user/marketplace/report` | POST | ✅ | ⏳ |
| `/api/v2/user/marketplace/my-reports` | GET | ✅ | ⏳ |

### 6. Resources (系统资源)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/resources` | GET | ❌ | ⏳ |
| `/api/v2/user/resources/types` | GET | ❌ | ⏳ |
| `/api/v2/user/resources/categories/{type}` | GET | ❌ | ⏳ |
| `/api/v2/user/resources/{id}` | GET | ❌ | ⏳ |

### 7. Assets (用户素材)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/assets` | GET | ✅ | ⏳ |
| `/api/v2/user/assets` | POST | ✅ | ⏳ |
| `/api/v2/user/assets/{id}` | DELETE | ✅ | ⏳ |
| `/api/v2/user/assets/from-url` | POST | ✅ | ⏳ |
| `/api/v2/user/assets/check-url` | GET | ✅ | ⏳ |
| `/api/v2/user/assets/{id}/increment-usage` | POST | ✅ | ⏳ |
| `/api/v2/user/assets/dashboard` | GET | ✅ | ⏳ |
| `/api/v2/user/assets/deleted` | GET | ✅ | ⏳ |
| `/api/v2/user/assets/{id}/restore` | POST | ✅ | ⏳ |

### 8. Templates (模板)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/templates/asset` | GET | ❌ | ⏳ |
| `/api/v2/user/templates/asset` | POST | ✅ | ⏳ |
| `/api/v2/user/templates/asset/{id}` | PUT | ✅ | ⏳ |
| `/api/v2/user/templates/asset/{id}` | DELETE | ✅ | ⏳ |
| `/api/v2/user/templates/asset/{id}/use` | POST | ✅ | ⏳ |
| `/api/v2/user/templates/page` | GET | ❌ | ⏳ |
| `/api/v2/user/templates/page` | POST | ✅ | ⏳ |
| `/api/v2/user/templates/page/{id}` | PUT | ✅ | ⏳ |
| `/api/v2/user/templates/page/{id}` | DELETE | ✅ | ⏳ |
| `/api/v2/user/templates/page/{id}/use` | POST | ✅ | ⏳ |

### 9. Themes (主题)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/themes/current` | GET | ❌ | ⏳ |

### 10. Tools (工具)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/tools/pdf-preview` | POST | ✅ | ⏳ |
| `/api/v2/user/tools/ocr` | POST | ✅ | ⏳ |

### 11. Tasks (异步任务)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/tasks/{id}` | GET | ✅ | ⏳ |
| `/api/v2/user/tasks/{id}/cancel` | POST | ✅ | ⏳ |

### 12. Payment (支付)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/payment/checkout` | POST | ✅ | ⏳ |
| `/api/v2/user/payment/portal` | POST | ✅ | ⏳ |

### 13. Generation (AI 生成)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/generate/images/images` | POST | ✅ | ⏳ |
| `/api/v2/user/generate/images/images/async` | POST | ✅ | ⏳ |
| `/api/v2/user/generate/pdf/pdf` | POST | ✅ | ⏳ |
| `/api/v2/user/generate/story/story` | POST | ✅ | ⏳ |
| `/api/v2/user/generate/story/inspiration` | POST | ✅ | ⏳ |

### 14. Generations (生成历史)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/generations/history` | GET | ✅ | ⏳ |
| `/api/v2/user/generations/{id}` | PATCH | ✅ | ⏳ |
| `/api/v2/user/generations/{id}` | DELETE | ✅ | ⏳ |
| `/api/v2/user/generations/batch-delete` | POST | ✅ | ⏳ |

### 15. Config (配置)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/config` | GET | ❌ | ⏳ |
| `/api/v2/user/config/group/{name}` | GET | ❌ | ⏳ |
| `/api/v2/user/config/{key}` | GET | ❌ | ⏳ |

### 16. Export (导出)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/export/projects/{id}/pdf` | GET | ✅ | ⏳ |
| `/api/v2/user/export/projects/{id}/preview` | GET | ✅ | ⏳ |
| `/api/v2/user/export/projects/{id}/zip` | GET | ✅ | ⏳ |
| `/api/v2/user/export/projects/{id}/pdf/async` | POST | ✅ | ⏳ |
| `/api/v2/user/export/projects/{id}/zip/async` | POST | ✅ | ⏳ |

### 17. Onboarding (新手引导)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/onboarding/steps` | GET | ✅ | ⏳ |
| `/api/v2/user/onboarding/steps/start` | POST | ✅ | ⏳ |
| `/api/v2/user/onboarding/steps/complete` | POST | ✅ | ⏳ |
| `/api/v2/user/onboarding/steps/skip` | POST | ✅ | ⏳ |
| `/api/v2/user/onboarding/checklist` | GET | ✅ | ⏳ |

### 18. Referrals (推荐)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/referrals` | POST | ✅ | ⏳ |
| `/api/v2/user/referrals` | GET | ✅ | ⏳ |
| `/api/v2/user/referrals/stats` | GET | ✅ | ⏳ |
| `/api/v2/user/referrals/code/{code}` | GET | ❌ | ⏳ |
| `/api/v2/user/referrals/{id}/complete` | POST | ✅ | ⏳ |

### 19. Seller (卖家)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/seller/stats` | GET | ✅ | ⏳ |

### 20. Experiments (A/B 实验)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/experiments/{key}/assign` | POST | ❌ | ⏳ |
| `/api/v2/user/experiments/{key}/exposure` | POST | ❌ | ⏳ |
| `/api/v2/user/experiments/{key}/conversion` | POST | ❌ | ⏳ |
| `/api/v2/user/experiments/user/{identifier}` | GET | ❌ | ⏳ |

### 21. Analytics (数据分析)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/analytics/events` | POST | ❌ | ⏳ |

### 22. Campaigns (活动)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/campaigns/active` | GET | ❌ | ⏳ |
| `/api/v2/user/campaigns/{id}/claim` | POST | ✅ | ⏳ |
| `/api/v2/user/campaigns/{id}/dismiss` | POST | ✅ | ⏳ |

### 23. Articles (文章)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/articles` | GET | ❌ | ⏳ |
| `/api/v2/user/articles/categories` | GET | ❌ | ⏳ |
| `/api/v2/user/articles/search` | GET | ❌ | ⏳ |
| `/api/v2/user/articles/featured` | GET | ❌ | ⏳ |
| `/api/v2/user/articles/{slug}` | GET | ❌ | ⏳ |
| `/api/v2/user/articles/{slug}/related` | GET | ❌ | ⏳ |

### 24. Static Pages (静态页面)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/static-pages` | GET | ❌ | ⏳ |
| `/api/v2/user/static-pages/{slug}` | GET | ❌ | ⏳ |

### 25. Logs (日志)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/logs/error` | POST | ❌ | ⏳ |
| `/api/v2/user/logs/errors` | POST | ❌ | ⏳ |

### 26. System Resources (系统资源管理)

| 端点 | 方法 | 认证 | 状态 |
|------|------|------|------|
| `/api/v2/user/system-resources` | GET | ❌ | ⏳ |
| `/api/v2/user/system-resources/stats` | GET | ❌ | ⏳ |
| `/api/v2/user/system-resources/{id}` | GET | ❌ | ⏳ |
| `/api/v2/user/system-resources` | POST | Admin | ⏳ |
| `/api/v2/user/system-resources/{id}` | PATCH | Admin | ⏳ |
| `/api/v2/user/system-resources/{id}/replace` | POST | Admin | ⏳ |
| `/api/v2/user/system-resources/{id}` | DELETE | Admin | ⏳ |
| `/api/v2/user/system-resources/batch` | POST | Admin | ⏳ |
| `/api/v2/user/system-resources/{id}/audit-log` | GET | Admin | ⏳ |

---

## 推荐测试顺序

1. Projects  
2. Support  
3. Profile  
4. Billing  
5. Resources  
6. Assets  
7. Templates  
8. Themes  
9. Marketplace  
10. Payment  
11. Seller  
12. Generation  
13. Tasks  
14. Export

---

## 汇总统计

| 分类 | 模块数 | 端点数 | 已通过 | 已修复待验证 | 待测试 |
|------|--------|--------|--------|--------------|--------|
| 核心功能 | 4 | 20 | 13 | 4 | 3 |
| 内容功能 | 4 | 24 | 0 | 0 | 24 |
| 业务功能 | 3 | 13 | 0 | 0 | 13 |
| 生成功能 | 3 | 14 | 0 | 0 | 14 |
| 辅助功能 | 12 | 49 | 0 | 0 | 49 |
| **总计** | **26** | **~120** | 13 | 4 | 103 |
