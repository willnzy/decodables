import os
import logging
import jwt # requires pyjwt
import traceback
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request, Header, Depends, UploadFile, File, Form, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import uuid
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from io import BytesIO
import base64
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from svix.webhooks import Webhook, WebhookVerificationError

# v3.22: Sentry Error Tracking (optional, enabled via SENTRY_DSN env var)
# v3.25: Added Logs, Metrics, Profiling and AI Agents monitoring (SDK >= 2.44.0)
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.openai import OpenAIIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                ),
                # AI Agents: Monitor OpenAI/LLM calls (token usage, costs, latency)
                OpenAIIntegration(
                    include_prompts=True,  # Capture prompts for debugging
                    tiktoken_encoding_name="cl100k_base",
                ),
            ],
            # Performance monitoring
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            # Profiling: Find slow code paths (SDK >= 2.24.1)
            profile_session_sample_rate=float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
            profile_lifecycle="trace",  # Auto-run profiler when there's an active transaction
            environment=os.environ.get("ENV", "development"),
            release=os.environ.get("APP_VERSION", "3.25.0"),
            send_default_pii=False,  # Don't send PII by default
            before_send=lambda event, hint: _sanitize_sentry_event(event),
            # Experimental features (SDK >= 2.44.0)
            _experiments={
                "enable_logs": True,      # Logs feature
                "enable_metrics": True,   # Metrics feature
            },
        )
        logging.info("[Sentry] Full observability initialized (errors, traces, profiles, logs, metrics, AI)")
    except ImportError as e:
        logging.warning(f"[Sentry] sentry-sdk or integration not installed: {e}")
    except Exception as e:
        logging.error(f"[Sentry] Initialization failed: {e}")


def _sanitize_sentry_event(event):
    """
    Sanitize Sentry event before sending.
    Remove sensitive data like auth tokens, API keys, etc.
    """
    if "request" in event:
        if "headers" in event["request"]:
            headers = event["request"]["headers"]
            # Redact sensitive headers
            sensitive_headers = ["authorization", "x-api-key", "cookie", "x-auth-token"]
            for key in list(headers.keys()):
                if key.lower() in sensitive_headers:
                    headers[key] = "[REDACTED]"
        
        # Redact sensitive query params
        if "query_string" in event["request"]:
            qs = event["request"]["query_string"]
            if "token" in qs.lower() or "key" in qs.lower():
                event["request"]["query_string"] = "[REDACTED]"
    
    return event

# v3.12: Unified error handling
from exceptions import (
    AppException, ErrorCode, ErrorResponse,
    UnauthorizedException, ForbiddenException, AdminRequiredException,
    NotFoundException, ProjectNotFoundException, InsufficientCreditsException,
    ValidationException, RateLimitException, InternalServerException
)
from middleware import (
    RequestIDMiddleware, setup_logging, 
    get_request_id, set_user_id
)

# Setup structured logging with request context
logger = setup_logging(
    level=logging.INFO,
    json_format=os.environ.get("LOG_FORMAT") == "json"  # JSON in production
)

# v3.9: Import timezone utilities
from timezone_utils import get_request_timezone

# Import service modules
from services.db_service import (
    # Access control
    is_member, can_access_resource, publish_permission, validate_allowed_tiers, listing_is_public_visible,
    get_total_credits,
    # System configs (public)
    get_system_config, get_all_system_configs, get_configs_by_group,
    # Users
    get_user_profile, create_user_profile, update_subscription_tier, update_user_profile,
    refresh_monthly_credits, search_users, get_full_user_audit, admin_adjust_credits,
    update_user_timezone,
    # Credits
    log_credit_transaction, log_payment_record, credit_deduct, add_credits_permanent, add_credits_monthly,
    deduct_credits_atomic, add_credits, get_credit_history,
    # Projects
    get_user_projects, get_project_detail, create_project, save_project,
    soft_delete_project, restore_project, update_project_hash, get_all_projects_feed,
    count_user_projects,  # Accurate project total
    # Assets
    save_asset, get_assets, get_system_resources,
    # Marketplace
    get_marketplace_listings, get_marketplace_item, get_seller_listings, create_listing,
    submit_listing_for_review, unpublish_listing, update_listing, check_user_purchase,
    execute_purchase, get_user_purchases, get_seller_stats, record_listing_usage, get_leaderboard,
    # Admin moderation
    admin_get_moderation_list, admin_get_moderation_detail, admin_approve_listing,
    admin_reject_listing, admin_delete_listing, admin_unpublish_listing,
    # Admin features
    admin_log_operation, admin_get_operation_logs, admin_get_user_projects,
    admin_get_dashboard_stats, admin_get_user_growth_stats, admin_get_revenue_stats,
    admin_get_project_stats, admin_get_credit_usage_stats, admin_get_tier_distribution,
    admin_get_conversion_funnel, admin_get_ai_insights, admin_get_ai_recommendations,
    admin_get_behavior_analysis, log_user_event, admin_get_user_events, admin_get_event_stats,
    # Notifications
    get_user_notifications, mark_notification_read, mark_all_notifications_read, create_broadcast,
    send_notification_to_user, send_notification_to_users, get_users_by_tier,
    get_all_notification_stats, get_notification_history,
    # Discounts
    get_user_discount, create_user_discount,
    # Logs
    log_activity, create_support_ticket,
    # Supabase client
    supabase
)
from domains.billing.payment_service import (
    create_checkout_session, create_portal_session, construct_event,
    get_customer_subscriptions, get_customer_payments, cancel_subscription, 
    create_refund, get_payment_intent_details
)
from services.ai.image_generator import generate_8_images
# v3.23: Task Queue and WebSocket for async generation
from infrastructure.task_queue import task_queue, progress_tracker
from infrastructure.websocket import ws_manager
from services.ai.zine_generator import create_foldable_book, create_assets_zip
from services.ai.story_generator import generate_story_json, client as openai_client # reuse client
from services.ai.prompt_enhancer import enhance_prompt, enhance_asset_prompt  # AI prompt enhancement
from domains.platform.analytics_service import (
    track_event, track_ai_generation, track_payment, 
    track_marketplace_action, track_project_action, AnalyticsEvents
)

# Environment variables
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")
# Security: Clerk public key (PEM) for token verification.
# Production: fetch from Clerk Dashboard -> API Keys -> JWKS or set CLERK_PEM_PUBLIC_KEY.
CLERK_PEM_PUBLIC_KEY = os.environ.get("CLERK_PEM_PUBLIC_KEY") 

# Import Redis-backed limiter from rate_limiter module
from infrastructure.rate_limiter import limiter

app = FastAPI(title="MagicZine AI API v3.27 - Full v2 Migration (Production)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration - allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",                       # Local development
    "http://127.0.0.1:3000",                       # Local development (fallback)
    "https://makedecodables.vercel.app",           # Vercel preview (develop branch)
    "https://makedecodables.com",                  # Production domain
    "https://www.makedecodables.com",              # Production domain (www)
    "https://make-decodables.vercel.app",          # Vercel legacy
    "https://decodables-production.up.railway.app" # Railway API host
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time", "*"],
    max_age=3600,  # Preflight cache duration (seconds)
)

# v3.12: Request ID middleware for tracing
app.add_middleware(RequestIDMiddleware)

# ==========================================
# DEPRECATED ROUTERS (v3.27: Migrated to api/user and api/admin)
# ==========================================
# The following routers have been migrated to the new v2 API structure.
# All endpoints are now available under /api/v2/user/* and /api/v2/admin/*
# Keeping imports commented for reference during transition period.

# v3.13: Mount admin router (configs, moderation, etc.)
# v3.24: Admin routers refactored into smaller modules
# DEPRECATED: Migrated to api/admin/*
# from routers.admin_system import router as admin_system_router
# from routers.admin_metrics import router as admin_metrics_router
# from routers.admin_campaigns import router as admin_campaigns_router
# from routers.admin_tasks_mgmt import router as admin_tasks_mgmt_router
# from routers.admin_ai_models import router as admin_ai_models_router
# app.include_router(admin_system_router)
# app.include_router(admin_metrics_router)
# app.include_router(admin_campaigns_router)
# app.include_router(admin_tasks_mgmt_router)
# app.include_router(admin_ai_models_router)

# v3.13: Holiday themes and marketing campaigns routers
# DEPRECATED: Migrated to api/user/*
# from routers.themes import router as themes_router
# from routers.campaigns import router as campaigns_router
# app.include_router(themes_router)
# app.include_router(campaigns_router)

# v3.17: System resources management router
# DEPRECATED: Migrated to api/user/system_resources.py
# from routers.system_resources import router as system_resources_router
# app.include_router(system_resources_router)

# v3.20: A/B Testing experiments routers
# v3.24: Experiments routers refactored
# DEPRECATED: Migrated to api/user/experiments.py and api/admin/experiments.py
# from routers.experiments_public import router as experiments_public_router
# from routers.experiments_admin import router as experiments_admin_router
# app.include_router(experiments_public_router)
# app.include_router(experiments_admin_router)

# v3.24: Webhooks, Logs and Analytics routers (refactored from app.py)
# DEPRECATED: Migrated to api/user/*
# from routers.webhooks import router as webhooks_router
# from routers.logs import router as logs_router
# from routers.analytics import router as analytics_router
# app.include_router(webhooks_router)
# app.include_router(logs_router)
# app.include_router(analytics_router)

# v3.24: Generation router (refactored from app.py)
# DEPRECATED: Migrated to api/user/generation*.py
# from routers.generation import include_generation_routers
# include_generation_routers(app)

# v3.24: Tasks router (refactored from app.py)
# DEPRECATED: Migrated to api/user/tasks.py
# from routers.tasks import router as tasks_router
# app.include_router(tasks_router)

# v3.24: Generations router (refactored from app.py)
# DEPRECATED: Migrated to api/user/generations.py
# from routers.generations import router as generations_router
# app.include_router(generations_router)

# v3.24: Templates router (refactored from app.py)
# DEPRECATED: Migrated to api/user/templates.py
# from routers.templates import router as templates_router
# app.include_router(templates_router)

# v3.24: Admin sub-routers (refactored from app.py)
# DEPRECATED: Migrated to api/admin/*
# from routers.admin_users import router as admin_users_router
# from routers.admin_subscriptions import router as admin_subscriptions_router
# from routers.admin_notifications import router as admin_notifications_router
# from routers.admin_stats import router as admin_stats_router
# from routers.admin_moderation import router as admin_moderation_router
# from routers.admin_logs import router as admin_logs_router
# from routers.admin_ai import router as admin_ai_router
# from routers.admin_events import router as admin_events_router
# from routers.admin_config import router as admin_config_router
# app.include_router(admin_users_router)
# app.include_router(admin_subscriptions_router)
# app.include_router(admin_notifications_router)
# app.include_router(admin_stats_router)
# app.include_router(admin_moderation_router)
# app.include_router(admin_logs_router)
# app.include_router(admin_ai_router)
# app.include_router(admin_events_router)
# app.include_router(admin_config_router)

# v3.24: User and utility routers
# DEPRECATED: Migrated to api/user/*
# from routers.user_assets import router as user_assets_router
# from routers.user_profile import router as user_profile_router
# from routers.tools import router as tools_router
# from routers.payment import router as payment_router
# from routers.support import router as support_router
# app.include_router(user_assets_router)
# app.include_router(user_profile_router)
# app.include_router(tools_router)
# app.include_router(payment_router)
# app.include_router(support_router)

# v3.24: Config and export routers
# DEPRECATED: Migrated to api/user/*
# from routers.config import router as config_router
# from routers.export import router as export_router
# app.include_router(config_router)
# app.include_router(export_router)

# v3.24: Projects, Marketplace and Resources routers
# DEPRECATED: Migrated to api/user/*
# from routers.projects import router as projects_router
# from routers.marketplace import router as marketplace_router
# from routers.resources import router as resources_router
# app.include_router(projects_router)
# app.include_router(marketplace_router)
# app.include_router(resources_router)

# ==========================================
# DEPRECATED: OLD DDD API ROUTER
# ==========================================
# v3.25: New DDD-based API routers (Phase 6 - gradual migration)
# These use the new container + handler architecture
# DEPRECATED: Replaced by api/user and api/admin structure
# from api import api_router as ddd_api_router
# app.include_router(ddd_api_router)

# ==========================================
# v3.27: ACTIVE API ROUTERS - Full v2 Migration Complete
# ==========================================
# Stage 4 Complete: All routers migrated from routers/* to api/user and api/admin
# Total: 40 router files → 25 user modules + 15 admin modules = 40 v2 modules
# All endpoints now under:
#   - /api/v2/user/*   (User-facing APIs: ~109 endpoints)
#   - /api/v2/admin/*  (Admin-facing APIs: ~95 endpoints)
#
# Migration status: 100% complete (204 endpoints)
# Old routers (routers/*) deprecated and commented out above

from api.user import user_router
from api.admin import admin_router
app.include_router(user_router)
app.include_router(admin_router)


# ==========================================
# Global Exception Handlers (v3.12)
# ==========================================

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    Handle custom application exceptions.
    Returns a standardized error response with request_id for tracing.
    """
    request_id = get_request_id() or getattr(request.state, 'request_id', None)
    
    # Log the error with full context (context is NOT exposed to client)
    logger.warning(
        f"AppException: {exc.code} - {exc.message}",
        extra={
            "error_code": exc.code,
            "status_code": exc.status_code,
            "context": exc.context,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Build response
    error_response = exc.to_response(request_id)
    
    response = JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True),
        headers=exc.headers or {}
    )
    
    # Add request ID to response header
    if request_id:
        response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors (422).
    Converts validation errors to our standard format.
    """
    request_id = get_request_id() or getattr(request.state, 'request_id', None)
    
    # Extract validation error details
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body' prefix
        errors.append({
            "field": field or "body",
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={"errors": errors, "body": str(exc.body)[:500]}  # Truncate body
    )
    
    error_response = ErrorResponse(
        code=ErrorCode.VALIDATION_ERROR.value,
        message="Request validation failed",
        request_id=request_id,
        details={"errors": errors}
    )
    
    response = JSONResponse(
        status_code=422,
        content=error_response.model_dump(exclude_none=True)
    )
    
    if request_id:
        response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle FastAPI HTTPException (convert to our format).
    """
    request_id = get_request_id() or getattr(request.state, 'request_id', None)
    
    # Map common HTTP status codes to our error codes
    code_map = {
        400: ErrorCode.BAD_REQUEST,
        401: ErrorCode.AUTH_UNAUTHORIZED,
        403: ErrorCode.AUTH_FORBIDDEN,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        429: ErrorCode.TOO_MANY_REQUESTS,
        500: ErrorCode.SERVER_ERROR,
    }
    
    error_code = code_map.get(exc.status_code, ErrorCode.SERVER_ERROR)
    
    error_response = ErrorResponse(
        code=error_code.value,
        message=str(exc.detail),
        request_id=request_id
    )
    
    response = JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True)
    )
    
    if request_id:
        response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions.
    
    IMPORTANT: This is the "firewall" that prevents raw Python errors
    from being exposed to clients. It logs the full stack trace for
    debugging while returning a sanitized error to the client.
    """
    request_id = get_request_id() or getattr(request.state, 'request_id', None)
    
    # Log FULL error details (stack trace, context) for debugging
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {exc}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": request.url.path,
            "method": request.method,
            "query_params": str(request.query_params),
        },
        exc_info=True  # Include full stack trace
    )
    
    # Return SANITIZED error to client (no internal details)
    error_response = ErrorResponse(
        code=ErrorCode.SERVER_ERROR.value,
        message="Internal server error. Please try again later.",
        request_id=request_id
    )
    
    response = JSONResponse(
        status_code=500,
        content=error_response.model_dump(exclude_none=True)
    )
    
    if request_id:
        response.headers["X-Request-ID"] = request_id
    
    return response

# ===========================================
# Background scheduler
# ===========================================
from scheduler import init_scheduler, shutdown_scheduler, run_aggregation_now

# ==========================================
# Instance Identification (for multi-instance deployment)
# ==========================================
# [Why]: When scaling to multiple instances, each instance needs a unique ID
# for log tracing and debugging. This helps identify which instance handled a request.
import uuid
INSTANCE_ID = os.environ.get("RAILWAY_REPLICA_ID", uuid.uuid4().hex[:8])
logger.info(f"🚀 Starting instance: {INSTANCE_ID}")


@app.on_event("startup")
async def startup_event():
    """
    Initialize scheduled jobs when FastAPI starts.
    
    MULTI-INSTANCE NOTE:
    - Scheduler is controlled by ENABLE_SCHEDULER env var (default: true)
    - When deploying multiple instances, set ENABLE_SCHEDULER=false for all
      except ONE instance to prevent duplicate task execution.
    - Railway deployment: Set env var in only one replica.
    """
    logger.info(f"📅 Instance {INSTANCE_ID} starting scheduler check...")
    init_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduled jobs and close connections when FastAPI shuts down."""
    logger.info(f"👋 Instance {INSTANCE_ID} shutting down...")
    shutdown_scheduler()

    # Gracefully close Redis connection
    from core.cache import close_redis
    close_redis()

# ==========================================
# 3. Routes
# ==========================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "3.27",
        "api_version": "v2",
        "migration_status": "complete"
    }

# --- Webhooks (v3.24: moved to routers/webhooks.py) ---

# --- Analytics ---
# Note: The main analytics endpoint is at line ~5941 (log_analytics_events)
# which has rate limiting, IP/geo enrichment, and writes to user_events table.
# The AnalyticsEventsRequest model is kept for potential future use with
# a separate structured analytics endpoint.

# --- Error Logging (v3.24: moved to routers/logs.py) ---

# --- User ---

