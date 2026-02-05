# v1/v2 → v3 迁移映射表

> **状态**: draft
> **创建日期**: 2026-02-05
> **更新日期**: 2026-02-05
> **用途**: 验证 v1 和 v2 内容在 v3 中的覆盖完整性

---

## 迁移状态说明

| 状态 | 说明 |
|------|------|
| ✅ 已规划 | 在 v3 有明确对应位置 |
| 📋 待整合 | 需要整合到其他文档中 |
| 🗄️ 归档 | 移入 archive/ |
| ❓ 待定 | 需要进一步评估 |

---

## 00-governance/ → internal/10-governance/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/10-governance/README.md | ✅ 已规划 |
| codebase-health-matrix.md | internal/10-governance/ | 📋 待整合 |
| document-template.md | internal/10-governance/templates/ | ✅ 已规划 |
| documentation-architecture-v4.md | internal/10-governance/ | ✅ 已迁移 |
| information-architecture.md | internal/10-governance/ | 📋 待整合 |
| maintenance-workflow.md | internal/10-governance/ | 📋 待整合 |
| naming-conventions.md | internal/10-governance/conventions.md | ✅ 已规划 |
| project-implementation-plan.md | archive/ | 🗄️ 归档 |
| shared-docs-registry.md | internal/10-governance/ | 📋 待整合 |
| shared-policy.md | internal/10-governance/sync-policy.md | ✅ 已规划 |
| status-and-versioning.md | internal/10-governance/ | 📋 待整合 |
| v3-refactoring-completion-report.md | archive/ | 🗄️ 归档 |
| templates/faq-template.md | internal/10-governance/templates/ | ✅ 已迁移 |
| templates/news-template.md | internal/10-governance/templates/ | ✅ 已迁移 |

---

## 01-architecture/ → internal/04-engineering/architecture/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/04-engineering/architecture/README.md | ✅ 已规划 |
| architecture-proposal.md | internal/04-engineering/architecture/overview.md | ✅ 已规划 |
| backend-architecture.md | internal/04-engineering/architecture/backend.md | ✅ 已规划 |
| frontend-architecture.md | internal/04-engineering/architecture/frontend.md | ✅ 已规划 |
| frontend-architecture-audit.md | archive/ | 🗄️ 归档 |
| self-hosted-auth-design.md | internal/04-engineering/modules/auth/ | ✅ 已规划 |
| system-refactoring-proposal-v2.md | archive/ | 🗄️ 归档 |
| adr/0001-use-ddd-architecture.md | internal/04-engineering/architecture/decisions/ | ✅ 已规划 |
| adr/0002-database-driven-config.md | internal/04-engineering/architecture/decisions/ | ✅ 已规划 |
| adr/README.md | internal/04-engineering/architecture/decisions/ | ✅ 已规划 |

---

## 02-standards/ → internal/04-engineering/development/ + internal/03-design/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/04-engineering/development/README.md | ✅ 已规划 |
| backend-naming-standards.md | internal/04-engineering/development/backend.md | ✅ 已规划 |
| database-guide.md | internal/04-engineering/development/database.md | ✅ 已规划 |
| design-system.md | internal/03-design/ (拆分为 tokens/components/patterns) | ✅ 已规划 |
| frontend-development-guide.md | internal/04-engineering/development/frontend.md | ✅ 已规划 |
| integration-testing-guide.md | internal/04-engineering/development/testing.md | ✅ 已规划 |
| logging-standard.md | internal/04-engineering/development/backend.md | 📋 待整合 |
| responsive-design-guide.md | internal/03-design/patterns.md | ✅ 已规划 |
| testing-guide.md | internal/04-engineering/development/testing.md | ✅ 已规划 |
| top-bar-height-management.md | internal/03-design/patterns.md | 📋 待整合 |
| ui-navigation-design.md | internal/03-design/patterns.md | 📋 待整合 |
| feature-flag/feature-flag-design.md | internal/04-engineering/modules/ | ✅ 已规划 |
| feature-flag/feature-flag-engine.md | internal/04-engineering/modules/ | ✅ 已规划 |

---

## 03-business/ → internal/05-business/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/05-business/README.md | ✅ 已规划 |
| backend-business-logic.md | internal/05-business/ | 📋 待整合 |
| canvas-data-schema.md | internal/04-engineering/data/schema.md | ✅ 已规划 |
| pricing-system.md | internal/05-business/pricing.md | ✅ 已规划 |
| tier-naming-system.md | internal/05-business/tier-system.md | ✅ 已规划 |
| user-id-system.md | internal/05-business/user-system.md | ✅ 已规划 |
| entitlement/README.md | internal/05-business/entitlement/README.md | ✅ 已规划 |
| entitlement/permission-matrix.md | internal/05-business/entitlement/ | ✅ 已规划 |
| entitlement/permission-matrix-appendix.md | internal/05-business/entitlement/ | 📋 待整合 |
| entitlement/billing-lifecycle.md | internal/05-business/entitlement/ | ✅ 已规划 |
| entitlement/credits-lifecycle.md | internal/05-business/credits-system.md | ✅ 已规划 |
| entitlement/promotions.md | internal/05-business/entitlement/ | ✅ 已规划 |
| entitlement/tier-config.md | internal/05-business/tier-system.md | 📋 待整合 |
| entitlement/system-design.md | internal/05-business/entitlement/ | 📋 待整合 |
| entitlement/ui-spec.md | internal/02-product/features/billing.md | 📋 待整合 |
| entitlement/policy-rules.md | internal/05-business/entitlement/ | 📋 待整合 |
| entitlement/feature-flag-engine.md | internal/04-engineering/modules/ | 📋 待整合 |
| entitlement/implementation-guide.md | internal/04-engineering/modules/billing/ | 📋 待整合 |
| entitlement/trial-expiration.md | internal/05-business/entitlement/ | 📋 待整合 |
| entitlement/referral-rewards.md | internal/06-growth/retention/referral.md | ✅ 已规划 |
| entitlement/education-discount.md | internal/05-business/entitlement/promotions.md | 📋 待整合 |
| entitlement/marketing-programs.md | internal/06-growth/ | 📋 待整合 |
| entitlement/audits.md | archive/ | 🗄️ 归档 |

---

## 04-features/ → internal/02-product/features/ + internal/04-engineering/modules/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/02-product/features/README.md | ✅ 已规划 |
| v3-spec-overview.md | archive/ | 🗄️ 归档 |
| canvas-architecture.md | internal/04-engineering/modules/editor/ | ✅ 已规划 |
| editor-media-properties.md | internal/04-engineering/modules/editor/ | ✅ 已规划 |
| file-import-support.md | internal/04-engineering/modules/editor/ | ✅ 已规划 |
| image-crop-solution.md | internal/04-engineering/modules/editor/ | ✅ 已规划 |
| text-font-solution.md | internal/04-engineering/modules/editor/ | ✅ 已规划 |
| mobile-profile-page-design.md | internal/02-product/pages/user/profile.md | ✅ 已规划 |
| **user-capabilities/** | | |
| README.md | internal/02-product/features/README.md | 📋 待整合 |
| editor-system-design.md | internal/02-product/features/editor.md | ✅ 已规划 |
| workspace-system-design.md | internal/02-product/features/dashboard.md | ✅ 已规划 |
| marketplace-system-design.md | internal/02-product/features/marketplace.md | ✅ 已规划 |
| billing-system-design.md | internal/02-product/features/billing.md | ✅ 已规划 |
| assets-system-design.md | internal/02-product/features/editor.md | 📋 待整合 |
| templates-system-design.md | internal/02-product/features/marketplace.md | 📋 待整合 |
| generation-system-design.md | internal/02-product/features/editor.md (AI) | 📋 待整合 |
| analytics-system-design.md | internal/07-analytics/ | 📋 待整合 |
| notifications-system-design.md | internal/02-product/features/ | 📋 待整合 |
| onboarding-design.md | internal/06-growth/retention/onboarding.md | ✅ 已规划 |
| referrals-system-design.md | internal/06-growth/retention/referral.md | ✅ 已规划 |
| resources-system-design.md | internal/02-product/features/editor.md | 📋 待整合 |
| support-system-design.md | internal/06-growth/support/ | ✅ 已规划 |
| theme-system-design.md | internal/02-product/features/ | 📋 待整合 |
| tools-system-design.md | internal/02-product/features/editor.md | 📋 待整合 |
| content-organization-design.md | internal/02-product/features/dashboard.md | 📋 待整合 |
| **admin-capabilities/** | | |
| README.md | internal/02-product/features/admin.md | ✅ 已规划 |
| analytics-system-design.md | internal/02-product/features/admin.md | 📋 待整合 |
| articles-system-design.md | internal/02-product/features/admin.md | 📋 待整合 |
| asset-category-design.md | internal/02-product/features/admin.md | 📋 待整合 |
| config-ops-design.md | internal/02-product/features/admin.md | 📋 待整合 |
| marketing-ops-design.md | internal/02-product/features/admin.md | 📋 待整合 |
| moderation-system-design.md | internal/02-product/features/admin.md | 📋 待整合 |
| static-pages-cms-design.md | internal/02-product/features/admin.md | 📋 待整合 |
| system-ops-design.md | internal/02-product/features/admin.md | 📋 待整合 |
| user-ops-design.md | internal/02-product/features/admin.md | 📋 待整合 |

---

## 05-api/ → internal/04-engineering/api/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/04-engineering/api/README.md | ✅ 已规划 |
| api-reference.md | internal/04-engineering/development/api-guide.md | ✅ 已规划 |
| user-endpoints.md | internal/04-engineering/api/user-endpoints.md | ✅ 已规划 |
| admin-endpoints.md | internal/04-engineering/api/admin-endpoints.md | ✅ 已规划 |
| user-api-review.md | archive/ | 🗄️ 归档 |
| admin-api-review.md | archive/ | 🗄️ 归档 |

---

## 06-operations/ → internal/08-operations/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/08-operations/README.md | ✅ 已规划 |
| deployment-scaling.md | internal/08-operations/deployment.md | ✅ 已规划 |

---

## 07-plans/ + 08-reports/ → archive/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| 07-plans/README.md | archive/ | 🗄️ 归档 |
| 08-reports/README.md | archive/ | 🗄️ 归档 |

---

## 09-reference/ → internal/10-governance/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/10-governance/ | 📋 待整合 |
| feature-coverage-matrix.md | internal/10-governance/ | 📋 待整合 |
| knowledge-base.md | internal/01-project/glossary.md | 📋 待整合 |
| shared-docs-registry.md | internal/10-governance/ | 📋 待整合 |

---

## 10-product/ → internal/02-product/pages/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/02-product/pages/README.md | ✅ 已规划 |
| **user/** | internal/02-product/pages/user/ | |
| account/*.md | internal/02-product/pages/user/auth.md | 📋 待整合 |
| dashboard/*.md | internal/02-product/pages/user/dashboard.md | 📋 待整合 |
| editor/*.md | internal/02-product/pages/user/editor.md | 📋 待整合 |
| marketplace/*.md | internal/02-product/pages/user/marketplace.md | 📋 待整合 |
| profile/*.md | internal/02-product/pages/user/profile.md | 📋 待整合 |
| **admin/** | internal/02-product/pages/admin/ | |
| admin-dashboard/*.md | internal/02-product/pages/admin/ | 📋 待整合 |
| analytics-ops/*.md | internal/02-product/pages/admin/ | 📋 待整合 |
| config-management/*.md | internal/02-product/pages/admin/ | 📋 待整合 |
| content-management/*.md | internal/02-product/pages/admin/ | 📋 待整合 |
| marketing-ops/*.md | internal/02-product/pages/admin/ | 📋 待整合 |

---

## 11-go-to-market/ → internal/06-growth/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/06-growth/README.md | ✅ 已规划 |

---

## 12-support/ → internal/06-growth/support/ + public/faq/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/06-growth/support/README.md | ✅ 已规划 |

---

## 13-legal-compliance/ → internal/09-compliance/ + public/legal/

| v2 文件 | v3 位置 | 状态 |
|---------|---------|------|
| README.md | internal/09-compliance/README.md + public/legal/ | ✅ 已规划 |

---

## 统计汇总

| 类别 | 数量 |
|------|------|
| ✅ 已规划/已迁移 | 约 60 |
| 📋 待整合 | 约 50 |
| 🗄️ 归档 | 约 15 |
| **总计** | 约 125 |

---

## 迁移优先级

### P0 - 立即需要

| 文档 | 原因 |
|------|------|
| 05-business/*.md | 核心业务规则 |
| 01-architecture/backend.md | 后端架构 |
| 01-architecture/frontend.md | 前端架构 |

### P1 - 短期需要

| 文档 | 原因 |
|------|------|
| 02-standards/development-*.md | 开发常用 |
| 04-features/user-capabilities/*.md | 功能规格 |
| 05-api/*.md | API 参考 |

### P2 - 中期需要

| 文档 | 原因 |
|------|------|
| 10-product/**/*.md | 页面设计 |
| 04-features/admin-capabilities/*.md | Admin 功能 |

### P3 - 按需迁移

| 文档 | 原因 |
|------|------|
| 00-governance/* | 治理文档 |
| 06-operations/* | 运维文档 |

---

## 下一步行动

1. **P0 文档迁移** - 复制核心业务规则和架构文档到 v3
2. **整合重复内容** - 将 📋 待整合的文档内容合并到目标文档
3. **归档旧文档** - 将 🗄️ 标记的文档移入 archive/
4. **验证完整性** - 逐个确认知识点已覆盖

---

# Part 2: v1 → v3 迁移映射

> v1 文档在前后端仓库中不完全同步，需要分别处理

---

## 后端 v1 (decodables/docs/v1/)

### v1/main/ → internal/04-engineering/

| v1 文件 | v3 位置 | 状态 | 说明 |
|---------|---------|------|------|
| api-reference.md | internal/04-engineering/development/api-guide.md | ✅ 已规划 | |
| architecture-proposal.md | internal/04-engineering/architecture/overview.md | ✅ 已规划 | |
| backend-architecture.md | internal/04-engineering/architecture/backend.md | ✅ 已规划 | |
| backend-business-logic.md | internal/05-business/ | 📋 待整合 | |
| codebase-health-matrix.md | internal/10-governance/ | 📋 待整合 | |
| database-guide.md | internal/04-engineering/development/database.md | ✅ 已规划 | |
| deployment-scaling.md | internal/08-operations/deployment.md | ✅ 已规划 | |
| knowledge-base.md | internal/01-project/glossary.md | 📋 待整合 | |
| naming-conventions.md | internal/04-engineering/development/backend.md | ✅ 已规划 | |
| testing-guide.md | internal/04-engineering/development/testing.md | ✅ 已规划 | |

### v1/adr/ → internal/04-engineering/architecture/decisions/

| v1 文件 | v3 位置 | 状态 |
|---------|---------|------|
| 0001-use-ddd-architecture.md | internal/04-engineering/architecture/decisions/ | ✅ 已规划 |
| 0002-database-driven-config.md | internal/04-engineering/architecture/decisions/ | ✅ 已规划 |

### v1/monitoring/ → internal/08-operations/

| v1 文件 | v3 位置 | 状态 |
|---------|---------|------|
| grafana-setup-guide.md | internal/08-operations/monitoring.md | 📋 待整合 |

### v1/tmp/ → archive/

| v1 文件 | v3 位置 | 状态 | 说明 |
|---------|---------|------|------|
| 001-message-system-optimization.md | archive/ | 🗄️ 归档 | 临时优化文档 |
| 003-sql-cross-audit.md | archive/ | 🗄️ 归档 | 审计文档 |
| 20260130-payment-*.md | archive/ | 🗄️ 归档 | 支付审计 |
| API-*.md | archive/ | 🗄️ 归档 | API 审计 |
| auth-security-audit-*.md | archive/ | 🗄️ 归档 | 安全审计 |

---

## 前端 v1 (decodables-fe/docs/v1/)

### v1/main/ → internal/ (前端专属)

| v1 文件 | v3 位置 | 状态 | 说明 |
|---------|---------|------|------|
| canvas-architecture-design.md | internal/04-engineering/modules/editor/ | ✅ 已规划 | 🔵 前端专属 |
| editor-media-properties-redesign.md | internal/04-engineering/modules/editor/ | ✅ 已规划 | 🔵 前端专属 |
| file-import-support-design.md | internal/04-engineering/modules/editor/ | ✅ 已规划 | 🔵 前端专属 |
| image-crop-solution-design.md | internal/04-engineering/modules/editor/ | ✅ 已规划 | 🔵 前端专属 |
| text-font-solution-design.md | internal/04-engineering/modules/editor/ | ✅ 已规划 | 🔵 前端专属 |
| make-decodables-design-system.md | internal/03-design/ | ✅ 已规划 | 🔵 前端专属 |
| responsive-design-guide.md | internal/03-design/patterns.md | ✅ 已规划 | 🔵 前端专属 |
| frontend-development-guide.md | internal/04-engineering/development/frontend.md | ✅ 已规划 | 🔵 前端专属 |
| frontend-architecture-audit-v1.md | archive/ | 🗄️ 归档 | 审计报告 |
| integration-testing-guide.md | internal/04-engineering/development/testing.md | ✅ 已规划 | |
| ui-navigation-design.md | internal/03-design/patterns.md | 📋 待整合 | |
| top-bar-height-management.md | internal/03-design/patterns.md | 📋 待整合 | |
| Mobile-Profile-Page-Design.md | internal/02-product/pages/user/profile.md | ✅ 已规划 | |
| v3-spec-overview.md | archive/ | 🗄️ 归档 | 版本规划 |

### v1/operation/ → archive/ (前端专属)

| v1 文件 | v3 位置 | 状态 | 说明 |
|---------|---------|------|------|
| refactor/CODE-REFACTOR-PLAN.md | archive/ | 🗄️ 归档 | 重构计划 |
| tmp/*.md | archive/ | 🗄️ 归档 | 临时操作文档 |

### v1/archive/ → archive/

| v1 文件 | v3 位置 | 状态 |
|---------|---------|------|
| editor-audit-report.md | archive/ | 🗄️ 归档 |

### v1/tmp/ → archive/ (前端专属)

| v1 文件类型 | v3 位置 | 状态 | 说明 |
|-------------|---------|------|------|
| 20260130-*.md | archive/ | 🗄️ 归档 | Dashboard 审计 |
| 20260131-*.md | archive/ | 🗄️ 归档 | 各页面审计 |
| audit-sessions/*.md | archive/ | 🗄️ 归档 | 系统审计会话 |
| workspace-*.md | archive/ | 🗄️ 归档 | 工作区设计 |

---

## 前后端共享 v1/shared/ → internal/05-business/ + others

> 两边的 shared/ 目录内容应相同

| v1 文件 | v3 位置 | 状态 | 说明 |
|---------|---------|------|------|
| user-id-system.md | internal/05-business/user-system.md | ✅ 已规划 | |
| tier-naming-system.md | internal/05-business/tier-system.md | ✅ 已规划 | |
| tier-permissions.md | internal/05-business/entitlement/ | 📋 待整合 | |
| pricing-system-design.md | internal/05-business/pricing.md | ✅ 已规划 | |
| canvas-data-schema.md | internal/04-engineering/data/schema.md | ✅ 已规划 | |
| self-hosted-auth-design.md | internal/04-engineering/modules/auth/ | ✅ 已规划 | |
| feature-flag-design.md | internal/04-engineering/modules/ | ✅ 已规划 | |
| feature-flag-engine.md | internal/04-engineering/modules/ | ✅ 已规划 | |
| onboarding-design.md | internal/06-growth/retention/onboarding.md | ✅ 已规划 | |
| theme-system-design.md | internal/02-product/features/ | 📋 待整合 | |
| static-pages-cms-design.md | internal/02-product/features/admin.md | 📋 待整合 | |
| articles-system-design.md | internal/02-product/features/admin.md | 📋 待整合 | |
| analytics-system-design.md | internal/07-analytics/ | 📋 待整合 | |
| asset-category-design.md | internal/02-product/features/ | 📋 待整合 | |
| message-logging-standard.md | internal/04-engineering/development/backend.md | 📋 待整合 | |
| entitlement-*.md | internal/05-business/entitlement/ | ✅ 已规划 | |
| admin-api-review.md | archive/ | 🗄️ 归档 | |
| user-api-review.md | archive/ | 🗄️ 归档 | |
| project-implementation-plan.md | archive/ | 🗄️ 归档 | |
| system-refactoring-proposal-v2.md | archive/ | 🗄️ 归档 | |
| v3-refactoring-completion-report.md | archive/ | 🗄️ 归档 | |

### v1/shared/entitlement/ → internal/05-business/entitlement/

| v1 文件 | v3 位置 | 状态 |
|---------|---------|------|
| 01-permission-matrix.md | internal/05-business/entitlement/permission-matrix.md | ✅ 已规划 |
| 02-tier-config.md | internal/05-business/tier-system.md | 📋 待整合 |
| 03-system-design.md | internal/05-business/entitlement/ | 📋 待整合 |
| 04-feature-flag-engine.md | internal/04-engineering/modules/ | 📋 待整合 |
| 05-ui-spec.md | internal/02-product/features/billing.md | 📋 待整合 |
| 06-priority-rules.md | internal/05-business/entitlement/ | 📋 待整合 |
| 07-tier-inheritance.md | internal/05-business/entitlement/ | 📋 待整合 |
| 08-user-groups.md | internal/05-business/entitlement/ | 📋 待整合 |
| 09-config-versioning.md | internal/05-business/entitlement/ | 📋 待整合 |
| 10-workspace-override.md | internal/05-business/entitlement/ | 📋 待整合 |
| 11-trial-expiration.md | internal/05-business/entitlement/ | 📋 待整合 |
| 12-tier-downgrade.md | internal/05-business/entitlement/billing-lifecycle.md | 📋 待整合 |
| 13-subscription-pause.md | internal/05-business/entitlement/billing-lifecycle.md | 📋 待整合 |
| 14-billing-cycle-switch.md | internal/05-business/entitlement/billing-lifecycle.md | 📋 待整合 |
| 15-credits-lifecycle.md | internal/05-business/credits-system.md | ✅ 已规划 |
| 16-renewal-reminders.md | internal/05-business/entitlement/billing-lifecycle.md | 📋 待整合 |
| 17-invoice-management.md | internal/05-business/entitlement/billing-lifecycle.md | 📋 待整合 |
| 18-refund-processing.md | internal/05-business/entitlement/billing-lifecycle.md | 📋 待整合 |
| 19-promotions.md | internal/05-business/entitlement/promotions.md | ✅ 已规划 |
| 20-referral-rewards.md | internal/06-growth/retention/referral.md | ✅ 已规划 |
| 21-education-discount.md | internal/05-business/entitlement/promotions.md | 📋 待整合 |
| 22-free-quota.md | internal/05-business/entitlement/ | 📋 待整合 |
| 23-feature-sunset.md | internal/05-business/entitlement/ | 📋 待整合 |
| 24-conflict-resolution.md | internal/05-business/entitlement/ | 📋 待整合 |
| 25-future-scenarios.md | archive/ | 🗄️ 归档 |
| 26-audit-checklist.md | archive/ | 🗄️ 归档 |
| 27-audit-report-*.md | archive/ | 🗄️ 归档 |
| 28-audit-supplement-*.md | archive/ | 🗄️ 归档 |

### v1/shared/entitlement/implementation/ → internal/04-engineering/modules/billing/

| v1 文件 | v3 位置 | 状态 |
|---------|---------|------|
| 01-database-schema.md | internal/04-engineering/data/schema.md | 📋 待整合 |
| 02-backend-services.md | internal/04-engineering/modules/billing/ | 📋 待整合 |
| 03-backend-repositories.md | internal/04-engineering/modules/billing/ | 📋 待整合 |
| 04-backend-apis.md | internal/04-engineering/api/ | 📋 待整合 |
| 05-frontend-stores.md | internal/04-engineering/modules/billing/ | 📋 待整合 |
| 06-frontend-components.md | internal/04-engineering/modules/billing/ | 📋 待整合 |
| 07-migration-scripts.md | archive/ | 🗄️ 归档 |

---

## v1 统计汇总

| 来源 | 类别 | 数量 |
|------|------|------|
| **后端 v1** | | |
| | main/ | 10 |
| | adr/ | 3 |
| | monitoring/ | 1 |
| | tmp/ | ~10 |
| **前端 v1** | | |
| | main/ | 14 |
| | operation/ | ~15 |
| | archive/ | 1 |
| | tmp/ | ~40 |
| **共享 v1** | | |
| | shared/ | ~25 |
| | shared/entitlement/ | ~30 |
| | shared/entitlement/implementation/ | 8 |
| **总计** | | **~160** |

---

## v1 特殊处理说明

### 后端专属文档 (🔴)

这些文档只在后端 v1 存在，迁移到 v3 时放在后端仓库：

- api-reference.md
- backend-architecture.md
- backend-business-logic.md
- database-guide.md
- deployment-scaling.md
- grafana-setup-guide.md

### 前端专属文档 (🔵)

这些文档只在前端 v1 存在，迁移到 v3 时放在前端仓库：

- canvas-architecture-design.md
- editor-media-properties-redesign.md
- file-import-support-design.md
- image-crop-solution-design.md
- text-font-solution-design.md
- make-decodables-design-system.md
- responsive-design-guide.md
- frontend-development-guide.md
- ui-navigation-design.md
- operation/refactor/*
- operation/tmp/*

### 共享文档处理

shared/ 目录的文档在 v3 中：
- 业务规则 → `internal/05-business/` (两边都有)
- 技术实现 → 按前后端分别放置

---

## 总体统计

| 来源 | 文档数 | 已规划 | 待整合 | 归档 |
|------|--------|--------|--------|------|
| v2 | ~125 | ~60 | ~50 | ~15 |
| v1 | ~160 | ~50 | ~60 | ~50 |
| **总计** | **~285** | **~110** | **~110** | **~65** |

> 注：部分 v1 和 v2 文档内容重复，实际需要迁移的知识点少于文档总数
