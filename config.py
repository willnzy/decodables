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
    "https://decodables-production.up.railway.app" # Railway API
]

# Rate Limiting
RATE_LIMIT_DEFAULT = "100/minute"
RATE_LIMIT_GENERATE = "10/minute"
RATE_LIMIT_OCR = "10/minute"

# ==========================================
# DEPRECATED: Credits Configuration
# ==========================================
# Use TierService for dynamic configuration from database.
# These values are EMERGENCY FALLBACK only.
# Authoritative source: database system_configs table
# ==========================================
CREDITS_PER_IMAGE = 5           # database: credits.cost.image_generation = 5
CREDITS_PER_OCR = 10            # database: credits.cost.ocr = 10
CREDITS_SIGNUP_BONUS = 50       # database: SIGNUP_BONUS_CREDITS = 50
CREDITS_MONTHLY_STARTER = 200   # database: tier.t2.monthly_credits = 200
CREDITS_MONTHLY_PRO = 500       # database: tier.t3.monthly_credits = 500

# Marketplace
MAX_LISTING_PRICE = 500
SELLER_REVENUE_PERCENT = 90  # Seller gets 90%, platform gets 10%

# Trial Period (Legacy - deprecated, use TierService.get_trial_duration_days() instead)
# This is kept for backward compatibility but should be migrated to system_configs
TRIAL_DAYS = 30  # Default: Free users get 30-day trial with full access

# Tiers
VALID_TIERS = ["free", "starter", "pro"]
MEMBER_TIERS = ["starter", "pro"]

# Allowed Tiers Whitelist (PRD v3.2)
ALLOWED_TIERS_WHITELIST = [
    ["free"],
    ["starter", "pro"],
    ["pro"],
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
