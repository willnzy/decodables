 # Shared 文档同步索引
 
 > 统一记录 shared 文档的归属、同步状态与变更流程。
 
 **状态**: draft  
 **版本**: 0.1.0  
 **版本日期**: 2026-02-04  
 **最后复核**: 2026-02-04  
 **负责人**: Docs Working Group  
 **适用范围**: shared  
 **source_repo**: both  
 **sync_required**: yes  
 **来源/依据**: `decodables-fe/docs/shared/`、`decodables/docs/shared/`、`decodables/docs/v2/09-reference/feature-coverage-matrix.md`
 
 ---
 
 ## 1. 目标
 
 - 统一 shared 文档的归属与同步规则
 - 提供唯一索引入口，支持双端一致性追踪
 - 避免重复、遗漏、冲突
 
## 1.1 设计约束（强制）

- 禁止照搬旧文档结构或原文段落
- 必须以新结构重组表达，仅引用证据来源
- 每条记录必须指向唯一主文档

 ## 2. 同步规则
 
 - shared 文档必须在两端保持同路径与同内容
 - 任一端更新必须同步到另一端
 - 共享文档只在 `docs/v2/` 下维护新版结构
 
 ## 3. 状态字段
 
 - `pending`: 已映射，尚未建立 v2 骨架
 - `needs-review`: 已建立骨架，待结构审查
 - `done`: 内容迁移完成并复核通过
 - `archived`: 停用，仅保留历史
 
 ## 4. 变更流程
 
 1. 在任一端更新 shared 文档
 2. 同步到另一端，保持一致
 3. 在覆盖矩阵更新状态
 
 ## 5. 索引清单
 
> 由覆盖矩阵驱动，所有 shared 文档必须在此登记。

| shared_key | v2_path | status | owner | last_review | source |
| --- | --- | --- | --- | --- | --- |
| `shared-docs-registry` | `docs/v2/09-reference/shared-docs-registry.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/README.md` |
| `admin-api-review` | `docs/v2/05-api/admin-api-review.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/admin-api-review.md` |
| `user-api-review` | `docs/v2/05-api/user-api-review.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/user-api-review.md` |
| `analytics-system-design` | `docs/v2/04-features/admin-capabilities/analytics-system-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/analytics-system-design.md` |
| `articles-system-design` | `docs/v2/04-features/admin-capabilities/articles-system-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/articles-system-design.md` |
| `asset-category-design` | `docs/v2/04-features/admin-capabilities/asset-category-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/asset-category-design.md` |
| `static-pages-cms-design` | `docs/v2/04-features/admin-capabilities/static-pages-cms-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/static-pages-cms-design.md` |
| `onboarding-design` | `docs/v2/04-features/user-capabilities/onboarding-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/onboarding-design.md` |
| `theme-system-design` | `docs/v2/04-features/user-capabilities/theme-system-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/theme-system-design.md` |
| `canvas-data-schema` | `docs/v2/03-business/canvas-data-schema.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/canvas-data-schema.md` |
| `pricing-system-design` | `docs/v2/03-business/pricing-system.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/pricing-system-design.md` |
| `tier-naming-system` | `docs/v2/03-business/tier-naming-system.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/tier-naming-system.md` |
| `tier-permissions` | `docs/v2/03-business/entitlement/permission-matrix.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/tier-permissions.md` |
| `user-id-system` | `docs/v2/03-business/user-id-system.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/user-id-system.md` |
| `entitlement-system-design` | `docs/v2/03-business/entitlement/system-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement-system-design.md` |
| `entitlement-permission-matrix` | `docs/v2/03-business/entitlement/permission-matrix.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement-permission-matrix.md` |
| `entitlement-ui-spec` | `docs/v2/03-business/entitlement/ui-spec.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement-ui-spec.md` |
| `entitlement/README` | `docs/v2/03-business/entitlement/README.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/README.md` |
| `entitlement/01-permission-matrix-appendix` | `docs/v2/03-business/entitlement/permission-matrix-appendix.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/01-permission-matrix-appendix.md` |
| `entitlement/01-permission-matrix` | `docs/v2/03-business/entitlement/permission-matrix.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/01-permission-matrix.md` |
| `entitlement/02-tier-config` | `docs/v2/03-business/entitlement/tier-config.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/02-tier-config.md` |
| `entitlement/03-system-design` | `docs/v2/03-business/entitlement/system-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/03-system-design.md` |
| `entitlement/04-feature-flag-engine` | `docs/v2/03-business/entitlement/feature-flag-engine.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/04-feature-flag-engine.md` |
| `entitlement/05-ui-spec` | `docs/v2/03-business/entitlement/ui-spec.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/05-ui-spec.md` |
| `entitlement/06-priority-rules` | `docs/v2/03-business/entitlement/policy-rules.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/06-priority-rules.md` |
| `entitlement/07-tier-inheritance` | `docs/v2/03-business/entitlement/policy-rules.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/07-tier-inheritance.md` |
| `entitlement/08-user-groups` | `docs/v2/03-business/entitlement/policy-rules.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/08-user-groups.md` |
| `entitlement/09-config-versioning` | `docs/v2/03-business/entitlement/policy-rules.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/09-config-versioning.md` |
| `entitlement/10-workspace-override` | `docs/v2/03-business/entitlement/policy-rules.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/10-workspace-override.md` |
| `entitlement/11-trial-expiration` | `docs/v2/03-business/entitlement/trial-expiration.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/11-trial-expiration.md` |
| `entitlement/12-tier-downgrade` | `docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/12-tier-downgrade.md` |
| `entitlement/13-subscription-pause` | `docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/13-subscription-pause.md` |
| `entitlement/14-billing-cycle-switch` | `docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/14-billing-cycle-switch.md` |
| `entitlement/15-credits-lifecycle` | `docs/v2/03-business/entitlement/credits-lifecycle.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/15-credits-lifecycle.md` |
| `entitlement/16-renewal-reminders` | `docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/16-renewal-reminders.md` |
| `entitlement/17-invoice-management` | `docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/17-invoice-management.md` |
| `entitlement/18-refund-processing` | `docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/18-refund-processing.md` |
| `entitlement/19-promotions` | `docs/v2/03-business/entitlement/promotions.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/19-promotions.md` |
| `entitlement/20-referral-rewards` | `docs/v2/03-business/entitlement/referral-rewards.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/20-referral-rewards.md` |
| `entitlement/21-education-discount` | `docs/v2/03-business/entitlement/education-discount.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/21-education-discount.md` |
| `entitlement/22-free-quota` | `docs/v2/03-business/entitlement/marketing-programs.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/22-free-quota.md` |
| `entitlement/23-feature-sunset` | `docs/v2/03-business/entitlement/marketing-programs.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/23-feature-sunset.md` |
| `entitlement/24-conflict-resolution` | `docs/v2/03-business/entitlement/policy-rules.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/24-conflict-resolution.md` |
| `entitlement/25-future-scenarios` | `docs/v2/03-business/entitlement/marketing-programs.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/25-future-scenarios.md` |
| `entitlement/26-audit-checklist` | `docs/v2/03-business/entitlement/audits.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/26-audit-checklist.md` |
| `entitlement/27-audit-report-20260204` | `docs/v2/03-business/entitlement/audits.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/27-audit-report-20260204.md` |
| `entitlement/28-audit-supplement-20260204` | `docs/v2/03-business/entitlement/audits.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/28-audit-supplement-20260204.md` |
| `entitlement/implementation/README` | `docs/v2/03-business/entitlement/implementation-guide.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/implementation/README.md` |
| `entitlement/implementation/01-database-schema` | `docs/v2/03-business/entitlement/implementation-guide.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/implementation/01-database-schema.md` |
| `entitlement/implementation/02-backend-services` | `docs/v2/03-business/entitlement/implementation-guide.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/implementation/02-backend-services.md` |
| `entitlement/implementation/03-backend-repositories` | `docs/v2/03-business/entitlement/implementation-guide.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/implementation/03-backend-repositories.md` |
| `entitlement/implementation/04-backend-apis` | `docs/v2/03-business/entitlement/implementation-guide.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/implementation/04-backend-apis.md` |
| `entitlement/implementation/05-frontend-stores` | `docs/v2/03-business/entitlement/implementation-guide.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/implementation/05-frontend-stores.md` |
| `entitlement/implementation/06-frontend-components` | `docs/v2/03-business/entitlement/implementation-guide.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/implementation/06-frontend-components.md` |
| `entitlement/implementation/07-migration-scripts` | `docs/v2/03-business/entitlement/implementation-guide.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/entitlement/implementation/07-migration-scripts.md` |
| `feature-flag-design` | `docs/v2/02-standards/feature-flag/feature-flag-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/feature-flag-design.md` |
| `feature-flag-engine` | `docs/v2/02-standards/feature-flag/feature-flag-engine.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/feature-flag-engine.md` |
| `message-logging-standard` | `docs/v2/02-standards/logging-standard.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/message-logging-standard.md` |
| `project-implementation-plan` | `docs/v2/00-governance/project-implementation-plan.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/project-implementation-plan.md` |
| `system-refactoring-proposal-v2` | `docs/v2/01-architecture/system-refactoring-proposal-v2.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/system-refactoring-proposal-v2.md` |
| `self-hosted-auth-design` | `docs/v2/01-architecture/self-hosted-auth-design.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/self-hosted-auth-design.md` |
| `v3-refactoring-completion-report` | `docs/v2/00-governance/v3-refactoring-completion-report.md` | needs-review | Docs Working Group | 2026-02-04 | `docs/shared/v3-refactoring-completion-report.md` |
