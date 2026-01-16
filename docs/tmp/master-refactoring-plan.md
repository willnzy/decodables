# Master Refactoring Plan v1.1

> **Role**: Chief Refactoring Execution Officer
> **Date**: 2026-01-16
> **Stage**: Pre-launch Architecture Cleanup
> **Reference**: `backend-comprehensive-audit.md v2.1`

---

## Executive Summary

This is the **atomic, executable, zero-logic-gap** refactoring plan for Make Decodables backend.

**Core Principles (四大铁律)**:
1. **Ruthless Deletion** - Delete, don't deprecate
2. **Architecture Conformity** - Strict V3 Container Pattern + DDD
3. **Simplification** - Guard Clauses, merge duplicates, no over-engineering
4. **Safety First** - Preserve auth, billing atomicity, complete type hints

**Scope**:
- 80 issues (10 CRITICAL, 27 HIGH, 28 MEDIUM, 15 LOW)
- Estimated: 127.5h → Optimized: ~100h (aggressive cleanup)
- Net code reduction: 500+ lines

---

## Chapter 1: The Kill List (清理清单)

> **Priority**: Execute FIRST before any refactoring
> **Estimated Time**: 1.5 hour
> **Risk**: LOW (no business logic affected)

### 1.1 Pre-Deletion Verification: test_themes.py

**MANDATORY CHECK before deletion**:

The file `tests/test_themes.py` contains 336 lines of well-structured test logic for:
- Dynamic date calculations (Thanksgiving, Black Friday, Mother's Day, etc.)
- Fixed date rule parsing (Christmas, Valentine's, New Year wrap-around)
- `is_theme_active()` integration tests
- Edge case handling

**Verification Steps**:
```bash
# 1. Check if themes module exists anywhere
grep -r "routers.themes" --include="*.py" | grep -v test
grep -r "calculate_dynamic_date" --include="*.py" | grep -v test
grep -r "is_theme_active" --include="*.py" | grep -v test

# 2. If themes functionality exists elsewhere, migrate tests
# 3. If themes functionality is deprecated/removed, safe to delete
```

**Decision Matrix**:

| Scenario | Action |
|----------|--------|
| `routers.themes` exists | Fix import path, keep tests |
| Functions exist in different module | Update imports, keep tests |
| Themes functionality completely removed | DELETE (orphan) |
| Themes functionality planned for future | Move to `tests/archived/` |

**Current Assessment**: `routers.themes` does NOT exist. Functions `calculate_dynamic_date`, `is_theme_active`, `_check_fixed_date` are NOT found in production code. **SAFE TO DELETE** as orphan file.

### 1.2 Files to DELETE (物理删除文件)

```bash
# ============================================================
# ORPHAN TEST FILE - References non-existent module
# ============================================================
[DELETE] tests/test_themes.py
# Reason: Imports routers.themes which does not exist (line 13)
# Verified: File exists, 336 lines, no production dependency
# Pre-check: ✅ Confirmed no valuable logic to migrate

# ============================================================
# TEMPORARY MIGRATION SCRIPTS - v1→v2 migration complete
# ============================================================
[DELETE] scripts/tmp/compare_v1_v2_apis.py
# Reason: One-time v1/v2 API comparison tool, migration complete
# Verified: 16,356 bytes, outputs to docs/tmp/

[DELETE] scripts/tmp/verify_v2_endpoints.py
# Reason: One-time v2 endpoint verification, migration complete
# Verified: 8,715 bytes, verification script

[DELETE] scripts/tmp/quick_api_check.sh
# Reason: Quick bash utility for API comparison, no longer needed
# Verified: 783 bytes, shell script

[DELETE] scripts/tmp/add_recovery_constraints_indexes.py
# Reason: Database migration script, should be in migrations/v2/
# Verified: 9,082 bytes, schema modification (move logic if needed)
```

### 1.3 Code Blocks to DELETE (删除代码块)

| File | Lines | Description | Action |
|------|-------|-------------|--------|
| `app.py` | 255-372 | Commented-out deprecated route imports | DELETE 37 lines |
| `domains/identity/constants.py` | 47-60 | DEPRECATED tier mappings | DELETE 13 lines |
| `domains/shared/access_control.py` | 175-210 | 3 deprecated methods | DELETE 35 lines |

**Total Lines to Delete**: ~85 lines

### 1.4 Duplicates to CONSOLIDATE (合并重复)

| Duplicate | Location 1 | Location 2 | Action |
|-----------|------------|------------|--------|
| `AnalyticsEventsRequest` | `api/user/analytics.py:112` | `api/schemas/admin/analytics.py:24` | KEEP in schemas/, DELETE from api/user/ |
| `_is_allowed_url()` | `api/user/export.py:101-121` | Called by `domains/export/` | MOVE to `core/validators/url_validator.py` |

### 1.5 Documentation to CREATE (Phase 0)

**MANDATORY**: Create technical documentation for Webhook Retry mechanism before refactoring.

```
[CREATE] docs/main/WEBHOOK-RETRY-MECHANISM.md
```

**Content Outline**:
```markdown
# Webhook Retry Mechanism (P3-022)

## Overview
Exponential backoff retry system for failed Stripe/Clerk webhooks.

## Architecture
- Service: `domains/webhooks/webhook_retry_service.py`
- Repository: `infrastructure/repositories/webhook_repository.py`
- API: `api/admin/webhooks_retry.py`
- Scheduler: `scheduler.py`

## Retry Strategy
- Max retries: 5 (configurable via WEBHOOK_MAX_RETRIES)
- Delays: 1min → 5min → 15min → 1h → 2h (exponential backoff)
- Max age: 72h (after which webhooks are marked permanently failed)
- Batch size: 50 per run

## Key Functions
- `WebhookRetryService.should_retry()`: Eligibility check
- `WebhookRetryService.get_retry_delay()`: Backoff calculation
- `WebhookRetryService.retry_stripe_webhooks()`: Stripe retry logic
- `WebhookRetryService.retry_clerk_webhooks()`: Clerk retry logic

## Configuration (config.py)
- WEBHOOK_MAX_RETRIES: 5
- WEBHOOK_RETRY_DELAYS: [60, 300, 900, 3600, 7200]
- WEBHOOK_MAX_RETRY_AGE_HOURS: 72
- WEBHOOK_RETRY_BATCH_SIZE: 50
- WEBHOOK_SCHEDULER_INTERVAL: 60

## Monitoring
- Logs: `[Webhook Retry]` prefix
- Stats returned: {processed, failed, skipped}
```

### 1.6 Execution Commands

```bash
# Step 0: Create webhook retry documentation
# (Use Write tool to create docs/main/WEBHOOK-RETRY-MECHANISM.md)

# Step 1: Verify test_themes.py has no valuable logic to migrate
grep -r "calculate_dynamic_date\|is_theme_active" --include="*.py" | grep -v test
# If no results, proceed with deletion

# Step 2: Delete orphan files
rm tests/test_themes.py
rm scripts/tmp/compare_v1_v2_apis.py
rm scripts/tmp/verify_v2_endpoints.py
rm scripts/tmp/quick_api_check.sh
rm scripts/tmp/add_recovery_constraints_indexes.py

# Step 3: Commit deletion
git add -A
git commit -m "chore: remove orphan test file and obsolete migration scripts

- Delete tests/test_themes.py (imports non-existent routers.themes)
- Delete scripts/tmp/*.py and *.sh (v1→v2 migration complete)
- Add webhook retry mechanism documentation
- Net reduction: 5 files, ~400 lines"

# Step 4: Code block cleanup (done via Edit tool)
# - app.py: Remove commented imports
# - constants.py: Remove DEPRECATED mappings
# - access_control.py: Remove deprecated methods
```

---

## Chapter 2: Architecture Migration Sequence (架构迁移序列)

> **CRITICAL**: Execute in strict order - dependencies flow downward
> **Total Estimated Time**: 68h

### Step 1: Core/Shared Layer (4h)

**Goal**: Create shared utilities that all layers can safely import

#### Task 1.1: Create URL Validator in Core (2h)

**Purpose**: Move SSRF protection to core layer (currently in API layer, called by Domain)

```
[CREATE] core/validators/url_validator.py
[MOVE FROM] api/user/export.py:101-121 (_is_allowed_url)
[UPDATE] api/user/export.py - import from core/
[UPDATE] domains/export/export_service.py:229,465 - import from core/
```

**Before** (Layer Violation):
```python
# domains/export/export_service.py
async def export_project_zip(...):
    from api.user.export import _is_allowed_url  # ❌ Domain→API
    valid_urls = [url for url in image_urls if _is_allowed_url(url)]
```

**After** (Correct):
```python
# core/validators/url_validator.py
"""
URL validation utilities for SSRF protection.
Placed in core/ layer to be accessible by all layers without violating DDD.
"""
from typing import Set
from urllib.parse import urlparse

ALLOWED_IMAGE_HOSTS: Set[str] = {
    "images.unsplash.com",
    "cdn.makedecodables.com",
    "fal.media",
    "storage.googleapis.com",
    # Add other trusted hosts
}

def is_allowed_url(url: str) -> bool:
    """
    Validate URL against SSRF attacks.
    Only allows URLs from trusted image hosting providers.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.netloc in ALLOWED_IMAGE_HOSTS
    except Exception:
        return False
```

```python
# domains/export/export_service.py
from core.validators.url_validator import is_allowed_url  # ✅ Core layer

# api/user/export.py
from core.validators.url_validator import is_allowed_url  # ✅ Single source
```

#### Task 1.2: Move Generation Helpers to Domain (2h)

**Purpose**: Fix Domain→Application import violation

```
[MOVE] application/services/generation_helpers.py → domains/generation/helpers.py
[UPDATE] domains/generation/generation_service.py:34-38
[UPDATE] domains/generation/story_service.py:29
[UPDATE] Any application/ files that import these helpers
```

**Before** (Layer Violation):
```python
# domains/generation/generation_service.py
from application.services.generation_helpers import (  # ❌ Domain→Application
    calculate_cost,
    get_base_cost,
    build_generation_record,
)
```

**After** (Correct):
```python
# domains/generation/helpers.py (new location)
"""
Generation cost calculation and record building utilities.
Domain-level helpers for generation business logic.
"""

def calculate_cost(tier: str, operation: str, quantity: int = 1) -> int:
    """Calculate credit cost based on tier and operation type."""
    ...

def get_base_cost(operation: str) -> int:
    """Get base credit cost for an operation."""
    ...

def build_generation_record(user_id: str, prompt: str, result: dict) -> dict:
    """Build a generation history record."""
    ...
```

```python
# domains/generation/generation_service.py
from domains.generation.helpers import (  # ✅ Same layer
    calculate_cost,
    get_base_cost,
    build_generation_record,
)
```

---

### Step 2: Infrastructure Layer (12h)

**Goal**: Standardize Repository interfaces, ensure all repos are registered in Container

#### Task 2.1: Audit and Register Missing Handlers (4h)

**Problem**: 16 handlers defined but not registered in Container

| Handler | Location | Status |
|---------|----------|--------|
| `ExportProjectCommandHandler` | `application/commands/export/` | ❌ Not Registered |
| `BatchDeleteGenerationsHandler` | `application/commands/generation/` | ❌ Not Registered |
| `RefundCreditsCommandHandler` | `application/commands/billing/` | ❌ Not Registered |
| ... (13 more) | Various | ❌ Not Registered |

**Action**: Add all 16 handlers to `container.py`:
```python
# container.py - Add missing handler registrations

# Export handlers
async def get_export_project_handler(self) -> ExportProjectCommandHandler:
    return ExportProjectCommandHandler(
        project_repo=await self.get_project_repository(),
        export_service=await self.get_export_service(),
    )

# ... repeat for all 16 handlers
```

#### Task 2.2: Verify Repository Interfaces (4h)

**Goal**: Ensure all repositories implement their interfaces correctly

```
[VERIFY] domains/*/repository.py interfaces
[CHECK] infrastructure/repositories/*_repository.py implementations
[FIX] Any missing interface methods
```

#### Task 2.3: Audit config.py for Hardcoded Secrets (4h) 🔒 NEW

**Purpose**: Ensure ALL sensitive values come from environment variables

**Current State of config.py**:
```python
# ✅ CORRECT - Using environment variables
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")
CLERK_PEM_PUBLIC_KEY = os.environ.get("CLERK_PEM_PUBLIC_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

# ⚠️ REVIEW NEEDED - Default values may be sensitive
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@makedecodables.com")
SUPPORT_EMAIL_FROM = os.environ.get("SUPPORT_EMAIL_FROM", "noreply@makedecodables.com")
```

**Audit Checklist**:

| Config Variable | Source | Status | Action |
|-----------------|--------|--------|--------|
| `CLERK_WEBHOOK_SECRET` | env | ✅ | - |
| `CLERK_PEM_PUBLIC_KEY` | env | ✅ | - |
| `STRIPE_WEBHOOK_SECRET` | env | ✅ | - |
| `RESEND_API_KEY` | env | ✅ | - |
| `OPENAI_ASSISTANT_ID` | env | ✅ | - |
| `CORS_ORIGINS` | hardcoded list | ⚠️ | Move to env in production |
| `WEBHOOK_*` configs | env with defaults | ✅ | Acceptable defaults |

**Actions**:
1. Scan entire codebase for hardcoded secrets:
   ```bash
   grep -rn "sk_live\|sk_test\|pk_live\|pk_test" --include="*.py"
   grep -rn "password\s*=\s*['\"]" --include="*.py"
   grep -rn "api_key\s*=\s*['\"]" --include="*.py"
   ```

2. Add validation for required secrets:
   ```python
   # config.py - Add at end
   def validate_production_config():
       """Validate that all required secrets are configured in production."""
       if not IS_PRODUCTION:
           return

       required_secrets = [
           ("CLERK_WEBHOOK_SECRET", CLERK_WEBHOOK_SECRET),
           ("CLERK_PEM_PUBLIC_KEY", CLERK_PEM_PUBLIC_KEY),
           ("STRIPE_WEBHOOK_SECRET", STRIPE_WEBHOOK_SECRET),
       ]

       missing = [name for name, value in required_secrets if not value]
       if missing:
           raise RuntimeError(f"Missing required secrets in production: {missing}")
   ```

3. Move CORS_ORIGINS to environment variable:
   ```python
   # Before
   CORS_ORIGINS: List[str] = [
       "http://localhost:3000",
       "https://make-decodables.vercel.app",
       "https://decodables-production.up.railway.app"
   ]

   # After
   CORS_ORIGINS: List[str] = os.environ.get(
       "CORS_ORIGINS",
       "http://localhost:3000,https://make-decodables.vercel.app"
   ).split(",")
   ```

---

### Step 3: Domain Layer (32h)

**Goal**: Purify Domain layer - remove ALL API/Application dependencies

#### Task 3.1: Create Domain Exceptions (8h)

**Problem**: 65+ HTTPException in Domain layer

**Solution**: Create domain-specific exceptions

```
[CREATE] domains/billing/exceptions.py
[CREATE] domains/identity/exceptions.py (extend existing)
[CREATE] domains/creation/exceptions.py
[CREATE] domains/marketplace/exceptions.py
[CREATE] domains/webhooks/exceptions.py
```

**Example - domains/billing/exceptions.py**:
```python
"""
Billing domain exceptions.
These are caught by API layer and converted to HTTP responses.
"""
from core.exceptions import DomainException

class BillingError(DomainException):
    """Base billing error."""
    pass

class InsufficientCreditsError(BillingError):
    """User does not have enough credits for operation."""
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient credits: need {required}, have {available}")

class PaymentProcessingError(BillingError):
    """Error processing payment with Stripe."""
    pass

class SubscriptionNotFoundError(BillingError):
    """Subscription not found for user."""
    pass

class RefundNotAllowedError(BillingError):
    """Refund not allowed for this transaction."""
    pass
```

#### Task 3.2: Replace HTTPException in Domain Services (16h)

**Files to modify** (by priority):

| File | HTTPException Count | Priority |
|------|---------------------|----------|
| `domains/webhooks/stripe_webhook_service.py` | 23 | 🔴 CRITICAL |
| `domains/billing/service.py` | 15 | 🔴 CRITICAL |
| `domains/identity/service.py` | 12 | 🟠 HIGH |
| `domains/creation/service.py` | 8 | 🟠 HIGH |
| `domains/marketplace/service.py` | 7 | 🟡 MEDIUM |

**Before**:
```python
# domains/billing/service.py
from fastapi import HTTPException  # ❌

async def deduct_credits(self, user_id: str, amount: int):
    balance = await self.credit_repo.get_balance(user_id)
    if balance < amount:
        raise HTTPException(400, "Insufficient credits")  # ❌
```

**After**:
```python
# domains/billing/service.py
from domains.billing.exceptions import InsufficientCreditsError  # ✅

async def deduct_credits(self, user_id: str, amount: int):
    balance = await self.credit_repo.get_balance(user_id)
    if balance < amount:
        raise InsufficientCreditsError(required=amount, available=balance)  # ✅
```

#### Task 3.3: API Layer Exception Translation (8h)

**Add exception handlers to API layer**:
```python
# api/user/billing.py
from domains.billing.exceptions import (
    InsufficientCreditsError,
    PaymentProcessingError,
)

@router.post("/deduct")
async def deduct_credits(...):
    try:
        await billing_service.deduct_credits(user_id, amount)
    except InsufficientCreditsError as e:
        raise HTTPException(400, detail=str(e))  # ✅ API layer converts
    except PaymentProcessingError as e:
        raise HTTPException(502, detail="Payment processing failed")
```

---

### Step 4: API Layer (20h)

**Goal**: All API files use Container for dependency injection, no direct Repository access

#### Task 4.1: Fix Direct Repository Calls (16h)

**Problem**: 31 API files directly instantiate Repository (bypassing Service layer)

**Most Severe Violations** (fix first):

| File | Instantiation Count | Priority |
|------|---------------------|----------|
| `api/admin/users.py` | 12 | 🔴 CRITICAL |
| `api/admin/subscriptions.py` | 9 | 🔴 CRITICAL |
| `api/admin/metrics.py` | 6 | 🟠 HIGH |
| `api/admin/articles.py` | 6 | 🟠 HIGH |
| `api/admin/events.py` | 4 | 🟠 HIGH |
| `api/user/projects.py` | 2 | 🟠 HIGH |
| ... (25 more files) | Various | Various |

**Before** (Wrong):
```python
# api/admin/users.py
@router.get("/search")
async def search_users_api(query: str):
    db = await get_async_db_client()
    user_repo = SupabaseUserRepository(db)  # ❌ Direct instantiation
    return await user_repo.search(query)
```

**After** (Correct):
```python
# api/admin/users.py
@router.get("/search")
async def search_users_api(
    query: str,
    user_service: UserService = Depends(get_user_service)  # ✅ DI
):
    return await user_service.search(query)

# Dependency function
async def get_user_service() -> UserService:
    container = get_container()
    return await container.get_user_service()
```

#### Task 4.2: Standardize Dependency Injection Pattern (4h)

**Create consistent DI helpers**:
```python
# api/dependencies/services.py
"""
Service dependency injection helpers.
All API endpoints should use these instead of direct Container access.
"""
from functools import lru_cache
from container import Container

@lru_cache()
def get_container() -> Container:
    return Container()

async def get_user_service():
    return await get_container().get_user_service()

async def get_billing_service():
    return await get_container().get_billing_service()

async def get_project_service():
    return await get_container().get_project_service()

# ... one for each service
```

---

## Chapter 3: Critical Logic Fixes (紧急逻辑修复)

> **Priority**: Execute in Phase 1 (Days 1-3)
> **These issues can cause data loss or security breaches**

### 3.1 CRITICAL: time.sleep() Blocking Event Loop (2h)

**Problem**: 3 occurrences in async functions block entire FastAPI event loop

**File**: `application/services/ai_chat_service.py`

| Line | Context | Impact |
|------|---------|--------|
| 83 | Polling loop for OpenAI response | Blocks all concurrent requests |
| 98 | Retry backoff | Blocks all concurrent requests |
| 179 | Retry backoff in vision chat | Blocks all concurrent requests |

**Before** (Blocking):
```python
# application/services/ai_chat_service.py:75-100
async def chat_with_assistant(message: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            run = openai_client.beta.threads.runs.create(...)
            while run.status in ["queued", "in_progress"]:
                time.sleep(0.5)  # ❌ Line 83 - BLOCKS EVENT LOOP
                run = openai_client.beta.threads.runs.retrieve(...)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))  # ❌ Line 98 - BLOCKS EVENT LOOP
```

**After** (Non-blocking + Guard Clauses):
```python
# application/services/ai_chat_service.py
import asyncio
from typing import Optional

async def chat_with_assistant(message: str, max_retries: int = 3) -> dict:
    """
    Send message to OpenAI Assistant and await response.

    Uses asyncio.sleep() for non-blocking waits - critical for
    concurrent request handling in FastAPI.
    """
    if not openai_client:
        raise ServiceUnavailableError("OpenAI client not initialized")

    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            return await _execute_assistant_chat(message)
        except (TimeoutError, APIError) as e:
            last_error = e
            logger.warning(
                f"[AI Chat] Attempt {attempt + 1}/{max_retries} failed",
                error=str(e)
            )

        # Guard: Skip sleep on last attempt
        if attempt >= max_retries - 1:
            break

        await asyncio.sleep(1 * (attempt + 1))  # ✅ Non-blocking

    raise last_error or ServiceUnavailableError("AI Chat failed after retries")


async def _execute_assistant_chat(message: str) -> dict:
    """Execute single chat attempt with polling."""
    run = openai_client.beta.threads.runs.create(...)

    while run.status in ["queued", "in_progress"]:
        await asyncio.sleep(0.5)  # ✅ Non-blocking polling
        run = openai_client.beta.threads.runs.retrieve(...)

    if run.status == "failed":
        raise APIError(f"Assistant run failed: {run.last_error}")

    return _extract_response(run)
```

---

### 3.2 CRITICAL: Missing await Statements (16h)

**Problem**: 152+ async database operations called without await

**Impact**:
- Database operations silently don't execute
- Payment succeeds but credits not added
- Data inconsistency

**Most Critical Files**:

| File | Missing await Count | Impact |
|------|---------------------|--------|
| `domains/webhooks/stripe_webhook_service.py` | 47 | 🔴 Payment data loss |
| `domains/billing/service.py` | 23 | 🔴 Credit data loss |
| `infrastructure/repositories/` | 38 | 🔴 All data operations |

**Detection Pattern**:
```bash
# Find missing await on repository calls
grep -r "self\.\w*_repo\.\w*(" domains/ --include="*.py" | grep -v "await" | grep -v "#"
```

**Before** (Missing await):
```python
# domains/webhooks/stripe_webhook_service.py
async def handle_checkout_completed(self, session):
    # ❌ Missing await - payment record not created!
    self.payment_repo.create(user_id, amount, ...)

    # ❌ Missing await - credits not added!
    self.credit_repo.add_credits_permanent(user_id, credits, ...)
```

**After** (Correct):
```python
async def handle_checkout_completed(self, session):
    # ✅ Await ensures execution
    await self.payment_repo.create(user_id, amount, ...)
    await self.credit_repo.add_credits_permanent(user_id, credits, ...)
```

**Systematic Fix Approach**:
1. Run grep to find all missing await
2. Group by file
3. Fix one file at a time
4. Run tests after each file
5. Commit after each file

---

### 3.3 CRITICAL: JWT Audience Verification Disabled (4h)

**Problem**: JWT validation skips audience check, allowing tokens from other Clerk apps

**File**: `dependencies.py:47-52`

**Before** (Insecure):
```python
payload = jwt.decode(
    token,
    CLERK_PEM_PUBLIC_KEY,
    algorithms=["RS256"],
    options={"verify_aud": False}  # ❌ Accepts tokens from ANY Clerk app
)
```

**After** (Secure):
```python
from config import CLERK_APP_ID  # Add to config.py

payload = jwt.decode(
    token,
    CLERK_PEM_PUBLIC_KEY,
    algorithms=["RS256"],
    audience=CLERK_APP_ID,  # ✅ Only accept our app's tokens
    options={"verify_aud": True}
)
```

**Config Addition**:
```python
# config.py
CLERK_APP_ID = os.environ.get("CLERK_APP_ID")  # e.g., "app_xxxxx"
```

---

### 3.4 HIGH: CORS Wildcard Headers (1h)

**File**: `app.py:246-247`

**Before** (Security Risk):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # ❌ Allows any header
    expose_headers=["X-Request-ID", "X-Response-Time", "*"],  # ❌ Exposes all
)
```

**After** (Secure):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "X-Requested-With",
        "Accept",
        "Accept-Language",
    ],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)
```

---

### 3.5 HIGH: Sentry Captures AI Prompts (0.5h)

**File**: `app.py:39`

**Before** (PII Leak):
```python
sentry_sdk.init(
    ...
    include_prompts=True,  # ❌ Sends user prompts to Sentry
)
```

**After** (Secure):
```python
sentry_sdk.init(
    ...
    include_prompts=False,  # ✅ Don't send prompts
)
```

---

### 3.6 CRITICAL: Non-Atomic Credit Operations (8h)

**Problem**: Credit operations are not atomic - server crash between steps causes data loss

**File**: `domains/webhooks/stripe_webhook_service.py:251-279`

**Before** (Non-atomic):
```python
async def handle_checkout_completed(self, session):
    user_id = session.metadata.user_id
    credits = session.metadata.credits

    # Step 1: Record payment
    await self.payment_repo.create(user_id, amount, ...)

    # ⚠️ SERVER CRASHES HERE = Payment recorded but no credits!

    # Step 2: Add credits
    await self.credit_repo.add_credits_permanent(user_id, credits, ...)
```

**After** (Atomic via PostgreSQL RPC):

**Step 1: Create RPC Function**
```sql
-- migrations/v2/01_core_business.sql (add to end)

CREATE OR REPLACE FUNCTION process_credit_purchase(
    p_user_id TEXT,
    p_payment_id TEXT,
    p_amount_cents INTEGER,
    p_credits INTEGER,
    p_stripe_session_id TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_payment_record JSONB;
BEGIN
    -- Atomic transaction: both succeed or both fail

    -- 1. Create payment record
    INSERT INTO payments (
        user_id, payment_id, amount_cents, credits,
        stripe_session_id, status, created_at
    ) VALUES (
        p_user_id, p_payment_id, p_amount_cents, p_credits,
        p_stripe_session_id, 'completed', NOW()
    )
    RETURNING to_jsonb(payments.*) INTO v_payment_record;

    -- 2. Add permanent credits
    UPDATE profiles
    SET credits_permanent = credits_permanent + p_credits,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- 3. Create transaction log
    INSERT INTO credit_transactions (
        user_id, amount, type, description, created_at
    ) VALUES (
        p_user_id, p_credits, 'purchase',
        'Credit purchase: ' || p_credits || ' credits', NOW()
    );

    RETURN jsonb_build_object(
        'success', true,
        'payment', v_payment_record,
        'credits_added', p_credits
    );

EXCEPTION WHEN OTHERS THEN
    -- Transaction auto-rollbacks on error
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM
    );
END;
$$;
```

**Step 2: Use in Service**
```python
# domains/webhooks/stripe_webhook_service.py
async def handle_checkout_completed(self, session):
    """Process completed checkout with atomic credit addition."""
    user_id = session.metadata.get("user_id")
    credits = int(session.metadata.get("credits", 0))

    # Guard clauses
    if not user_id:
        raise WebhookProcessingError("Missing user_id in session metadata")
    if credits <= 0:
        raise WebhookProcessingError("Invalid credits amount")

    # Atomic operation via RPC
    result = await self.db.rpc(
        "process_credit_purchase",
        {
            "p_user_id": user_id,
            "p_payment_id": generate_payment_id(),
            "p_amount_cents": session.amount_total,
            "p_credits": credits,
            "p_stripe_session_id": session.id,
        }
    ).execute()

    if not result.data.get("success"):
        raise PaymentProcessingError(result.data.get("error"))

    logger.info(
        "Credit purchase processed atomically",
        user_id=user_id,
        credits=credits,
        payment_id=result.data["payment"]["payment_id"]
    )

    return result.data
```

---

### 3.7 HIGH: asyncio.run() in Running Event Loop (2h)

**Problem**: `asyncio.run()` cannot be called inside an already running event loop

**File**: `dependencies.py:349`

**Before** (Causes RuntimeError):
```python
@lru_cache()
def get_analytics_service() -> AnalyticsService:
    try:
        db_client = asyncio.run(get_async_db_client())  # ❌ Fails in FastAPI
    except RuntimeError:
        from core.database import supabase
        db_client = supabase  # Fallback to sync client
    ...
```

**After** (Proper async initialization):
```python
# Option 1: Make it async
async def get_analytics_service() -> AnalyticsService:
    db_client = await get_async_db_client()  # ✅
    repository = SupabaseAnalyticsEventsRepository(db_client)
    return AnalyticsService(repository)

# Option 2: Use sync client consistently
@lru_cache()
def get_analytics_service() -> AnalyticsService:
    from core.database import supabase  # Sync client
    repository = SupabaseAnalyticsEventsRepository(supabase)
    return AnalyticsService(repository)
```

---

### 3.8 HIGH: Upgrade /health Endpoint with Real Connectivity Checks (4h) 🆕 NEW

**Problem**: Current `/health` endpoint does basic checks but needs enhanced real connectivity verification.

**File**: `api/health.py`

**Current State Analysis**:
- ✅ Has `check_supabase_connection()` - queries `profiles` table
- ✅ Has `is_redis_available()` - checks Redis availability
- ⚠️ `check_supabase_connection()` is async but called without await on line 52
- ⚠️ No timeout handling for health checks
- ⚠️ No explicit TCP connectivity test

**Before** (Bug on line 52):
```python
@router.get("/health")
async def health_check(request: Request):
    redis_ok = is_redis_available()
    supabase_ok = check_supabase_connection()  # ❌ Missing await!
```

**After** (Fixed + Enhanced):
```python
import asyncio
from typing import TypedDict

class HealthStatus(TypedDict):
    status: str
    version: str
    environment: str
    services: dict
    latency_ms: dict


@router.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request) -> HealthStatus:
    """
    Basic health check with real connectivity verification.

    Checks:
    - Supabase: Executes actual query with 5s timeout
    - Redis: Executes PING command with 2s timeout

    Returns degraded status if Redis is down (non-critical),
    unhealthy status if Supabase is down (critical).
    """
    latency = {}

    # Check Supabase with timeout
    supabase_start = asyncio.get_event_loop().time()
    try:
        supabase_ok = await asyncio.wait_for(
            check_supabase_connection(),
            timeout=5.0
        )
        latency["supabase_ms"] = round(
            (asyncio.get_event_loop().time() - supabase_start) * 1000
        )
    except asyncio.TimeoutError:
        supabase_ok = False
        latency["supabase_ms"] = 5000  # Timeout

    # Check Redis with timeout
    redis_start = asyncio.get_event_loop().time()
    try:
        redis_ok = await asyncio.wait_for(
            check_redis_connection(),
            timeout=2.0
        )
        latency["redis_ms"] = round(
            (asyncio.get_event_loop().time() - redis_start) * 1000
        )
    except asyncio.TimeoutError:
        redis_ok = False
        latency["redis_ms"] = 2000  # Timeout

    # Determine overall status
    if redis_ok and supabase_ok:
        status = "healthy"
    elif supabase_ok:
        status = "degraded"  # Redis down but can operate
    else:
        status = "unhealthy"  # Database down

    return {
        "status": status,
        "version": API_VERSION,
        "environment": ENV,
        "services": {
            "supabase": "up" if supabase_ok else "down",
            "redis": "up" if redis_ok else "down",
        },
        "latency_ms": latency,
    }


async def check_redis_connection() -> bool:
    """
    Check Redis connectivity with actual PING command.
    Returns True if Redis responds to PING within timeout.
    """
    try:
        from core.cache.redis_provider import get_redis_client
        redis_client = get_redis_client()
        if not redis_client:
            return False
        # Execute actual PING command
        result = redis_client.ping()
        return result is True
    except Exception as e:
        logger.warning(f"[Health] Redis check failed: {e}")
        return False
```

---

## Chapter 4: Code Quality Standards (质量标准清单)

> **Mandatory Checklist for ALL code changes**

### 4.1 Documentation Standards

| Rule | Description | Enforcement |
|------|-------------|-------------|
| **Public Method Comments** | All public methods must have docstring explaining WHY, not just WHAT | Code Review |
| **English Only** | All comments and docstrings in English | Pre-commit |
| **No TODO in Production** | All TODO comments must be tracked in issue tracker | CI Check |

**Example**:
```python
async def deduct_credits(self, user_id: str, amount: int) -> CreditBalance:
    """
    Deduct credits from user's balance.

    Deduction order: monthly credits first, then permanent.
    This ensures users consume expiring credits before permanent ones,
    maximizing their value from subscription benefits.

    Args:
        user_id: The user's unique identifier
        amount: Number of credits to deduct

    Returns:
        Updated credit balance

    Raises:
        InsufficientCreditsError: If user doesn't have enough credits
    """
```

### 4.2 Async Programming Standards

| Rule | Description | Violation |
|------|-------------|-----------|
| **No time.sleep()** | Always use `await asyncio.sleep()` in async functions | 🔴 CRITICAL |
| **Await All Coroutines** | Every async method call must have `await` | 🔴 CRITICAL |
| **No asyncio.run()** | Never call `asyncio.run()` inside FastAPI handlers | 🔴 CRITICAL |
| **run_in_threadpool** | Use for CPU-bound or sync I/O in async context | 🟡 MEDIUM |

**Linting Rule (add to pyproject.toml)**:
```toml
[tool.ruff]
select = ["ASYNC"]  # Enable async linting rules
```

### 4.3 Input Validation Standards

| Rule | Description |
|------|-------------|
| **Pydantic Models** | All API request bodies must use Pydantic models |
| **Field Constraints** | Use Field() with min/max for numeric inputs |
| **Enum Validation** | Use Literal[] or Enum for fixed choices |
| **Path Validation** | Validate path parameters with regex patterns |

**Example**:
```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class CreditDeductRequest(BaseModel):
    amount: int = Field(..., ge=1, le=10000, description="Credits to deduct")
    operation: Literal["generation", "ocr", "export"] = Field(...)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
```

### 4.4 Exception Handling Standards

| Layer | Exception Type | Example |
|-------|----------------|---------|
| **Domain** | Domain Exceptions | `InsufficientCreditsError` |
| **Application** | Application Exceptions | `CommandValidationError` |
| **API** | HTTPException | `HTTPException(400, detail=...)` |
| **Infrastructure** | Infrastructure Exceptions | `DatabaseConnectionError` |

**Never**:
- ❌ Use HTTPException in Domain layer
- ❌ Use bare `except:` without specific type
- ❌ Swallow exceptions silently

### 4.5 Type Hints Standards

| Rule | Description |
|------|-------------|
| **100% Coverage** | All function parameters and returns must have type hints |
| **No Any** | Avoid `Any` type - use Union or specific types |
| **Generic Collections** | Use `list[T]` not `List[T]` (Python 3.9+) |
| **Optional Explicit** | Use `X | None` not `Optional[X]` (Python 3.10+) |

**Example**:
```python
# ✅ Correct
async def get_user(user_id: str) -> UserProfile | None:
    ...

# ❌ Wrong
async def get_user(user_id) -> Optional[UserProfile]:
    ...
```

### 4.6 Guard Clause Standards

| Rule | Description |
|------|-------------|
| **Early Return** | Return/raise early for invalid conditions |
| **Max 2 Nesting** | No more than 2 levels of if/for nesting |
| **Positive Conditions** | Prefer `if not valid:` over `if valid: ... else: raise` |

**Before** (Deep Nesting):
```python
async def process(data):
    if data:
        if data.user_id:
            if data.amount > 0:
                if data.type in VALID_TYPES:
                    return await do_process(data)
    return None
```

**After** (Guard Clauses):
```python
async def process(data):
    if not data:
        return None
    if not data.user_id:
        return None
    if data.amount <= 0:
        return None
    if data.type not in VALID_TYPES:
        return None

    return await do_process(data)
```

### 4.7 API Schema Standards (No Dict or Any) 🆕 NEW

| Rule | Description | Severity |
|------|-------------|----------|
| **No `dict` in Request Body** | All request bodies must use typed Pydantic models | 🔴 CRITICAL |
| **No `Any` in Schemas** | All fields must have explicit types | 🔴 CRITICAL |
| **No `Dict[str, Any]`** | Use typed dictionaries or specific models | 🟠 HIGH |

**❌ WRONG - Never do this**:
```python
class BadRequest(BaseModel):
    data: dict  # ❌ No type info
    metadata: Any  # ❌ Accepts anything
    options: Dict[str, Any]  # ❌ No value type

@router.post("/process")
async def process(data: dict):  # ❌ Untyped request body
    ...
```

**✅ CORRECT - Always use specific types**:
```python
class ProjectMetadata(BaseModel):
    page_count: int
    template_id: str | None = None
    tags: list[str] = []

class ProcessRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    action: Literal["export", "duplicate", "archive"]
    metadata: ProjectMetadata
    options: ProcessOptions  # Another typed model

@router.post("/process")
async def process(request: ProcessRequest):  # ✅ Typed request
    ...
```

**Enforcement**:
```bash
# Add to CI/pre-commit
grep -rn ": dict\b\|: Any\b\|Dict\[str, Any\]" api/schemas/ --include="*.py"
# Should return no results
```

### 4.8 Test Migration Check (Pre-Deletion) 🆕 NEW

| Rule | Description |
|------|-------------|
| **Verify Before Delete** | Before deleting any test file, verify no valuable logic needs migration |
| **Document Decision** | Record why tests are safe to delete or where they were migrated |

**Checklist for deleting test files**:
```markdown
## Test File Deletion Checklist

File: tests/test_xxx.py

1. [ ] Search for tested module in production code
   ```bash
   grep -r "module_name" --include="*.py" | grep -v test
   ```

2. [ ] If module exists: Update test imports, do NOT delete
3. [ ] If module removed: Check if similar functionality exists elsewhere
4. [ ] If functionality migrated: Move tests to new location
5. [ ] If functionality deprecated: Safe to delete, document reason

Decision: [DELETE/KEEP/MIGRATE]
Reason: [Explanation]
```

---

## Chapter 5: Execution Timeline

### Phase 0: Immediate Cleanup (1.5h)
- [ ] Create webhook retry mechanism documentation
- [ ] Verify test_themes.py has no valuable logic (see 1.1)
- [ ] Delete 5 orphan files
- [ ] Delete 85 lines of deprecated code
- [ ] Commit: `chore: cleanup orphan files and deprecated code`

### Phase 1: Critical Fixes (Days 1-3, 35.5h)
- [ ] P0-1: Fix 3x time.sleep() in ai_chat_service.py (2h)
- [ ] P0-2: Fix 152+ missing await statements (16h)
- [ ] P0-3: Fix JWT audience verification (4h)
- [ ] P0-4: Fix CORS wildcard headers (1h)
- [ ] P0-5: Fix Sentry include_prompts (0.5h)
- [ ] P0-6: Create atomic credit RPC (8h)
- [ ] P0-7: Upgrade /health endpoint with real connectivity checks (4h) 🆕

### Phase 2: Architecture Alignment (Week 1-2, 36.5h)
- [ ] P1-1: Fix Domain→API layer violation (2h)
- [ ] P1-2: Fix Domain→Application violation (2h)
- [ ] P1-3: Fix 31 API direct repo calls (8h)
- [ ] P1-4: Create Domain Exceptions (16h)
- [ ] P1-5: Register 16 missing handlers (4h)
- [ ] P1-6: Delete app.py commented code (0.5h)
- [ ] P1-7: Audit config.py for hardcoded secrets (4h) 🆕

### Phase 3: Performance & Quality (Week 2-3, 26h)
- [ ] P2-1: Fix N+1 queries (12h)
- [ ] P2-2: Create batch RPC functions (8h)
- [ ] P2-3: Fix remaining sync blocking (6h)

### Phase 4: Testing & Documentation (Week 3-4, 37h)
- [ ] P3-1: Webhooks tests 25%→60% (16h)
- [ ] P3-2: Export tests 30%→60% (12h)
- [ ] P3-3: Update documentation (8h)
- [ ] P3-4: Merge duplicate schemas (1h)

---

## Appendix A: Quick Reference Commands

```bash
# Find time.sleep in async
grep -rn "time\.sleep" --include="*.py" | grep -v test | grep -v __pycache__

# Find missing await on repo calls
grep -rn "self\.\w*_repo\.\w*(" domains/ --include="*.py" | grep -v "await"

# Find HTTPException in Domain
grep -rn "from fastapi import HTTPException" domains/

# Find Domain→API imports
grep -rn "from api\." domains/

# Find Domain→Application imports
grep -rn "from application\." domains/

# Find direct Repository instantiation in API
grep -rn "Repository(db" api/ --include="*.py"

# Find dict/Any in API schemas (should be empty)
grep -rn ": dict\b\|: Any\b\|Dict\[str, Any\]" api/schemas/ --include="*.py"

# Find hardcoded secrets (should be empty)
grep -rn "sk_live\|sk_test\|pk_live\|pk_test\|password\s*=\s*['\"]" --include="*.py"
```

---

## Appendix B: File Change Summary

| Action | Files | Lines Changed |
|--------|-------|---------------|
| DELETE | 5 files | -400 lines |
| DELETE CODE | 3 files | -85 lines |
| CREATE | 7 files | +350 lines |
| MODIFY | 45+ files | ~2100 lines |
| **NET** | - | **-135 lines** |

---

## Appendix C: New Tasks Summary (v1.1 Additions)

| Task | Phase | Hours | Description |
|------|-------|-------|-------------|
| Hardcoded Secrets Audit | 2 | 4h | Scan and secure config.py |
| /health Connectivity Upgrade | 1 | 4h | Add real DB/Redis checks with timeout |
| Webhook Retry Documentation | 0 | 0.5h | Document P3-022 mechanism |
| Test Migration Check | 0 | 0.5h | Verify test_themes.py before deletion |
| No Dict/Any Rule | 4 | - | Enforce in code review |

---

**Document Version**: v1.1
**Created**: 2026-01-16
**Updated**: 2026-01-16
**Author**: Chief Refactoring Execution Officer
**Status**: READY FOR EXECUTION

---

## Approval Checklist

- [ ] Kill List verified and approved
- [ ] Test migration check for test_themes.py completed
- [ ] Architecture migration sequence approved
- [ ] Critical fixes prioritized correctly
- [ ] Quality standards understood (including No Dict/Any rule)
- [ ] Timeline realistic
- [ ] New tasks (hardcoded secrets, /health upgrade) approved

**Next Step**: Upon approval, begin Phase 0 (Immediate Cleanup)
