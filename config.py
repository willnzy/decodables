"""
Configuration Module
Centralized configuration management

@module config
"""

import os
from typing import List

# Environment
ENV = os.environ.get("ENV", "development")
IS_PRODUCTION = ENV == "production"

# API Settings
API_TITLE = "MagicZine AI API v3.2"
API_VERSION = "3.2.0"

# Clerk Authentication
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")
CLERK_PEM_PUBLIC_KEY = os.environ.get("CLERK_PEM_PUBLIC_KEY")
# Test JWT Public Key (for integration testing without Clerk login)
# When configured, backend accepts both Clerk-signed and test-signed JWTs
# ⚠️ SECURITY: Only enabled in non-production environments!
_test_jwt_key = os.environ.get("TEST_JWT_PUBLIC_KEY")
TEST_JWT_PUBLIC_KEY = _test_jwt_key if not IS_PRODUCTION else None

# Log warning if test key is configured in production (should never happen)
if IS_PRODUCTION and _test_jwt_key:
    import logging
    logging.getLogger(__name__).critical(
        "🚨 SECURITY ALERT: TEST_JWT_PUBLIC_KEY is configured in PRODUCTION! "
        "This key will be IGNORED for security reasons. "
        "Remove TEST_JWT_PUBLIC_KEY from production environment variables immediately!"
    )
# v3.27.1: Authorized Party (azp) verification
# Clerk includes 'azp' in JWT by default (unlike 'aud')
# This is the frontend origin that requested the token
# Format: comma-separated list of allowed origins
# Example: "https://makedecodables.com,https://www.makedecodables.com"
CLERK_ALLOWED_ORIGINS = os.environ.get("CLERK_ALLOWED_ORIGINS", "")
# Legacy: CLERK_FRONTEND_API (kept for backwards compatibility, prefer CLERK_ALLOWED_ORIGINS)
CLERK_FRONTEND_API = os.environ.get("CLERK_FRONTEND_API")

# Stripe
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# Email (Resend)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@makedecodables.com")
SUPPORT_EMAIL_FROM = os.environ.get("SUPPORT_EMAIL_FROM", "noreply@makedecodables.com")

# OpenAI Assistant (for AI Support Chat)
OPENAI_ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

# CORS Settings
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",                       # Local development
    "https://make-decodables.vercel.app",          # Vercel production
    "https://decodables-staging.up.railway.app",   # Railway API (staging)
    "https://decodables-production.up.railway.app" # Railway API (production)
]

# Rate Limiting
RATE_LIMIT_DEFAULT = "100/minute"
RATE_LIMIT_GENERATE = "10/minute"
RATE_LIMIT_OCR = "10/minute"

# ==========================================
# ⚠️ DEPRECATED - DO NOT USE IN BUSINESS LOGIC
# ==========================================
# These constants are EMERGENCY FALLBACK ONLY.
# All values MUST be read from database via TierService/ConfigService.
#
# ✅ Correct usage:
#    cost = await tier_service.get_operation_cost("image_generation")
#
# ❌ Wrong usage:
#    cost = CREDITS_PER_IMAGE  # Never do this!
#
# Authoritative source: database system_configs table
# ==========================================
# CREDITS_PER_IMAGE = 5        # ❌ REMOVED - use tier_service.get_operation_cost("image_generation")
# CREDITS_PER_OCR = 10         # ❌ REMOVED - use tier_service.get_operation_cost("ocr")
# CREDITS_SIGNUP_BONUS = 50    # ❌ REMOVED - use tier_service.get_signup_bonus()
# CREDITS_MONTHLY_T2 = 100     # ❌ REMOVED - use tier_service.get_monthly_credits("t2")
# CREDITS_MONTHLY_T3 = 200     # ❌ REMOVED - use tier_service.get_monthly_credits("t3")

# Marketplace
MAX_LISTING_PRICE = 500
SELLER_REVENUE_PERCENT = 90  # Seller gets 90%, platform gets 10%

# Trial Period (Legacy - deprecated, use TierService.get_trial_duration_days() instead)
# This is kept for backward compatibility but should be migrated to system_configs
TRIAL_DAYS = 30  # Default: Free users get 30-day trial with full access

# Tiers (使用 t1/t2/t3 内部命名，display_name 从 database 读取)
VALID_TIERS = ["t1", "t2", "t3"]
MEMBER_TIERS = ["t2", "t3"]  # 付费会员

# Allowed Tiers Whitelist (PRD v3.2)
ALLOWED_TIERS_WHITELIST = [
    ["t1"],           # t1 only
    ["t2", "t3"],     # t2 and above
    ["t3"],           # t3 only
]

# ==========================================
# Webhook Retry Configuration (P3-022)
# ==========================================

# Maximum number of retry attempts for failed webhooks
WEBHOOK_MAX_RETRIES = int(os.environ.get("WEBHOOK_MAX_RETRIES", "5"))

# Retry delays in seconds (exponential backoff)
# Attempt 1: 60s, Attempt 2: 300s (5min), Attempt 3: 900s (15min),
# Attempt 4: 3600s (1h), Attempt 5: 7200s (2h)
WEBHOOK_RETRY_DELAYS = [60, 300, 900, 3600, 7200]

# How often to run the retry task scheduler (in seconds)
WEBHOOK_SCHEDULER_INTERVAL = int(os.environ.get("WEBHOOK_SCHEDULER_INTERVAL", "60"))

# Maximum age for retrying failed webhooks (in hours)
# After this time, failed webhooks are marked as permanently failed
WEBHOOK_MAX_RETRY_AGE_HOURS = int(os.environ.get("WEBHOOK_MAX_RETRY_AGE_HOURS", "72"))

# Batch size for processing failed webhooks in one run
WEBHOOK_RETRY_BATCH_SIZE = int(os.environ.get("WEBHOOK_RETRY_BATCH_SIZE", "50"))
