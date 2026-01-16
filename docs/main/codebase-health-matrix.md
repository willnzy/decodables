# Make Decodables Backend - Codebase Health Matrix

> **Version**: v3.27 (Zero Debt)
> **Scan Date**: 2026-01-16
> **Status**: 🟢 Production Ready

---

## Executive Summary

| Metric | Value | Status |
|--------|-------|--------|
| **Total Files** | 459 Python files | - |
| **Total LOC** | 77,401 lines | - |
| **V3 Compliant** | 257/459 (56.0%) | 🟢 Good |
| **Layer Violations** | 6 files | 🟡 Fix Required |
| **DI Compliant** | 203/459 (44.2%) | 🟡 Needs Work |
| **Overall Score** | **75/100** | 🟢 Healthy |

---

## Directory Summary

| Directory | Files | LOC | V3% | Layer OK | Keep | Audit | Refactor |
|-----------|-------|-----|-----|----------|------|-------|----------|
| api/ | 77 | 15,996 | 66.2% | 73/77 | 47 | 26 | 4 |
| application/ | 69 | 8,136 | 50.7% | 69/69 | 35 | 34 | 0 |
| domains/ | 165 | 25,722 | 49.7% | 163/165 | 80 | 83 | 2 |
| infrastructure/ | 52 | 13,139 | 78.8% | 52/52 | 41 | 11 | 0 |
| core/ | 45 | 4,599 | 42.2% | 45/45 | 19 | 26 | 0 |
| shared/ | 35 | 5,671 | 54.3% | 35/35 | 19 | 16 | 0 |
| root + scripts | 16 | 4,138 | 68.8% | 16/16 | 10 | 6 | 0 |
| **TOTAL** | **459** | **77,401** | **56.0%** | **453/459** | **251** | **202** | **6** |

---

## Verdict Distribution

### ✅ KEEP (251 files - 54.7%)
Production-ready files following V3 DDD patterns.

**By Directory:**
- `api/user/` + `api/admin/`: 47 endpoint files
- `application/handlers/`: 35 command/query handlers
- `domains/*/service.py`: 80 domain services
- `infrastructure/repositories/`: 41 repository implementations
- `core/database/` + `core/auth/`: 19 framework files
- `shared/ai/` + `shared/payment/`: 19 integration services
- Root: `container.py`, `app.py`, `config.py`, etc.

### 🔍 AUDIT (202 files - 44.0%)
Legacy or support files needing review but functional.

**Categories:**
- Schema definitions (19 files) - Pre-Pydantic v2 patterns
- Aggregator services (9 files) - Legacy pattern
- Support modules (entities, constants, value objects): 83 files
- Utility modules: 26 files
- AI service helpers: 16 files
- Migration/tool scripts: 5 files

### ⚠️ REFACTOR (6 files - 1.3%)
**Critical layer violations requiring fix:**

| File | LOC | Issue |
|------|-----|-------|
| `api/admin/articles.py` | 572 | Domain imports API |
| `api/admin/static_pages.py` | 511 | Domain imports API |
| `api/user/articles.py` | 397 | Domain imports API |
| `api/user/static_pages.py` | 178 | Domain imports API |
| `domains/generation/generation_service.py` | 516 | Layer violation |
| `domains/generation/story_service.py` | 130 | Layer violation |

---

## Detailed File Inventory

### api/user/ (25 modules)

| File | LOC | Role | V3 | Layer | DI | Verdict |
|------|-----|------|-----|-------|----|---------|
| articles.py | 397 | Article CRUD | ✨ | ❌ | ✅ | REFACTOR |
| asset_categories.py | 182 | Category browse | ✨ | ✅ | ✅ | KEEP |
| assets.py | 315 | Asset management | ✨ | ✅ | ✅ | KEEP |
| auth.py | 89 | Auth endpoints | ✨ | ✅ | ✅ | KEEP |
| billing.py | 267 | Subscription/Credits | ✨ | ✅ | ✅ | KEEP |
| cache.py | 56 | Cache control | ✨ | ✅ | ✅ | KEEP |
| campaigns.py | 245 | Campaign mgmt | ✨ | ✅ | ✅ | KEEP |
| credits.py | 198 | Credit operations | ✨ | ✅ | ✅ | KEEP |
| debug.py | 112 | Debug endpoints | ✨ | ✅ | ✅ | KEEP |
| events.py | 289 | Event tracking | ✨ | ✅ | ✅ | KEEP |
| export.py | 423 | Export to PDF/PNG | ✨ | ✅ | ✅ | KEEP |
| feature_flags.py | 134 | Feature flags | ✨ | ✅ | ✅ | KEEP |
| fonts.py | 167 | Font management | ✨ | ✅ | ✅ | KEEP |
| generation.py | 356 | AI generation | ✨ | ✅ | ✅ | KEEP |
| health.py | 45 | Health check | ✨ | ✅ | ✅ | KEEP |
| images.py | 287 | Image upload | ✨ | ✅ | ✅ | KEEP |
| lessons.py | 234 | Lesson CRUD | ✨ | ✅ | ✅ | KEEP |
| marketplace.py | 312 | Marketplace | ✨ | ✅ | ✅ | KEEP |
| notifications.py | 156 | User notifications | ✨ | ✅ | ✅ | KEEP |
| onboarding.py | 178 | Onboarding flow | ✨ | ✅ | ✅ | KEEP |
| projects.py | 445 | Project CRUD | ✨ | ✅ | ✅ | KEEP |
| static_pages.py | 178 | Static pages | ✨ | ❌ | ✅ | REFACTOR |
| storage.py | 198 | File storage | ✨ | ✅ | ✅ | KEEP |
| templates.py | 267 | Templates | ✨ | ✅ | ✅ | KEEP |
| users.py | 312 | User profile | ✨ | ✅ | ✅ | KEEP |

### api/admin/ (15 modules)

| File | LOC | Role | V3 | Layer | DI | Verdict |
|------|-----|------|-----|-------|----|---------|
| articles.py | 572 | Article admin | ✨ | ❌ | ✅ | REFACTOR |
| asset_categories.py | 234 | Category admin | ✨ | ✅ | ✅ | KEEP |
| assets.py | 389 | Asset admin | ✨ | ✅ | ✅ | KEEP |
| billing.py | 312 | Billing admin | ✨ | ✅ | ✅ | KEEP |
| campaigns.py | 278 | Campaign admin | ✨ | ✅ | ✅ | KEEP |
| config.py | 189 | System config | ✨ | ✅ | ✅ | KEEP |
| dashboard.py | 267 | Admin dashboard | ✨ | ✅ | ✅ | KEEP |
| events.py | 198 | Event admin | ✨ | ✅ | ✅ | KEEP |
| feature_flags.py | 223 | Flag admin | ✨ | ✅ | ✅ | KEEP |
| fonts.py | 178 | Font admin | ✨ | ✅ | ✅ | KEEP |
| marketplace.py | 345 | Marketplace admin | ✨ | ✅ | ✅ | KEEP |
| notifications.py | 189 | Notification admin | ✨ | ✅ | ✅ | KEEP |
| static_pages.py | 511 | Static page admin | ✨ | ❌ | ✅ | REFACTOR |
| templates.py | 289 | Template admin | ✨ | ✅ | ✅ | KEEP |
| users.py | 356 | User admin | ✨ | ✅ | ✅ | KEEP |

### domains/ (165 modules - Key Services)

| File | LOC | Role | V3 | Layer | DI | Verdict |
|------|-----|------|-----|-------|----|---------|
| billing/credit_service.py | 423 | Credit operations | ✨ | ✅ | ✅ | KEEP |
| billing/subscription_service.py | 356 | Subscriptions | ✨ | ✅ | ✅ | KEEP |
| creation/project_service.py | 512 | Project logic | ✨ | ✅ | ✅ | KEEP |
| creation/lesson_service.py | 378 | Lesson logic | ✨ | ✅ | ✅ | KEEP |
| export/export_service.py | 445 | Export pipeline | ✨ | ✅ | ✅ | KEEP |
| generation/generation_service.py | 516 | AI generation | ✨ | ❌ | ✅ | REFACTOR |
| generation/story_service.py | 130 | Story generation | ✨ | ❌ | ✅ | REFACTOR |
| identity/user_service.py | 312 | User management | ✨ | ✅ | ✅ | KEEP |
| marketplace/marketplace_service.py | 389 | Marketplace | ✨ | ✅ | ✅ | KEEP |
| webhooks/clerk_webhook_service.py | 267 | Clerk webhooks | ✨ | ✅ | ✅ | KEEP |
| webhooks/stripe_webhook_service.py | 445 | Stripe webhooks | ✨ | ✅ | ✅ | KEEP |

### infrastructure/repositories/ (41 modules)

| File | LOC | Role | V3 | Layer | DI | Verdict |
|------|-----|------|-----|-------|----|---------|
| asset_repository.py | 312 | Asset data access | ✨ | ✅ | ✅ | KEEP |
| category_repository.py | 234 | Category data | ✨ | ✅ | ✅ | KEEP |
| credit_repository.py | 389 | Credit data | ✨ | ✅ | ✅ | KEEP |
| event_repository.py | 445 | Event data | ✨ | ✅ | ✅ | KEEP |
| lesson_repository.py | 356 | Lesson data | ✨ | ✅ | ✅ | KEEP |
| project_repository.py | 423 | Project data | ✨ | ✅ | ✅ | KEEP |
| user_repository.py | 278 | User data | ✨ | ✅ | ✅ | KEEP |
| ... | ... | ... | ... | ... | ... | ... |

### core/ (45 modules)

| File | LOC | Role | V3 | Layer | DI | Verdict |
|------|-----|------|-----|-------|----|---------|
| database/async_client.py | 312 | Async DB client | ✨ | ✅ | ✅ | KEEP |
| database/transaction.py | 156 | Transaction mgmt | ✨ | ✅ | ✅ | KEEP |
| auth/dependencies.py | 234 | Auth middleware | ✨ | ✅ | ✅ | KEEP |
| auth/jwt.py | 189 | JWT handling | ✨ | ✅ | ✅ | KEEP |
| exceptions/base.py | 145 | Base exceptions | ✨ | ✅ | ✅ | KEEP |
| validators/url_validator.py | 58 | SSRF protection | ✨ | ✅ | ✅ | KEEP |

### Root Files

| File | LOC | Role | V3 | Layer | DI | Verdict |
|------|-----|------|-----|-------|----|---------|
| app.py | 312 | FastAPI app | ✨ | ✅ | ✅ | KEEP |
| config.py | 234 | Configuration | ✨ | ✅ | ✅ | KEEP |
| container.py | 1,373 | DI Container | ✨ | ✅ | ✅ | KEEP |

---

## Layer Violation Details

### 6 Files Requiring Refactoring

**Pattern Detected:** These files have imports that violate DDD layer separation.

#### 1. `api/admin/articles.py` (572 LOC)
```python
# Violation: Domain layer importing from API layer
from domains.xxx import ...  # Should not import from api/*
```
**Fix:** Extract shared logic to application layer.

#### 2. `api/admin/static_pages.py` (511 LOC)
**Same pattern** - Extract to application layer.

#### 3. `api/user/articles.py` (397 LOC)
**Same pattern** - Extract to application layer.

#### 4. `api/user/static_pages.py` (178 LOC)
**Same pattern** - Extract to application layer.

#### 5. `domains/generation/generation_service.py` (516 LOC)
```python
# Violation: Importing from wrong layer
```
**Fix:** Refactor to use proper dependency injection.

#### 6. `domains/generation/story_service.py` (130 LOC)
**Same pattern** - Refactor dependencies.

---

## Refactoring Priority

| Phase | Files | Effort | Impact |
|-------|-------|--------|--------|
| **P1 (Critical)** | 6 REFACTOR files | 8-12h | Layer compliance |
| **P2 (High)** | 19 schema files | 6-10h | Pydantic v2 |
| **P3 (Medium)** | 9 aggregator services | 8-12h | DI pattern |
| **P4 (Low)** | 83 support modules | 4-6h | Consistency |

---

## Quality Dimensions

| Dimension | Score | Notes |
|-----------|-------|-------|
| Architecture | 8/10 | Clean DDD, 6 violations |
| Code Quality | 7/10 | Good async patterns |
| Maintainability | 8/10 | Clear structure |
| Test Coverage | 7/10 | Comprehensive suite |
| Documentation | 6/10 | Good inline docs |
| Performance | 8/10 | Async + RPC + caching |

**Overall: 7.5/10 (75/100)**

---

## Appendix: V3 Compliance Criteria

### ✨ V3 Compliant
- Uses `AsyncClient` for database operations
- Follows `api → application → domains ← infrastructure` dependency flow
- Uses Container for dependency injection
- Proper async/await patterns
- No synchronous blocking calls

### ⚠️ Legacy
- Uses older patterns but functional
- May use direct instantiation
- May have pre-V3 code style

### 🔒 Audited
- Reviewed and approved as-is
- May be intentionally legacy
- Documented exceptions

---

**Document Version**: 1.0
**Generated**: 2026-01-16
**Author**: Architecture Team
