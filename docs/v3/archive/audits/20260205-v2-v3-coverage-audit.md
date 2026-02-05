# v2 → v3 文档覆盖审计报告

> **审计日期**: 2026-02-05
> **审计范围**: 后端 v2 + 前端 v2 → 后端 v3
> **审计方法**: 目录对比 + 内容深度分析

---

## 审计说明

| 状态 | 说明 |
|------|------|
| ✅ 完全覆盖 | v3 中有对应文档且内容完整 |
| 🟡 部分覆盖 | v3 中有相关文档但内容不完整或仅有框架 |
| ❌ 未覆盖 | v3 中没有对应内容 |
| 🗄️ 归档 | 内容已过时，应归档处理 |

---

## 1. 00-governance (文档治理)

**v2 路径**: `decodables/docs/v2/00-governance/`
**v3 对应**: `decodables/docs/v3/internal/10-governance/`

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | ✅ 完全覆盖 | internal/10-governance/README.md | 已迁移 |
| codebase-health-matrix.md | 🟡 部分覆盖 | internal/10-governance/ | 有规划但未迁移 |
| document-template.md | ✅ 完全覆盖 | internal/10-governance/templates/ | 已有多个模板 |
| documentation-architecture-v4.md | ✅ 完全覆盖 | internal/10-governance/ | 已迁移 |
| information-architecture.md | 🟡 部分覆盖 | internal/10-governance/ | 待整合 |
| maintenance-workflow.md | 🟡 部分覆盖 | internal/10-governance/ | 待整合 |
| naming-conventions.md | 🟡 部分覆盖 | internal/10-governance/conventions.md | 规划中 |
| project-implementation-plan.md | 🗄️ 归档 | archive/ | 历史规划 |
| shared-docs-registry.md | 🟡 部分覆盖 | internal/10-governance/ | 待整合 |
| shared-policy.md | 🟡 部分覆盖 | internal/10-governance/sync-policy.md | 规划中 |
| status-and-versioning.md | 🟡 部分覆盖 | internal/10-governance/ | 待整合 |
| v3-refactoring-completion-report.md | 🗄️ 归档 | archive/ | 历史报告 |
| templates/faq-template.md | ✅ 完全覆盖 | internal/10-governance/templates/ | 已迁移 |
| templates/news-template.md | ✅ 完全覆盖 | internal/10-governance/templates/ | 已迁移 |

**小结**: ✅ 5 | 🟡 7 | ❌ 0 | 🗄️ 2

---

## 2. 01-architecture (架构文档)

**v2 路径**: `decodables/docs/v2/01-architecture/`
**v3 对应**: `decodables/docs/v3/internal/04-engineering/architecture/`

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | ✅ 完全覆盖 | internal/04-engineering/architecture/README.md | |
| architecture-proposal.md | ✅ 完全覆盖 | internal/04-engineering/architecture/overview.md | |
| backend-architecture.md | ✅ 完全覆盖 | internal/04-engineering/architecture/backend.md | 内容丰富完整 |
| frontend-architecture.md | ✅ 完全覆盖 | internal/04-engineering/architecture/frontend.md | |
| frontend-architecture-audit.md | 🗄️ 归档 | archive/ | 审计报告 |
| self-hosted-auth-design.md | 🟡 部分覆盖 | internal/04-engineering/modules/auth/ | 有 architecture.md 但不完整 |
| system-refactoring-proposal-v2.md | 🗄️ 归档 | archive/ | 历史规划 |
| adr/0001-use-ddd-architecture.md | ❌ 未覆盖 | internal/04-engineering/architecture/decisions/ | 仅有 README |
| adr/0002-database-driven-config.md | ❌ 未覆盖 | internal/04-engineering/architecture/decisions/ | 仅有 README |
| adr/README.md | 🟡 部分覆盖 | internal/04-engineering/architecture/decisions/ | 有框架 |

**小结**: ✅ 4 | 🟡 2 | ❌ 2 | 🗄️ 2

---

## 3. 02-standards (开发规范)

**v2 路径**: `decodables/docs/v2/02-standards/`
**v3 对应**: `decodables/docs/v3/internal/04-engineering/development/` + `internal/03-design/`

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | 🟡 部分覆盖 | internal/04-engineering/development/README.md | 有框架 |
| backend-naming-standards.md | 🟡 部分覆盖 | internal/04-engineering/development/backend/ | 仅有 README |
| database-guide.md | 🟡 部分覆盖 | internal/04-engineering/architecture/database.md | 有文件待验证 |
| design-system.md | 🟡 部分覆盖 | internal/03-design/ | 拆分为 tokens/components/patterns |
| frontend-development-guide.md | 🟡 部分覆盖 | internal/04-engineering/development/frontend/ | 仅有 README |
| integration-testing-guide.md | ❌ 未覆盖 | internal/04-engineering/development/testing.md | 未创建 |
| logging-standard.md | ❌ 未覆盖 | internal/04-engineering/development/backend.md | 待整合 |
| responsive-design-guide.md | 🟡 部分覆盖 | internal/03-design/patterns/ | 仅有框架 |
| testing-guide.md | ❌ 未覆盖 | internal/04-engineering/development/testing.md | 未创建 |
| top-bar-height-management.md | ❌ 未覆盖 | internal/03-design/patterns.md | 待整合 |
| ui-navigation-design.md | ❌ 未覆盖 | internal/03-design/patterns.md | 待整合 |
| feature-flag/feature-flag-design.md | 🟡 部分覆盖 | internal/02-product/features/feature-flags.md | 有功能规格 |
| feature-flag/feature-flag-engine.md | ❌ 未覆盖 | internal/04-engineering/modules/ | 待创建 |

**小结**: ✅ 0 | 🟡 7 | ❌ 6 | 🗄️ 0

---

## 4. 03-business (业务规则) ⚠️ 重点关注

**v2 路径**: `decodables/docs/v2/03-business/`
**v3 对应**: `decodables/docs/v3/internal/05-business/`

### 4.1 核心业务文档

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | ✅ 完全覆盖 | internal/05-business/README.md | |
| backend-business-logic.md | 🟡 部分覆盖 | internal/05-business/ | 待拆分整合 |
| canvas-data-schema.md | ❌ 未覆盖 | internal/04-engineering/data/schema.md | 未创建 |
| pricing-system.md | 🟡 部分覆盖 | internal/05-business/pricing/pricing-strategy.md | 有但不完整 |
| tier-naming-system.md | ✅ 完全覆盖 | internal/05-business/tier-system/overview.md | |
| user-id-system.md | ✅ 完全覆盖 | internal/05-business/user-id-system.md | |

### 4.2 entitlement/ 权益系统 ⚠️ 重点

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | ✅ 完全覆盖 | internal/05-business/entitlement/README.md | |
| permission-matrix.md | ❌ 未覆盖 | internal/05-business/entitlement/ | **核心文档缺失** |
| permission-matrix-appendix.md | ❌ 未覆盖 | internal/05-business/entitlement/ | 待整合 |
| tier-config.md | 🟡 部分覆盖 | internal/05-business/tier-system/ | 部分内容在 permissions.md |
| system-design.md | ❌ 未覆盖 | internal/05-business/entitlement/ | **核心文档缺失** |
| feature-flag-engine.md | ❌ 未覆盖 | internal/04-engineering/modules/ | 待创建 |
| ui-spec.md | ❌ 未覆盖 | internal/02-product/features/billing.md | 待整合 |
| policy-rules.md | ❌ 未覆盖 | internal/05-business/entitlement/ | **核心文档缺失** |
| billing-lifecycle.md | ❌ 未覆盖 | internal/05-business/entitlement/ | **核心文档缺失** |
| credits-lifecycle.md | ✅ 完全覆盖 | internal/05-business/credits-system/overview.md | 内容完整 |
| trial-expiration.md | ❌ 未覆盖 | internal/05-business/entitlement/ | 待创建 |
| promotions.md | ❌ 未覆盖 | internal/05-business/entitlement/ | 待创建 |
| referral-rewards.md | ❌ 未覆盖 | internal/06-growth/retention/referral.md | 未创建 |
| education-discount.md | ❌ 未覆盖 | internal/05-business/entitlement/promotions.md | 待整合 |
| marketing-programs.md | ❌ 未覆盖 | internal/06-growth/ | 待创建 |
| audits.md | 🗄️ 归档 | archive/ | 历史审计 |
| implementation-guide.md | ❌ 未覆盖 | internal/04-engineering/modules/billing/ | 待创建 |

**小结**: ✅ 5 | 🟡 3 | ❌ 14 | 🗄️ 1

---

## 5. 04-features (功能设计) ⚠️ 重点关注

**v2 路径**: `decodables/docs/v2/04-features/`
**v3 对应**: `decodables/docs/v3/internal/02-product/features/` + `internal/04-engineering/modules/`

### 5.1 核心功能文档

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | ✅ 完全覆盖 | internal/02-product/features/README.md | |
| v3-spec-overview.md | 🗄️ 归档 | archive/ | |
| canvas-architecture.md | 🟡 部分覆盖 | internal/04-engineering/modules/editor/architecture.md | 有但待补充细节 |
| editor-media-properties.md | 🟡 部分覆盖 | internal/04-engineering/modules/editor/ | 待补充 |
| file-import-support.md | 🟡 部分覆盖 | internal/02-product/features/file-import.md | 有功能规格 |
| image-crop-solution.md | ❌ 未覆盖 | internal/04-engineering/modules/editor/ | 待创建 |
| text-font-solution.md | ❌ 未覆盖 | internal/04-engineering/modules/editor/ | 待创建 |
| mobile-profile-page-design.md | 🟡 部分覆盖 | internal/02-product/pages/user/profile.md | 有框架 |

### 5.2 user-capabilities/ 用户功能

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | 🟡 部分覆盖 | internal/02-product/features/README.md | |
| editor-system-design.md | ✅ 完全覆盖 | internal/02-product/features/editor.md | |
| workspace-system-design.md | ✅ 完全覆盖 | internal/02-product/features/dashboard.md | |
| marketplace-system-design.md | ✅ 完全覆盖 | internal/02-product/features/marketplace.md | |
| billing-system-design.md | ✅ 完全覆盖 | internal/02-product/features/subscription.md + credits.md | 内容完整 |
| assets-system-design.md | ❌ 未覆盖 | internal/02-product/features/editor.md | 待整合 |
| templates-system-design.md | 🟡 部分覆盖 | internal/02-product/features/templates.md | 有框架 |
| generation-system-design.md | 🟡 部分覆盖 | internal/02-product/features/ai-generation.md | 有框架 |
| analytics-system-design.md | ❌ 未覆盖 | internal/07-analytics/ | 仅有 README |
| notifications-system-design.md | 🟡 部分覆盖 | internal/02-product/features/notifications.md | 有框架 |
| onboarding-design.md | 🟡 部分覆盖 | internal/02-product/features/onboarding.md | 有框架 |
| referrals-system-design.md | ❌ 未覆盖 | internal/06-growth/retention/referral.md | 未创建 |
| resources-system-design.md | ❌ 未覆盖 | internal/02-product/features/editor.md | 待整合 |
| support-system-design.md | ❌ 未覆盖 | internal/06-growth/support/ | 仅有 README |
| theme-system-design.md | ❌ 未覆盖 | internal/02-product/features/ | 待创建 |
| tools-system-design.md | ❌ 未覆盖 | internal/02-product/features/editor.md | 待整合 |
| content-organization-design.md | ❌ 未覆盖 | internal/02-product/features/dashboard.md | 待整合 |

### 5.3 admin-capabilities/ 管理功能 ⚠️

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | 🟡 部分覆盖 | internal/04-engineering/modules/admin/README.md | 仅有框架 |
| analytics-system-design.md | ❌ 未覆盖 | internal/02-product/features/admin.md | **待创建** |
| articles-system-design.md | ❌ 未覆盖 | internal/02-product/features/admin.md | **待创建** |
| asset-category-design.md | ❌ 未覆盖 | internal/02-product/features/admin.md | **待创建** |
| config-ops-design.md | ❌ 未覆盖 | internal/02-product/features/admin.md | **待创建** |
| marketing-ops-design.md | ❌ 未覆盖 | internal/02-product/features/admin.md | **待创建** |
| moderation-system-design.md | ❌ 未覆盖 | internal/02-product/features/admin.md | **待创建** |
| static-pages-cms-design.md | ❌ 未覆盖 | internal/02-product/features/admin.md | **待创建** |
| system-ops-design.md | ❌ 未覆盖 | internal/02-product/features/admin.md | **待创建** |
| user-ops-design.md | ❌ 未覆盖 | internal/02-product/features/admin.md | **待创建** |

**小结**: ✅ 5 | 🟡 11 | ❌ 19 | 🗄️ 1

---

## 6. 05-api (API文档) ⚠️ 重点关注

**v2 路径**: `decodables/docs/v2/05-api/`
**v3 对应**: `decodables/docs/v3/internal/04-engineering/api/`

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | 🟡 部分覆盖 | internal/04-engineering/api/README.md | 仅有框架，无实际端点 |
| api-reference.md | ❌ 未覆盖 | internal/04-engineering/api/ | **核心文档缺失** |
| user-endpoints.md | ❌ 未覆盖 | internal/04-engineering/api/user-endpoints.md | **规划中未创建** |
| admin-endpoints.md | ❌ 未覆盖 | internal/04-engineering/api/admin-endpoints.md | **规划中未创建** |
| user-api-review.md | 🗄️ 归档 | archive/ | 审计报告 |
| admin-api-review.md | 🗄️ 归档 | archive/ | 审计报告 |

**小结**: ✅ 0 | 🟡 1 | ❌ 3 | 🗄️ 2

---

## 7. 06-operations (运维)

**v2 路径**: `decodables/docs/v2/06-operations/`
**v3 对应**: `decodables/docs/v3/internal/08-operations/`

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | 🟡 部分覆盖 | internal/08-operations/README.md | 仅有框架 |
| deployment-scaling.md | ❌ 未覆盖 | internal/08-operations/deployment.md | 未创建 |

**小结**: ✅ 0 | 🟡 1 | ❌ 1 | 🗄️ 0

---

## 8. 09-reference (参考)

**v2 路径**: `decodables/docs/v2/09-reference/`
**v3 对应**: `decodables/docs/v3/internal/11-reference/`

| v2 文件 | 状态 | v3 位置 | 备注 |
|---------|------|---------|------|
| README.md | 🟡 部分覆盖 | internal/11-reference/README.md | |
| feature-coverage-matrix.md | 🟡 部分覆盖 | internal/11-reference/feature-matrix.md | 有但待完善 |
| knowledge-base.md | 🟡 部分覆盖 | internal/11-reference/glossary.md | 有但待完善 |
| shared-docs-registry.md | ❌ 未覆盖 | internal/10-governance/ | 待整合 |

**小结**: ✅ 0 | 🟡 3 | ❌ 1 | 🗄️ 0

---

## 9. 10-product (产品页面) ⚠️ 重点关注

**v2 路径**: `decodables/docs/v2/10-product/`
**v3 对应**: `decodables/docs/v3/internal/02-product/pages/`

### 9.1 user/ 用户端页面

| v2 目录/文件 | 状态 | v3 位置 | 备注 |
|--------------|------|---------|------|
| **account/** | | | |
| login.md | ❌ 未覆盖 | internal/02-product/pages/user/auth.md | **待创建** |
| register.md | ❌ 未覆盖 | internal/02-product/pages/user/auth.md | **待创建** |
| forgot-password.md | ❌ 未覆盖 | internal/02-product/pages/user/auth.md | **待创建** |
| reset-password.md | ❌ 未覆盖 | internal/02-product/pages/user/auth.md | **待创建** |
| verify-email.md | ❌ 未覆盖 | internal/02-product/pages/user/auth.md | **待创建** |
| **dashboard/** | | | |
| home.md | ❌ 未覆盖 | internal/02-product/pages/user/dashboard.md | **待创建** |
| dashboard.md | ❌ 未覆盖 | internal/02-product/pages/user/dashboard.md | **待创建** |
| notifications.md | ❌ 未覆盖 | internal/02-product/pages/user/notifications.md | **待创建** |
| manual.md | ❌ 未覆盖 | public/manual/ | 有框架 |
| news.md | ❌ 未覆盖 | public/news/ | 有框架 |
| about-us.md | ✅ 完全覆盖 | internal/02-product/pages/user/about-us.md | |
| contact-us.md | ✅ 完全覆盖 | internal/02-product/pages/user/contact-us.md | |
| privacy-policy.md | ✅ 完全覆盖 | internal/02-product/pages/user/privacy.md | |
| terms-of-service.md | ✅ 完全覆盖 | internal/02-product/pages/user/terms.md | |
| billing-policy.md | ❌ 未覆盖 | internal/02-product/pages/user/ | **待创建** |
| **editor/** | | | |
| create.md | ❌ 未覆盖 | internal/02-product/pages/user/editor.md | **待创建** |
| **marketplace/** | | | |
| marketplace.md | ❌ 未覆盖 | internal/02-product/pages/user/marketplace.md | **待创建** |
| marketplace-guidelines.md | ❌ 未覆盖 | internal/02-product/pages/user/ | **待创建** |
| **profile/** | | | |
| profile.md | ❌ 未覆盖 | internal/02-product/pages/user/profile.md | **待创建** |
| transaction-history.md | ❌ 未覆盖 | internal/02-product/pages/user/ | **待创建** |

### 9.2 admin/ 管理端页面 ⚠️

| v2 目录/文件 | 状态 | v3 位置 | 备注 |
|--------------|------|---------|------|
| **admin-dashboard/** | | | |
| admin-dashboard.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **仅有 README** |
| users.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **待创建** |
| moderation.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **待创建** |
| operations.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **待创建** |
| **analytics-ops/** | | | |
| analytics.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **待创建** |
| **config-management/** | | | |
| configs.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **待创建** |
| **content-management/** | | | |
| articles.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **待创建** |
| content.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **待创建** |
| themes.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **待创建** |
| **marketing-ops/** | | | |
| marketing.md | ❌ 未覆盖 | internal/02-product/pages/admin/ | **待创建** |

**小结**: ✅ 4 | 🟡 0 | ❌ 26 | 🗄️ 0

---

## 总体统计

### 按目录汇总

| v2 目录 | ✅ 完全覆盖 | 🟡 部分覆盖 | ❌ 未覆盖 | 🗄️ 归档 | 总计 |
|---------|-------------|-------------|----------|---------|------|
| 00-governance | 5 | 7 | 0 | 2 | 14 |
| 01-architecture | 4 | 2 | 2 | 2 | 10 |
| 02-standards | 0 | 7 | 6 | 0 | 13 |
| 03-business | 5 | 3 | 14 | 1 | 23 |
| 04-features | 5 | 11 | 19 | 1 | 36 |
| 05-api | 0 | 1 | 3 | 2 | 6 |
| 06-operations | 0 | 1 | 1 | 0 | 2 |
| 09-reference | 0 | 3 | 1 | 0 | 4 |
| 10-product | 4 | 0 | 26 | 0 | 30 |
| **总计** | **23** | **35** | **72** | **8** | **138** |

### 覆盖率

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 完全覆盖 | 23 | 16.7% |
| 🟡 部分覆盖 | 35 | 25.4% |
| ❌ 未覆盖 | 72 | 52.2% |
| 🗄️ 归档 | 8 | 5.8% |
| **有效文档总计** | **130** | (排除归档) |
| **实际覆盖率** | | **44.6%** (完全+部分) |

---

## 需要补充的文档清单 (按优先级)

### P0 - 核心业务必须补充 (12个)

| 优先级 | v2 文档 | 缺失原因 | 业务影响 |
|--------|---------|----------|----------|
| P0-1 | 03-business/entitlement/permission-matrix.md | 核心权限矩阵缺失 | 权限判断依据 |
| P0-2 | 03-business/entitlement/system-design.md | 权益系统设计缺失 | 理解系统架构 |
| P0-3 | 03-business/entitlement/policy-rules.md | 策略规则缺失 | 权限继承逻辑 |
| P0-4 | 03-business/entitlement/billing-lifecycle.md | 订阅生命周期缺失 | 订阅状态管理 |
| P0-5 | 05-api/api-reference.md | API 总览缺失 | API 开发参考 |
| P0-6 | 05-api/user-endpoints.md | 用户端点缺失 | API 开发参考 |
| P0-7 | 05-api/admin-endpoints.md | 管理端点缺失 | Admin API 参考 |
| P0-8 | 04-features/admin-capabilities/*.md (9个) | Admin 功能全部缺失 | Admin 系统开发 |
| P0-9 | 01-architecture/adr/*.md | 架构决策记录缺失 | 架构理解 |
| P0-10 | 02-standards/testing-guide.md | 测试规范缺失 | 测试开发 |
| P0-11 | 02-standards/feature-flag-engine.md | FF 引擎缺失 | Feature Flag 开发 |
| P0-12 | 03-business/canvas-data-schema.md | Canvas 数据结构缺失 | 编辑器开发 |

### P1 - 功能规格需要补充 (15个)

| 优先级 | v2 文档 | 缺失原因 |
|--------|---------|----------|
| P1-1 | 04-features/user-capabilities/assets-system-design.md | 素材系统设计 |
| P1-2 | 04-features/user-capabilities/theme-system-design.md | 主题系统设计 |
| P1-3 | 04-features/user-capabilities/referrals-system-design.md | 推荐系统设计 |
| P1-4 | 04-features/user-capabilities/analytics-system-design.md | 用户分析设计 |
| P1-5 | 04-features/user-capabilities/support-system-design.md | 支持系统设计 |
| P1-6 | 04-features/image-crop-solution.md | 裁切方案设计 |
| P1-7 | 04-features/text-font-solution.md | 字体方案设计 |
| P1-8 | 03-business/entitlement/promotions.md | 促销规则 |
| P1-9 | 03-business/entitlement/trial-expiration.md | 试用规则 |
| P1-10 | 03-business/entitlement/referral-rewards.md | 推荐奖励规则 |
| P1-11 | 03-business/entitlement/education-discount.md | 教育优惠规则 |
| P1-12 | 02-standards/logging-standard.md | 日志规范 |
| P1-13 | 02-standards/integration-testing-guide.md | 集成测试指南 |
| P1-14 | 06-operations/deployment-scaling.md | 部署扩展指南 |
| P1-15 | 03-business/entitlement/implementation-guide.md | 权益实现指南 |

### P2 - 产品页面需要补充 (26个)

| 优先级 | v2 目录 | 缺失页面数 |
|--------|---------|------------|
| P2-1 | 10-product/user/account/ | 5 (登录/注册/密码找回等) |
| P2-2 | 10-product/user/dashboard/ | 6 (首页/仪表盘/通知等) |
| P2-3 | 10-product/user/editor/ | 1 (编辑器页面) |
| P2-4 | 10-product/user/marketplace/ | 2 (市场/指南) |
| P2-5 | 10-product/user/profile/ | 2 (个人中心/交易历史) |
| P2-6 | 10-product/admin/ | 10 (全部 Admin 页面) |

### P3 - 治理与规范补充 (10个)

| 优先级 | v2 文档 | 缺失原因 |
|--------|---------|----------|
| P3-1 | 00-governance/codebase-health-matrix.md | 健康度指标 |
| P3-2 | 00-governance/information-architecture.md | 信息架构 |
| P3-3 | 00-governance/maintenance-workflow.md | 维护流程 |
| P3-4 | 00-governance/naming-conventions.md | 命名规范 |
| P3-5 | 00-governance/shared-docs-registry.md | 共享文档注册 |
| P3-6 | 00-governance/shared-policy.md | 共享策略 |
| P3-7 | 00-governance/status-and-versioning.md | 状态与版本 |
| P3-8 | 02-standards/top-bar-height-management.md | 顶栏高度管理 |
| P3-9 | 02-standards/ui-navigation-design.md | UI 导航设计 |
| P3-10 | 09-reference/shared-docs-registry.md | 共享文档注册 |

---

## 建议行动计划

### Phase 1: P0 核心业务文档 (立即执行)

1. **权益系统迁移** (P0-1~P0-4)
   - 从 v2 复制 entitlement 核心文档到 v3
   - 整合到 `internal/05-business/entitlement/` 结构

2. **API 文档迁移** (P0-5~P0-7)
   - 创建 API 端点文档
   - 按模块组织 (auth, billing, projects 等)

3. **Admin 功能文档迁移** (P0-8)
   - 在 v3 创建统一的 admin 功能规格文档
   - 整合 9 个 Admin 功能设计

### Phase 2: P1 功能规格补充

1. 迁移缺失的功能设计文档
2. 整合重复内容到对应的 features/*.md
3. 补充技术实现细节到 modules/

### Phase 3: P2 产品页面补充

1. 创建页面设计模板
2. 批量迁移用户端页面设计
3. 补充 Admin 端页面设计

### Phase 4: P3 治理规范完善

1. 整合治理文档
2. 完善开发规范

---

## 审计结论

1. **覆盖率不足**: 有效文档覆盖率仅 44.6%，超过一半的 v2 内容未迁移到 v3

2. **核心缺失严重**: 
   - 权益系统 (entitlement) 核心文档 14 个中有 13 个未覆盖
   - API 文档几乎全部缺失
   - Admin 功能文档全部缺失
   - 产品页面设计 26 个未覆盖

3. **结构已就绪**: v3 的目录结构已经规划好，大多数位置已有 README 框架

4. **迁移映射存在**: v3 已有 `v2-to-v3-migration-map.md`，但标记"待整合"的内容实际未执行

**建议**: 立即启动 P0 文档迁移，特别是权益系统和 API 文档，这些是开发的核心参考资料。

---

**END OF AUDIT REPORT**
