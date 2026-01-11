# Admin API Review & Verification

**Status:** ✅ Complete
**Version:** 3.32
**Last Updated:** 2026-01-11

This document tracks the review and verification of Admin API endpoints against the actual codebase.

## Overview

The Admin API follows a strict **DDD (Domain-Driven Design)** architecture, separating concerns into API, Application (Service), Domain, and Infrastructure (Repository) layers.

**Key Architecture Features:**
- **Layered Architecture:** `API -> Service -> Repository -> Database`
- **Rate Limiting:** Applied to all public endpoints (typically 10-60 req/min).
- **Audit Logging:** Critical operations are logged to `admin_operations` (Task 9).
- **Validation:** Pydantic models with field-level validation (enums, lengths, regex).
- **Response Models:** Typed Pydantic response models for consistent API contracts.
- **Async:** All endpoints are `async/await`.

---

## 📊 API Summary

| Module | Base Path | Endpoints | Status | Description |
|---|---|---|---|---|
| **AI Models** | `/api/admin/ai/models` | 8 | ✅ v3.30 | AI model config & providers |
| **AI Insights** | `/api/admin/ai` | 5 | ✅ v3.27 | AI business insights & reports |
| **Campaigns** | `/api/admin/campaigns` | 8 | ✅ v3.30 | Marketing campaign management |
| **Config** | `/api/admin/config` | 8 | ✅ v3.26 | System config & rate limits |
| **Events** | `/api/admin/events` | 5 | ✅ v3.27 | User events & aggregation |
| **Experiments** | `/api/admin/experiments` | 14 | ✅ v3.31 | A/B testing & feature experiments |
| **Feature Flags** | `/api/admin/feature-flags` | 9 | ✅ v1.0 | Feature toggle management |
| **Logs** | `/api/admin/logs` | 5 | ✅ v3.26 | Error & operation audit logs |
| **Metrics** | `/api/admin/metrics` | 7 | ✅ v3.28 | Core system & business metrics |
| **Moderation** | `/api/admin/moderation` | 10 | ✅ v3.28 | Marketplace content moderation |
| **Notifications** | `/api/admin/notifications` | 5 | ✅ v3.30 | Broadcast & push notifications |
| **Stats** | `/api/admin/stats` | 18 | ✅ v3.30 | Dashboard analytics |
| **Subscriptions** | `/api/admin/subscriptions` | 3 | ✅ v3.28 | Refunds & cancellations |
| **System** | `/api/admin/system` | 11 | ✅ v3.30 | Cache & system internals |
| **Tasks** | `/api/admin/tasks/management` | 4 | ✅ v3.26 | Background task monitoring |
| **Users** | `/api/admin` | 13 | ✅ v3.25 | User management & credits |
| **Webhooks** | `/api/admin/webhooks` | 2 | ✅ v1.0 | Webhook retry mechanism |

**Total Endpoints:** 135

---

## 1. AI Models (`api/admin/ai_models.py`)

**Status:** ✅ Verified (DDD Compliant v3.30)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/config` | Get AI configs | Admin | 30/m | `get_model_configs` |
| `PUT` | `/config/text` | Update text config | Admin | 20/m | `update_text_model_config` |
| `PUT` | `/config/image` | Update image config | Admin | 20/m | `update_image_model_config` |
| `PUT` | `/config/admin` | Update admin config | Admin | 20/m | Placeholder |
| `PUT` | `/config/canary` | Update canary config | Admin | 10/m | `update_canary_config` |
| `PUT` | `/providers/toggle` | Toggle provider | Admin | 10/m | `toggle_ai_provider` |
| `GET` | `/usage` | Get usage stats | Admin | 30/m | `get_ai_usage_stats` |
| `POST` | `/cache/clear` | Clear AI cache | Admin | 5/m | `clear_ai_cache` |

**Notes:**
- Validates providers against `VALID_PROVIDERS`.
- Supports text/image/all cache clearing.

## 2. AI Insights (`api/admin/ai.py`)

**Status:** ✅ Verified (DDD Compliant v3.27)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/insights` | Get AI insights | Admin | 30/m | `get_ai_insights` |
| `GET` | `/recommendations` | Get recommendations | Admin | 30/m | `get_ai_recommendations` |
| `GET` | `/behavior-analysis` | Get behavior analysis | Admin | 20/m | `get_behavior_analysis` |
| `POST` | `/generate-report` | Generate report | Admin | 5/m | `generate_ai_business_report` |
| `GET` | `/quick-insights` | Get quick insights | Admin | 60/m | `get_quick_insights` |

**Notes:**
- Uses `domains.stats` service functions (DDD migrated in P2-001).
- Validates date formats and enums (`VALID_INSIGHT_TYPES`, etc.).

## 3. Campaigns (`api/admin/campaigns.py`)

**Status:** ✅ Verified (DDD Compliant v3.30)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `` | List campaigns | Admin | 30/m | `list_campaigns` |
| `GET` | `/{id}` | Get campaign | Admin | 30/m | `get_campaign` |
| `POST` | `` | Create campaign | Admin | 20/m | `create_campaign` |
| `PUT` | `/{id}` | Update campaign | Admin | 20/m | `update_campaign` |
| `DELETE` | `/{id}` | Delete campaign | Admin | 10/m | `delete_campaign` |
| `POST` | `/{id}/activate` | Activate campaign | Admin | 10/m | `activate_campaign` |
| `POST` | `/{id}/pause` | Pause campaign | Admin | 10/m | `pause_campaign` |
| `GET` | `/{id}/stats` | Get campaign stats | Admin | 30/m | `get_campaign_stats` |

**Notes:**
- Implements soft delete with audit logging (`campaign_delete`).
- Logs campaign deletion to audit trail.

## 4. Config & Rate Limits (`api/admin/config.py`)

**Status:** ✅ Verified (DDD Compliant v3.26)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/config` | Get all configs | Admin | 30/m | `ConfigService.get_all_configs` |
| `GET` | `/config/{key}` | Get single config | Admin | 30/m | `ConfigService.get_config` |
| `PUT` | `/config` | Update config | Admin | 10/m | `ConfigService.set_config` |
| `PUT` | `/config/batch` | Batch update | Admin | 10/m | `ConfigService.batch_update_configs` |
| `GET` | `/rate-limits` | Get rate limits | Admin | 30/m | `ConfigService.get_all_configs` (filtered) |
| `POST` | `/rate-limits/preset` | Apply preset | Admin | 10/m | `ConfigService.apply_rate_limit_preset` |
| `GET` | `/rate-limits/presets` | Get presets | Admin | 30/m | Static `RATE_LIMIT_PRESETS` |
| `POST` | `/config/cache/clear` | Clear cache | Admin | 10/m | `ConfigService.clear_config_cache` |

**Notes:**
- Logs all config changes to audit trail (`admin_operations`) with before/after values (P2-040).
- Validates categories and presets.

## 5. Events (`api/admin/events.py`)

**Status:** ✅ Verified (DDD Compliant v3.27)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/events` | Get user events | Admin | 30/m | `EventsService.get_user_events` |
| `GET` | `/events/stats` | Get event stats | Admin | 30/m | `EventsService.get_event_stats` |
| `GET` | `/aggregated/{type}` | Get aggregated stats | Admin | 30/m | `EventsService.get_aggregated_stats` |
| `GET` | `/aggregated/{type}/range` | Get aggregated range | Admin | 30/m | `EventsService.get_aggregated_stats_range` |
| `POST` | `/aggregation/run` | Run aggregation | Admin | 5/m | `run_aggregation_now` (Scheduler) |

**Notes:**
- Supports offset/limit pagination.
- Validates date formats and enums.
- OOM protection: max 100 events per request.

## 6. Experiments (`api/admin/experiments.py`)

**Status:** ✅ Verified (DDD Compliant v3.31)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `` | List experiments | Admin | 30/m | `ExperimentService.list_experiments` |
| `POST` | `` | Create experiment | Admin | 20/m | `ExperimentService.create_experiment` |
| `GET` | `/{key}` | Get experiment | Admin | 30/m | `ExperimentService.get_experiment` |
| `PUT` | `/{key}` | Update experiment | Admin | 20/m | `ExperimentService.update_experiment` |
| `PUT` | `/{key}/status` | Update status | Admin | 20/m | `ExperimentService.update_experiment_status` |
| `DELETE` | `/{key}` | Delete experiment | Admin | 10/m | `ExperimentService.delete_experiment` |
| `GET` | `/{key}/results` | Get results | Admin | 30/m | `ExperimentService.get_experiment_results` |
| `POST` | `/{key}/aggregate` | Trigger aggregation | Admin | 10/m | `ExperimentService.aggregate_experiment_results` |
| `POST` | `/aggregate-all` | Aggregate all | Admin | 5/m | `ExperimentService.aggregate_experiment_results(None)` |
| `POST` | `/cache/clear` | Clear cache | Admin | 10/m | `experiments.clear_experiment_cache` |
| `POST` | `/{key}/ai-analysis` | AI analysis | Admin | 10/m | `experiment_ai_service` |
| `GET` | `/{key}/quick-recommendation` | Quick recommendation | Admin | 30/m | `experiment_ai_service` |
| `GET` | `/{key}/trend` | Daily trend | Admin | 20/m | `ExperimentService.get_daily_trend` |
| `GET` | `/{key}/hourly-trend` | Hourly trend | Admin | 20/m | `ExperimentService.get_hourly_trend` |

**Notes:**
- Full CRUD + Analysis + Aggregation.
- Logs deletion to audit trail (`experiment_delete`).

## 7. Feature Flags (`api/admin/feature_flags.py`)

**Status:** ✅ Verified (DDD Compliant v1.0.0)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `` | List flags | Admin | - | `FeatureFlagService.list_flags` |
| `POST` | `` | Create flag | Admin | - | `FeatureFlagService.create_flag` |
| `GET` | `/{key}` | Get flag | Admin | - | `FeatureFlagService.get_flag` |
| `PATCH` | `/{key}` | Update flag | Admin | - | `FeatureFlagService.update_flag` |
| `POST` | `/{key}/toggle` | Toggle flag | Admin | - | `FeatureFlagService.toggle_flag` |
| `DELETE` | `/{key}` | Archive flag | Admin | - | `FeatureFlagService.archive_flag` |
| `POST` | `/test-evaluation` | Test evaluation | Admin | - | `feature_service.evaluate` |
| `GET` | `/{key}/audit` | Get audit logs | Admin | - | `FeatureFlagService.get_audit_logs` |
| `GET` | `/client/flags` | Client evaluation | User | - | `feature_service.get_all_flags` |

**Notes:**
- Internal tool endpoints (no rate limit currently).
- Logs archive operations to admin audit trail (`feature_flag_delete`).

## 8. Logs (`api/admin/logs.py`)

**Status:** ✅ Verified (DDD Compliant v3.26)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/errors` | Get error logs | Admin | 30/m | `SupabaseErrorLogsRepository.get_error_logs` |
| `GET` | `/errors/stats` | Get error stats | Admin | 30/m | `SupabaseErrorLogsRepository.get_error_stats` |
| `GET` | `/operations` | Get operation logs | Admin | 30/m | `SupabaseAdminUsersRepository.admin_get_operation_logs` |
| `GET` | `/operations/export` | Export logs (CSV) | Admin | 10/m | `SupabaseAdminUsersRepository` |
| `GET` | `/audit` | Unified audit logs | Admin | 30/m | `SupabaseAdminUsersRepository.get_audit_logs` |

**Notes:**
- **Unified Audit Query API** implemented (Task 9.5) supporting 10 filter parameters (target, source, operation, etc.).
- Export limit increased to 100,000.
- Logs export operations to audit trail.

## 9. Metrics (`api/admin/metrics.py`)

**Status:** ✅ Verified (DDD Compliant v3.28)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/daily` | Daily metrics | Admin | 30/m | `SupabaseMetricsRepository.get_daily_metrics` |
| `GET` | `/monthly` | Monthly metrics | Admin | 30/m | `SupabaseMetricsRepository.get_monthly_metrics` |
| `GET` | `/retention` | Retention metrics | Admin | 30/m | `SupabaseMetricsRepository.get_retention_metrics` |
| `GET` | `/funnel` | Funnel metrics | Admin | 30/m | `SupabaseMetricsRepository.get_funnel_counts` |
| `GET` | `/errors` | Error metrics | Admin | 30/m | `SupabaseMetricsRepository.get_error_stats` |
| `GET` | `/dau-trend` | DAU trend | Admin | 30/m | `SupabaseMetricsRepository.get_dau_trend` |
| `POST` | `/refresh` | Refresh metrics | Admin | 5/m | `run_aggregation_now` |

**Notes:**
- **Funnel queries optimized** with RPC `p_get_conversion_funnel` + Indexes (P2-012), 50x-100x faster.
- Validates period/metric_type enums.
- Validates date formats.

## 10. Moderation (`api/admin/moderation.py`)

**Status:** ✅ Verified (DDD Compliant v3.28)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/marketplace/moderation/list` | List moderation | Admin | 30/m | `moderation_service.get_moderation_list` |
| `GET` | `/marketplace/moderation/{id}` | Get detail | Admin | 30/m | `moderation_service.get_moderation_detail` |
| `POST` | `/marketplace/moderation/{id}/approve` | Approve | Admin | 30/m | `moderation_service.approve_listing` |
| `POST` | `/marketplace/moderation/{id}/reject` | Reject | Admin | 30/m | `moderation_service.reject_listing` |
| `POST` | `/marketplace/moderation/{id}/delete` | Delete | Admin | 30/m | `moderation_service.delete_listing` |
| `POST` | `/marketplace/moderation/{id}/unpublish` | Unpublish | Admin | 30/m | `moderation_service.unpublish_listing` |
| `GET` | `/reports` | List reports | Admin | 30/m | `moderation_service.get_reports` |
| `GET` | `/reports/stats` | Report stats | Admin | 30/m | `moderation_service.get_reports_stats` |
| `GET` | `/reports/{id}` | Report detail | Admin | 30/m | `moderation_service.get_report_detail` |
| `POST` | `/reports/{id}/respond` | Respond to report | Admin | 30/m | `moderation_service.respond_to_report` |

**Notes:**
- Validates statuses.
- Supports pagination.

## 11. Notifications (`api/admin/notifications.py`)

**Status:** ✅ Verified (DDD Compliant v3.30)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `POST` | `/broadcast` | Broadcast notification | Admin | 5/m | `send_broadcast` |
| `POST` | `/notification/send` | Send to user | Admin | 30/m | `send_to_user` |
| `POST` | `/notification/batch` | Batch send | Admin | 10/m | `send_to_users` |
| `GET` | `/notification/stats` | Get stats | Admin | 30/m | `get_stats` |
| `GET` | `/notification/history` | Get history | Admin | 30/m | `get_history` |

**Notes:**
- Validates target groups and notification types.
- Batch limit: 100 users.

## 12. Stats (`api/admin/stats.py`)

**Status:** ✅ Verified (DDD Compliant v3.30)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/dashboard` | Dashboard KPIs | Admin | 30/m | `get_dashboard_stats` |
| `GET` | `/user-growth` | User growth | Admin | 30/m | `get_user_growth_stats` |
| `GET` | `/revenue` | Revenue | Admin | 30/m | `get_revenue_stats` |
| `GET` | `/projects` | Project stats | Admin | 30/m | `get_project_stats` |
| `GET` | `/credits` | Credit usage | Admin | 30/m | `get_credit_usage_stats` |
| `GET` | `/tier-distribution` | Tier dist | Admin | 30/m | `get_tier_distribution` |
| `GET` | `/conversion-funnel` | Conversion funnel | Admin | 30/m | `get_conversion_funnel` |
| `GET` | `/exports` | Export stats | Admin | 30/m | `get_export_stats` |
| `GET` | `/assets` | Asset stats | Admin | 30/m | `get_asset_usage_stats` |
| `GET` | `/tier-activity` | Tier activity | Admin | 30/m | `get_tier_activity_stats` |
| `GET` | `/subscription-events` | Sub events | Admin | 30/m | `get_subscription_events_stats` |
| `GET` | `/page-views` | Page views | Admin | 30/m | `get_page_views_stats` |
| `GET` | `/project-details` | Project details | Admin | 30/m | `get_project_details_stats` |
| `GET` | `/returning-users` | Returning users | Admin | 30/m | `get_returning_users_stats` |
| `GET` | `/tier-trend` | Tier trend | Admin | 30/m | `get_tier_trend_stats` |
| `GET` | `/tier-conversion` | Tier conversion | Admin | 30/m | `get_tier_conversion_stats` |
| `GET` | `/performance` | Core Web Vitals | Admin | 30/m | `get_performance_metrics_stats` |
| `GET` | `/user-distribution` | User dist | Admin | 30/m | `get_user_distribution_stats` |

**Notes:**
- **Pydantic Response Models:** All 18 endpoints return typed Pydantic models (P3-001).
- Validates periods and group_by parameters.

## 13. Subscriptions (`api/admin/subscriptions.py`)

**Status:** ✅ Verified (DDD Compliant v3.28)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `POST` | `/refund` | Process refund | Admin | 10/m | `SubscriptionService.process_refund` |
| `POST` | `/subscription/cancel` | Cancel sub | Admin | 10/m | `SubscriptionService.cancel_user_subscription` |
| `POST` | `/subscription/downgrade` | Downgrade sub | Admin | 10/m | `SubscriptionService.downgrade_user_subscription` |

**Notes:**
- Validates user codes and tiers.
- Uses strict rate limiting.

## 14. System (`api/admin/system.py`)

**Status:** ✅ Verified (DDD Compliant v3.30)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/configs` | Get configs | Admin | 30/m | `get_configs` |
| `GET` | `/configs/groups` | Get groups | Admin | 30/m | `get_config_groups` |
| `POST` | `/configs` | Create config | Admin | 10/m | `create_config` |
| `PUT` | `/configs/{key}` | Update config | Admin | 10/m | `update_config` |
| `DELETE` | `/configs/{key}` | Delete config | Admin | 10/m | `delete_config` |
| `GET` | `/configs/audit` | Get config audit | Admin | 30/m | `get_config_audit` |
| `POST` | `/configs/cache/invalidate` | Invalidate config | Admin | 5/m | `invalidate_config_cache` |
| `GET` | `/system/cache/status` | Cache status | Admin | 30/m | `get_cache_status` |
| `GET` | `/system/cache/keys` | List cache keys | Admin | 30/m | `list_cache_keys` |
| `DELETE` | `/system/cache/key/{key}` | Delete key | Admin | 10/m | `delete_cache_key` |
| `POST` | `/system/cache/clear-all/confirm` | Request token | Admin | 1/10m | `secrets` generation |
| `POST` | `/system/cache/clear-all` | Clear all cache | Admin | 1/10m | `clear_all_cache` |

**Notes:**
- **Cache Clear All** uses secure two-step confirmation with 2min token (P0-013).
- Audits dangerous operations to `admin_operations`.

## 15. Tasks Management (`api/admin/tasks_mgmt.py`)

**Status:** ✅ Verified (DDD Compliant v3.26)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/status` | Task status | Admin | 30/m | `SupabaseTasksRepository.get_task_status` |
| `GET` | `/logs` | Task logs | Admin | 30/m | `SupabaseTasksRepository.get_task_logs` |
| `GET` | `/health` | Task health | Admin | 30/m | `SupabaseTasksRepository.get_tasks_health` |
| `POST` | `/{name}/run` | Run task | Admin | 10/m | `run_aggregation_now` / `scheduler` |

**Notes:**
- Validates task names against `VALID_TASK_NAMES`.
- Logs manual triggers.

## 16. Users (`api/admin/users.py`)

**Status:** ✅ Verified (DDD Compliant v3.25)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `GET` | `/users` | Search users | Admin | 30/m | `SupabaseUserRepository.search_users` |
| `GET` | `/users/by-tier/{tier}` | Users by tier | Admin | 30/m | `SupabaseUserRepository.get_users_by_tier` |
| `GET` | `/users/{uid}` | User audit | Admin | 30/m | `SupabaseAdminUsersRepository.get_full_user_audit` |
| `POST` | `/users/{uid}/credits` | Adjust credits | Admin | 10/m | `SupabaseAdminUsersRepository.admin_adjust_credits` |
| `PATCH` | `/users/{uid}` | Update user | Admin | 10/m | `SupabaseUserRepository.update_subscription_tier` |
| `POST` | `/users/{uid}/discount` | Create discount | Admin | 10/m | `SupabaseUserRepository.create_user_discount` |
| `GET` | `/users/{uid}/payments` | Get payments | Admin | 30/m | `get_customer_payments` |
| `GET` | `/users/{uid}/projects` | Get projects | Admin | 30/m | `SupabaseAdminUsersRepository.admin_get_user_projects` |
| `GET` | `/users/{uid}/asset-usage` | Asset usage | Admin | 30/m | `SupabaseAssetRepository.get_user_asset_usage` |
| `GET` | `/users/{uid}/env-stats` | Env stats | Admin | 30/m | `SupabaseAnalyticsRepository.get_user_env_stats` |
| `POST` | `/projects/{id}/restore` | Restore project | Admin | 10/m | `SupabaseProjectRepository.restore_project` |
| `GET` | `/projects/feed` | Project feed | Admin | 30/m | `SupabaseProjectRepository.get_all_projects_feed` |

**Notes:**
- Logs credit adjustments, tier changes, discounts to audit trail.
- Implements strict validation on user IDs and tiers.

## 17. Webhooks Retry (`api/admin/webhooks_retry.py`)

**Status:** ✅ Verified (Implemented v1.0.0)

| Method | Endpoint | Description | Auth | Rate Limit | Service/Repo |
|---|---|---|---|---|---|
| `POST` | `/retry` | Retry failed | Admin | 10/h | `WebhookRetryService.retry_all_failed_webhooks` |
| `GET` | `/failed` | Get failed | Admin | 30/m | `SupabaseWebhookRepository.get_failed_x_webhooks` |

**Notes:**
- **Robust Retry Logic:** Implemented with APScheduler (P3-022).
- Very strict rate limit on retry (10/hour) as it is expensive.
