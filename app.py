import os
import jwt # requires pyjwt
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Header, Depends, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
import base64
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from svix.webhooks import Webhook, WebhookVerificationError

# Import service modules
from db_service import (
    # Access control
    is_member, can_access_resource, publish_permission, validate_allowed_tiers, listing_is_public_visible,
    get_total_credits,
    # Users
    get_user_profile, create_user_profile, update_subscription_tier, update_user_profile,
    refresh_monthly_credits, search_users, get_full_user_audit, admin_adjust_credits,
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
from payment_service import (
    create_checkout_session, create_portal_session, construct_event,
    get_customer_subscriptions, get_customer_payments, cancel_subscription, 
    create_refund, get_payment_intent_details
)
from image_generator import generate_8_images
from zine_generator import create_foldable_book, create_assets_zip
from story_generator import generate_story_json, client as openai_client # reuse client

# Environment variables
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")
# Security: Clerk public key (PEM) for token verification.
# Production: fetch from Clerk Dashboard -> API Keys -> JWKS or set CLERK_PEM_PUBLIC_KEY.
CLERK_PEM_PUBLIC_KEY = os.environ.get("CLERK_PEM_PUBLIC_KEY") 

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="MagicZine AI API v3.0 (Production)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration - allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:3000",                      # Local development
    "http://127.0.0.1:3000",                      # Local development (fallback)
    "https://make-decodables.vercel.app",         # Vercel production
    "https://decodables-production.up.railway.app" # Railway API host
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Preflight cache duration (seconds)
)

# ===========================================
# Background scheduler
# ===========================================
from scheduler import init_scheduler, shutdown_scheduler, run_aggregation_now

@app.on_event("startup")
async def startup_event():
    """Initialize scheduled jobs when FastAPI starts."""
    init_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduled jobs when FastAPI shuts down."""
    shutdown_scheduler()

# Middleware to ensure every response has CORS headers, even on errors
@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    """
    Ensure every response contains CORS headers, even when exceptions occur.
    """
    try:
        response = await call_next(request)
        origin = request.headers.get("origin")
        if origin and origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    except Exception as e:
        # Return an error response with CORS headers when exceptions occur
        origin = request.headers.get("origin")
        cors_headers = {}
        if origin and origin in ALLOWED_ORIGINS:
            cors_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            }
        import traceback
        print(f"Middleware exception: {e}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers=cors_headers
        )

# Global exception handler - ensure error responses include CORS headers
from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that attaches CORS headers to error responses.
    """
    import traceback
    print(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    print(traceback.format_exc())
    
    # Determine request origin
    origin = request.headers.get("origin")
    cors_headers = {}
    if origin and origin in [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://make-decodables.vercel.app",
        "https://decodables-production.up.railway.app"
    ]:
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    
    # Preserve status code for HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=cors_headers
        )
    
    # All other exceptions -> 500
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if os.environ.get("ENV") == "development" else "An error occurred"
        },
        headers=cors_headers
    )

# ==========================================
# 1. Authentication dependencies
# ==========================================
async def get_current_user(authorization: str = Header(None)):
    """
    Validate the Bearer token.
    Production mode: verify JWT signature.
    Development mode: if the public key is missing, fall back to an insecure mode for local testing.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Token")
    
    token = authorization.split(" ")[1]
    payload = None
    
    # -------------------------------------------------------
    # [Real Auth] Production path
    # -------------------------------------------------------
    if CLERK_PEM_PUBLIC_KEY:
        try:
            # Verify Clerk-issued JWT
            payload = jwt.decode(token, CLERK_PEM_PUBLIC_KEY, algorithms=["RS256"], options={"verify_aud": False})
            user_id = payload.get("sub")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    else:
        # [Dev Auth] Without a public key, only extract user_id (local dev only)
        # WARNING: insecure fallback for quick debugging
        print("⚠️ WARNING: Running in INSECURE AUTH mode (Missing CLERK_PEM_PUBLIC_KEY)")
        try:
            # Decode without signature verification
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub")
        except:
            # If decoding fails, treat token string as user_id (mock fallback)
            user_id = token

    # Ensure the user exists in the database
    profile = get_user_profile(user_id)
    
    # Auto-create the user when missing (handles delayed or failed webhooks)
    if not profile:
        # Extract user info from JWT payload
        email = ""
        username = ""
        avatar_url = ""
        
        if payload:
            # Possible Clerk JWT fields
            email = payload.get("email", payload.get("primary_email", ""))
            username = payload.get("username", payload.get("name", ""))
            avatar_url = payload.get("image_url", payload.get("picture", ""))
        
        # Create the user profile
        try:
            create_user_profile(user_id, email, username, avatar_url)
            profile = get_user_profile(user_id)
            print(f"✅ Auto-created profile for user {user_id} (webhook may have been delayed)")
        except Exception as e:
            print(f"❌ Failed to auto-create user profile: {e}")
            raise HTTPException(status_code=401, detail="User not found and could not be created")
    
    if not profile:
        raise HTTPException(status_code=401, detail="User not found in database")
    
    return profile

async def get_current_user_optional(authorization: str = Header(None)):
    """
    Optional user lookup used for tracking anonymous behavior.
    Returns None if no token is provided.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        token = authorization.split(" ")[1]
        
        if CLERK_PEM_PUBLIC_KEY:
            payload = jwt.decode(token, CLERK_PEM_PUBLIC_KEY, algorithms=["RS256"], options={"verify_aud": False})
            user_id = payload.get("sub")
            profile = get_user_profile(user_id)
            return profile
        else:
            # Development mode
            return None
    except Exception:
        return None

async def require_admin(user: dict = Depends(get_current_user)):
    """Guard that ensures the caller is an admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_member(user: dict = Depends(get_current_user)):
    """Guard that ensures the caller is a Starter/Pro member."""
    if not is_member(user):
        raise HTTPException(status_code=403, detail="Membership required")
    return user

# ==========================================
# 2. Data models
# ==========================================
class StoryGenRequest(BaseModel):
    topic: str
    style: Optional[str] = "Children's book illustration"

class ImageGenRequest(BaseModel):
    project_id: Optional[str] = None  # Optional - may be None when generating from Dashboard
    prompts: List[str]
    reference_image: Optional[str] = None  # Base64 encoded image or URL
    reference_strength: Optional[float] = 0.7  # 0.0-1.0, higher = more similar to reference
    image_size: Optional[str] = "landscape_4_3"  # Image aspect ratio: landscape_4_3, square, portrait_4_3, etc.

class PdfGenRequest(BaseModel):
    project_id: str
    current_hash: str
    image_urls: List[str]
    texts: List[str]

class ProjectUpdate(BaseModel):
    canvas_data: Optional[dict] = None
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    used_listing_ids: Optional[List[str]] = None  # Newly referenced listing IDs

class CheckoutRequest(BaseModel):
    plan_type: str  # 'credits_100', 'starter', or 'pro'

class SupportTicketRequest(BaseModel):
    email: Optional[str] = None  # Optional - will use user's email if not provided
    message: str

class ContactFormRequest(BaseModel):
    email: str  # Required for guest users
    message: str

class FeedbackWithImagesRequest(BaseModel):
    email: str
    message: str
    images: Optional[List[dict]] = []  # List of {name, data} where data is base64

class AdminAdjustRequest(BaseModel):
    user_id: str
    amount: int
    bucket: Optional[str] = "permanent"  # 'monthly' | 'permanent'
    reason: str

class AdminTierRequest(BaseModel):
    user_id: str
    tier: str

class AdminDowngradeRequest(BaseModel):
    user_id: str
    user_code: str  # For verification
    user_email: str  # For verification
    target_tier: str  # 'starter' | 'free'
    immediate: bool = False  # True = immediate, False = apply at period end
    reason: str

class AdminDiscountRequest(BaseModel):
    user_id: str
    discount_percent: int
    valid_days: int
    target_plan: Optional[str] = None

class AdminBroadcastRequest(BaseModel):
    title: str
    content: str
    target_group: Optional[str] = "all"  # 'all', 'free', 'starter', 'pro'

class MarketplacePublishRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    thumbnail_url: str
    resource_url: str
    resource_type: str  # 'project' | 'asset'
    price_credits: int = 0
    allowed_tiers: List[str]  # Required; only ['free'], ['starter','pro'], or ['pro']

class MarketplacePurchaseRequest(BaseModel):
    listing_id: str
    idempotency_key: Optional[str] = None  # Prevent duplicate purchases
    utm_source: Optional[str] = None  # Analytics tracking
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    referral_context: Optional[str] = None  # 'homepage', 'search', 'category', etc.

class ListingUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price_credits: Optional[int] = None
    is_public: Optional[bool] = None
    allowed_tiers: Optional[List[str]] = None

class AdminModerationRejectRequest(BaseModel):
    reason: str

class AdminRefundRequest(BaseModel):
    user_id: str
    user_code: str  # Must match email for verification
    payment_intent_id: str
    amount_cents: Optional[int] = None  # None = full refund
    reason: str

class AdminCancelSubscriptionRequest(BaseModel):
    user_id: str
    user_code: str  # Must match email for verification
    subscription_id: str
    immediate: bool = False  # True = cancel now, False = cancel at period end
    reason: str

class AnalyticsEvent(BaseModel):
    event_type: str
    event_level: Optional[str] = None
    timestamp: Optional[str] = None
    utc_timestamp: Optional[str] = None
    properties: Optional[dict] = None
    session_id: Optional[str] = None
    env: Optional[dict] = None
    user_properties: Optional[dict] = None

class AnalyticsEventsRequest(BaseModel):
    events: List[AnalyticsEvent]

# ==========================================
# 3. Routes
# ==========================================

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0"}

# --- Webhooks ---
@app.post("/api/webhooks/clerk")
async def clerk_webhook(request: Request):
    if not CLERK_WEBHOOK_SECRET:
        raise HTTPException(500, "Missing CLERK_WEBHOOK_SECRET")
    
    payload = await request.body()
    headers = request.headers
    try:
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        evt = wh.verify(payload, headers)
    except WebhookVerificationError:
        raise HTTPException(400, "Invalid signature")

    event_type = evt["type"]
    data = evt["data"]
    
    if event_type == "user.created":
        user_id = data["id"]
        email = data["email_addresses"][0]["email_address"]
        username = data.get("username")
        image_url = data.get("image_url")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        
        # Check whether the user already exists (may have been created via JIT)
        existing_profile = get_user_profile(user_id)
        if existing_profile:
            # Update missing info for the existing JIT-created user
            update_user_profile(user_id, avatar_url=image_url, username=username, first_name=first_name, last_name=last_name)
            # If email is missing, update it separately
            if not existing_profile.get("email") and email:
                supabase.table("profiles").update({"email": email}).eq("id", user_id).execute()
            print(f"✅ User {user_id} already exists (JIT created), updated profile info")
            return {"status": "updated", "reason": "jit_created"}
        
        # Ensure email uniqueness (avoid duplicate accounts)
        existing_by_email = search_users(email)
        if existing_by_email:
            print(f"⚠️ User with email {email} already exists, skipping creation")
            return {"status": "skipped", "reason": "email_exists"}
        
        # Create a full profile (including names)
        create_user_profile(user_id, email, username, image_url, first_name=first_name, last_name=last_name)
        
        # Log signup event
        log_activity(user_id, "user_signup", {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "method": "clerk"
        })
    
    elif event_type == "user.updated":
        # User updated avatar/username/names
        user_id = data.get("id")
        new_avatar = data.get("image_url")
        new_username = data.get("username")
        new_first_name = data.get("first_name")
        new_last_name = data.get("last_name")
        
        # Sync updates to Supabase (including name fields)
        update_user_profile(user_id, avatar_url=new_avatar, username=new_username, first_name=new_first_name, last_name=new_last_name)
        
        # Log profile update
        log_activity(user_id, "profile_updated", {
            "avatar_changed": new_avatar is not None,
            "username_changed": new_username is not None,
            "name_changed": new_first_name is not None or new_last_name is not None
        })
        print(f"✅ Updated profile for user {user_id}")
    
    elif event_type == "session.created":
        # Log login event
        user_id = data.get("user_id")
        if user_id:
            log_activity(user_id, "user_login", {
                "client_ip": evt.get("event_attributes", {}).get("http_request", {}).get("client_ip"),
                "user_agent": evt.get("event_attributes", {}).get("http_request", {}).get("user_agent")
            })
    
    elif event_type in ["session.ended", "session.removed", "session.revoked"]:
        # Log logout event
        user_id = data.get("user_id")
        if user_id:
            log_activity(user_id, "user_logout", {
                "reason": event_type
            })
    
    return {"status": "processed"}

@app.post("/api/webhooks/stripe")
async def stripe_webhook_endpoint(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = construct_event(payload, stripe_signature)
    except Exception as e:
        raise HTTPException(400, str(e))
    
    event_type = event['type']
    
    # One-time purchase completed
    if event_type == 'checkout.session.completed':
        session = event['data']['object']
        uid = session['metadata'].get('user_id')
        plan = session['metadata'].get('plan_type')
        amount_total = session.get('amount_total', 0)  # Amount in cents
        currency = session.get('currency', 'usd').upper()
        
        if uid and plan:
            if plan == 'credits_100':
                # Purchase credits -> add to permanent bucket
                add_credits_permanent(uid, 100, "Purchase 100 Credits", "topup_purchase")
                # Log payment
                log_payment_record(uid, amount_total, currency, "credits_purchase", f"Purchase 100 Credits - ${amount_total/100:.2f}")
                log_activity(uid, "credits_purchase", {"amount": 100, "payment": amount_total})
            elif plan in ['starter', 'pro']:
                # New subscription: update tier and grant monthly credits
                update_subscription_tier(uid, plan, session.get('customer'), "active")
                amt = 500 if plan == 'starter' else 1000
                add_credits_monthly(uid, amt, f"{plan.capitalize()} Monthly Credits", "sub_grant")
                # Log subscription payment
                log_payment_record(uid, amount_total, currency, "sub_payment", f"{plan.capitalize()} Plan Subscription - ${amount_total/100:.2f}")
                log_activity(uid, "subscription_started", {"plan": plan, "payment": amount_total})
    
    # Subscription renewal (monthly refresh)
    elif event_type == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        amount_paid = invoice.get('amount_paid', 0)  # Amount in cents
        currency = invoice.get('currency', 'usd').upper()
        billing_reason = invoice.get('billing_reason', '')  # subscription_create, subscription_cycle, etc.
        
        # Look up user
        if customer_id:
            # Match via stripe_customer_id
            user_res = supabase.table("profiles").select("id, tier")\
                .eq("stripe_customer_id", customer_id).execute()
            
            if user_res.data:
                user = user_res.data[0]
                uid = user['id']
                tier = user['tier']
                
                # Refresh monthly credits (reset, no rollover) on renewal
                if tier in ['starter', 'pro'] and billing_reason == 'subscription_cycle':
                    refresh_monthly_credits(uid, tier)
                    # Log renewal payment
                    log_payment_record(uid, amount_paid, currency, "sub_renewal", f"{tier.capitalize()} Plan Renewal - ${amount_paid/100:.2f}")
                    log_activity(uid, "monthly_credits_refreshed", {"tier": tier, "payment": amount_paid})
    
    # Subscription canceled or expired
    elif event_type in ['customer.subscription.deleted', 'customer.subscription.updated']:
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        status = subscription.get('status')
        
        if customer_id:
            user_res = supabase.table("profiles").select("id")\
                .eq("stripe_customer_id", customer_id).execute()
            
            if user_res.data:
                uid = user_res.data[0]['id']
                
                if status in ['canceled', 'unpaid', 'past_due']:
                    # Downgrade to free
                    update_subscription_tier(uid, 'free', subscription_status='inactive')
                    log_activity(uid, "subscription_ended", {"reason": status})
                elif status == 'active':
                    # Subscription reactivated
                    plan_id = subscription.get('items', {}).get('data', [{}])[0].get('price', {}).get('id', '')
                    # Map price_id to tier
                    new_tier = 'starter' if 'starter' in plan_id.lower() else 'pro'
                    update_subscription_tier(uid, new_tier, subscription_status='active')
    
    return {"status": "ok"}

# --- Analytics ---
@app.post("/api/analytics/events")
async def track_analytics_events(request: AnalyticsEventsRequest):
    """
    Receive and store analytics events from frontend.
    Events are batched and sent periodically.
    """
    try:
        events = request.events
        
        # Store events in database
        for event in events:
            event_data = {
                "event_type": event.event_type,
                "event_level": event.event_level,
                "timestamp": event.timestamp,
                "properties": event.properties or {},
                "session_id": event.session_id,
                "env": event.env or {},
                "user_properties": event.user_properties or {},
            }
            
            # Try to get user_id from user_properties
            user_id = None
            if event.user_properties:
                user_id = event.user_properties.get("user_id")
            
            # Insert into analytics_events table
            supabase.table("analytics_events").insert({
                "user_id": user_id,
                "event_type": event.event_type,
                "event_level": event.event_level,
                "event_data": event_data,
                "session_id": event.session_id,
            }).execute()
        
        return {"status": "ok", "events_received": len(events)}
    except Exception as e:
        # Log error but don't fail - analytics should not break the app
        print(f"[Analytics] Error storing events: {e}")
        return {"status": "ok", "events_received": len(request.events), "warning": "Some events may not have been stored"}

# --- Error Logging ---
class ErrorLogRequest(BaseModel):
    """Request model for error logging"""
    error_id: Optional[str] = None
    error_type: str  # API, NETWORK, JS_ERROR, UNHANDLED_REJECTION, REACT_ERROR, CORS, OTHER
    error_code: Optional[str] = None
    message: str
    status_code: Optional[int] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    page_url: Optional[str] = None
    user_agent: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Optional[dict] = None
    client_timestamp: Optional[str] = None
    session_id: Optional[str] = None
    user_code: Optional[str] = None  # User code for easier identification

class ErrorLogBatchRequest(BaseModel):
    """Request model for batch error logging"""
    errors: List[ErrorLogRequest]

@app.post("/api/logs/error")
async def log_error(request: ErrorLogRequest, authorization: Optional[str] = Header(None)):
    """
    Receive and store a single error log from frontend.
    Does not require authentication - errors should be logged even for unauthenticated users.
    """
    try:
        # Try to extract user_id from token if provided
        user_id = None
        if authorization and authorization.startswith("Bearer "):
            try:
                token = authorization.split(" ")[1]
                # Simple decode without verification for logging purposes
                import jwt
                decoded = jwt.decode(token, options={"verify_signature": False})
                user_id = decoded.get("sub")
            except:
                pass
        
        # Insert error log
        error_data = {
            "error_id": request.error_id,
            "error_type": request.error_type,
            "error_code": request.error_code,
            "message": request.message[:2000] if request.message else None,  # Limit message length
            "status_code": request.status_code,
            "endpoint": request.endpoint[:500] if request.endpoint else None,
            "method": request.method,
            "user_id": user_id,
            "user_code": request.user_code,
            "session_id": request.session_id,
            "page_url": request.page_url[:2000] if request.page_url else None,
            "user_agent": request.user_agent[:500] if request.user_agent else None,
            "stack_trace": request.stack_trace[:5000] if request.stack_trace else None,
            "context": request.context or {},
            "client_timestamp": request.client_timestamp,
        }
        
        supabase.table("error_logs").insert(error_data).execute()
        
        # Also log to console for immediate visibility
        print(f"[ErrorLog] {request.error_type} - {request.message[:100] if request.message else 'No message'}")
        
        return {"status": "ok"}
    except Exception as e:
        # Don't fail on logging errors
        print(f"[ErrorLog] Failed to store error: {e}")
        return {"status": "ok", "warning": "Error may not have been stored"}

@app.post("/api/logs/errors")
async def log_errors_batch(request: ErrorLogBatchRequest, authorization: Optional[str] = Header(None)):
    """
    Receive and store batch error logs from frontend.
    """
    try:
        # Try to extract user_id from token if provided
        user_id = None
        if authorization and authorization.startswith("Bearer "):
            try:
                token = authorization.split(" ")[1]
                import jwt
                decoded = jwt.decode(token, options={"verify_signature": False})
                user_id = decoded.get("sub")
            except:
                pass
        
        # Insert all errors
        error_records = []
        for err in request.errors:
            error_records.append({
                "error_id": err.error_id,
                "error_type": err.error_type,
                "error_code": err.error_code,
                "message": err.message[:2000] if err.message else None,
                "status_code": err.status_code,
                "endpoint": err.endpoint[:500] if err.endpoint else None,
                "method": err.method,
                "user_id": user_id,
                "user_code": err.user_code,
                "session_id": err.session_id,
                "page_url": err.page_url[:2000] if err.page_url else None,
                "user_agent": err.user_agent[:500] if err.user_agent else None,
                "stack_trace": err.stack_trace[:5000] if err.stack_trace else None,
                "context": err.context or {},
                "client_timestamp": err.client_timestamp,
            })
        
        if error_records:
            supabase.table("error_logs").insert(error_records).execute()
        
        return {"status": "ok", "errors_received": len(error_records)}
    except Exception as e:
        print(f"[ErrorLog] Failed to store batch errors: {e}")
        return {"status": "ok", "warning": "Some errors may not have been stored"}

# --- User ---
@app.get("/api/user/me")
def get_me(user: dict = Depends(get_current_user)):
    """
    Get current user info (PRD v3.2).
    
    Important: Checks and resets monthly credits if needed (monthly reset logic)
    - Monthly credits reset every 30 days for Starter/Pro users
    - Permanent credits are never reset
    """
    from db_service import check_and_reset_monthly_credits_if_needed, get_user_profile
    
    user_id = user["id"]
    
    # Reset monthly credits when needed (permanent credits never reset)
    check_and_reset_monthly_credits_if_needed(user_id)
    
    # Fetch the latest profile data (it may have changed)
    user_profile = get_user_profile(user_id)
    if not user_profile:
        # Fallback to user dict if profile not found
        user_profile = user
    
    return {
        **user_profile,
        "credits_total": user_profile.get("credits_monthly", 0) + user_profile.get("credits_permanent", 0),
        "is_member": is_member(user_profile)
    }

@app.get("/api/user/history")
def get_history(page: int = 1, limit: int = 20, user: dict = Depends(get_current_user)):
    items = get_credit_history(user["id"], page, limit)
    return {"items": items, "total": len(items), "page": page}

@app.get("/api/user/assets")
def my_assets(project_id: Optional[str]=None, scope: Optional[str]=None, user: dict = Depends(get_current_user)):
    """
    Fetch user assets.
    
    - Starter: restricted to current project assets
    - Pro: can access assets across all projects (history)
    - Purchased assets: always accessible
    """
    # Only Pro users can access cross-project history
    if scope == "all" and user["tier"] != "pro":
        raise HTTPException(403, "Pro required for cross-project history")
    target_proj = project_id if scope != "all" else None
    return get_assets(user["id"], target_proj)

@app.post("/api/user/assets")
@limiter.limit("20/minute")  # Upload rate limit
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """Upload personal assets (Pro only, PRD v3.2)."""
    # Check personal upload permission (Pro only - PRD v3.2)
    # Normalize tier to lowercase for consistent comparison
    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(
            403,
            "Personal asset upload requires Pro plan. Please upgrade to upload your own assets."
        )
    
    import uuid
    from image_generator import supabase as storage_supabase, BUCKET_NAME
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")
    
    # Validate file size (5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size is 5MB")
    
    # Ensure storage client is configured
    if not storage_supabase:
        raise HTTPException(500, "Storage service not configured")
    
    # Generate a unique filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    
    try:
        # Upload file to generated-images bucket (reuse image_generator client)
        storage_supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=contents,
            file_options={"content-type": file.content_type}
        )
        
        # Fetch the public URL
        url = storage_supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        
        # Save metadata into assets table
        save_asset(user["id"], url, "uploaded", project_id)
        
        return {"url": url, "filename": filename}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to upload file: {str(e)}")

@app.delete("/api/user/assets/{asset_id}")
def delete_asset(asset_id: str, permanent: bool = False, user: dict = Depends(get_current_user)):
    """
    Delete a user asset (PRD v3.3).
    
    Args:
        asset_id: Asset ID to delete
        permanent: If true, permanently hides from trash (stage 2 delete)
                   If false, soft delete to trash (stage 1 delete)
    """
    from db_service import soft_delete_asset, permanently_hide_asset
    
    try:
        if permanent:
            # Stage 2: Permanently hide from trash
            result = permanently_hide_asset(asset_id, user["id"])
            if result:
                log_activity(user["id"], "permanent_delete_asset", {"asset_id": asset_id})
                return {"success": True, "status": "permanently_hidden", "stage": 2}
            else:
                raise HTTPException(404, "Asset not found or not in trash")
        else:
            # Stage 1: Soft delete to trash
            soft_delete_asset(asset_id, user["id"])
            log_activity(user["id"], "delete_asset", {"asset_id": asset_id})
            return {"success": True, "status": "deleted", "stage": 1}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(404, str(e) or "Asset not found")


@app.get("/api/user/assets/dashboard")
def dashboard_assets(
    view: str = Query("all", pattern="^(all|bought|selling)$"),
    page: int = 1, 
    limit: int = 15,  # 15 per page (5x3 grid)
    search: str = None,
    user: dict = Depends(get_current_user)
):
    """
    Get assets for dashboard with view type filtering (PRD v3.3).
    
    Args:
        view: View type - "all" (default), "bought", or "selling"
        page: Page number (default: 1)
        limit: Items per page (default: 15 for 5x3 grid)
        search: Search query to filter assets by name/description
    
    Returns:
        Assets list with:
        - items: Array of assets with marketplace_listing info
        - total: Total count for current view
        - page: Current page
        - view_type: Current view type
    """
    from db_service import get_dashboard_assets
    
    print(f"[API] dashboard_assets: view={view}, page={page}, search={search}")
    
    result = get_dashboard_assets(
        user_id=user["id"],
        view_type=view,
        page=page,
        limit=limit,
        search=search
    )
    
    return result


@app.get("/api/user/assets/seller-stats")
def get_asset_seller_stats(user: dict = Depends(get_current_user)):
    """
    Get seller statistics for assets (PRD v3.3).
    
    Returns:
        Dict with:
        - total_selling: Number of active asset listings
        - total_sales: Total number of sales across all listings
        - unique_buyers: Total unique buyers
        - total_revenue: Total credits earned from sales
        - total_usage: Total usage count across all listings
    """
    from db_service import get_seller_asset_stats
    return get_seller_asset_stats(user["id"])


@app.get("/api/user/assets/deleted")
def list_deleted_assets(
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Retrieve the user's deleted assets (last 30 days)."""
    from db_service import get_user_deleted_assets
    return get_user_deleted_assets(user["id"], page, limit)


@app.post("/api/user/assets/{asset_id}/restore")
def restore_user_asset(
    asset_id: str,
    user: dict = Depends(get_current_user)
):
    """Allow a user to restore their own deleted asset."""
    from db_service import restore_asset
    try:
        asset = restore_asset(asset_id, user["id"])
        if asset:
            log_activity(user["id"], "restore_asset", {"asset_id": asset_id})
            return {"status": "ok", "asset": asset}
        else:
            raise HTTPException(status_code=404, detail="Asset not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/user/purchases")
def my_purchases(page: int = 1, limit: int = 50, user: dict = Depends(get_current_user)):
    """Fetch the user's purchased items."""
    items = get_user_purchases(user["id"], page, limit)
    return {"items": items, "total": len(items)}

@app.get("/api/user/notifications")
def my_notifications(unread_only: bool = False, user: dict = Depends(get_current_user)):
    """Fetch user notifications."""
    items = get_user_notifications(user["id"], unread_only)
    return {"items": items}

@app.post("/api/user/notifications/{id}/read")
def mark_read(id: str, user: dict = Depends(get_current_user)):
    """Mark a notification as read."""
    mark_notification_read(id, user["id"])
    return {"status": "ok"}


@app.post("/api/user/notifications/read-all")
def mark_all_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    mark_all_notifications_read(user["id"])
    return {"status": "ok"}

@app.get("/api/resources/stickers")
def get_stickers(user: dict = Depends(get_current_user)):
    """Fetch sticker resources filtered by tier."""
    return get_system_resources("sticker", user["tier"])

# --- Projects ---
@app.get("/api/projects")
def list_projects(
    page: int = 1, 
    limit: int = 6, 
    search: str = None, 
    include_canvas_data: bool = True,  # Whether to include canvas_data for staged loading
    user: dict = Depends(get_current_user)
):
    """List user projects with pagination and search support.
    
    Staged loading:
    - include_canvas_data=False: return basic info only (faster)
    - include_canvas_data=True: include canvas_data for preview rendering
    """
    print(f"[API] list_projects: page={page}, limit={limit}, search={search}, include_canvas_data={include_canvas_data}, user_id={user['id']}")
    items = get_user_projects(user["id"], page, limit, search, include_canvas_data)
    # Use count_user_projects for an accurate total
    total_count = count_user_projects(user["id"], search)
    print(f"[API] list_projects: items={len(items) if items else 0}, total={total_count}")
    return {"items": items, "total": total_count, "page": page}


@app.get("/api/projects/deleted")
def list_deleted_projects(
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Retrieve the user's deleted projects."""
    from db_service import get_user_deleted_projects
    return get_user_deleted_projects(user["id"], page, limit)


@app.get("/api/projects/dashboard")
def dashboard_projects(
    view: str = Query("all", pattern="^(all|bought|selling)$"),
    page: int = 1, 
    limit: int = 20, 
    search: str = None,
    include_canvas: bool = True,
    user: dict = Depends(get_current_user)
):
    """
    Get projects for dashboard with view type filtering (PRD v3.3).
    
    Args:
        view: View type - "all" (default), "bought", or "selling"
        page: Page number (default: 1)
        limit: Items per page (default: 20)
        search: Search query to filter projects by title (optional)
        include_canvas: Whether to include canvas_data (default: true)
    
    Returns:
        Projects list with:
        - items: Array of projects with marketplace_listing info
        - total: Total count for current view
        - page: Current page
        - view_type: Current view type
        
    View Types:
        - all: Shows all projects (created + bought + selling)
        - bought: Only purchased projects (read-only)
        - selling: Only projects with active marketplace listings
    """
    from db_service import get_dashboard_projects
    
    print(f"[API] dashboard_projects: view={view}, page={page}, search={search}")
    
    result = get_dashboard_projects(
        user_id=user["id"],
        view_type=view,
        page=page,
        limit=limit,
        search=search,
        include_canvas_data=include_canvas
    )
    
    return result


@app.get("/api/projects/seller-stats")
def get_project_seller_stats(user: dict = Depends(get_current_user)):
    """
    Get seller statistics for projects (PRD v3.3).
    
    Returns:
        Dict with:
        - total_selling: Number of active project listings
        - total_sales: Total number of sales across all listings
        - unique_buyers: Total unique buyers
        - total_revenue: Total credits earned from sales
        - total_usage: Total usage count across all listings
    """
    from db_service import get_seller_project_stats
    return get_seller_project_stats(user["id"])


@app.post("/api/projects/{project_id}/restore")
def restore_user_project(
    project_id: str,
    user: dict = Depends(get_current_user)
):
    """Allow a user to restore their own deleted project."""
    from db_service import user_restore_project
    try:
        project = user_restore_project(project_id, user["id"])
        if project:
            log_activity(user["id"], "restore_project", {"project_id": project_id})
            return {"status": "ok", "project": project}
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class ProjectCreate(BaseModel):
    title: Optional[str] = "My Magic Story"
    canvas_data: Optional[dict] = None

@app.post("/api/projects")
@limiter.limit("20/minute")  # Project creation rate limit
def new_project(request: Request, req: ProjectCreate = None, user: dict = Depends(get_current_user)):
    p = create_project(user["id"], req.title if req else None, req.canvas_data if req else None)
    log_activity(user["id"], "create_project")
    return p

@app.get("/api/projects/{id}")
def get_proj(id: str, user: dict = Depends(get_current_user)):
    p = get_project_detail(id, user["id"])
    if not p: raise HTTPException(404)
    
    # Debug: Log returned canvas_data
    canvas_data = p.get('canvas_data', {})
    if canvas_data:
        pages = canvas_data.get('pages', []) if isinstance(canvas_data, dict) else canvas_data
        print(f"[GET_PROJECT] Returning project {id}")
        print(f"[GET_PROJECT] canvas_data.pages count: {len(pages) if pages else 0}")
        for i, page in enumerate(pages[:3]):  # Only log first 3 pages
            if page:
                has_canvas = bool(page.get('canvasJson'))
                obj_count = len(page.get('canvasJson', {}).get('objects', [])) if page.get('canvasJson') else 0
                has_preview = bool(page.get('previewImage'))
                print(f"[GET_PROJECT] Page {i}: hasCanvasJson={has_canvas}, objectCount={obj_count}, hasPreview={has_preview}")
    else:
        print(f"[GET_PROJECT] No canvas_data for project {id}")
    
    return p

@app.put("/api/projects/{id}")
def save_proj(id: str, req: ProjectUpdate, user: dict = Depends(get_current_user)):
    """
    Save project API (PRD §12).
    
    - No credits charged for saving
    - Persist canvas_data and listing references
    - Validate access to any newly added listings (can_access_resource)
    - Record listing usage stats for newly referenced items
    """
    # Debug: Log incoming canvas_data
    if req.canvas_data:
        pages = req.canvas_data.get('pages', [])
        print(f"[SAVE_PROJECT] Saving project {id}")
        print(f"[SAVE_PROJECT] canvas_data.pages count: {len(pages)}")
        for i, page in enumerate(pages):
            if page:
                has_canvas = bool(page.get('canvasJson'))
                obj_count = len(page.get('canvasJson', {}).get('objects', [])) if page.get('canvasJson') else 0
                has_preview = bool(page.get('previewImage'))
                print(f"[SAVE_PROJECT] Page {i}: hasCanvasJson={has_canvas}, objectCount={obj_count}, hasPreview={has_preview}")
    else:
        print(f"[SAVE_PROJECT] No canvas_data received for project {id}")
    
    locked_elements = []
    new_usage_recorded = []
    
    # Handle newly referenced listings
    if req.used_listing_ids:
        for listing_id in req.used_listing_ids:
            # Fetch listing details
            listing = get_marketplace_item(listing_id, user["id"])
            
            if listing:
                # Verify access permissions
                allowed_tiers = listing.get("allowed_tiers", ["free"])
                if not can_access_resource(user, allowed_tiers):
                    locked_elements.append({
                        "listing_id": listing_id,
                        "title": listing.get("title", "Unknown"),
                        "reason": "Upgrade required to access this resource"
                    })
                else:
                    # Record usage (deduplicated)
                    is_new = record_listing_usage(listing_id, user["id"], id)
                    if is_new:
                        new_usage_recorded.append(listing_id)
    
    # Persist project
    save_project(id, user["id"], req.canvas_data, req.thumbnail_url, req.title)
    
    # Flag project if it contains locked elements
    if locked_elements:
        supabase.table("projects").update({
            "contains_locked_elements": True
        }).eq("id", id).eq("user_id", user["id"]).execute()
    
    return {
        "status": "saved",
        "locked_elements": locked_elements,
        "usage_recorded": new_usage_recorded
    }

@app.post("/api/projects/{id}/duplicate")
@limiter.limit("10/minute")  # Project duplication rate limit
def duplicate_proj(request: Request, id: str, user: dict = Depends(get_current_user)):
    """
    Duplicate/Copy a project.
    - Own projects: Creates copy with title + " copied"
    - Purchased projects: Creates copy with same title, preserves source info
    """
    from db_service import duplicate_project
    try:
        new_project = duplicate_project(id, user["id"])
        if new_project:
            log_activity(user["id"], "duplicate_project", {"source_project_id": id, "new_project_id": new_project["id"]})
            return new_project
        else:
            raise HTTPException(500, "Failed to copy project")
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(400, error_msg)

@app.delete("/api/projects/{id}")
def delete_proj(id: str, permanent: bool = False, user: dict = Depends(get_current_user)):
    """
    Delete a project (PRD v3.3).
    
    Args:
        id: Project ID to delete
        permanent: If true, permanently hides from trash (stage 2 delete)
                   If false, soft delete to trash (stage 1 delete)
    
    Stage 1 (permanent=false):
        - Sets is_deleted=true, deleted_at=now()
        - Project appears in trash for 30 days
        - Can be restored
    
    Stage 2 (permanent=true):
        - Sets is_hidden_from_trash=true
        - Project no longer visible to user
        - Data retained in database
    """
    try:
        if permanent:
            # Stage 2: Permanently hide from trash
            from db_service import permanently_hide_project
            result = permanently_hide_project(id, user["id"])
            if result:
                log_activity(user["id"], "permanent_delete_project", {"project_id": id})
                return {"status": "permanently_hidden", "stage": 2}
            else:
                raise HTTPException(404, "Project not found or not in trash")
        else:
            # Stage 1: Soft delete to trash
            soft_delete_project(id, user["id"])
            log_activity(user["id"], "delete_project", {"project_id": id})
            return {"status": "deleted", "stage": 1}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(404, str(e) or "Project not found")

# --- Core Gen ---
@app.post("/api/generate/story")
@limiter.limit("20/minute")
def gen_story(request: Request, req: StoryGenRequest, user: dict = Depends(get_current_user)):
    try:
        return generate_story_json(req.topic)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/generate/images")
@limiter.limit("10/minute")
async def gen_images(request: Request, req: ImageGenRequest, user: dict = Depends(get_current_user)):
    """
    Generate images using AI (PRD v3.2).
    
    Model selection based on tier:
    - Free/Starter: Standard model (flux-schnell)
    - Pro: High-quality model (flux-dev)
    
    Supports optional reference image for style/content guidance.
    """
    blacklist = ["nsfw", "nude", "sex"]
    if any(w in p.lower() for p in req.prompts for w in blacklist):
        raise HTTPException(400, "Safety Violation")
    
    # Reference image costs extra (7 credits vs 5)
    base_cost = 7 if req.reference_image else 5
    cost = len(req.prompts) * base_cost
    try:
        result = credit_deduct(user["id"], cost, "generation", 
            f"Gen {len(req.prompts)} images" + (" with ref" if req.reference_image else ""))
    except Exception as e:
        if "INSUFFICIENT" in str(e):
            raise HTTPException(402, "Insufficient credits")
        raise HTTPException(500, str(e))
    
    # Select model based on tier (PRD v3.2)
    # Normalize tier to lowercase for consistent comparison
    tier = (user.get("tier") or "free").lower()
    if tier == "pro":
        # High-quality model for Pro users
        model = "flux-dev"
    else:
        # Standard model for Free/Starter users
        model = "flux-schnell"
    
    # Generate images (with or without reference)
    urls, task_id = await generate_8_images(
        req.prompts, 
        model=model,
        reference_image=req.reference_image,
        reference_strength=req.reference_strength or 0.7,
        image_size=req.image_size or "landscape_4_3"
    )
    for url, prompt in zip(urls, req.prompts):
        save_asset(user["id"], url, "ai_generated", req.project_id, prompt)
    
    return {
        "image_urls": urls, 
        "balance": result["total"],
        "balance_monthly": result["balance_monthly"],
        "balance_permanent": result["balance_permanent"],
        "model_used": model,
        "used_reference": bool(req.reference_image)
    }

# Advanced OCR endpoint - detects tables, text, and images
@app.post("/api/tools/ocr")
@limiter.limit("10/minute")
async def ocr_tool(
    request: Request, 
    file: UploadFile = File(...), 
    project_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """
    Advanced Smart Scan (Pro only).
    
    Recognizes the following from uploaded images:
    - Text content (multi-language)
    - Table structures
    - Handwritten or sketched regions
    
    Returns structured JSON suitable for direct canvas insertion.
    """
    if user["tier"] != "pro":
        raise HTTPException(status_code=403, detail="Upgrade to Teacher Pro to use Smart Scan")
    
    # Deduct 5 credits for Smart Scan
    try:
        credit_result = credit_deduct(user["id"], 5, "ocr", "Smart Scan")
    except Exception as e:
        if "INSUFFICIENT" in str(e):
            raise HTTPException(402, "Insufficient credits")
        raise
    
    try:
        # Read file contents
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        # Upload original image to Supabase Storage
        import uuid
        from image_generator import supabase as storage_supabase, BUCKET_NAME
        
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
        filename = f"scans/{user['id']}/{uuid.uuid4()}.{ext}"
        
        source_image_url = None
        if storage_supabase:
            try:
                storage_supabase.storage.from_(BUCKET_NAME).upload(
                    path=filename,
                    file=contents,
                    file_options={"content-type": file.content_type or "image/png"}
                )
                source_image_url = storage_supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
            except Exception as upload_err:
                print(f"Failed to upload scan source: {upload_err}")
        
        # Use GPT-4o for adaptive OCR prompts
        ocr_prompt = """You are an expert OCR and content analysis system. 

STEP 1: First, identify what type of content this image contains:
- Document/Worksheet: forms, worksheets, printed documents
- Handwritten: notes, handwriting, sketches with text
- Logo/Brand: logos, banners, marketing materials
- Photo with text: photos containing signs, labels, or captions
- Table/Data: spreadsheets, data tables
- Mixed: combination of the above

STEP 2: Based on the content type, extract ALL information appropriately.

OUTPUT FORMAT (JSON):
{
  "content_type": "document" | "handwritten" | "logo" | "photo" | "table" | "mixed",
  "blocks": [
    {
      "type": "text",
      "content": "Exact text as it appears - MUST extract ALL readable text",
      "style": "title" | "heading" | "paragraph" | "bullet" | "label" | "handwritten" | "logo_text",
      "position": "top" | "middle" | "bottom"
    },
    {
      "type": "table",
      "rows": 3,
      "cols": 2, 
      "cells": [["Cell content..."]],
      "position": "top" | "middle" | "bottom"
    },
    {
      "type": "image",
      "description": "Detailed description of non-text visuals (icons, illustrations, photos)",
      "position": "top" | "middle" | "bottom"
    }
  ],
  "summary": "What this image contains and its purpose"
}

CRITICAL EXTRACTION RULES:
1. **ALL TEXT MUST BE EXTRACTED** - every readable character, word, sentence
2. **Logo text is still TEXT** - "Make Decodables" in a logo = text block with style "logo_text"
3. **Separate blocks for separate text areas** - don't merge unrelated text
4. **Tables must preserve structure** - extract cell by cell
5. **Handwriting** - transcribe as accurately as possible, mark style as "handwritten"
6. **Numbers, dates, codes** - extract exactly as shown

Return ONLY valid JSON, no markdown formatting."""

        response = openai_client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4o for best recognition accuracy
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ocr_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ],
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # Parse OCR response
        import json
        ocr_result = json.loads(response.choices[0].message.content)
        
        # Convert extracted content into canvas elements
        canvas_elements = []
        y_offset = 50
        
        for block in ocr_result.get("blocks", []):
            if block["type"] == "text":
                canvas_elements.append({
                    "type": "text",
                    "content": block["content"],
                    "x": 50,
                    "y": y_offset,
                    "width": 400,
                    "fontSize": 24 if block.get("style") == "title" else 16,
                    "fontWeight": "bold" if block.get("style") == "title" else "normal"
                })
                y_offset += 60 if block.get("style") == "title" else 40
                
            elif block["type"] == "table":
                canvas_elements.append({
                    "type": "table",
                    "rows": block["rows"],
                    "cols": block["cols"],
                    "cells": block["cells"],
                    "x": 50,
                    "y": y_offset,
                    "width": 400,
                    "height": block["rows"] * 40
                })
                y_offset += block["rows"] * 40 + 20
                
            elif block["type"] == "image":
                canvas_elements.append({
                    "type": "image_placeholder",
                    "description": block["description"],
                    "x": 50,
                    "y": y_offset,
                    "width": 200,
                    "height": 200
                })
                y_offset += 220
        
        # Persist scan data in assets table
        scan_data = {
            "source_image_url": source_image_url,
            "ocr_result": ocr_result,
            "canvas_elements": canvas_elements
        }
        
        # Store as a 'scanned' asset entry
        asset_id = None
        try:
            asset_result = supabase.table("assets").insert({
                "user_id": user["id"],
                "project_id": project_id,
                "url": source_image_url or "",
                "type": "scanned",
                "metadata": scan_data
            }).execute()
            if asset_result.data:
                asset_id = asset_result.data[0]["id"]
        except Exception as save_err:
            print(f"Failed to save scanned asset: {save_err}")
        
        return {
            "success": True,
            "asset_id": asset_id,
            "source_image_url": source_image_url,
            "ocr_result": ocr_result,
            "canvas_elements": canvas_elements,
            "summary": ocr_result.get("summary", ""),
            "balance": credit_result["total"],
            "balance_monthly": credit_result["balance_monthly"],
            "balance_permanent": credit_result["balance_permanent"]
        }
        
    except json.JSONDecodeError as je:
        print(f"OCR JSON Parse Error: {je}")
        raise HTTPException(500, "Failed to parse OCR result")
    except Exception as e:
        print(f"OCR Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"OCR Failed: {str(e)}")

# --- Export ---

# Generate PDF directly from project data (Dashboard) - free
@app.get("/api/projects/{project_id}/pdf")
@limiter.limit("10/minute")  # PDF generation consumes server resources
def get_project_pdf(request: Request, project_id: str, user: dict = Depends(get_current_user)):
    """Generate a PDF from stored project data without re-uploading assets (always free)."""
    proj = get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")
    
    canvas_data = proj.get("canvas_data", {})
    
    # Handle legacy vs new canvas_data formats
    if isinstance(canvas_data, list):
        # Legacy format: canvas_data is a pages array
        pages = canvas_data
        paper_size = "US_LETTER"
    else:
        # New format: canvas_data is { pages, paperSize }
        pages = canvas_data.get("pages", [])
        paper_size_raw = canvas_data.get("paperSize", "Letter")
        paper_size = "A4" if paper_size_raw == "A4" else "US_LETTER"
    
    # Extract preview images and prompt text
    image_urls = []
    texts = []
    for page in pages:
        if isinstance(page, dict):
            image_urls.append(page.get("previewImage", "") or "")
            texts.append(page.get("prompt", "") or "")
        else:
            image_urls.append("")
            texts.append("")
    
    # Pad to 8 pages
    while len(image_urls) < 8:
        image_urls.append("")
        texts.append("")
    
    # Render PDF
    buf = BytesIO()
    create_foldable_book(image_urls, texts, buf, paper_type=paper_size)
    buf.seek(0)
    
    # Build filename
    title = proj.get("title", "project").replace(" ", "_")
    
    # Log download (no credits deducted)
    log_activity(user["id"], "download_pdf", {"project_id": project_id})
    
    return StreamingResponse(
        buf, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename={title}.pdf"}
    )

# Generate PDF preview image (prevent direct download bypass)
@app.get("/api/projects/{project_id}/preview")
@limiter.limit("20/minute")  # Preview generation rate limit
def preview_project_as_image(request: Request, project_id: str, user: dict = Depends(get_current_user)):
    """Generate a PNG preview of the PDF to deter direct downloads."""
    import fitz  # PyMuPDF
    
    proj = get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")
    
    canvas_data = proj.get("canvas_data", {})
    
    # Handle legacy vs new canvas_data structure
    if isinstance(canvas_data, list):
        pages = canvas_data
        paper_size = "US_LETTER"
    else:
        pages = canvas_data.get("pages", [])
        paper_size_raw = canvas_data.get("paperSize", "Letter")
        paper_size = "A4" if paper_size_raw == "A4" else "US_LETTER"
    
    # Extract preview images and text prompts
    image_urls = []
    texts = []
    for page in pages:
        if isinstance(page, dict):
            image_urls.append(page.get("previewImage", "") or "")
            texts.append(page.get("prompt", "") or "")
        else:
            image_urls.append("")
            texts.append("")
    
    # Pad to 8 pages
    while len(image_urls) < 8:
        image_urls.append("")
        texts.append("")
    
    # Render PDF into memory
    pdf_buffer = BytesIO()
    create_foldable_book(image_urls, texts, pdf_buffer, paper_type=paper_size)
    pdf_buffer.seek(0)
    
    # Convert the PDF into an image
    try:
        pdf_doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        page = pdf_doc[0]  # Single page booklet
        
        # Render at 2x zoom for crisp preview
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PNG
        img_buffer = BytesIO(pix.tobytes("png"))
        pdf_doc.close()
        
        # Log preview event
        log_activity(user["id"], "preview_pdf", {"project_id": project_id})
        
        return StreamingResponse(
            img_buffer, 
            media_type="image/png",
            headers={"Cache-Control": "no-store"}
        )
    except Exception as e:
        print(f"PDF to image conversion error: {e}")
        raise HTTPException(500, "Failed to generate preview")

@app.post("/api/generate/pdf")
@limiter.limit("10/minute")  # PDF generation rate limit
def dl_pdf(request: Request, req: PdfGenRequest, user: dict = Depends(get_current_user)):
    """Generate a PDF (always free per PRD v3.0)."""
    # No credits charged; only update hash for cache/version tracking
    proj = get_project_detail(req.project_id, user["id"])
    if proj and req.current_hash != proj.get("last_downloaded_hash"):
        update_project_hash(req.project_id, req.current_hash)
            
    buf = BytesIO()
    create_foldable_book(req.image_urls, req.texts, buf)
    buf.seek(0)
    log_activity(user["id"], "download_pdf", {"project_id": req.project_id})
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=zine.pdf"})

@app.post("/api/export/zip")
@limiter.limit("5/minute")  # ZIP export is resource intensive
def dl_zip(request: Request, req: PdfGenRequest, user: dict = Depends(get_current_user)):
    """Export a ZIP (Pro only, PRD v3.2)."""
    # Normalize tier to lowercase for consistent comparison
    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "ZIP export requires Pro plan. Starter users can export PDF only.")
    buf = BytesIO()
    create_assets_zip(req.image_urls, buf)
    buf.seek(0)
    log_activity(user["id"], "export_zip", {"project_id": req.project_id})
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=assets.zip"})

# Export ZIP directly from saved project (PDF + images)
@app.get("/api/projects/{project_id}/zip")
@limiter.limit("5/minute")  # ZIP export is resource intensive
def get_project_zip(request: Request, project_id: str, user: dict = Depends(get_current_user)):
    """Export a ZIP from stored project data (includes PDF + images) - Pro only (PRD v3.2)."""
    # Enforce Pro-only access (PRD v3.2)
    # Normalize tier to lowercase for consistent comparison
    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "ZIP export requires Pro plan. Starter users can export PDF only.")
    
    proj = get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")
    
    canvas_data = proj.get("canvas_data", {})
    
    # Handle legacy vs new canvas_data
    if isinstance(canvas_data, list):
        pages = canvas_data
        paper_size = "US_LETTER"
    else:
        pages = canvas_data.get("pages", [])
        paper_size_raw = canvas_data.get("paperSize", "Letter")
        paper_size = "A4" if paper_size_raw == "A4" else "US_LETTER"
    
    # Extract preview images and text
    image_urls = []
    texts = []
    for page in pages:
        if isinstance(page, dict):
            image_urls.append(page.get("previewImage", "") or "")
            texts.append(page.get("prompt", "") or "")
        else:
            image_urls.append("")
            texts.append("")
    
    # Pad to 8 pages
    while len(image_urls) < 8:
        image_urls.append("")
        texts.append("")
    
    title = proj.get("title", "project").replace(" ", "_")
    
    # Build ZIP containing PDF and all images
    import zipfile
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Generate and add PDF
        pdf_buffer = BytesIO()
        create_foldable_book(image_urls, texts, pdf_buffer, paper_type=paper_size)
        pdf_buffer.seek(0)
        zf.writestr(f"{title}.pdf", pdf_buffer.read())
        
        # 2. Add all images
        import requests
        import re
        
        for i, img_url in enumerate(image_urls):
            if not img_url:
                continue
            
            try:
                if img_url.startswith('data:'):
                    # Handle base64-embedded images
                    match = re.match(r'data:image/([^;]+);base64,(.+)', img_url)
                    if match:
                        ext = match.group(1)
                        if ext == 'jpeg':
                            ext = 'jpg'
                        img_data = base64.b64decode(match.group(2))
                        zf.writestr(f"Page_{i+1}.{ext}", img_data)
                else:
                    # Handle HTTP image URLs
                    resp = requests.get(img_url, timeout=10)
                    if resp.status_code == 200:
                        # Infer file extension from Content-Type or URL
                        content_type = resp.headers.get('content-type', 'image/png')
                        ext = content_type.split('/')[-1].split(';')[0]
                        if ext == 'jpeg':
                            ext = 'jpg'
                        zf.writestr(f"Page_{i+1}.{ext}", resp.content)
            except Exception as e:
                print(f"ZIP: Failed to add image {i+1}: {e}")
    
    zip_buffer.seek(0)
    
    # Log ZIP export event
    log_activity(user["id"], "export_zip", {"project_id": project_id})
    
    return StreamingResponse(
        zip_buffer, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename={title}.zip"}
    )

# --- Marketplace ---
@app.get("/api/marketplace/items")
@limiter.limit("60/minute")  # Listing query rate limit
def marketplace_items(
    request: Request,
    featured: bool = False, 
    resource_type: Optional[str] = None,
    sort: Optional[str] = "latest",  # 'latest' | 'popular' | 'best_selling'
    tier: Optional[str] = None,  # 'all' | 'free' | 'starter' | 'pro'
    price: Optional[str] = None,  # 'all' | 'free' | 'paid'
    mine: bool = False,
    page: int = 1, 
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """
    Fetch marketplace listings (PRD §13).
    
    Public results default to moderation_status='approved', is_public=true, is_deleted=false.
    When mine=true, return the caller's listings across all states.
    """
    try:
        print(f"[marketplace_items] Request params: resource_type={resource_type}, sort={sort}, tier={tier}, price={price}, mine={mine}, page={page}, limit={limit}")
        print(f"[marketplace_items] User: {user.get('id', 'unknown')}, tier: {user.get('tier', 'unknown')}")
        
        # Query database for listings
        items = get_marketplace_listings(
            featured=featured,
            resource_type=resource_type,
            page=page,
            limit=limit,
            sort=sort,
            tier_filter=tier,
            price_filter=price,
            mine=mine,
            user_id=user["id"] if mine else None
        )
        
        print(f"[marketplace_items] Retrieved {len(items)} items from database")
        
        # Enrich each item with accessibility and ownership flags
        for item in items:
            try:
                allowed_tiers = item.get("allowed_tiers", ["free", "starter", "pro"])
                if not isinstance(allowed_tiers, list):
                    allowed_tiers = ["free", "starter", "pro"]
                item["is_accessible"] = can_access_resource(user, allowed_tiers)
                item["is_owned"] = check_user_purchase(user["id"], item["id"])
            except Exception as e:
                print(f"[marketplace_items] Error processing item {item.get('id', 'unknown')}: {e}")
                import traceback
                print(traceback.format_exc())
                # Fall back to safe defaults
                item["is_accessible"] = False
                item["is_owned"] = False
        
        result = {"items": items, "total": len(items), "page": page}
        print(f"[marketplace_items] Returning {len(items)} items")
        return result
    except HTTPException:
        # Propagate HTTPException with original status code
        raise
    except Exception as e:
        import traceback
        error_msg = f"Failed to load marketplace items: {str(e)}"
        print(f"[marketplace_items] ERROR: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/marketplace/item/{listing_id}")
def marketplace_item_detail(
    listing_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Retrieve single listing details (PRD §13).
    
    - Public access: only approved + public + not deleted
    - Seller: can view their own listings in any state
    - Admin: unrestricted access
    """
    item = get_marketplace_item(listing_id, user["id"])
    
    if not item:
        # Allow admins to load any status directly
        if user.get("role") == "admin":
            item = supabase.table("marketplace_listings").select("*, profiles(username, avatar_url)")\
                .eq("id", listing_id).single().execute().data
        
        if not item:
            raise HTTPException(404, "Listing not found")
    
    # Attach permission info
    allowed_tiers = item.get("allowed_tiers", ["free", "starter", "pro"])
    item["is_accessible"] = can_access_resource(user, allowed_tiers)
    item["is_owned"] = check_user_purchase(user["id"], item["id"])
    
    return item

@app.post("/api/marketplace/publish")
@limiter.limit("10/minute")  # Publish rate limit
def marketplace_publish(request: Request, req: MarketplacePublishRequest, user: dict = Depends(require_member)):
    """
    Submit listing for review (PRD §7/8).
    
    Permissions:
    - Free: cannot publish
    - Starter: resource_type='asset' and price_credits must be 0
    - Pro: resource_type in {'asset','project'} with price_credits 0..500
    
    Listing enters moderation_status='pending' and requires admin approval.
    """
    # 1. Validate publish permission
    perm = publish_permission(user, req.resource_type, req.price_credits)
    if not perm["allowed"]:
        raise HTTPException(403, perm["reason"])
    
    # 2. Validate allowed_tiers whitelist
    tiers_validation = validate_allowed_tiers(req.allowed_tiers)
    if not tiers_validation["valid"]:
        raise HTTPException(400, tiers_validation["reason"])
    
    # 3. Create listing (auto-pending)
    listing = create_listing(
        seller_id=user["id"],
        title=req.title,
        description=req.description,
        thumbnail_url=req.thumbnail_url,
        resource_url=req.resource_url,
        resource_type=req.resource_type,
        price_credits=req.price_credits,
        allowed_tiers=req.allowed_tiers,
        submit_for_review=True
    )
    
    log_activity(user["id"], "marketplace_publish", {
        "listing_id": listing["id"],
        "resource_type": req.resource_type,
        "price_credits": req.price_credits
    })
    
    return {
        "listing_id": listing["id"],
        "moderation_status": listing.get("moderation_status", "pending"),
        "message": "Submitted for review"
    }

@app.post("/api/marketplace/unpublish")
def marketplace_unpublish(req: MarketplacePurchaseRequest, user: dict = Depends(get_current_user)):
    """
    Unpublish listing (PRD §13).
    
    Sets is_public=false while preserving purchases and usage_count.
    """
    result = unpublish_listing(req.listing_id, user["id"])
    
    if not result:
        raise HTTPException(404, "Listing not found or not owned by you")
    
    log_activity(user["id"], "marketplace_unpublish", {"listing_id": req.listing_id})
    
    return {"status": "unpublished"}

@app.post("/api/marketplace/purchase")
@limiter.limit("10/minute")  # Purchase rate limit (anti-fraud)
def marketplace_purchase(request: Request, req: MarketplacePurchaseRequest, user: dict = Depends(get_current_user)):
    """Purchase a marketplace listing."""
    result = execute_purchase(
        buyer_id=user["id"], 
        listing_id=req.listing_id,
        idempotency_key=req.idempotency_key,
        utm_source=req.utm_source,
        utm_medium=req.utm_medium,
        utm_campaign=req.utm_campaign,
        referral_context=req.referral_context
    )
    
    if not result["success"]:
        if "Upgrade" in result["message"]:
            raise HTTPException(403, result["message"])
        elif "Insufficient" in result["message"]:
            raise HTTPException(402, result["message"])
        else:
            raise HTTPException(400, result["message"])
    
    if not result.get("already_owned"):
        log_activity(user["id"], "marketplace_purchase", {"listing_id": req.listing_id})
    
    return result

@app.get("/api/marketplace/my-listings")
def my_listings(page: int = 1, limit: int = 20, user: dict = Depends(get_current_user)):
    """Retrieve listings published by the current user."""
    items = get_seller_listings(user["id"], page, limit)
    return {"items": items, "total": len(items)}

@app.put("/api/marketplace/listings/{listing_id}")
def update_my_listing(listing_id: str, req: ListingUpdateRequest, user: dict = Depends(get_current_user)):
    """Update one of the current user's listings."""
    updates = req.dict(exclude_none=True)
    result = update_listing(listing_id, user["id"], updates)
    if not result:
        raise HTTPException(404, "Listing not found or not owned by you")
    return result

@app.get("/api/marketplace/seller/stats")
def seller_stats(user: dict = Depends(get_current_user)):
    """Fetch seller stats (PRD §13)."""
    stats = get_seller_stats(user["id"])
    return stats

@app.get("/api/marketplace/leaderboard")
def marketplace_leaderboard(
    period: str = "monthly",  # 'monthly' | 'all_time'
    type: str = "all",  # 'all' | 'project' | 'asset'
    user: dict = Depends(get_current_user)
):
    """
    Fetch leaderboard (PRD §9).
    
    Returns top 10 listings with usage_count and rank (approved + public + not deleted only).
    """
    leaderboard = get_leaderboard(period=period, board_type=type, limit=10)
    return {"items": leaderboard, "period": period, "type": type}


# --- Content Reports ---
class ReportRequest(BaseModel):
    listing_id: str
    reason: str

@app.post("/api/marketplace/report")
@limiter.limit("10/minute")  # Rate limit for reports
def submit_report(request: Request, req: ReportRequest, user: dict = Depends(get_current_user)):
    """
    Submit a content report for a marketplace listing.
    
    Users can report listings for copyright violations, inappropriate content, etc.
    """
    from db_service import create_report
    try:
        report = create_report(user["id"], req.listing_id, req.reason)
        if report:
            log_activity(user["id"], "submit_report", {"listing_id": req.listing_id})
            return {"success": True, "report_id": report["id"], "message": "Report submitted successfully"}
        raise HTTPException(500, "Failed to submit report")
    except Exception as e:
        error_msg = str(e)
        if "already reported" in error_msg.lower():
            raise HTTPException(400, error_msg)
        raise HTTPException(500, error_msg)

@app.get("/api/marketplace/my-reports")
def get_my_reports(page: int = 1, limit: int = 20, user: dict = Depends(get_current_user)):
    """Get reports submitted by the current user."""
    from db_service import get_user_reports
    reports = get_user_reports(user["id"], page, limit)
    return {"items": reports, "total": len(reports)}

# --- Pay & Support ---
@app.post("/api/payment/checkout")
@limiter.limit("5/minute")  # Strict rate limit for payment APIs
def pay(request: Request, req: CheckoutRequest, user: dict = Depends(get_current_user)):
    # Apply discount if available
    discount = get_user_discount(user["id"], req.plan_type)
    discount_percent = discount.get("discount_percent", 0) if discount else 0
    
    url = create_checkout_session(user["id"], req.plan_type, discount_percent)
    return {"url": url, "discount_applied": discount_percent}

@app.post("/api/payment/portal")
@limiter.limit("10/minute")  # Billing portal rate limit
def portal(request: Request, user: dict = Depends(get_current_user)):
    if not user.get("stripe_customer_id"): raise HTTPException(400, "No subscription found")
    return {"url": create_portal_session(user["id"], user.get("stripe_customer_id"))}

@app.post("/api/support/email")
@limiter.limit("3/minute")  # Support ticket anti-spam limit
def ticket(request: Request, req: SupportTicketRequest, user: dict = Depends(get_current_user)):
    # Use provided email or fallback to user's profile email
    email = req.email or user.get("email", "unknown@user.com")
    create_support_ticket(user["id"], email, req.message)
    return {"status": "ok"}

@app.post("/api/contact")
@limiter.limit("3/minute")  # Public endpoint rate limit (abuse protection)
def contact_form(request: Request, req: ContactFormRequest):
    """
    Public contact form endpoint - no authentication required.
    Used by Contact Us page for both logged in and guest users.
    """
    # Create support ticket with "guest" as user_id for unauthenticated users
    create_support_ticket("guest", req.email, req.message)
    return {"status": "ok"}

@app.post("/api/feedback")
@limiter.limit("3/minute")  # Feedback anti-spam limit
def feedback_with_images(request: Request, req: FeedbackWithImagesRequest):
    """
    Submit feedback with optional images.
    Works for both logged in and guest users.
    """
    from db_service import send_feedback_with_images
    
    # Try to get user info if authenticated
    user_id = "guest"
    try:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = verify_clerk_token(token)
            user_id = payload.get("sub", "guest")
    except:
        pass
    
    send_feedback_with_images(user_id, req.email, req.message, req.images)
    return {"status": "ok", "message": "Feedback submitted successfully"}

# --- Admin ---
@app.get("/api/admin/users")
@limiter.limit("60/minute")  # Search rate limit (anti-scraping)
def adm_users(request: Request, query: str, admin: dict = Depends(require_admin)):
    users = search_users(query)
    return {"users": users}

@app.get("/api/admin/user/{uid}")
def adm_audit(uid: str, admin: dict = Depends(require_admin)):
    return get_full_user_audit(uid)

@app.post("/api/admin/credits/adjust")
@limiter.limit("30/minute")  # Admin action rate limit
def adm_adj(request: Request, req: AdminAdjustRequest, admin: dict = Depends(require_admin)):
    """Manually adjust a user's credits (supports bucket selection)."""
    admin_adjust_credits(req.user_id, req.amount, req.bucket, req.reason)
    log_activity(admin["id"], "admin_credits_adjust", {
        "target_user": req.user_id,
        "amount": req.amount,
        "bucket": req.bucket,
        "reason": req.reason
    })
    # Record in admin audit log
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="credit_adjust",
        target_user_id=req.user_id,
        details=f"{'+' if req.amount > 0 else ''}{req.amount} {req.bucket} credits",
        reason=req.reason
    )
    return {"status": "ok"}

@app.post("/api/admin/tier/update")
@limiter.limit("30/minute")  # Admin action rate limit
def adm_tier(request: Request, req: AdminTierRequest, admin: dict = Depends(require_admin)):
    # Capture current tier for logging
    old_profile = get_user_profile(req.user_id)
    old_tier = old_profile.get("tier", "unknown") if old_profile else "unknown"
    
    # Derive subscription_status from target tier
    # Starter/Pro => active, Free => inactive
    subscription_status = "active" if req.tier in ["starter", "pro"] else "inactive"
    update_subscription_tier(req.user_id, req.tier, subscription_status=subscription_status)
    log_activity(admin["id"], "admin_tier_update", {
        "target_user": req.user_id,
        "new_tier": req.tier,
        "subscription_status": subscription_status
    })
    # Record tier change in audit log
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="tier_change",
        target_user_id=req.user_id,
        details=f"{old_tier} → {req.tier}",
        reason=None
    )
    return {"status": "ok"}

@app.post("/api/admin/discount")
def adm_discount(req: AdminDiscountRequest, admin: dict = Depends(require_admin)):
    """Create a user-specific discount."""
    discount = create_user_discount(
        req.user_id, 
        req.discount_percent, 
        req.valid_days, 
        req.target_plan
    )
    log_activity(admin["id"], "admin_discount_create", {
        "target_user": req.user_id,
        "discount_percent": req.discount_percent
    })
    return discount

@app.get("/api/admin/user/{uid}/payments")
def adm_user_payments(uid: str, admin: dict = Depends(require_admin)):
    """
    Fetch a user's payment history (for refund workflows).
    
    Returns:
    - user_code: unique verification code
    - user_email: email on file
    - payments: list with refundable amounts
    - subscriptions: subscription history with status info
    """
    user = get_user_profile(uid)
    if not user:
        raise HTTPException(404, "User not found")
    
    user_code = user.get("user_code")
    user_email = user.get("email")
    
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        return {"user_code": user_code, "user_email": user_email, "payments": [], "subscriptions": []}
    
    # Retrieve payment list
    payments = get_customer_payments(customer_id, limit=20)
    payment_list = []
    for pi in payments:
        # Calculate refunded vs refundable amounts
        amount_refunded = pi.amount - (pi.amount_received if hasattr(pi, 'amount_received') else pi.amount)
        refundable_amount = pi.amount_received if hasattr(pi, 'amount_received') else pi.amount
        is_fully_refunded = refundable_amount <= 0
        
        payment_list.append({
            "id": pi.id,
            "amount": pi.amount,  # Original charge amount
            "amount_refunded": amount_refunded,  # Amount already refunded
            "refundable_amount": refundable_amount,  # Remaining refundable amount
            "currency": pi.currency,
            "status": pi.status,
            "created": pi.created,
            "description": pi.description,
            "is_partially_refunded": amount_refunded > 0 and not is_fully_refunded,
            "is_fully_refunded": is_fully_refunded,
        })
    
    # Retrieve subscription information
    subscriptions = get_customer_subscriptions(customer_id)
    sub_list = []
    for sub in subscriptions:
        sub_list.append({
            "id": sub.id,
            "status": sub.status,
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "plan": sub.items.data[0].price.id if sub.items.data else None,
            "created": sub.created,
        })
    
    return {
        "user_code": user_code,
        "user_email": user_email,
        "payments": payment_list, 
        "subscriptions": sub_list
    }

@app.post("/api/admin/refund")
@limiter.limit("10/minute")  # Refund operation rate limit
def adm_refund(request: Request, req: AdminRefundRequest, admin: dict = Depends(require_admin)):
    """
    Admin refund operation (full or partial) with safety checks:
    1. User must exist
    2. user_code/email must match records
    3. PaymentIntent must exist
    4. PaymentIntent must belong to the user
    5. Refund amount cannot exceed refundable amount
    6. PaymentIntent must not be fully refunded already
    """
    user = get_user_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Safety check: ensure user_code matches profile
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match. Please verify the user code.")
    
    # Fetch user's Stripe customer ID
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(400, "User has no Stripe customer ID")
    
    # Fetch PaymentIntent details
    pi = get_payment_intent_details(req.payment_intent_id)
    if not pi:
        raise HTTPException(404, "Payment not found")
    
    # Safety check #1: ensure PaymentIntent belongs to user
    if pi.customer != customer_id:
        raise HTTPException(403, "Payment does not belong to this user")
    
    # Safety check #2: validate PaymentIntent status
    if pi.status != 'succeeded':
        raise HTTPException(400, f"Cannot refund payment with status: {pi.status}")
    
    # Safety check #3: compute refundable amount
    # amount_received is net of prior refunds
    refundable_amount = pi.amount_received if hasattr(pi, 'amount_received') else pi.amount
    
    if refundable_amount <= 0:
        raise HTTPException(400, "Payment has already been fully refunded")
    
    # Safety check #4: validate partial refund amount
    if req.amount_cents is not None:
        if req.amount_cents <= 0:
            raise HTTPException(400, "Refund amount must be positive")
        if req.amount_cents > refundable_amount:
            raise HTTPException(400, f"Refund amount ({req.amount_cents}) exceeds refundable amount ({refundable_amount})")
    
    # Execute Stripe refund
    result = create_refund(
        req.payment_intent_id,
        amount_cents=req.amount_cents,
        reason="requested_by_customer"
    )
    
    if not result["success"]:
        raise HTTPException(400, f"Refund failed: {result['error']}")
    
    refund = result["refund"]
    refund_amount = refund.amount
    currency = refund.currency.upper()
    
    # Record refund in user transaction history
    log_payment_record(
        req.user_id,
        -refund_amount,  # Negative to denote refund
        currency,
        "refund",
        f"Refund - ${refund_amount/100:.2f} | Reason: {req.reason}"
    )
    
    # Log admin operation
    log_activity(admin["id"], "admin_refund", {
        "target_user": req.user_id,
        "payment_intent_id": req.payment_intent_id,
        "refund_id": refund.id,
        "amount_cents": refund_amount,
        "original_amount": pi.amount,
        "refundable_amount": refundable_amount,
        "reason": req.reason
    })
    
    # Capture audit entry
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="refund",
        target_user_id=req.user_id,
        details=f"${refund_amount/100:.2f} {currency} (PI: {req.payment_intent_id[:20]}...)",
        reason=req.reason
    )
    
    return {
        "status": "refunded",
        "refund_id": refund.id,
        "amount": refund_amount,
        "currency": currency
    }

@app.post("/api/admin/subscription/cancel")
@limiter.limit("10/minute")  # Subscription operation rate limit
def adm_cancel_subscription(request: Request, req: AdminCancelSubscriptionRequest, admin: dict = Depends(require_admin)):
    """
    Admin-initiated subscription cancellation.
    
    - immediate=True: cancel immediately
    - immediate=False: cancel at end of current billing period
    
    Safety checklist:
    1. User exists
    2. user_code/email matches
    3. Stripe customer ID present
    4. Subscription belongs to user
    5. Subscription status is active/trialing/past_due
    6. Subscription not already scheduled for cancellation
    """
    import stripe
    
    user = get_user_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Safety check: ensure user_code matches profile
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match. Please verify the user code.")
    
    # Retrieve Stripe customer ID
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(400, "User has no Stripe customer ID")
    
    # Safety check #1: fetch subscription details
    try:
        subscription_detail = stripe.Subscription.retrieve(req.subscription_id)
    except stripe.error.StripeError as e:
        raise HTTPException(404, f"Subscription not found: {str(e)}")
    
    # Safety check #2: subscription belongs to user
    if subscription_detail.customer != customer_id:
        raise HTTPException(403, "Subscription does not belong to this user")
    
    # Safety check #3: subscription status is cancellable
    if subscription_detail.status not in ['active', 'trialing', 'past_due']:
        raise HTTPException(400, f"Cannot cancel subscription with status: {subscription_detail.status}")
    
    # Safety check #4: not already scheduled for cancellation (when delayed)
    if not req.immediate and subscription_detail.cancel_at_period_end:
        raise HTTPException(400, "Subscription is already scheduled for cancellation")
    
    # Execute cancellation
    result = cancel_subscription(req.subscription_id, immediate=req.immediate)
    
    if not result["success"]:
        raise HTTPException(400, f"Cancel subscription failed: {result['error']}")
    
    subscription = result["subscription"]
    
    # Determine plan name for logging
    plan_name = "Unknown"
    if subscription_detail.items.data:
        price_id = subscription_detail.items.data[0].price.id
        if 'starter' in price_id.lower():
            plan_name = "Starter"
        elif 'pro' in price_id.lower():
            plan_name = "Pro"
    
    # Immediate cancellation → downgrade to Free
    if req.immediate:
        update_subscription_tier(req.user_id, "free", subscription_status="canceled")
        
        # Log transaction history entry
        log_payment_record(
            req.user_id,
            0,
            "USD",
            "sub_canceled",
            f"{plan_name} Subscription Canceled (Immediate) | Reason: {req.reason}"
        )
    else:
        # Log scheduled cancellation entry
        log_payment_record(
            req.user_id,
            0,
            "USD",
            "sub_cancel_scheduled",
            f"{plan_name} Subscription Cancel Scheduled | Ends: {subscription.current_period_end} | Reason: {req.reason}"
        )
    
    # Log admin action
    log_activity(admin["id"], "admin_cancel_subscription", {
        "target_user": req.user_id,
        "subscription_id": req.subscription_id,
        "plan": plan_name,
        "immediate": req.immediate,
        "reason": req.reason
    })
    
    # Capture audit entry
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="subscription_cancel",
        target_user_id=req.user_id,
        details=f"{plan_name} ({'immediate' if req.immediate else 'at period end'})",
        reason=req.reason
    )
    
    return {
        "status": "canceled" if req.immediate else "cancel_scheduled",
        "subscription_id": subscription.id,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "current_period_end": subscription.current_period_end
    }

@app.post("/api/admin/subscription/downgrade")
@limiter.limit("10/minute")  # Subscription operation rate limit
def adm_downgrade_subscription(request: Request, req: AdminDowngradeRequest, admin: dict = Depends(require_admin)):
    """
    Admin-assisted subscription downgrade.
    
    Supported downgrade paths:
    - Pro → Starter (plan change)
    - Pro → Free (cancel subscription)
    - Starter → Free (cancel subscription)
    
    - immediate=True: take effect immediately
    - immediate=False: apply after current period
    
    Safety checklist:
    1. User exists
    2. user_code/email matches
    3. Target tier is lower than current tier
    4. Stripe subscription is valid
    """
    import stripe
    
    user = get_user_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Safety check #1: validate user_code
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match")
    
    # Safety check #2: validate email
    if user.get("email") != req.user_email:
        raise HTTPException(403, "User email does not match")
    
    current_tier = user.get("tier", "free")
    target_tier = req.target_tier.lower()
    
    # Safety check #3: verify downgrade path
    tier_levels = {"free": 0, "starter": 1, "pro": 2}
    if tier_levels.get(target_tier, -1) >= tier_levels.get(current_tier, 0):
        raise HTTPException(400, f"Cannot downgrade from {current_tier} to {target_tier}")
    
    if target_tier not in ["free", "starter"]:
        raise HTTPException(400, "Invalid target tier. Must be 'free' or 'starter'")
    
    customer_id = user.get("stripe_customer_id")
    
    # Case 1: downgrading to Free (subscription cancellation)
    if target_tier == "free":
        if not customer_id:
            # No Stripe subscription; update DB directly
            update_subscription_tier(req.user_id, "free", subscription_status="inactive")
            
            # Reset monthly credits
            supabase.table("profiles").update({
                "credits_monthly": 0
            }).eq("id", req.user_id).execute()
            
            log_payment_record(
                req.user_id, 0, "USD", "tier_downgrade",
                f"Downgrade from {current_tier.title()} to Free (No subscription) | Reason: {req.reason}"
            )
            
            log_activity(admin["id"], "admin_downgrade", {
                "target_user": req.user_id,
                "from_tier": current_tier,
                "to_tier": "free",
                "immediate": req.immediate,
                "reason": req.reason
            })
            
            return {
                "status": "downgraded",
                "from_tier": current_tier,
                "to_tier": "free"
            }
        
        # Active Stripe subscription must be canceled
        subscriptions = get_customer_subscriptions(customer_id)
        active_sub = None
        for sub in subscriptions:
            if sub.status in ['active', 'trialing']:
                active_sub = sub
                break
        
        if not active_sub:
            # No active subscription; update directly
            update_subscription_tier(req.user_id, "free", subscription_status="inactive")
            supabase.table("profiles").update({"credits_monthly": 0}).eq("id", req.user_id).execute()
            
            log_payment_record(
                req.user_id, 0, "USD", "tier_downgrade",
                f"Downgrade from {current_tier.title()} to Free | Reason: {req.reason}"
            )
            
            log_activity(admin["id"], "admin_downgrade", {
                "target_user": req.user_id,
                "from_tier": current_tier,
                "to_tier": "free",
                "reason": req.reason
            })
            
            return {"status": "downgraded", "from_tier": current_tier, "to_tier": "free"}
        
        # Cancel subscription
        if req.immediate:
            result = cancel_subscription(active_sub.id, immediate=True)
            if not result["success"]:
                raise HTTPException(400, f"Failed to cancel subscription: {result['error']}")
            
            update_subscription_tier(req.user_id, "free", subscription_status="canceled")
            supabase.table("profiles").update({"credits_monthly": 0}).eq("id", req.user_id).execute()
            
            log_payment_record(
                req.user_id, 0, "USD", "tier_downgrade",
                f"Downgrade from {current_tier.title()} to Free (Immediate) | Reason: {req.reason}"
            )
        else:
            result = cancel_subscription(active_sub.id, immediate=False)
            if not result["success"]:
                raise HTTPException(400, f"Failed to schedule cancellation: {result['error']}")
            
            log_payment_record(
                req.user_id, 0, "USD", "tier_downgrade_scheduled",
                f"Downgrade scheduled: {current_tier.title()} to Free | Effective: {result['subscription'].current_period_end} | Reason: {req.reason}"
            )
        
        log_activity(admin["id"], "admin_downgrade", {
            "target_user": req.user_id,
            "from_tier": current_tier,
            "to_tier": "free",
            "immediate": req.immediate,
            "subscription_id": active_sub.id,
            "reason": req.reason
        })
        
        return {
            "status": "downgraded" if req.immediate else "downgrade_scheduled",
            "from_tier": current_tier,
            "to_tier": "free",
            "subscription_id": active_sub.id
        }
    
    # Case 2: Pro → Starter (plan change)
    if current_tier == "pro" and target_tier == "starter":
        if not customer_id:
            raise HTTPException(400, "User has no Stripe customer ID for subscription change")
        
        subscriptions = get_customer_subscriptions(customer_id)
        active_sub = None
        for sub in subscriptions:
            if sub.status in ['active', 'trialing']:
                active_sub = sub
                break
        
        if not active_sub:
            raise HTTPException(400, "No active subscription found to downgrade")
        
        # Lookup Starter price ID
        starter_price_id = os.environ.get("STRIPE_STARTER_MONTHLY_PRICE_ID")
        if not starter_price_id:
            raise HTTPException(500, "Starter price ID not configured")
        
        try:
            # Modify subscription plan
            # proration_behavior options:
            # - 'create_prorations': issue prorated credit
            # - 'none': no refund, immediate switch
            # - 'always_invoice': generate invoice immediately
            updated_sub = stripe.Subscription.modify(
                active_sub.id,
                items=[{
                    "id": active_sub.items.data[0].id,
                    "price": starter_price_id
                }],
                proration_behavior='create_prorations' if req.immediate else 'none',
                billing_cycle_anchor='unchanged' if not req.immediate else 'now'
            )
            
            if req.immediate:
                # Update tier immediately
                update_subscription_tier(req.user_id, "starter", subscription_status="active")
                
                # Adjust monthly credits to Starter allowance (500)
                supabase.table("profiles").update({
                    "credits_monthly": 500
                }).eq("id", req.user_id).execute()
                
                log_payment_record(
                    req.user_id, 0, "USD", "tier_downgrade",
                    f"Downgrade from Pro to Starter (Immediate) | Reason: {req.reason}"
                )
            else:
                log_payment_record(
                    req.user_id, 0, "USD", "tier_downgrade_scheduled",
                    f"Downgrade scheduled: Pro to Starter | Next billing: {updated_sub.current_period_end} | Reason: {req.reason}"
                )
            
            log_activity(admin["id"], "admin_downgrade", {
                "target_user": req.user_id,
                "from_tier": "pro",
                "to_tier": "starter",
                "immediate": req.immediate,
                "subscription_id": active_sub.id,
                "reason": req.reason
            })
            
            # Record downgrade in audit log
            admin_log_operation(
                admin_id=admin["id"],
                operation_type="subscription_downgrade",
                target_user_id=req.user_id,
                details=f"Pro → Starter ({'immediate' if req.immediate else 'at period end'})",
                reason=req.reason
            )
            
            return {
                "status": "downgraded" if req.immediate else "downgrade_scheduled",
                "from_tier": "pro",
                "to_tier": "starter",
                "subscription_id": active_sub.id
            }
            
        except stripe.error.StripeError as e:
            raise HTTPException(400, f"Stripe error: {str(e)}")
    
    raise HTTPException(400, "Invalid downgrade path")

@app.post("/api/admin/broadcast")
@limiter.limit("5/minute")  # Broadcast rate limit (abuse protection)
def adm_broadcast(request: Request, req: AdminBroadcastRequest, admin: dict = Depends(require_admin)):
    """Send a system-wide broadcast notification."""
    notification = create_broadcast(req.title, req.content, req.target_group)
    log_activity(admin["id"], "admin_broadcast", {
        "target_group": req.target_group,
        "title": req.title
    })
    # Capture audit entry
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="broadcast",
        target_user_id=None,
        details=f"Broadcast to {req.target_group}: {req.title[:50]}",
        reason=None
    )
    return notification


class AdminSendNotificationRequest(BaseModel):
    user_id: str
    title: str
    content: str
    notification_type: Optional[str] = "system"


class AdminBatchNotificationRequest(BaseModel):
    user_ids: List[str]
    title: str
    content: str
    notification_type: Optional[str] = "system"


@app.post("/api/admin/notification/send")
@limiter.limit("30/minute")
def adm_send_notification(request: Request, req: AdminSendNotificationRequest, admin: dict = Depends(require_admin)):
    """Send a notification to a single user."""
    notification = send_notification_to_user(
        user_id=req.user_id,
        title=req.title,
        content=req.content,
        notification_type=req.notification_type
    )
    
    if not notification:
        raise HTTPException(500, "Failed to send notification")
    
    log_activity(admin["id"], "admin_notification_send", {
        "target_user": req.user_id,
        "title": req.title
    })
    
    # Record in audit log
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="notification_send",
        target_user_id=req.user_id,
        details=f"Notification: {req.title[:50]}",
        reason=None
    )
    
    return {"status": "sent", "notification": notification}


@app.post("/api/admin/notification/batch")
@limiter.limit("10/minute")
def adm_batch_notification(request: Request, req: AdminBatchNotificationRequest, admin: dict = Depends(require_admin)):
    """Send notifications to multiple users."""
    if len(req.user_ids) > 100:
        raise HTTPException(400, "Cannot send to more than 100 users at once")
    
    notifications = send_notification_to_users(
        user_ids=req.user_ids,
        title=req.title,
        content=req.content,
        notification_type=req.notification_type
    )
    
    log_activity(admin["id"], "admin_notification_batch", {
        "user_count": len(req.user_ids),
        "title": req.title
    })
    
    # Record in audit log
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="notification_batch",
        target_user_id=None,
        details=f"Batch notification to {len(req.user_ids)} users: {req.title[:50]}",
        reason=None
    )
    
    return {"status": "sent", "count": len(notifications)}


@app.get("/api/admin/notification/stats")
def adm_notification_stats(admin: dict = Depends(require_admin)):
    """Fetch notification statistics."""
    return get_all_notification_stats()


# --- Admin Error Logs ---
@app.get("/api/admin/error-logs")
def adm_get_error_logs(
    page: int = 1,
    limit: int = 50,
    error_type: Optional[str] = None,
    status_code: Optional[int] = None,
    user_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """
    Fetch error logs with filtering and pagination.
    
    Args:
        page: Page number (1-based)
        limit: Items per page (max 100)
        error_type: Filter by error type (API, NETWORK, JS_ERROR, etc.)
        status_code: Filter by HTTP status code
        user_code: Filter by user code (e.g., USR001)
        start_date: Filter from date (ISO format)
        end_date: Filter to date (ISO format)
        search: Search in message and endpoint
    """
    try:
        limit = min(limit, 100)  # Cap at 100
        offset = (page - 1) * limit
        
        # Build query
        query = supabase.table("error_logs").select("*", count="exact")
        
        # Apply filters
        if error_type:
            query = query.eq("error_type", error_type)
        if status_code:
            query = query.eq("status_code", status_code)
        if user_code:
            query = query.ilike("user_code", f"%{user_code}%")
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)
        if search:
            query = query.or_(f"message.ilike.%{search}%,endpoint.ilike.%{search}%")
        
        # Execute with pagination
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        total = result.count or 0
        total_pages = (total + limit - 1) // limit if total > 0 else 1
        
        logs = result.data or []
        
        # Enrich logs with user_code from profiles if missing
        user_ids_without_code = [
            log["user_id"] for log in logs 
            if log.get("user_id") and not log.get("user_code")
        ]
        
        if user_ids_without_code:
            # Fetch user codes from profiles
            profiles_result = supabase.table("profiles").select("id, user_code").in_("id", list(set(user_ids_without_code))).execute()
            user_code_map = {p["id"]: p.get("user_code") for p in (profiles_result.data or [])}
            
            # Enrich logs
            for log in logs:
                if log.get("user_id") and not log.get("user_code"):
                    log["user_code"] = user_code_map.get(log["user_id"])
        
        return {
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }
    except Exception as e:
        error_msg = str(e)
        print(f"[Admin] Error fetching error logs: {error_msg}")
        # If table doesn't exist, return empty data instead of error
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            return {
                "logs": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 1,
                "warning": "Error logs table not created. Please run the migration."
            }
        raise HTTPException(500, f"Failed to fetch error logs: {error_msg}")


@app.get("/api/admin/error-logs/stats")
def adm_get_error_stats(
    hours: int = 24,
    admin: dict = Depends(require_admin)
):
    """
    Get error statistics for the specified time period.
    
    Args:
        hours: Number of hours to look back (default 24)
    """
    try:
        from datetime import datetime, timedelta
        
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        # Get all errors in time period
        errors = supabase.table("error_logs").select(
            "error_type, status_code, endpoint"
        ).gte("created_at", cutoff).execute()
        
        # Calculate statistics
        by_type = {}
        by_status = {}
        by_endpoint = {}
        
        for err in (errors.data or []):
            # Count by type
            t = err.get("error_type", "UNKNOWN")
            by_type[t] = by_type.get(t, 0) + 1
            
            # Count by status
            s = err.get("status_code") or 0
            by_status[s] = by_status.get(s, 0) + 1
            
            # Count by endpoint (top 10)
            e = err.get("endpoint")
            if e:
                e = e.split("?")[0]  # Remove query params
                by_endpoint[e] = by_endpoint.get(e, 0) + 1
        
        # Sort endpoints by count and take top 10
        top_endpoints = sorted(by_endpoint.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "hours": hours,
            "total": len(errors.data or []),
            "by_type": by_type,
            "by_status": by_status,
            "top_endpoints": dict(top_endpoints),
        }
    except Exception as e:
        error_msg = str(e)
        print(f"[Admin] Error fetching error stats: {error_msg}")
        # If table doesn't exist, return empty stats instead of error
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            return {
                "hours": hours,
                "total": 0,
                "by_type": {},
                "by_status": {},
                "top_endpoints": {},
                "warning": "Error logs table not created. Please run the migration."
            }
        raise HTTPException(500, f"Failed to fetch error stats: {error_msg}")


@app.get("/api/admin/notification/history")
def adm_notification_history(
    page: int = 1, 
    limit: int = 50,
    notification_type: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch notification delivery history."""
    notifications = get_notification_history(page, limit, notification_type)
    return {"notifications": notifications, "page": page}


@app.get("/api/admin/users/by-tier/{tier}")
def adm_get_users_by_tier(tier: str, admin: dict = Depends(require_admin)):
    """List user IDs for a specified tier."""
    if tier not in ["free", "starter", "pro"]:
        raise HTTPException(400, "Invalid tier. Must be 'free', 'starter', or 'pro'")
    
    user_ids = get_users_by_tier(tier)
    return {"tier": tier, "count": len(user_ids), "user_ids": user_ids}


@app.post("/api/admin/projects/{project_id}/restore")
def adm_restore_project(project_id: str, admin: dict = Depends(require_admin)):
    """Restore a deleted project."""
    project = restore_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    log_activity(admin["id"], "admin_project_restore", {"project_id": project_id})
    return project

@app.get("/api/admin/projects/feed")
def adm_projects_feed(page: int = 1, limit: int = 50, admin: dict = Depends(require_admin)):
    """Fetch the site-wide project feed."""
    items = get_all_projects_feed(page, limit)
    return {"items": items, "total": len(items), "page": page}

# --- Admin Marketplace Moderation (PRD §16) ---
@app.get("/api/admin/marketplace/moderation/list")
def adm_moderation_list(
    status: Optional[str] = None,  # 'pending' | 'approved' | 'rejected' | 'all'
    type: Optional[str] = None,  # 'project' | 'asset'
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """
    Retrieve moderation list (PRD §16).
    
    Tabs: Pending / Approved / Rejected / All
    """
    items = admin_get_moderation_list(
        status=status,
        resource_type=type,
        page=page,
        limit=limit
    )
    return {"items": items, "total": len(items), "page": page}

@app.get("/api/admin/marketplace/moderation/{listing_id}")
def adm_moderation_detail(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Retrieve moderation detail (PRD §16).
    
    Preview: thumbnail + resource_url
    Metadata: title/description/allowed_tiers/price_credits
    """
    item = admin_get_moderation_detail(listing_id)
    if not item:
        raise HTTPException(404, "Listing not found")
    return item

@app.post("/api/admin/marketplace/moderation/{listing_id}/approve")
def adm_moderation_approve(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Approve listing (PRD §16).
    
    pending → approved
    """
    result = admin_approve_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_approve", {"listing_id": listing_id})
    
    # Record approval in audit log
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="listing_approve",
        target_user_id=result.get("seller_id"),
        details=f"Approved listing: {result.get('title', listing_id)[:50]}",
        reason=None
    )
    return {"status": "approved", "listing_id": listing_id}

@app.post("/api/admin/marketplace/moderation/{listing_id}/reject")
def adm_moderation_reject(
    listing_id: str, 
    req: AdminModerationRejectRequest,
    admin: dict = Depends(require_admin)
):
    """
    Reject listing (PRD §16).
    
    pending → rejected (reason required)
    """
    try:
        result = admin_reject_listing(listing_id, admin["id"], req.reason)
    except Exception as e:
        raise HTTPException(400, str(e))
    
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_reject", {
        "listing_id": listing_id,
        "reason": req.reason
    })
    
    # Record rejection in audit log
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="listing_reject",
        target_user_id=result.get("seller_id"),
        details=f"Rejected listing: {result.get('title', listing_id)[:50]}",
        reason=req.reason
    )
    return {"status": "rejected", "listing_id": listing_id, "reason": req.reason}

@app.post("/api/admin/marketplace/moderation/{listing_id}/delete")
def adm_moderation_delete(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Soft-delete listing (PRD §16) by setting is_deleted=true.
    """
    result = admin_delete_listing(listing_id)
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_delete", {"listing_id": listing_id})
    return {"status": "deleted", "listing_id": listing_id}

@app.post("/api/admin/marketplace/moderation/{listing_id}/unpublish")
def adm_moderation_unpublish(listing_id: str, admin: dict = Depends(require_admin)):
    """
    Force-unpublish a listing (PRD §16) by setting is_public=false.
    """
    result = admin_unpublish_listing(listing_id)
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_unpublish", {"listing_id": listing_id})
    return {"status": "unpublished", "listing_id": listing_id}


# ==========================================
# Admin Content Reports
# ==========================================

@app.get("/api/admin/reports")
def adm_get_reports(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """
    Get all content reports with optional status filtering.
    
    Args:
        status: Filter by status ('pending', 'reviewed', 'resolved', 'dismissed')
    """
    from db_service import admin_get_reports, admin_get_reports_count
    reports = admin_get_reports(status=status, page=page, limit=limit)
    total = admin_get_reports_count(status=status)
    return {"items": reports, "total": total, "page": page}

@app.get("/api/admin/reports/stats")
def adm_get_reports_stats(admin: dict = Depends(require_admin)):
    """Get reports statistics by status."""
    from db_service import admin_get_reports_count
    return {
        "pending": admin_get_reports_count("pending"),
        "reviewed": admin_get_reports_count("reviewed"),
        "resolved": admin_get_reports_count("resolved"),
        "dismissed": admin_get_reports_count("dismissed"),
        "total": admin_get_reports_count()
    }

@app.get("/api/admin/reports/{report_id}")
def adm_get_report_detail(report_id: str, admin: dict = Depends(require_admin)):
    """Get detailed information about a specific report."""
    from db_service import admin_get_report_detail
    report = admin_get_report_detail(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    return report

class ReportResponseRequest(BaseModel):
    status: str  # 'reviewed' | 'resolved' | 'dismissed'
    response: Optional[str] = None

@app.post("/api/admin/reports/{report_id}/respond")
def adm_respond_to_report(
    report_id: str,
    req: ReportResponseRequest,
    admin: dict = Depends(require_admin)
):
    """
    Respond to a content report.
    
    Admin can update status and optionally provide a response message to the reporter.
    """
    from db_service import admin_respond_to_report
    
    try:
        result = admin_respond_to_report(
            report_id=report_id,
            admin_id=admin["id"],
            status=req.status,
            response=req.response
        )
        if result:
            admin_log_operation(
                admin["id"], 
                "report_response", 
                details=f"Report {report_id} - Status: {req.status}",
                reason=req.response
            )
            return {"success": True, "report": result}
        raise HTTPException(404, "Report not found")
    except Exception as e:
        raise HTTPException(400, str(e))


# ==========================================
# Admin Operation Logs (audit trail)
# ==========================================

@app.get("/api/admin/logs")
def adm_get_operation_logs(
    operation_type: Optional[str] = None,
    admin_id: Optional[str] = None,
    target_user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Fetch administrator operation logs."""
    return admin_get_operation_logs(
        operation_type=operation_type,
        admin_id=admin_id,
        target_user_id=target_user_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit
    )

@app.get("/api/admin/logs/export")
def adm_export_operation_logs(
    operation_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Export operation logs as CSV."""
    import csv
    from io import StringIO
    
    result = admin_get_operation_logs(
        operation_type=operation_type,
        start_date=start_date,
        end_date=end_date,
        page=1,
        limit=10000  # Export up to 10k rows
    )
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Time", "Operation", "Admin", "Target User", "Target Email", "Details", "Reason"])
    
    for log in result.get("logs", []):
        writer.writerow([
            log.get("created_at"),
            log.get("operation_type"),
            log.get("admin_email"),
            log.get("target_user_code"),
            log.get("target_user_email"),
            log.get("details"),
            log.get("reason")
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=operation-logs.csv"}
    )


# ==========================================
# Admin User Projects (management)
# ==========================================

@app.get("/api/admin/user/{uid}/projects")
def adm_get_user_projects(
    uid: str,
    page: int = 1,
    limit: int = 20,
    include_deleted: bool = True,
    admin: dict = Depends(require_admin)
):
    """Fetch all projects owned by a specific user."""
    return admin_get_user_projects(uid, page, limit, include_deleted)


# ==========================================
# Admin Stats & Analytics
# ==========================================

@app.get("/api/admin/stats/dashboard")
def adm_get_dashboard_stats(
    period: str = "month",
    admin: dict = Depends(require_admin)
):
    """Fetch dashboard KPIs."""
    return admin_get_dashboard_stats(period)

@app.get("/api/admin/stats/user-growth")
def adm_get_user_growth_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day",
    admin: dict = Depends(require_admin)
):
    """Fetch user growth stats."""
    return admin_get_user_growth_stats(start_date, end_date, group_by)

@app.get("/api/admin/stats/revenue")
def adm_get_revenue_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day",
    admin: dict = Depends(require_admin)
):
    """Fetch revenue stats."""
    return admin_get_revenue_stats(start_date, end_date, group_by)

@app.get("/api/admin/stats/projects")
def adm_get_project_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch project stats."""
    return admin_get_project_stats(start_date, end_date)

@app.get("/api/admin/stats/credits")
def adm_get_credit_usage_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch credit usage stats."""
    return admin_get_credit_usage_stats(start_date, end_date)

@app.get("/api/admin/stats/exports")
def adm_get_export_stats(admin: dict = Depends(require_admin)):
    """Fetch export operation stats (PDF, ZIP, print, preview)."""
    # Read pre-aggregated data from aggregated_stats
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "export_stats_30d")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {"totalPdf": 0, "totalZip": 0, "totalPrint": 0, "totalPreview": 0, "trend": []}
    except Exception as e:
        print(f"Failed to get export stats: {e}")
        return {"totalPdf": 0, "totalZip": 0, "totalPrint": 0, "totalPreview": 0, "trend": []}

@app.get("/api/admin/stats/assets")
def adm_get_asset_usage_stats(admin: dict = Depends(require_admin)):
    """Fetch asset usage ranking stats."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "asset_usage_ranking")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {"top_assets": [], "by_type": {}, "total_usage": 0, "total_assets_used": 0}
    except Exception as e:
        print(f"Failed to get asset usage stats: {e}")
        return {"top_assets": [], "by_type": {}, "total_usage": 0, "total_assets_used": 0}

@app.get("/api/admin/user/{uid}/asset-usage")
def adm_get_user_asset_usage(uid: str, admin: dict = Depends(require_admin)):
    """Fetch asset usage stats for a specific user."""
    try:
        # Retrieve assets used by the user
        usage_res = supabase.table("listing_usage").select(
            "listing_id, used_at, marketplace_listings(id, title, thumbnail_url, resource_type)"
        ).eq("used_by_user_id", uid).execute()
        
        # Count usage occurrences
        usage_counts = {}
        for record in usage_res.data or []:
            listing_id = record.get("listing_id")
            listing_info = record.get("marketplace_listings", {})
            if listing_id:
                if listing_id not in usage_counts:
                    usage_counts[listing_id] = {
                        "listing_id": listing_id,
                        "title": listing_info.get("title", "Unknown"),
                        "thumbnail_url": listing_info.get("thumbnail_url", ""),
                        "resource_type": listing_info.get("resource_type", ""),
                        "count": 0
                    }
                usage_counts[listing_id]["count"] += 1
        
        # Convert into ranking list
        user_assets = list(usage_counts.values())
        user_assets.sort(key=lambda x: -x["count"])
        
        return {
            "assets": user_assets[:20],  # Top 20
            "total_assets_used": len(user_assets),
            "total_usage": sum(a["count"] for a in user_assets)
        }
    except Exception as e:
        print(f"Failed to get user asset usage: {e}")
        return {"assets": [], "total_assets_used": 0, "total_usage": 0}

@app.get("/api/admin/stats/tier-distribution")
def adm_get_tier_distribution(admin: dict = Depends(require_admin)):
    """Fetch user tier distribution."""
    return admin_get_tier_distribution()

@app.get("/api/admin/stats/conversion-funnel")
def adm_get_conversion_funnel(
    period: str = "month",
    admin: dict = Depends(require_admin)
):
    """Fetch conversion funnel stats."""
    return admin_get_conversion_funnel(period)


@app.get("/api/admin/stats/tier-activity")
def adm_get_tier_activity(admin: dict = Depends(require_admin)):
    """Fetch per-tier activity stats."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "tier_activity")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/stats/subscription-events")
def adm_get_subscription_events(admin: dict = Depends(require_admin)):
    """Fetch subscription event stats (upgrade/downgrade/cancel/refund)."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "subscription_events_30d")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {"totalUpgrades": 0, "totalDowngrades": 0, "totalCancellations": 0, "totalRefunds": 0, "trend": []}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/stats/page-views")
def adm_get_page_views(admin: dict = Depends(require_admin)):
    """Fetch page view stats."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "page_views_7d")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {"pages": {}, "total_views": 0, "guest_views": 0}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/stats/project-details")
def adm_get_project_details(admin: dict = Depends(require_admin)):
    """Fetch detailed project stats (deleted, OCR, page counts)."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "project_details_30d")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {"deleted_projects": 0, "ocr_usage": 0, "total_pages_sample": 0, "avg_pages_per_project": 0}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/stats/returning-users")
def adm_get_returning_users(admin: dict = Depends(require_admin)):
    """Fetch returning user stats."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "returning_users")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/stats/tier-trend")
def adm_get_tier_trend(admin: dict = Depends(require_admin)):
    """Fetch tier trend (user counts by tier over time)."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "tier_trend_30d")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {"trend": []}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/stats/tier-conversion")
def adm_get_tier_conversion(admin: dict = Depends(require_admin)):
    """Fetch tier conversion stats."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "tier_conversion_30d")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {"conversions": []}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/stats/performance")
def adm_get_performance_metrics(admin: dict = Depends(require_admin)):
    """Fetch page performance (Core Web Vitals) stats."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "performance_metrics_7d")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {"metrics": {}, "by_page": {}, "total_samples": 0}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/stats/user-distribution")
def adm_get_user_distribution(admin: dict = Depends(require_admin)):
    """Fetch user distribution stats (country, browser, OS, device)."""
    try:
        result = supabase.table("aggregated_stats")\
            .select("data")\
            .eq("stat_type", "user_distribution_7d")\
            .order("date", desc=True)\
            .limit(1).execute()
        
        if result.data:
            return result.data[0].get("data", {})
        return {
            "country": [],
            "browser": [],
            "os": [],
            "device_type": [],
            "language": [],
            "timezone": [],
            "total_sessions": 0
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/user/{uid}/env-stats")
def adm_get_user_env_stats(uid: str, admin: dict = Depends(require_admin)):
    """Fetch environment stats for a specific user (IP, country, browser, OS, device)."""
    try:
        from collections import defaultdict
        
        # Pull recent events (last 30 days)
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        events = supabase.table("user_events")\
            .select("properties, event_type, created_at")\
            .eq("user_id", uid)\
            .gte("created_at", start_date)\
            .order("created_at", desc=True)\
            .limit(500)\
            .execute()
        
        if not events.data:
            return {
                "total_events": 0,
                "countries": [],
                "browsers": [],
                "os_list": [],
                "devices": [],
                "languages": [],
                "timezones": [],
                "last_ip": None,
                "last_seen": None,
                "first_seen": None,
                "page_views": [],
            }
        
        # Aggregate stats
        country_counts = defaultdict(int)
        browser_counts = defaultdict(int)
        os_counts = defaultdict(int)
        device_counts = defaultdict(int)
        language_counts = defaultdict(int)
        timezone_counts = defaultdict(int)
        page_view_counts = defaultdict(int)
        
        last_ip = None
        last_seen = None
        first_seen = None
        
        for event in events.data:
            props = event.get("properties", {})
            created_at = event.get("created_at")
            
            # Track timestamps
            if created_at:
                if not last_seen:
                    last_seen = created_at
                first_seen = created_at
            
            # Capture most recent IP
            ip = props.get("server_ip") or props.get("ip")
            if ip and not last_ip:
                last_ip = ip
            
            # Country
            country = props.get("server_country") or props.get("country_code")
            if country and country not in ("unknown", ""):
                country_counts[country] += 1
            
            # Browser
            browser = props.get("client_browser") or props.get("browser")
            if browser:
                browser_name = browser.split()[0] if browser else "unknown"
                browser_counts[browser_name] += 1
            
            # Operating system
            os_info = props.get("client_os") or props.get("os")
            if os_info:
                os_name = os_info.split()[0] if os_info else "unknown"
                os_counts[os_name] += 1
            
            # Device type
            device = props.get("client_device_type") or props.get("device_type")
            if device:
                device_counts[device] += 1
            
            # Language
            lang = props.get("client_language") or props.get("language")
            if lang:
                lang_code = lang.split("-")[0] if lang else "unknown"
                language_counts[lang_code] += 1
            
            # Timezone
            tz = props.get("client_timezone") or props.get("timezone")
            if tz:
                timezone_counts[tz] += 1
            
            # Page views
            page_url = props.get("page_url")
            if page_url and event.get("event_type") == "page_view":
                page_view_counts[page_url] += 1
        
        # Convert aggregated counts into sorted lists
        def to_sorted_list(counts, limit=10):
            return [{"name": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])[:limit]]
        
        return {
            "total_events": len(events.data),
            "countries": to_sorted_list(country_counts),
            "browsers": to_sorted_list(browser_counts),
            "os_list": to_sorted_list(os_counts),
            "devices": to_sorted_list(device_counts),
            "languages": to_sorted_list(language_counts),
            "timezones": to_sorted_list(timezone_counts, 5),
            "page_views": to_sorted_list(page_view_counts, 10),
            "last_ip": last_ip,
            "last_seen": last_seen,
            "first_seen": first_seen,
        }
    except Exception as e:
        return {"error": str(e)}


# ==========================================
# Admin AI Analysis
# ==========================================

@app.get("/api/admin/ai/insights")
def adm_get_ai_insights(
    type: str = "all",
    admin: dict = Depends(require_admin)
):
    """Fetch AI insights."""
    return admin_get_ai_insights(type)

@app.get("/api/admin/ai/recommendations")
def adm_get_ai_recommendations(
    area: str = "all",
    admin: dict = Depends(require_admin)
):
    """Fetch AI optimization recommendations."""
    return admin_get_ai_recommendations(area)

@app.get("/api/admin/ai/behavior-analysis")
def adm_get_behavior_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Fetch AI-powered user behavior analysis."""
    return admin_get_behavior_analysis(start_date, end_date)


# ==========================================
# User Events Tracking
# ==========================================

class UserEventsRequest(BaseModel):
    events: List[dict]

def get_client_ip(request: Request) -> str:
    """
    Retrieve the client IP, supporting X-Forwarded-For / X-Real-IP / CF-Connecting-IP.
    """
    # Cloudflare
    if cf_ip := request.headers.get("CF-Connecting-IP"):
        return cf_ip
    
    # Standard proxy headers
    if x_forwarded_for := request.headers.get("X-Forwarded-For"):
        # Use first IP in list (originating client)
        return x_forwarded_for.split(",")[0].strip()
    
    if x_real_ip := request.headers.get("X-Real-IP"):
        return x_real_ip
    
    # Direct connection fallback
    return request.client.host if request.client else "unknown"


def get_country_from_ip(ip: str) -> dict:
    """
    Infer country from IP (demo only – use GeoIP in production).
    """
    # Cloudflare country header preferred (must be captured at request time)
    
    # Simple IP prefix heuristic (replace with GeoIP API)
    country_info = {
        "country_code": "unknown",
        "country_name": "Unknown",
        "continent": "Unknown",
    }
    
    # Sample prefix checks for demo purposes
    if ip.startswith("127.") or ip.startswith("localhost") or ip == "::1":
        country_info = {"country_code": "LOCAL", "country_name": "Localhost", "continent": "Local"}
    elif ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        country_info = {"country_code": "PRIVATE", "country_name": "Private Network", "continent": "Private"}
    
    return country_info


def get_cloudflare_geo(request: Request) -> dict:
    """
    Extract geo info from Cloudflare headers.
    """
    return {
        "country_code": request.headers.get("CF-IPCountry", "unknown"),
        "city": request.headers.get("CF-IPCity", "unknown"),
        "region": request.headers.get("CF-IPRegion", "unknown"),
        "timezone": request.headers.get("CF-IPTimezone", "unknown"),
    }


@app.post("/api/analytics/events")
@limiter.limit("60/minute")  # Event ingestion rate limit (batch)
async def log_analytics_events(request: Request, req: UserEventsRequest, user: dict = Depends(get_current_user_optional)):
    """
    Record user analytics events (batch submission with auto IP/geo/device enrichment).
    """
    user_id = user.get("id") if user else None
    
    # Enrich with server-side IP + geo
    client_ip = get_client_ip(request)
    geo_info = get_cloudflare_geo(request)
    country_info = get_country_from_ip(client_ip) if geo_info.get("country_code") == "unknown" else {}
    
    # Merge geo info
    location_info = {
        "ip": client_ip,
        "country_code": geo_info.get("country_code") or country_info.get("country_code", "unknown"),
        "city": geo_info.get("city", "unknown"),
        "region": geo_info.get("region", "unknown"),
        "cf_timezone": geo_info.get("timezone", "unknown"),
    }
    
    # Capture user agent metadata
    user_agent = request.headers.get("User-Agent", "unknown")
    accept_language = request.headers.get("Accept-Language", "unknown")
    
    # Event types that should also log to activity_logs
    ACTIVITY_LOG_EVENTS = {
        "project_print": "print_project",
        "project_export_pdf": "download_pdf",
        "project_export_zip": "export_zip",
        "project_preview": "preview_pdf",
        "project_delete": "delete_project",
        "project_create_complete": "create_project",
    }
    
    for event in req.events:
        event_type = event.get("event_type")
        properties = event.get("properties", {})
        env_info = event.get("env", {})
        
        # Merge server-side enrichment into properties
        enriched_properties = {
            **properties,
            # Server-side info (authoritative)
            "server_ip": client_ip,
            "server_country": location_info.get("country_code"),
            "server_city": location_info.get("city"),
            "server_region": location_info.get("region"),
            "server_user_agent": user_agent,
            "server_accept_language": accept_language,
            # Client-provided environment info
            "client_browser": env_info.get("browser"),
            "client_os": env_info.get("os"),
            "client_device_type": env_info.get("device_type"),
            "client_timezone": env_info.get("timezone"),
            "client_timezone_offset": env_info.get("timezone_offset"),
            "client_language": env_info.get("language"),
            "client_connection_type": env_info.get("connection_type"),
        }
        
        # Store event
        log_user_event(
            user_id=user_id,
            event_type=event_type,
            properties=enriched_properties,
            session_id=event.get("session_id")
        )
        
        # Mirror key events into activity_logs
        if user_id and event_type in ACTIVITY_LOG_EVENTS:
            log_activity(user_id, ACTIVITY_LOG_EVENTS[event_type], enriched_properties)
    
    return {"status": "ok", "count": len(req.events), "ip": client_ip, "country": location_info.get("country_code")}

@app.get("/api/admin/events")
def adm_get_user_events(
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 100,
    admin: dict = Depends(require_admin)
):
    """Fetch user events (with optional filters)."""
    return admin_get_user_events(
        event_type=event_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit
    )

@app.get("/api/admin/events/stats")
def adm_get_event_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "event_type",
    admin: dict = Depends(require_admin)
):
    """Fetch event statistics (grouped by event_type by default)."""
    return admin_get_event_stats(start_date, end_date, group_by)


# ===========================================
# Admin - Aggregated Stats APIs
# ===========================================

@app.get("/api/admin/aggregated/{stat_type}")
def adm_get_aggregated_stats(
    stat_type: str,
    use_cache: bool = True,
    admin: dict = Depends(require_admin)
):
    """
    Fetch aggregated stats for the given stat_type.
    Supported types: daily_users, daily_revenue, daily_projects, credit_usage_30d,
    tier_distribution, conversion_funnel_30d, event_stats_7d, etc.
    """
    from db_service import get_aggregated_stats
    data = get_aggregated_stats(stat_type, use_cache)
    
    if data is None:
        return {"data": None, "message": "No cached data available. Run aggregation task first."}
    
    return {"data": data}


@app.get("/api/admin/aggregated/{stat_type}/range")
def adm_get_aggregated_stats_range(
    stat_type: str,
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """Fetch aggregated stats over a specific number of days."""
    from db_service import get_aggregated_stats_range
    return get_aggregated_stats_range(stat_type, days)


@app.post("/api/admin/aggregation/run")
def adm_run_aggregation(
    task_type: str = "all",
    admin: dict = Depends(require_admin)
):
    """Manually trigger aggregation task (task_type: all | hourly | daily)."""
    return run_aggregation_now(task_type)


# ===========================================
# Admin - System Configuration
# ===========================================

from config_service import (
    get_config, set_config, get_all_configs, 
    batch_update_configs, apply_rate_limit_preset,
    clear_config_cache, RATE_LIMIT_PRESETS
)
from rate_limiter import get_current_limits


class ConfigUpdateRequest(BaseModel):
    config_key: str
    config_value: dict


class BatchConfigUpdateRequest(BaseModel):
    updates: List[dict]  # [{"config_key": "...", "config_value": {...}}, ...]


class RateLimitPresetRequest(BaseModel):
    preset: str  # "strict", "normal", "relaxed", "disabled"


@app.get("/api/admin/config")
def adm_get_all_configs(
    category: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """
    Fetch system configs, optionally filtered by category (rate_limit/analytics/system).
    """
    configs = get_all_configs(category)
    return {"configs": configs}


@app.get("/api/admin/config/{config_key:path}")
def adm_get_config(
    config_key: str,
    admin: dict = Depends(require_admin)
):
    """Fetch a single config key (bypass cache)."""
    config = get_config(config_key, use_cache=False)
    if config is None:
        raise HTTPException(404, f"Config not found: {config_key}")
    return {"config_key": config_key, "config_value": config}


@app.put("/api/admin/config")
@limiter.limit("30/minute")
def adm_update_config(
    request: Request,
    req: ConfigUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Update a single config entry."""
    success = set_config(req.config_key, req.config_value, admin["id"])
    if not success:
        raise HTTPException(500, "Failed to update config")
    
    # Record audit operation
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="config_update",
        target_user_id=None,
        details=f"Updated {req.config_key}",
        reason=None
    )
    
    return {"status": "ok", "config_key": req.config_key}


@app.put("/api/admin/config/batch")
@limiter.limit("10/minute")
def adm_batch_update_configs(
    request: Request,
    req: BatchConfigUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """Batch update multiple config entries."""
    results = batch_update_configs(req.updates, admin["id"])
    
    # Record audit operation
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="config_batch_update",
        target_user_id=None,
        details=f"Updated {len(req.updates)} configs",
        reason=None
    )
    
    return {"status": "ok", "results": results}


@app.get("/api/admin/rate-limits")
def adm_get_rate_limits(admin: dict = Depends(require_admin)):
    """Fetch the current formatted rate-limit configuration."""
    return get_current_limits()


@app.post("/api/admin/rate-limits/preset")
@limiter.limit("5/minute")
def adm_apply_rate_limit_preset(
    request: Request,
    req: RateLimitPresetRequest,
    admin: dict = Depends(require_admin)
):
    """Apply a rate-limit preset ("strict" | "normal" | "relaxed" | "disabled")."""
    if req.preset not in RATE_LIMIT_PRESETS:
        raise HTTPException(400, f"Invalid preset. Available: {list(RATE_LIMIT_PRESETS.keys())}")
    
    success = apply_rate_limit_preset(req.preset, admin["id"])
    if not success:
        raise HTTPException(500, "Failed to apply preset")
    
    # Record audit operation
    admin_log_operation(
        admin_id=admin["id"],
        operation_type="rate_limit_preset",
        target_user_id=None,
        details=f"Applied preset: {req.preset}",
        reason=None
    )
    
    return {
        "status": "ok", 
        "preset": req.preset,
        "description": RATE_LIMIT_PRESETS[req.preset].get("description")
    }


@app.get("/api/admin/rate-limits/presets")
def adm_get_rate_limit_presets(admin: dict = Depends(require_admin)):
    """Fetch available rate-limit presets."""
    return {"presets": RATE_LIMIT_PRESETS}


@app.post("/api/admin/config/cache/clear")
@limiter.limit("10/minute")
def adm_clear_config_cache(
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Clear config cache to apply new settings immediately."""
    clear_config_cache()
    return {"status": "ok", "message": "Config cache cleared"}
