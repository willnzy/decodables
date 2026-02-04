# 功能覆盖矩阵（可追溯）

> 用代码结构与旧文档双源对照，验证“完整、准确、合理”。

**状态**: active  
**版本**: 1.0.0  
**版本日期**: 2026-02-04  
**最后复核**: 2026-02-04  
**负责人**: Docs Working Group  
**适用范围**: backend  
**source_repo**: backend  
**sync_required**: yes  
**来源/依据**: `decodables-fe/app/`、`decodables-fe/app/admin/`、`decodables-fe/lib/config/`、`decodables/domains/`、`decodables/api/user/`、`decodables/api/admin/`

---

## 1. 证据来源清单

- 前端页面与 Admin：`decodables-fe/app/`、`decodables-fe/app/admin/`
- 前端配置系统：`decodables-fe/lib/config/`
- 后端能力域：`decodables/domains/`
- 后端 User API：`decodables/api/user/`
- 后端 Admin API：`decodables/api/admin/`

## 2. 页面清单（User / Admin）

| 页面 | 体验树归属 | 能力域归属 | 证据 |
|------|------------|------------|------|
| `/` 首页 | user-experience/dashboard | user-capabilities/dashboard | `decodables-fe/app/page.tsx` |
| `/create` 编辑器 | user-experience/editor | user-capabilities/editor | `decodables-fe/app/create/page.tsx` |
| `/dashboard` | user-experience/dashboard | user-capabilities/dashboard | `decodables-fe/app/dashboard/` |
| `/marketplace` | user-experience/marketplace | user-capabilities/marketplace | `decodables-fe/app/marketplace/` |
| `/profile` | user-experience/profile | user-capabilities/account | `decodables-fe/app/profile/page.tsx` |
| `/transaction-history` | user-experience/profile | user-capabilities/billing | `decodables-fe/app/transaction-history/page.tsx` |
| `/notifications` | user-experience/dashboard | user-capabilities/notifications | `decodables-fe/app/notifications/page.tsx` |
| `/manual` | user-experience/dashboard | user-capabilities/content-consumption | `decodables-fe/app/manual/` |
| `/manual/[slug]` | user-experience/dashboard | user-capabilities/content-consumption + user-capabilities/sharing | `decodables-fe/app/manual/[slug]/page.tsx` |
| `/news` | user-experience/dashboard | user-capabilities/content-consumption | `decodables-fe/app/news/` |
| `/news/[slug]` | user-experience/dashboard | user-capabilities/content-consumption + user-capabilities/sharing | `decodables-fe/app/news/[slug]/page.tsx` |
| `/about-us` | user-experience/dashboard | user-capabilities/content-consumption | `decodables-fe/app/about-us/` |
| `/contact-us` | user-experience/dashboard | user-capabilities/content-consumption | `decodables-fe/app/contact-us/` |
| `/privacy-policy` | user-experience/dashboard | user-capabilities/content-consumption | `decodables-fe/app/privacy-policy/` |
| `/terms-of-service` | user-experience/dashboard | user-capabilities/content-consumption | `decodables-fe/app/terms-of-service/` |
| `/billing-policy` | user-experience/dashboard | user-capabilities/content-consumption | `decodables-fe/app/billing-policy/` |
| `/marketplace-guidelines` | user-experience/marketplace | user-capabilities/content-consumption | `decodables-fe/app/marketplace-guidelines/` |
| `/login` | user-experience/account | user-capabilities/auth | `decodables-fe/app/(auth)/login/` |
| `/register` | user-experience/account | user-capabilities/auth | `decodables-fe/app/(auth)/register/` |
| `/forgot-password` | user-experience/account | user-capabilities/auth | `decodables-fe/app/(auth)/forgot-password/` |
| `/reset-password` | user-experience/account | user-capabilities/auth | `decodables-fe/app/(auth)/reset-password/` |
| `/verify-email` | user-experience/account | user-capabilities/auth | `decodables-fe/app/(auth)/verify-email/` |
| `/admin` | admin-experience/admin-dashboard | admin-capabilities/admin-console | `decodables-fe/app/admin/page.tsx` |
| `/admin/users` | admin-experience/admin-dashboard | admin-capabilities/user-ops | `decodables-fe/app/admin/users/` |
| `/admin/moderation` | admin-experience/admin-dashboard | admin-capabilities/moderation | `decodables-fe/app/admin/moderation/` |
| `/admin/articles` | admin-experience/content-management | admin-capabilities/content-ops | `decodables-fe/app/admin/articles/` |
| `/admin/marketing` | admin-experience/marketing-ops | admin-capabilities/marketing-ops | `decodables-fe/app/admin/marketing/` |
| `/admin/configs` | admin-experience/config-management | admin-capabilities/config-ops | `decodables-fe/app/admin/configs/` |
| `/admin/analytics` | admin-experience/analytics-ops | admin-capabilities/analytics-ops | `decodables-fe/app/admin/analytics/` |
| `/admin/themes` | admin-experience/content-management | admin-capabilities/content-ops | `decodables-fe/app/admin/themes/` |
| `/admin/operations` | admin-experience/admin-dashboard | admin-capabilities/system-ops | `decodables-fe/app/admin/operations/` |
| `/admin/content` | admin-experience/content-management | admin-capabilities/content-ops | `decodables-fe/app/admin/content/` |

> 说明：页面体验默认覆盖 PC/Mobile；若出现独立移动端页面，将在此表拆分记录。

## 3. 能力清单（User）

| 能力域 | 子域 | 证据 |
|--------|------|------|
| user-capabilities/editor | canvas | `decodables-fe/app/create/_components/canvas/`, `decodables-fe/app/create/_hooks/canvas/` |
| user-capabilities/editor | media-library | `decodables-fe/app/create/_components/media/` |
| user-capabilities/editor | drawing | `decodables-fe/app/create/_components/drawing/` |
| user-capabilities/editor | import | `decodables-fe/app/create/_components/import/` |
| user-capabilities/editor | crop | `decodables-fe/app/create/_hooks/useImageCropper.ts` |
| user-capabilities/editor | export | `decodables-fe/app/create/_hooks/editor/useEditorExport.ts` |
| user-capabilities/editor | smart-scan | `decodables-fe/app/create/_components/scan/SmartScanDialog.tsx` |
| user-capabilities/editor | ai-page-gen | `decodables-fe/app/create/_hooks/ai/useAIPageGeneration.ts` |
| user-capabilities/editor | ai-image-gen | `decodables-fe/app/create/_hooks/ai/useAIGeneration.ts` |
| user-capabilities/workspace | workspace-core | `decodables/domains/workspace/`, `decodables-fe/app/dashboard/_hooks/useWorkspace.ts` |
| user-capabilities/workspace | invitations | `decodables/domains/workspace/member_service.py`, `decodables-fe/app/dashboard/_hooks/useInvitations.ts` |
| user-capabilities/content-organization | folders | `decodables/domains/folder/`, `decodables-fe/app/dashboard/_hooks/useFolders.ts` |
| user-capabilities/content-organization | trash | `decodables-fe/app/dashboard/_components/sections/TrashSection.tsx` |
| user-capabilities/content-organization | recovery | `decodables/domains/creation/locked_elements.py` |
| user-capabilities/marketplace | listings | `decodables/domains/marketplace/` |
| user-capabilities/marketplace | reporting | `decodables-fe/components/marketplace/ListingCard.tsx`, `decodables-fe/components/marketplace/ReportDialog.tsx` |
| user-capabilities/marketplace | transactions | `decodables/domains/billing/` |
| user-capabilities/dashboard | overview | `decodables-fe/app/dashboard/` |
| user-capabilities/projects | create-project | `decodables-fe/app/create/_hooks/editor/useEditorProject.ts`, `decodables-fe/app/create/_hooks/ai/useAIGeneration.ts` |
| user-capabilities/assets | upload-assets | `decodables-fe/app/create/_components/media/custom/CustomAssets.tsx` |
| user-capabilities/notifications | notifications | `decodables-fe/app/notifications/page.tsx` |
| user-capabilities/billing | transaction-history | `decodables-fe/app/transaction-history/page.tsx` |
| user-capabilities/support | help-center | `decodables-fe/components/common/SupportButton.tsx` |
| user-capabilities/cta | floating-cta | `decodables-fe/components/common/FloatingCTA.tsx`, `decodables-fe/app/_components/landing/CTAButton.tsx` |
| user-capabilities/account | profile | `decodables/domains/identity/` |
| user-capabilities/account | auth | `decodables/domains/auth/` |
| user-capabilities/billing | subscriptions | `decodables/domains/subscriptions/` |
| user-capabilities/analytics | user-events | `decodables/domains/events/` |
| user-capabilities/assets | assets | `decodables/domains/assets/` |
| user-capabilities/sharing | articles-share | `decodables-fe/components/articles/ShareButtons.tsx` |
| user-capabilities/ui-system | toast | `decodables-fe/components/common/Toast.tsx`, `decodables-fe/components/GlobalProviders.tsx` |
| user-capabilities/ui-system | modal | `decodables-fe/components/ui/dialog.tsx`, `decodables-fe/components/GlobalProviders.tsx` |
| user-capabilities/templates | templates | `decodables/domains/templates/` |
| user-capabilities/themes | themes | `decodables/domains/themes/` |
| user-capabilities/themes | holiday-decor | `decodables-fe/components/holiday/HolidayProvider.tsx`, `decodables-fe/components/holiday/HolidayBanner.tsx`, `decodables/domains/themes/` |
| user-capabilities/tools | tools | `decodables/domains/tools/` |
| user-capabilities/generation | ai-generation | `decodables/domains/generation/` |
| user-capabilities/export | export | `decodables/domains/export/` |
| user-capabilities/search | search-filter | `decodables-fe/app/marketplace/_hooks/useMarketplaceFilters.ts` |
| user-capabilities/content-consumption | articles | `decodables/domains/articles/`, `decodables-fe/app/news/` |
| user-capabilities/content-consumption | manuals | `decodables-fe/app/manual/` |
| user-capabilities/content-consumption | static-pages | `decodables/domains/static_pages/` |
| user-capabilities/onboarding | onboarding | `decodables/domains/onboarding/` |
| user-capabilities/referrals | referrals | `decodables/domains/referrals/` |
| user-capabilities/support | support | `decodables/domains/support/`, `decodables-fe/components/common/SupportButton.tsx` |
| user-capabilities/notifications | notifications | `decodables/domains/platform/notifications/`, `decodables-fe/app/notifications/page.tsx` |
| user-capabilities/tags | tagging | `decodables/domains/tag/` |
| user-capabilities/resources | system-resources | `decodables-fe/hooks/useResources.ts`, `decodables-fe/services/resourceService.ts`, `decodables/api/user/resources.py`, `decodables/api/user/system_resources.py` |
| user-capabilities/auth | sessions-tokens | `decodables/domains/auth/service.py`, `decodables/domains/auth/token_service.py` |
| user-capabilities/security | rate-limiting | `decodables/infrastructure/rate_limiter.py` |
| user-capabilities/webhooks | stripe-webhooks | `decodables/api/user/webhooks.py`, `decodables/domains/webhooks/stripe_webhook_service.py` |
| user-capabilities/auth | session-repository | `decodables/infrastructure/repositories/session_repository.py` |
| user-capabilities/auth | auth-user-repository | `decodables/infrastructure/repositories/auth_user_repository.py` |
| user-capabilities/billing | billing-api | `decodables/api/user/billing.py`, `decodables/api/user/payment.py`, `decodables/infrastructure/repositories/payment_repository.py` |
| user-capabilities/workspace | workspace-api | `decodables/api/user/workspaces.py`, `decodables/api/user/workspace_invitations.py`, `decodables/api/user/workspace_members.py` |
| user-capabilities/content-organization | folders-api | `decodables/api/user/folders.py` |
| user-capabilities/assets | user-assets-api | `decodables/api/user/user_assets.py` |
| user-capabilities/marketplace | marketplace-api | `decodables/api/user/marketplace.py`, `decodables/api/user/seller.py` |
| user-capabilities/projects | projects-api | `decodables/api/user/projects.py` |
| user-capabilities/tags | tags-api | `decodables/api/user/tags.py` |
| user-capabilities/resources | resources-api | `decodables/api/user/resources.py` |
| user-capabilities/generation | generations-api | `decodables/api/user/generations.py`, `decodables/api/user/generation_images.py`, `decodables/api/user/generation_story.py`, `decodables/api/user/generation_pdf.py` |
| user-capabilities/templates | templates-api | `decodables/api/user/templates.py` |
| user-capabilities/tools | tools-api | `decodables/api/user/tools.py` |
| user-capabilities/analytics | analytics-api | `decodables/api/user/analytics.py` |
| user-capabilities/support | support-api | `decodables/api/user/support.py` |
| user-capabilities/account | profile-api | `decodables/api/user/user_profile.py` |
| user-capabilities/articles | articles-api | `decodables/api/user/articles.py` |
| user-capabilities/static-pages | static-pages-api | `decodables/api/user/static_pages.py` |
| user-capabilities/themes | themes-api | `decodables/api/user/themes.py` |
| user-capabilities/experiments | experiments-api | `decodables/api/user/experiments.py` |
| user-capabilities/tasks | tasks-api | `decodables/api/user/tasks.py` |
| user-capabilities/logs | logs-api | `decodables/api/user/logs.py` |
| user-capabilities/export | export-api | `decodables/api/user/export.py` |
| user-capabilities/config | config-api | `decodables/api/user/config.py` |
| user-capabilities/campaigns | campaigns-api | `decodables/api/user/campaigns.py` |
| user-capabilities/referrals | referrals-api | `decodables/api/user/referrals.py` |
| user-capabilities/onboarding | onboarding-api | `decodables/api/user/onboarding.py` |

## 4. 能力清单（Admin）

| 能力域 | 子域 | 证据 |
|--------|------|------|
| admin-capabilities/admin-console | admin-dashboard | `decodables-fe/app/admin/page.tsx` |
| admin-capabilities/user-ops | users | `decodables-fe/app/admin/users/`, `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | users-search | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | users-by-tier | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | user-audit | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | user-credits | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | user-tier-update | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | user-discount | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | user-payments | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | user-projects | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | user-asset-usage | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | user-env-stats | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | projects-restore | `decodables/api/admin/users.py` |
| admin-capabilities/user-ops | projects-feed | `decodables/api/admin/users.py` |
| admin-capabilities/moderation | content-reports | `decodables-fe/app/admin/moderation/`, `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | marketplace-list | `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | marketplace-detail | `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | marketplace-approve | `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | marketplace-reject | `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | marketplace-delete | `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | marketplace-unpublish | `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | reports-list | `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | reports-stats | `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | reports-detail | `decodables/api/admin/moderation.py` |
| admin-capabilities/moderation | reports-respond | `decodables/api/admin/moderation.py` |
| admin-capabilities/content-ops | articles | `decodables-fe/app/admin/articles/`, `decodables/api/admin/articles.py` |
| admin-capabilities/content-ops | articles-list | `decodables/api/admin/articles.py` |
| admin-capabilities/content-ops | articles-get | `decodables/api/admin/articles.py` |
| admin-capabilities/content-ops | articles-create | `decodables/api/admin/articles.py` |
| admin-capabilities/content-ops | articles-update | `decodables/api/admin/articles.py` |
| admin-capabilities/content-ops | articles-delete | `decodables/api/admin/articles.py` |
| admin-capabilities/content-ops | articles-publish | `decodables/api/admin/articles.py` |
| admin-capabilities/content-ops | articles-unpublish | `decodables/api/admin/articles.py` |
| admin-capabilities/content-ops | static-pages | `decodables-fe/app/admin/content/`, `decodables/api/admin/static_pages.py` |
| admin-capabilities/content-ops | static-pages-list | `decodables/api/admin/static_pages.py` |
| admin-capabilities/content-ops | static-pages-get | `decodables/api/admin/static_pages.py` |
| admin-capabilities/content-ops | static-pages-create | `decodables/api/admin/static_pages.py` |
| admin-capabilities/content-ops | static-pages-update | `decodables/api/admin/static_pages.py` |
| admin-capabilities/content-ops | static-pages-delete | `decodables/api/admin/static_pages.py` |
| admin-capabilities/content-ops | static-pages-publish | `decodables/api/admin/static_pages.py` |
| admin-capabilities/content-ops | static-pages-unpublish | `decodables/api/admin/static_pages.py` |
| admin-capabilities/content-ops | themes | `decodables-fe/app/admin/themes/`, `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-list | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-get | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-create | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-update | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-delete | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-batch-generate | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-generation-status | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-calendar | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-review | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-regenerate | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-history | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-batch-approve | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | themes-review-pending | `decodables/api/admin/themes.py` |
| admin-capabilities/content-ops | asset-categories | `decodables-fe/app/admin/content/`, `decodables/api/admin/asset_categories.py` |
| admin-capabilities/content-ops | asset-categories-list | `decodables/api/admin/asset_categories.py` |
| admin-capabilities/content-ops | asset-categories-tree | `decodables/api/admin/asset_categories.py` |
| admin-capabilities/content-ops | asset-categories-create | `decodables/api/admin/asset_categories.py` |
| admin-capabilities/content-ops | asset-categories-update | `decodables/api/admin/asset_categories.py` |
| admin-capabilities/content-ops | asset-categories-move | `decodables/api/admin/asset_categories.py` |
| admin-capabilities/content-ops | asset-categories-delete | `decodables/api/admin/asset_categories.py` |
| admin-capabilities/content-ops | asset-categories-resources | `decodables/api/admin/asset_categories.py` |
| admin-capabilities/marketing-ops | campaigns | `decodables-fe/app/admin/marketing/`, `decodables/api/admin/campaigns.py` |
| admin-capabilities/marketing-ops | campaigns-list | `decodables/api/admin/campaigns.py` |
| admin-capabilities/marketing-ops | campaigns-get | `decodables/api/admin/campaigns.py` |
| admin-capabilities/marketing-ops | campaigns-create | `decodables/api/admin/campaigns.py` |
| admin-capabilities/marketing-ops | campaigns-update | `decodables/api/admin/campaigns.py` |
| admin-capabilities/marketing-ops | campaigns-delete | `decodables/api/admin/campaigns.py` |
| admin-capabilities/marketing-ops | campaigns-activate | `decodables/api/admin/campaigns.py` |
| admin-capabilities/marketing-ops | campaigns-pause | `decodables/api/admin/campaigns.py` |
| admin-capabilities/marketing-ops | campaigns-stats | `decodables/api/admin/campaigns.py` |
| admin-capabilities/marketing-ops | experiments | `decodables-fe/app/admin/marketing/`, `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-admin | `decodables-fe/app/admin/marketing/_hooks/useExperiments.ts` |
| admin-capabilities/marketing-ops | experiments-list | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-create | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-get | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-update | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-delete | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-status | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-results | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-aggregate | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-aggregate-all | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-cache-clear | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-ai-analysis | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-quick-recommendation | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-daily-trend | `decodables/api/admin/experiments.py` |
| admin-capabilities/marketing-ops | experiments-hourly-trend | `decodables/api/admin/experiments.py` |
| admin-capabilities/config-ops | system-configs | `decodables-fe/app/admin/configs/`, `decodables/api/admin/config.py` |
| admin-capabilities/config-ops | tier-config | `decodables-fe/app/admin/configs/`, `decodables/api/admin/tiers.py` |
| admin-capabilities/config-ops | feature-flags | `decodables-fe/app/admin/configs/`, `decodables/api/admin/feature_flags.py` |
| admin-capabilities/config-ops | feature-flags-admin | `decodables-fe/app/admin/configs/_hooks/useFeatureFlags.ts` |
| admin-capabilities/config-ops | feature-flags-client | `decodables/api/admin/feature_flags.py` |
| admin-capabilities/config-ops | feature-flags-audit | `decodables/api/admin/feature_flags.py` |
| admin-capabilities/config-ops | feature-flags-evaluation | `decodables/api/admin/feature_flags.py` |
| admin-capabilities/config-ops | rate-limits-api | `decodables/api/admin/config.py` |
| admin-capabilities/config-ops | rate-limits-presets | `decodables/api/admin/config.py` |
| admin-capabilities/config-ops | config-cache | `decodables/api/admin/config.py` |
| admin-capabilities/analytics-ops | stats | `decodables-fe/app/admin/analytics/`, `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | metrics | `decodables-fe/app/admin/analytics/`, `decodables/api/admin/metrics.py` |
| admin-capabilities/analytics-ops | events | `decodables-fe/app/admin/analytics/`, `decodables/api/admin/events.py` |
| admin-capabilities/analytics-ops | ai-insights | `decodables-fe/app/admin/analytics/`, `decodables/api/admin/ai.py` |
| admin-capabilities/analytics-ops | metrics-daily | `decodables/api/admin/metrics.py` |
| admin-capabilities/analytics-ops | metrics-monthly | `decodables/api/admin/metrics.py` |
| admin-capabilities/analytics-ops | metrics-retention | `decodables/api/admin/metrics.py` |
| admin-capabilities/analytics-ops | metrics-funnel | `decodables/api/admin/metrics.py` |
| admin-capabilities/analytics-ops | metrics-errors | `decodables/api/admin/metrics.py` |
| admin-capabilities/analytics-ops | metrics-dau-trend | `decodables/api/admin/metrics.py` |
| admin-capabilities/analytics-ops | metrics-refresh | `decodables/api/admin/metrics.py` |
| admin-capabilities/analytics-ops | stats-dashboard | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-user-growth | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-revenue | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-projects | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-credits | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-tier-distribution | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-conversion-funnel | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-exports | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-assets | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-tier-activity | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-subscription-events | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-page-views | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-project-details | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-returning-users | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-tier-trend | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-tier-conversion | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-performance | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | stats-user-distribution | `decodables/api/admin/stats.py` |
| admin-capabilities/analytics-ops | events-user-events | `decodables/api/admin/events.py` |
| admin-capabilities/analytics-ops | events-stats | `decodables/api/admin/events.py` |
| admin-capabilities/analytics-ops | events-aggregated | `decodables/api/admin/events.py` |
| admin-capabilities/analytics-ops | events-aggregated-range | `decodables/api/admin/events.py` |
| admin-capabilities/analytics-ops | events-aggregation-run | `decodables/api/admin/events.py` |
| admin-capabilities/analytics-ops | ai-recommendations | `decodables/api/admin/ai.py` |
| admin-capabilities/analytics-ops | behavior-analysis | `decodables/api/admin/ai.py` |
| admin-capabilities/analytics-ops | ai-generate-report | `decodables/api/admin/ai.py` |
| admin-capabilities/analytics-ops | ai-quick-insights | `decodables/api/admin/ai.py` |
| admin-capabilities/system-ops | logs | `decodables-fe/app/admin/operations/`, `decodables/api/admin/logs.py` |
| admin-capabilities/system-ops | notifications | `decodables-fe/app/admin/operations/`, `decodables/api/admin/notifications.py` |
| admin-capabilities/system-ops | tasks | `decodables-fe/app/admin/operations/`, `decodables/api/admin/tasks_mgmt.py` |
| admin-capabilities/system-ops | webhooks-retry | `decodables-fe/app/admin/operations/`, `decodables/api/admin/webhooks_retry.py` |
| admin-capabilities/system-ops | system-api | `decodables/api/admin/system.py` |
| admin-capabilities/system-ops | tasks-status-api | `decodables/api/admin/tasks_mgmt.py` |
| admin-capabilities/system-ops | tasks-logs-api | `decodables/api/admin/tasks_mgmt.py` |
| admin-capabilities/system-ops | tasks-health-api | `decodables/api/admin/tasks_mgmt.py` |
| admin-capabilities/system-ops | tasks-run-api | `decodables/api/admin/tasks_mgmt.py` |
| admin-capabilities/system-ops | webhooks-retry-api | `decodables/api/admin/webhooks_retry.py` |
| admin-capabilities/system-ops | webhooks-failed-api | `decodables/api/admin/webhooks_retry.py` |
| admin-capabilities/system-ops | system-configs-api | `decodables/api/admin/system.py` |
| admin-capabilities/system-ops | system-configs-audit | `decodables/api/admin/system.py` |
| admin-capabilities/system-ops | system-cache-status | `decodables/api/admin/system.py` |
| admin-capabilities/system-ops | system-cache-keys | `decodables/api/admin/system.py` |
| admin-capabilities/system-ops | system-cache-clear | `decodables/api/admin/system.py` |
| admin-capabilities/system-ops | webhooks-retry-ui | `decodables-fe/app/admin/operations/_components/WebhookRetryPanel.tsx` |
| admin-capabilities/system-ops | user-creation-monitoring | `decodables-fe/app/admin/operations/`, `decodables/api/admin/user_creation_monitoring.py` |
| admin-capabilities/system-ops | user-creation-stats | `decodables/api/admin/user_creation_monitoring.py` |
| admin-capabilities/system-ops | user-creation-health | `decodables/api/admin/user_creation_monitoring.py` |
| admin-capabilities/system-ops | user-creation-events | `decodables/api/admin/user_creation_monitoring.py` |
| admin-capabilities/system-ops | user-creation-recent | `decodables/api/admin/user_creation_monitoring.py` |
| admin-capabilities/system-ops | user-creation-trends | `decodables/api/admin/user_creation_monitoring.py` |
| admin-capabilities/ai-ops | ai-models | `decodables/api/admin/ai_models.py` |
| admin-capabilities/ai-ops | ai-models-config | `decodables/api/admin/ai_models.py` |
| admin-capabilities/ai-ops | ai-models-providers | `decodables/api/admin/ai_models.py` |
| admin-capabilities/ai-ops | ai-models-usage | `decodables/api/admin/ai_models.py` |
| admin-capabilities/ai-ops | ai-models-cache | `decodables/api/admin/ai_models.py` |
| admin-capabilities/analytics-ops | events-ui | `decodables-fe/app/admin/analytics/_hooks/useEvents.ts` |
| admin-capabilities/analytics-ops | metrics-ui | `decodables-fe/app/admin/analytics/_hooks/useMetrics.ts` |
| admin-capabilities/analytics-ops | stats-ui | `decodables-fe/app/admin/analytics/_hooks/useStats.ts` |
| admin-capabilities/analytics-ops | ai-insights-ui | `decodables-fe/app/admin/analytics/_hooks/useAI.ts` |
| admin-capabilities/system-ops | operation-logs | `decodables-fe/app/admin/_hooks/useOperationLogs.ts` |
| admin-capabilities/system-ops | error-logs | `decodables-fe/app/admin/_hooks/useErrorLogs.ts` |
| admin-capabilities/system-ops | task-monitoring | `decodables-fe/app/admin/_hooks/useTaskStatus.ts` |
| admin-capabilities/system-ops | operation-logs-api | `decodables/api/admin/logs.py` |
| admin-capabilities/system-ops | error-logs-api | `decodables/api/admin/logs.py` |
| admin-capabilities/system-ops | audit-logs-api | `decodables/api/admin/logs.py` |
| admin-capabilities/analytics-ops | ai-reports | `decodables/application/services/ai_reports/` |
| admin-capabilities/analytics-ops | analytics-service | `decodables/domains/analytics/service.py` |
| admin-capabilities/analytics-ops | events-service | `decodables/domains/events/service.py` |
| admin-capabilities/analytics-ops | stats-domain | `decodables/domains/stats/` |
| admin-capabilities/system-ops | maintenance-scheduler | `decodables/infrastructure/tasks/maintenance_scheduler.py` |
| admin-capabilities/system-ops | audit-logging | `decodables/infrastructure/logging/activity_logger.py`, `decodables/infrastructure/repositories/activity_log_repository.py` |
| admin-capabilities/notifications-ops | templates | `decodables/domains/platform/aggregates/notification_template.py`, `decodables/infrastructure/repositories/notification_template_repository.py` |
| admin-capabilities/notifications-ops | api-endpoints | `decodables/api/admin/notifications.py` |
| admin-capabilities/system-resources-ops | admin-crud | `decodables/infrastructure/repositories/system_resources_admin_repository.py` |
| admin-capabilities/system-resources-ops | system-resources-api | `decodables/api/user/system_resources.py` |
| admin-capabilities/content-ops | content-repository | `decodables/infrastructure/repositories/content_repository.py` |
| admin-capabilities/content-ops | category-repository | `decodables/infrastructure/repositories/category_repository.py` |
| admin-capabilities/billing-ops | subscription-repository | `decodables/infrastructure/repositories/subscription_repository.py` |
| admin-capabilities/billing-ops | payment-repository | `decodables/infrastructure/repositories/payment_repository.py` |
| admin-capabilities/billing-ops | subscriptions-api | `decodables/api/admin/subscriptions.py` |
| admin-capabilities/billing-ops | subscriptions-refund | `decodables/api/admin/subscriptions.py` |
| admin-capabilities/billing-ops | subscriptions-cancel | `decodables/api/admin/subscriptions.py` |
| admin-capabilities/billing-ops | subscriptions-downgrade | `decodables/api/admin/subscriptions.py` |
| admin-capabilities/system-ops | webhooks-repo | `decodables/infrastructure/repositories/webhook_repository.py` |
| admin-capabilities/system-ops | tasks-repository | `decodables/infrastructure/repositories/tasks_repository.py` |

## 5. 页面 → 能力映射（关键路径）

| 页面 | 能力域 |
|------|--------|
| `/create` | user-capabilities/editor (canvas/media/import/drawing/crop/export/smart-scan/ai) + user-capabilities/projects |
| `/dashboard` | user-capabilities/dashboard + content-organization (folders/trash) + workspace + assets |
| `/transaction-history` | user-capabilities/billing (transaction-history) |
| `/notifications` | user-capabilities/notifications |
| `/marketplace` | user-capabilities/marketplace + assets + reporting |
| `/profile` | user-capabilities/account + billing |
| `/admin` | admin-capabilities/admin-console |
| `/admin/users` | admin-capabilities/user-ops |
| `/admin/moderation` | admin-capabilities/moderation |
| `/admin/marketing` | admin-capabilities/marketing-ops |
| `/admin/articles` | admin-capabilities/content-ops |
| `/admin/themes` | admin-capabilities/content-ops |
| `/admin/configs` | admin-capabilities/config-ops |
| `/admin/analytics` | admin-capabilities/analytics-ops |
| `/admin/content` | admin-capabilities/content-ops |
| `/admin/operations` | admin-capabilities/system-ops |

## 6. 旧文档 → 新归属映射

| 旧文档 | 新归属 | 处理状态 |
|--------|--------|----------|
| `decodables-fe/docs/main/canvas-architecture-design.md` | `decodables-fe/docs/v2/04-features/canvas-architecture.md` | done |
| `decodables-fe/docs/main/editor-media-properties-redesign.md` | `decodables-fe/docs/v2/04-features/editor-media-properties.md` | done |
| `decodables-fe/docs/main/file-import-support-design.md` | `decodables-fe/docs/v2/04-features/file-import-support.md` | done |
| `decodables-fe/docs/main/image-crop-solution-design.md` | `decodables-fe/docs/v2/04-features/image-crop-solution.md` | done |
| `decodables-fe/docs/main/text-font-solution-design.md` | `decodables-fe/docs/v2/04-features/text-font-solution.md` | needs-review |
| `decodables-fe/docs/main/make-decodables-design-system.md` | `decodables-fe/docs/v2/02-standards/design-system.md` | needs-review |
| `decodables-fe/docs/main/Mobile-Profile-Page-Design.md` | `decodables-fe/docs/v2/04-features/mobile-profile-page-design.md` | done |
| `decodables-fe/docs/main/v3-spec-overview.md` | `decodables-fe/docs/v2/04-features/v3-spec-overview.md` | done |
| `decodables-fe/docs/main/frontend-architecture-audit-v1.md` | `decodables-fe/docs/v2/01-architecture/frontend-architecture-audit.md` | needs-review |
| `decodables-fe/docs/main/frontend-development-guide.md` | `decodables-fe/docs/v2/02-standards/frontend-development-guide.md` | needs-review |
| `decodables-fe/docs/main/integration-testing-guide.md` | `decodables-fe/docs/v2/02-standards/integration-testing-guide.md` | needs-review |
| `decodables-fe/docs/main/responsive-design-guide.md` | `decodables-fe/docs/v2/02-standards/responsive-design-guide.md` | needs-review |
| `decodables-fe/docs/main/top-bar-height-management.md` | `decodables-fe/docs/v2/02-standards/top-bar-height-management.md` | needs-review |
| `decodables-fe/docs/main/ui-navigation-design.md` | `decodables-fe/docs/v2/02-standards/ui-navigation-design.md` | needs-review |
| `decodables-fe/docs/main/README.md` | `decodables-fe/docs/v2/README.md` | done |
| `decodables-fe/docs/shared/README.md` | `decodables-fe/docs/v2/09-reference/shared-docs-registry.md` | needs-review |
| `decodables-fe/docs/shared/admin-api-review.md` | `decodables-fe/docs/v2/05-api/admin-api-review.md` | needs-review |
| `decodables-fe/docs/shared/user-api-review.md` | `decodables-fe/docs/v2/05-api/user-api-review.md` | needs-review |
| `decodables-fe/docs/shared/analytics-system-design.md` | `decodables-fe/docs/v2/04-features/admin-capabilities/analytics-system-design.md` | needs-review |
| `decodables-fe/docs/shared/articles-system-design.md` | `decodables-fe/docs/v2/04-features/admin-capabilities/articles-system-design.md` | needs-review |
| `decodables-fe/docs/shared/asset-category-design.md` | `decodables-fe/docs/v2/04-features/admin-capabilities/asset-category-design.md` | needs-review |
| `decodables-fe/docs/shared/static-pages-cms-design.md` | `decodables-fe/docs/v2/04-features/admin-capabilities/static-pages-cms-design.md` | needs-review |
| `decodables-fe/docs/shared/onboarding-design.md` | `decodables-fe/docs/v2/04-features/user-capabilities/onboarding-design.md` | needs-review |
| `decodables-fe/docs/shared/theme-system-design.md` | `decodables-fe/docs/v2/04-features/user-capabilities/theme-system-design.md` | needs-review |
| `decodables-fe/docs/shared/canvas-data-schema.md` | `decodables-fe/docs/v2/03-business/canvas-data-schema.md` | needs-review |
| `decodables-fe/docs/shared/pricing-system-design.md` | `decodables-fe/docs/v2/03-business/pricing-system.md` | needs-review |
| `decodables-fe/docs/shared/tier-naming-system.md` | `decodables-fe/docs/v2/03-business/tier-naming-system.md` | needs-review |
| `decodables-fe/docs/shared/tier-permissions.md` | `decodables-fe/docs/v2/03-business/entitlement/permission-matrix.md` | needs-review |
| `decodables-fe/docs/shared/user-id-system.md` | `decodables-fe/docs/v2/03-business/user-id-system.md` | needs-review |
| `decodables-fe/docs/shared/entitlement-system-design.md` | `decodables-fe/docs/v2/03-business/entitlement/system-design.md` | needs-review |
| `decodables-fe/docs/shared/entitlement-permission-matrix.md` | `decodables-fe/docs/v2/03-business/entitlement/permission-matrix.md` | needs-review |
| `decodables-fe/docs/shared/entitlement-ui-spec.md` | `decodables-fe/docs/v2/03-business/entitlement/ui-spec.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/README.md` | `decodables-fe/docs/v2/03-business/entitlement/README.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/01-permission-matrix-appendix.md` | `decodables-fe/docs/v2/03-business/entitlement/permission-matrix-appendix.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/01-permission-matrix.md` | `decodables-fe/docs/v2/03-business/entitlement/permission-matrix.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/02-tier-config.md` | `decodables-fe/docs/v2/03-business/entitlement/tier-config.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/03-system-design.md` | `decodables-fe/docs/v2/03-business/entitlement/system-design.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/04-feature-flag-engine.md` | `decodables-fe/docs/v2/03-business/entitlement/feature-flag-engine.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/05-ui-spec.md` | `decodables-fe/docs/v2/03-business/entitlement/ui-spec.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/06-priority-rules.md` | `decodables-fe/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/07-tier-inheritance.md` | `decodables-fe/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/08-user-groups.md` | `decodables-fe/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/09-config-versioning.md` | `decodables-fe/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/10-workspace-override.md` | `decodables-fe/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/11-trial-expiration.md` | `decodables-fe/docs/v2/03-business/entitlement/trial-expiration.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/12-tier-downgrade.md` | `decodables-fe/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/13-subscription-pause.md` | `decodables-fe/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/14-billing-cycle-switch.md` | `decodables-fe/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/15-credits-lifecycle.md` | `decodables-fe/docs/v2/03-business/entitlement/credits-lifecycle.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/16-renewal-reminders.md` | `decodables-fe/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/17-invoice-management.md` | `decodables-fe/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/18-refund-processing.md` | `decodables-fe/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/19-promotions.md` | `decodables-fe/docs/v2/03-business/entitlement/promotions.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/20-referral-rewards.md` | `decodables-fe/docs/v2/03-business/entitlement/referral-rewards.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/21-education-discount.md` | `decodables-fe/docs/v2/03-business/entitlement/education-discount.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/22-free-quota.md` | `decodables-fe/docs/v2/03-business/entitlement/marketing-programs.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/23-feature-sunset.md` | `decodables-fe/docs/v2/03-business/entitlement/marketing-programs.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/24-conflict-resolution.md` | `decodables-fe/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/25-future-scenarios.md` | `decodables-fe/docs/v2/03-business/entitlement/marketing-programs.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/26-audit-checklist.md` | `decodables-fe/docs/v2/03-business/entitlement/audits.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/27-audit-report-20260204.md` | `decodables-fe/docs/v2/03-business/entitlement/audits.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/28-audit-supplement-20260204.md` | `decodables-fe/docs/v2/03-business/entitlement/audits.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/implementation/README.md` | `decodables-fe/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/implementation/01-database-schema.md` | `decodables-fe/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/implementation/02-backend-services.md` | `decodables-fe/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/implementation/03-backend-repositories.md` | `decodables-fe/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/implementation/04-backend-apis.md` | `decodables-fe/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/implementation/05-frontend-stores.md` | `decodables-fe/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/implementation/06-frontend-components.md` | `decodables-fe/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables-fe/docs/shared/entitlement/implementation/07-migration-scripts.md` | `decodables-fe/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables-fe/docs/shared/feature-flag-design.md` | `decodables-fe/docs/v2/02-standards/feature-flag/feature-flag-design.md` | needs-review |
| `decodables-fe/docs/shared/feature-flag-engine.md` | `decodables-fe/docs/v2/02-standards/feature-flag/feature-flag-engine.md` | needs-review |
| `decodables-fe/docs/shared/message-logging-standard.md` | `decodables-fe/docs/v2/02-standards/logging-standard.md` | needs-review |
| `decodables-fe/docs/shared/project-implementation-plan.md` | `decodables-fe/docs/v2/00-governance/project-implementation-plan.md` | needs-review |
| `decodables-fe/docs/shared/system-refactoring-proposal-v2.md` | `decodables-fe/docs/v2/01-architecture/system-refactoring-proposal-v2.md` | needs-review |
| `decodables-fe/docs/shared/self-hosted-auth-design.md` | `decodables-fe/docs/v2/01-architecture/self-hosted-auth-design.md` | needs-review |
| `decodables-fe/docs/shared/v3-refactoring-completion-report.md` | `decodables-fe/docs/v2/00-governance/v3-refactoring-completion-report.md` | needs-review |
| `decodables/docs/shared/README.md` | `decodables/docs/v2/09-reference/shared-docs-registry.md` | needs-review |
| `decodables/docs/shared/admin-api-review.md` | `decodables/docs/v2/05-api/admin-api-review.md` | needs-review |
| `decodables/docs/shared/user-api-review.md` | `decodables/docs/v2/05-api/user-api-review.md` | needs-review |
| `decodables/docs/shared/analytics-system-design.md` | `decodables/docs/v2/04-features/admin-capabilities/analytics-system-design.md` | needs-review |
| `decodables/docs/shared/articles-system-design.md` | `decodables/docs/v2/04-features/admin-capabilities/articles-system-design.md` | needs-review |
| `decodables/docs/shared/asset-category-design.md` | `decodables/docs/v2/04-features/admin-capabilities/asset-category-design.md` | needs-review |
| `decodables/docs/shared/static-pages-cms-design.md` | `decodables/docs/v2/04-features/admin-capabilities/static-pages-cms-design.md` | needs-review |
| `decodables/docs/shared/onboarding-design.md` | `decodables/docs/v2/04-features/user-capabilities/onboarding-design.md` | needs-review |
| `decodables/docs/shared/theme-system-design.md` | `decodables/docs/v2/04-features/user-capabilities/theme-system-design.md` | needs-review |
| `decodables/docs/shared/canvas-data-schema.md` | `decodables/docs/v2/03-business/canvas-data-schema.md` | needs-review |
| `decodables/docs/shared/pricing-system-design.md` | `decodables/docs/v2/03-business/pricing-system.md` | needs-review |
| `decodables/docs/shared/tier-naming-system.md` | `decodables/docs/v2/03-business/tier-naming-system.md` | needs-review |
| `decodables/docs/shared/tier-permissions.md` | `decodables/docs/v2/03-business/entitlement/permission-matrix.md` | needs-review |
| `decodables/docs/shared/user-id-system.md` | `decodables/docs/v2/03-business/user-id-system.md` | needs-review |
| `decodables/docs/shared/entitlement-system-design.md` | `decodables/docs/v2/03-business/entitlement/system-design.md` | needs-review |
| `decodables/docs/shared/entitlement-permission-matrix.md` | `decodables/docs/v2/03-business/entitlement/permission-matrix.md` | needs-review |
| `decodables/docs/shared/entitlement-ui-spec.md` | `decodables/docs/v2/03-business/entitlement/ui-spec.md` | needs-review |
| `decodables/docs/shared/entitlement/README.md` | `decodables/docs/v2/03-business/entitlement/README.md` | needs-review |
| `decodables/docs/shared/entitlement/01-permission-matrix.md` | `decodables/docs/v2/03-business/entitlement/permission-matrix.md` | needs-review |
| `decodables/docs/shared/entitlement/02-tier-config.md` | `decodables/docs/v2/03-business/entitlement/tier-config.md` | needs-review |
| `decodables/docs/shared/entitlement/03-system-design.md` | `decodables/docs/v2/03-business/entitlement/system-design.md` | needs-review |
| `decodables/docs/shared/entitlement/04-feature-flag-engine.md` | `decodables/docs/v2/03-business/entitlement/feature-flag-engine.md` | needs-review |
| `decodables/docs/shared/entitlement/05-ui-spec.md` | `decodables/docs/v2/03-business/entitlement/ui-spec.md` | needs-review |
| `decodables/docs/shared/entitlement/06-priority-rules.md` | `decodables/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables/docs/shared/entitlement/07-tier-inheritance.md` | `decodables/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables/docs/shared/entitlement/08-user-groups.md` | `decodables/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables/docs/shared/entitlement/09-config-versioning.md` | `decodables/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables/docs/shared/entitlement/10-workspace-override.md` | `decodables/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables/docs/shared/entitlement/11-trial-expiration.md` | `decodables/docs/v2/03-business/entitlement/trial-expiration.md` | needs-review |
| `decodables/docs/shared/entitlement/12-tier-downgrade.md` | `decodables/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables/docs/shared/entitlement/13-subscription-pause.md` | `decodables/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables/docs/shared/entitlement/14-billing-cycle-switch.md` | `decodables/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables/docs/shared/entitlement/15-credits-lifecycle.md` | `decodables/docs/v2/03-business/entitlement/credits-lifecycle.md` | needs-review |
| `decodables/docs/shared/entitlement/16-renewal-reminders.md` | `decodables/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables/docs/shared/entitlement/17-invoice-management.md` | `decodables/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables/docs/shared/entitlement/18-refund-processing.md` | `decodables/docs/v2/03-business/entitlement/billing-lifecycle.md` | needs-review |
| `decodables/docs/shared/entitlement/19-promotions.md` | `decodables/docs/v2/03-business/entitlement/promotions.md` | needs-review |
| `decodables/docs/shared/entitlement/20-referral-rewards.md` | `decodables/docs/v2/03-business/entitlement/referral-rewards.md` | needs-review |
| `decodables/docs/shared/entitlement/21-education-discount.md` | `decodables/docs/v2/03-business/entitlement/education-discount.md` | needs-review |
| `decodables/docs/shared/entitlement/22-free-quota.md` | `decodables/docs/v2/03-business/entitlement/marketing-programs.md` | needs-review |
| `decodables/docs/shared/entitlement/23-feature-sunset.md` | `decodables/docs/v2/03-business/entitlement/marketing-programs.md` | needs-review |
| `decodables/docs/shared/entitlement/24-conflict-resolution.md` | `decodables/docs/v2/03-business/entitlement/policy-rules.md` | needs-review |
| `decodables/docs/shared/entitlement/25-future-scenarios.md` | `decodables/docs/v2/03-business/entitlement/marketing-programs.md` | needs-review |
| `decodables/docs/shared/entitlement/26-audit-checklist.md` | `decodables/docs/v2/03-business/entitlement/audits.md` | needs-review |
| `decodables/docs/shared/entitlement/27-audit-report-20260204.md` | `decodables/docs/v2/03-business/entitlement/audits.md` | needs-review |
| `decodables/docs/shared/entitlement/28-audit-supplement-20260204.md` | `decodables/docs/v2/03-business/entitlement/audits.md` | needs-review |
| `decodables/docs/shared/entitlement/implementation/README.md` | `decodables/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables/docs/shared/entitlement/implementation/01-database-schema.md` | `decodables/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables/docs/shared/entitlement/implementation/02-backend-services.md` | `decodables/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables/docs/shared/entitlement/implementation/03-backend-repositories.md` | `decodables/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables/docs/shared/entitlement/implementation/04-backend-apis.md` | `decodables/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables/docs/shared/entitlement/implementation/05-frontend-stores.md` | `decodables/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables/docs/shared/entitlement/implementation/06-frontend-components.md` | `decodables/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables/docs/shared/entitlement/implementation/07-migration-scripts.md` | `decodables/docs/v2/03-business/entitlement/implementation-guide.md` | needs-review |
| `decodables/docs/shared/feature-flag-design.md` | `decodables/docs/v2/02-standards/feature-flag/feature-flag-design.md` | needs-review |
| `decodables/docs/shared/feature-flag-engine.md` | `decodables/docs/v2/02-standards/feature-flag/feature-flag-engine.md` | needs-review |
| `decodables/docs/shared/message-logging-standard.md` | `decodables/docs/v2/02-standards/logging-standard.md` | needs-review |
| `decodables/docs/shared/project-implementation-plan.md` | `decodables/docs/v2/00-governance/project-implementation-plan.md` | needs-review |
| `decodables/docs/shared/system-refactoring-proposal-v2.md` | `decodables/docs/v2/01-architecture/system-refactoring-proposal-v2.md` | needs-review |
| `decodables/docs/shared/self-hosted-auth-design.md` | `decodables/docs/v2/01-architecture/self-hosted-auth-design.md` | needs-review |
| `decodables/docs/shared/v3-refactoring-completion-report.md` | `decodables/docs/v2/00-governance/v3-refactoring-completion-report.md` | needs-review |
| `decodables/docs/main/api-reference.md` | `decodables/docs/v2/05-api/api-reference.md` | needs-review |
| `decodables/docs/main/architecture-proposal.md` | `decodables/docs/v2/01-architecture/architecture-proposal.md` | needs-review |
| `decodables/docs/main/backend-architecture.md` | `decodables/docs/v2/01-architecture/backend-architecture.md` | done |
| `decodables/docs/main/backend-business-logic.md` | `decodables/docs/v2/03-business/backend-business-logic.md` | done |
| `decodables/docs/main/codebase-health-matrix.md` | `decodables/docs/v2/00-governance/codebase-health-matrix.md` | needs-review |
| `decodables/docs/main/database-guide.md` | `decodables/docs/v2/02-standards/database-guide.md` | done |
| `decodables/docs/main/deployment-scaling.md` | `decodables/docs/v2/06-operations/deployment-scaling.md` | needs-review |
| `decodables/docs/main/knowledge-base.md` | `decodables/docs/v2/09-reference/knowledge-base.md` | needs-review |
| `decodables/docs/main/naming-conventions.md` | `decodables/docs/v2/00-governance/naming-conventions.md` | done |
| `decodables/docs/main/testing-guide.md` | `decodables/docs/v2/02-standards/testing-guide.md` | needs-review |
| `decodables/docs/main/README.md` | `decodables/docs/v2/README.md` | done |

## 7. 缺口记录

| 缺口项 | 发现来源 | 处理策略 |
|--------|----------|----------|
| `decodables-fe/docs/shared/` 与 `decodables/docs/shared/` 未映射 | 旧文档索引 | 已建立 shared 映射清单（完成） |
| `user-capabilities/*` 对应 v2 功能文档未全量建立 | 覆盖矩阵 | 按能力树补齐文档 |
| `admin-capabilities/*` 对应 v2 功能文档未全量建立 | 覆盖矩阵 | 按能力树补齐文档 |
