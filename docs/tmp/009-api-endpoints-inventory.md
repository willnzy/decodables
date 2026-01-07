# API v2 Endpoints Inventory

> Complete listing of all v2 API endpoints created in the architecture migration

**Generated**: 2026-01-07
**Status**: ✅ All 38 API files created and registered

---

## Summary

| Category | Files | Status |
|----------|-------|--------|
| **Public APIs** | 24 | ✅ Complete |
| **Admin APIs** | 14 | ✅ Complete |
| **Total** | **38** | ✅ Complete |

---

## Architecture Verification

### ✅ API Aggregation Check

**`api/__init__.py`** (Root aggregator):
- ✅ Imports all 24 public API routers
- ✅ Imports admin_router
- ✅ Creates main `api_router` with all routers included
- ✅ Exports all routers in `__all__`

**`api/admin/__init__.py`** (Admin aggregator):
- ✅ Imports all 14 admin API sub-routers
- ✅ Creates `admin_router` with prefix `/api/v2/admin`
- ✅ Includes all 14 sub-routers

**`app.py`** (Main application):
- ✅ Line 308-309: Imports and includes v2 API router
- ✅ v1 routers (lines 208-304) still present (correct transition state)
- ✅ Both v1 and v2 coexist during migration period

---

## Public APIs (24 files)

### 1. Billing & Credits (2 files)

#### `api/billing_api.py`
**Prefix**: `/api/v2/billing`
**Purpose**: Credit management (CQRS pattern)
**Key Endpoints**:
- `POST /api/v2/billing/deduct` - Deduct credits (Command)
- `GET /api/v2/billing/balance` - Get balance (Query)

#### `api/credits_api.py`
**Prefix**: `/api/v2/credits`
**Purpose**: User-facing credits API
**Key Endpoints**:
- `GET /api/v2/credits` - Get user credits
- `GET /api/v2/credits/history` - Credit transaction history

---

### 2. User & Profile (1 file)

#### `api/user_api.py`
**Prefix**: `/api/v2/user`
**Purpose**: User profile management
**Key Endpoints**:
- `GET /api/v2/user/profile` - Get user profile
- `PATCH /api/v2/user/profile` - Update profile

---

### 3. Projects & Assets (4 files)

#### `api/projects_api.py`
**Prefix**: `/api/v2/projects`
**Purpose**: Project CRUD operations
**Key Endpoints**:
- `GET /api/v2/projects` - List projects
- `POST /api/v2/projects` - Create project
- `GET /api/v2/projects/{id}` - Get project
- `PUT /api/v2/projects/{id}` - Update project
- `DELETE /api/v2/projects/{id}` - Delete project

#### `api/assets_api.py`
**Prefix**: `/api/v2/assets`
**Purpose**: User assets management
**Key Endpoints**:
- `GET /api/v2/assets` - List assets
- `POST /api/v2/assets` - Upload asset
- `DELETE /api/v2/assets/{id}` - Delete asset

#### `api/resources_api.py`
**Prefix**: `/api/v2/resources`
**Purpose**: System resources (stickers, backgrounds)
**Key Endpoints**:
- `GET /api/v2/resources/stickers` - Get stickers
- `GET /api/v2/resources/backgrounds` - Get backgrounds

#### `api/marketplace_api.py`
**Prefix**: `/api/v2/marketplace`
**Purpose**: Marketplace listings and purchases
**Key Endpoints**:
- `GET /api/v2/marketplace/listings` - Browse listings
- `POST /api/v2/marketplace/purchase` - Purchase asset

---

### 4. AI Generation (4 files)

#### `api/generation_api.py`
**Prefix**: `/api/v2/generate`
**Purpose**: AI content generation (text, image)
**Key Endpoints**:
- `POST /api/v2/generate/text` - Generate text
- `POST /api/v2/generate/image` - Generate image

#### `api/generations_api.py`
**Prefix**: `/api/v2/generations`
**Purpose**: Generation history and management
**Key Endpoints**:
- `GET /api/v2/generations` - List generations
- `GET /api/v2/generations/{id}` - Get generation
- `PATCH /api/v2/generations/{id}` - Update generation (favorite status) ✨ Optimized
- `POST /api/v2/generations/{id}/favorite` - ⚠️ DEPRECATED: Use PATCH instead
- `POST /api/v2/generations/batch-delete` - Batch delete ✨ Optimized
- `DELETE /api/v2/generations/batch` - ⚠️ DEPRECATED: Use POST /batch-delete instead

#### `api/templates_api.py`
**Prefix**: `/api/v2/templates`
**Purpose**: Prompt templates management
**Key Endpoints**:
- `GET /api/v2/templates` - List templates
- `POST /api/v2/templates` - Create template
- `DELETE /api/v2/templates/{id}` - Delete template

#### `api/tasks_api.py`
**Prefix**: `/api/v2/tasks`
**Purpose**: Async task status tracking
**Key Endpoints**:
- `GET /api/v2/tasks/{task_id}/status` - Get task status
- `GET /api/v2/tasks/{task_id}/result` - Get task result

---

### 5. Export & Tools (3 files)

#### `api/export_api.py`
**Prefix**: `/api/v2/export`
**Purpose**: PDF/ZIP export
**Key Endpoints**:
- `GET /api/v2/export/projects/{id}/zip` - Export ZIP ✨ Optimized
- `GET /api/v2/export/projects/{id}/pdf` - Export PDF
- `GET /api/v2/export/projects/{id}/preview` - Preview PDF
- `POST /api/v2/export/zip` - ⚠️ DEPRECATED: Use GET /projects/{id}/zip instead

#### `api/tools_api.py`
**Prefix**: `/api/v2/tools`
**Purpose**: PDF preview, OCR, and utilities
**Key Endpoints**:
- `POST /api/v2/tools/pdf/preview` - PDF preview
- `POST /api/v2/tools/ocr` - OCR text extraction

#### `api/websocket_api.py`
**Prefix**: `/api/v2/ws`
**Purpose**: WebSocket endpoints for real-time updates
**Key Endpoints**:
- `WS /api/v2/ws/tasks/{task_id}` - Task progress updates
- `WS /api/v2/ws/notifications` - Real-time notifications

---

### 6. Content & Marketing (3 files)

#### `api/themes_api.py`
**Prefix**: `/api/v2/themes`
**Purpose**: Holiday themes and seasonal content
**Key Endpoints**:
- `GET /api/v2/themes` - List themes
- `GET /api/v2/themes/{id}` - Get theme details

#### `api/campaigns_api.py`
**Prefix**: `/api/v2/campaigns`
**Purpose**: Marketing campaigns
**Key Endpoints**:
- `GET /api/v2/campaigns` - List campaigns
- `POST /api/v2/campaigns/{id}/participate` - Join campaign

#### `api/support_api.py`
**Prefix**: `/api/v2/support`
**Purpose**: Customer support and feedback
**Key Endpoints**:
- `POST /api/v2/support/ticket` - Create support ticket
- `POST /api/v2/support/feedback` - Submit feedback

---

### 7. Platform & System (7 files)

#### `api/platform_api.py`
**Prefix**: `/api/v2/platform`
**Purpose**: Feature flags and experiments
**Key Endpoints**:
- `GET /api/v2/platform/features` - Get feature flags
- `GET /api/v2/platform/features/{key}` - Get specific flag

#### `api/payment_api.py`
**Prefix**: `/api/v2/payment`
**Purpose**: Stripe checkout session creation
**Key Endpoints**:
- `POST /api/v2/payment/checkout` - Create checkout session
- `GET /api/v2/payment/plans` - List pricing plans

#### `api/analytics_api.py`
**Prefix**: `/api/v2/analytics`
**Purpose**: Analytics event tracking
**Key Endpoints**:
- `POST /api/v2/analytics/event` - Track event
- `POST /api/v2/analytics/batch` - Batch track events

#### `api/config_api.py`
**Prefix**: `/api/v2/config`
**Purpose**: Public configurations
**Key Endpoints**:
- `GET /api/v2/config` - Get all configs
- `GET /api/v2/config/{key}` - Get specific config
- `GET /api/v2/config/group/{group_name}` - Get config group

#### `api/logs_api.py`
**Prefix**: `/api/v2/logs`
**Purpose**: Error logging (user-facing)
**Key Endpoints**:
- `POST /api/v2/logs/error` - Log client error
- `POST /api/v2/logs/batch` - Batch log errors

#### `api/experiments_api.py`
**Prefix**: `/api/v2/experiments`
**Purpose**: Public A/B testing experiments
**Key Endpoints**:
- `POST /api/v2/experiments/{key}/assign` - Assign variant to user
- `POST /api/v2/experiments/{key}/exposure` - Track exposure
- `POST /api/v2/experiments/{key}/conversion` - Track conversion
- `GET /api/v2/experiments/user/{identifier}` - Get user's experiments

#### `api/webhooks_api.py`
**Prefix**: `/api/v2/webhooks`
**Purpose**: Third-party webhooks (Clerk, Stripe)
**Key Endpoints**:
- `POST /api/v2/webhooks/clerk` - Clerk webhook handler
- `POST /api/v2/webhooks/stripe` - Stripe webhook handler

**Migration Notes**:
- ✅ Logic identical to v1 (`/api/webhooks/clerk`, `/api/webhooks/stripe`)
- ✅ Idempotency protection via `process_webhook_event()` RPC
- ⚠️ Requires updating webhook URLs in third-party dashboards:
  - **Clerk**: https://dashboard.clerk.com → Webhooks → Update endpoint URL
  - **Stripe**: https://dashboard.stripe.com/webhooks → Update endpoint URL
- 📋 See `WEBHOOK-V2-STAGING-TESTING-GUIDE.md` for complete testing checklist

---

## Admin APIs (14 files)

**Common Prefix**: `/api/v2/admin`
**Authentication**: Requires admin role via `require_admin()` dependency

### 1. User Management (1 file)

#### `api/admin/users_api.py`
**Prefix**: `/api/v2/admin/users`
**Purpose**: User management (tier updates, bans, etc.)
**Key Endpoints**:
- `GET /api/v2/admin/users` - List all users
- `GET /api/v2/admin/users/{uid}` - Get user details
- `PATCH /api/v2/admin/users/{uid}` - Update user (tier, etc.) ✨ Optimized
- `POST /api/v2/admin/users/{uid}/tier` - ⚠️ DEPRECATED: Use PATCH /users/{uid} instead
- `POST /api/v2/admin/users/{uid}/ban` - Ban user
- `POST /api/v2/admin/users/{uid}/unban` - Unban user

---

### 2. Analytics & Metrics (2 files)

#### `api/admin/stats_api.py`
**Prefix**: `/api/v2/admin/stats`
**Purpose**: Dashboard KPIs and analytics
**Key Endpoints**:
- `GET /api/v2/admin/stats/overview` - Dashboard overview
- `GET /api/v2/admin/stats/users` - User statistics
- `GET /api/v2/admin/stats/revenue` - Revenue statistics

#### `api/admin/metrics_api.py`
**Prefix**: `/api/v2/admin/metrics`
**Purpose**: System metrics (daily/monthly aggregations)
**Key Endpoints**:
- `GET /api/v2/admin/metrics/daily` - Daily metrics
- `GET /api/v2/admin/metrics/monthly` - Monthly metrics
- `GET /api/v2/admin/metrics/errors` - Error metrics
- `GET /api/v2/admin/metrics/funnel` - Conversion funnel
- `GET /api/v2/admin/metrics/retention` - User retention
- `GET /api/v2/admin/metrics/dau-trend` - DAU trend
- `POST /api/v2/admin/metrics/refresh` - Refresh metrics

---

### 3. System Configuration (2 files)

#### `api/admin/config_api.py`
**Prefix**: `/api/v2/admin/config`
**Purpose**: System configuration management
**Key Endpoints**:
- `GET /api/v2/admin/config` - Get all configs
- `PUT /api/v2/admin/config/{key}` - Update config
- `POST /api/v2/admin/config/reload` - Reload configs

#### `api/admin/system_api.py`
**Prefix**: `/api/v2/admin/system`
**Purpose**: System operations (health checks, maintenance)
**Key Endpoints**:
- `GET /api/v2/admin/system/health` - Health check
- `POST /api/v2/admin/system/maintenance` - Toggle maintenance mode
- `POST /api/v2/admin/system/cache/clear` - Clear cache

---

### 4. Content Management (2 files)

#### `api/admin/campaigns_api.py`
**Prefix**: `/api/v2/admin/campaigns`
**Purpose**: Campaign management (CRUD)
**Key Endpoints**:
- `GET /api/v2/admin/campaigns` - List campaigns
- `POST /api/v2/admin/campaigns` - Create campaign
- `PUT /api/v2/admin/campaigns/{id}` - Update campaign
- `DELETE /api/v2/admin/campaigns/{id}` - Delete campaign

#### `api/admin/moderation_api.py`
**Prefix**: `/api/v2/admin/moderation`
**Purpose**: Content moderation
**Key Endpoints**:
- `GET /api/v2/admin/moderation/queue` - Moderation queue
- `POST /api/v2/admin/moderation/{id}/approve` - Approve content
- `POST /api/v2/admin/moderation/{id}/reject` - Reject content

---

### 5. Communication (1 file)

#### `api/admin/notifications_api.py`
**Prefix**: `/api/v2/admin/notifications`
**Purpose**: Notification management and broadcast
**Key Endpoints**:
- `POST /api/v2/admin/notifications/broadcast` - Broadcast notification
- `GET /api/v2/admin/notifications/history` - Notification history

---

### 6. Background Tasks (1 file)

#### `api/admin/tasks_api.py`
**Prefix**: `/api/v2/admin/tasks`
**Purpose**: Background task queue management
**Key Endpoints**:
- `GET /api/v2/admin/tasks` - List tasks
- `GET /api/v2/admin/tasks/{id}` - Get task details
- `POST /api/v2/admin/tasks/{id}/cancel` - Cancel task
- `POST /api/v2/admin/tasks/{id}/retry` - Retry task

---

### 7. AI Management (1 file)

#### `api/admin/ai_api.py`
**Prefix**: `/api/v2/admin/ai`
**Purpose**: AI insights and model configuration
**Key Endpoints**:
- `GET /api/v2/admin/ai/insights` - AI generation insights
- `GET /api/v2/admin/ai/usage` - AI usage statistics
- `GET /api/v2/admin/ai/behavior-analysis` - User behavior analysis
- `GET /api/v2/admin/ai/recommendations` - AI recommendations
- `GET /api/v2/admin/ai/quick-insights` - Quick insights
- `GET /api/v2/admin/ai/config` - Get AI model config
- `PUT /api/v2/admin/ai/config/text` - Update text model config
- `PUT /api/v2/admin/ai/config/image` - Update image model config
- `PUT /api/v2/admin/ai/config/canary` - Update canary config
- `PATCH /api/v2/admin/ai/providers/{provider}` - Update provider status ✨ Optimized
- `PUT /api/v2/admin/ai/providers/toggle` - ⚠️ DEPRECATED: Use PATCH /providers/{provider} instead
- `POST /api/v2/admin/ai/cache/clear` - Clear AI cache

**Migration Notes**:
- Combined from `admin_ai.py` (AI insights) + `admin_ai_models.py` (model config)
- All functionality preserved in single file

---

### 8. Logging (1 file)

#### `api/admin/logs_api.py`
**Prefix**: `/api/v2/admin/logs`
**Purpose**: Error and operation logs
**Key Endpoints**:
- `GET /api/v2/admin/logs/errors` - Error logs
- `GET /api/v2/admin/logs/errors/stats` - Error statistics
- `GET /api/v2/admin/logs/operations` - Operation logs
- `GET /api/v2/admin/logs/operations/export` - Export logs

**Migration Notes**:
- Combined from `admin_logs.py` (error logs) + operation logs

---

### 9. Subscriptions (1 file)

#### `api/admin/subscriptions_api.py`
**Prefix**: `/api/v2/admin/subscriptions`
**Purpose**: Subscription management (refund, cancel, downgrade)
**Key Endpoints**:
- `POST /api/v2/admin/subscriptions/refund` - Refund subscription
- `POST /api/v2/admin/subscriptions/cancel` - Cancel subscription
- `POST /api/v2/admin/subscriptions/downgrade` - Downgrade user

---

### 10. Events (1 file)

#### `api/admin/events_api.py`
**Prefix**: `/api/v2/admin/events`
**Purpose**: Events and aggregation
**Key Endpoints**:
- `GET /api/v2/admin/events` - List events
- `GET /api/v2/admin/events/stats` - Event statistics
- `GET /api/v2/admin/events/aggregated/{stat_type}` - Get aggregated stats
- `GET /api/v2/admin/events/aggregated/{stat_type}/range` - Get stats by date range
- `POST /api/v2/admin/events/aggregation/run` - Run aggregation

---

### 11. Experiments (1 file)

#### `api/admin/experiments_api.py`
**Prefix**: `/api/v2/admin/experiments`
**Purpose**: A/B testing experiment management
**Key Endpoints**:
- `GET /api/v2/admin/experiments` - List experiments
- `POST /api/v2/admin/experiments` - Create experiment
- `GET /api/v2/admin/experiments/{key}` - Get experiment
- `PUT /api/v2/admin/experiments/{key}` - Update experiment
- `DELETE /api/v2/admin/experiments/{key}` - Delete experiment
- `PUT /api/v2/admin/experiments/{key}/status` - Update status
- `GET /api/v2/admin/experiments/{key}/results` - Get results
- `GET /api/v2/admin/experiments/{key}/trend` - Get trend
- `GET /api/v2/admin/experiments/{key}/hourly-trend` - Hourly trend
- `POST /api/v2/admin/experiments/{key}/aggregate` - Aggregate data
- `POST /api/v2/admin/experiments/aggregate-all` - Aggregate all
- `POST /api/v2/admin/experiments/{key}/ai-analysis` - AI-powered analysis
- `GET /api/v2/admin/experiments/{key}/quick-recommendation` - Quick recommendation
- `POST /api/v2/admin/experiments/cache/clear` - Clear cache

---

## HTTP Method Optimizations

### Optimized Endpoints (6 total)

The following endpoints were optimized to follow RESTful best practices while maintaining backward compatibility:

1. **Export API**:
   - ✨ `GET /api/v2/export/projects/{id}/zip` (new, recommended)
   - ⚠️ `POST /api/v2/export/zip` (deprecated)

2. **Generations API**:
   - ✨ `PATCH /api/v2/generations/{id}` (new, recommended)
   - ⚠️ `POST /api/v2/generations/{id}/favorite` (deprecated)
   - ✨ `POST /api/v2/generations/batch-delete` (new, recommended)
   - ⚠️ `DELETE /api/v2/generations/batch` (deprecated)

3. **Admin AI API**:
   - ✨ `PATCH /api/v2/admin/ai/providers/{provider}` (new, recommended)
   - ⚠️ `PUT /api/v2/admin/ai/providers/toggle` (deprecated)

4. **Admin Users API**:
   - ✨ `PATCH /api/v2/admin/users/{uid}` (new, recommended)
   - ⚠️ `POST /api/v2/admin/users/{uid}/tier` (deprecated)

### Deprecation Strategy

- All deprecated endpoints marked with `deprecated=True` in FastAPI
- Will be removed in v3.0 (6 months after v2 release)
- Frontend should migrate to new optimized endpoints
- See `API-OPTIMIZATION-PLAN.md` for migration guide

---

## Next Steps (Phase 1 Completion)

### ✅ Completed

1. ✅ All 38 API files created
2. ✅ api/__init__.py aggregates all routers
3. ✅ api/admin/__init__.py aggregates admin routers
4. ✅ app.py includes v2 API router (lines 308-309)
5. ✅ This inventory document created

### ⏳ In Progress

- [ ] Start local server and verify Swagger documentation
- [ ] Test authentication middleware
- [ ] Create comprehensive .env.example

### 📋 Remaining (Phase 1)

- [ ] Environment variables migration
- [ ] API documentation updates
- [ ] Postman collection creation

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [API-HTTP-METHODS-GUIDELINES.md](./API-HTTP-METHODS-GUIDELINES.md) | RESTful API standards |
| [API-METHODS-AUDIT.md](./API-METHODS-AUDIT.md) | Comprehensive audit of 200+ endpoints |
| [API-OPTIMIZATION-PLAN.md](./API-OPTIMIZATION-PLAN.md) | HTTP method optimization roadmap |
| [WEBHOOK-V2-STAGING-TESTING-GUIDE.md](./WEBHOOK-V2-STAGING-TESTING-GUIDE.md) | Webhook testing checklist |
| [BACKEND-DEVELOPMENT-SOP.md](./BACKEND-DEVELOPMENT-SOP.md) | 6-phase execution plan |
| [BACKEND-NEXT-STEPS-SUMMARY.md](./BACKEND-NEXT-STEPS-SUMMARY.md) | Quick-start guide |

---

**Last Updated**: 2026-01-07
**Version**: 2.0.0
**Status**: Phase 1 - API Layer Completion (80% complete)
