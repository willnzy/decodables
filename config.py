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

# Credits Configuration
CREDITS_PER_IMAGE = 5
CREDITS_PER_OCR = 5
CREDITS_SIGNUP_BONUS = 50
CREDITS_MONTHLY_STARTER = 500
CREDITS_MONTHLY_PRO = 1000

# Marketplace
MAX_LISTING_PRICE = 500
SELLER_REVENUE_PERCENT = 90  # Seller gets 90%, platform gets 10%

# Tiers
VALID_TIERS = ["free", "starter", "pro"]
MEMBER_TIERS = ["starter", "pro"]

# Allowed Tiers Whitelist (PRD v3.2)
ALLOWED_TIERS_WHITELIST = [
    ["free"],
    ["starter", "pro"],
    ["pro"],
]

