# v2 → v3 迁移映射表

> **状态**: draft
> **创建日期**: 2026-02-05
> **用途**: 验证 v2 内容在 v3 中的覆盖完整性

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
