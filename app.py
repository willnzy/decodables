import os
import jwt # 需安装 pyjwt
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Header, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
import base64
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from svix.webhooks import Webhook, WebhookVerificationError

# 导入服务模块
from db_service import (
    # 权限校验
    is_member, can_access_resource, publish_permission, validate_allowed_tiers, listing_is_public_visible,
    get_total_credits,
    # 用户
    get_user_profile, create_user_profile, update_subscription_tier, update_user_profile,
    refresh_monthly_credits, search_users, get_full_user_audit, admin_adjust_credits,
    # Credits
    log_credit_transaction, log_payment_record, credit_deduct, add_credits_permanent, add_credits_monthly,
    deduct_credits_atomic, add_credits, get_credit_history,
    # 项目
    get_user_projects, get_project_detail, create_project, save_project,
    soft_delete_project, restore_project, update_project_hash, get_all_projects_feed,
    count_user_projects,  # 准确计算项目总数
    # 素材
    save_asset, get_assets, get_system_resources,
    # Marketplace
    get_marketplace_listings, get_marketplace_item, get_seller_listings, create_listing,
    submit_listing_for_review, unpublish_listing, update_listing, check_user_purchase,
    execute_purchase, get_user_purchases, get_seller_stats, record_listing_usage, get_leaderboard,
    # Admin 审核
    admin_get_moderation_list, admin_get_moderation_detail, admin_approve_listing,
    admin_reject_listing, admin_delete_listing, admin_unpublish_listing,
    # 通知
    get_user_notifications, mark_notification_read, create_broadcast,
    # 折扣
    get_user_discount, create_user_discount,
    # 日志
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
from story_generator import generate_story_json, client as openai_client # 复用 client

# 环境变量检查
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")
# [安全] Clerk 的公钥 (PEM格式)，用于验证 Token 签名。
# 生产环境请从 Clerk Dashboard -> API Keys -> JWKS 获取，或设置 CLERK_PEM_PUBLIC_KEY 环境变量
CLERK_PEM_PUBLIC_KEY = os.environ.get("CLERK_PEM_PUBLIC_KEY") 

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="MagicZine AI API v3.0 (Production)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 配置 - 明确允许的来源
ALLOWED_ORIGINS = [
    "http://localhost:3000",                      # 本地开发环境
    "http://127.0.0.1:3000",                      # 本地开发环境（备用）
    "https://make-decodables.vercel.app",         # Vercel 生产环境
    "https://decodables-production.up.railway.app" # Railway API 自身
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # 预检请求缓存时间（秒）
)

# 添加中间件确保所有响应都包含 CORS 头（即使出错）
@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    """
    确保所有响应都包含 CORS 头，即使发生错误
    """
    try:
        response = await call_next(request)
        origin = request.headers.get("origin")
        if origin and origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    except Exception as e:
        # 如果发生异常，也要返回带 CORS 头的错误响应
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

# 全局异常处理器 - 确保所有错误响应都包含 CORS 头
from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器，确保所有错误响应都包含 CORS 头
    """
    import traceback
    print(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    print(traceback.format_exc())
    
    # 获取请求的 origin
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
    
    # 如果是 HTTPException，保持原有状态码
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=cors_headers
        )
    
    # 其他异常返回 500
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if os.environ.get("ENV") == "development" else "An error occurred"
        },
        headers=cors_headers
    )

# ==========================================
# 1. 鉴权依赖 (Auth)
# ==========================================
async def get_current_user(authorization: str = Header(None)):
    """
    验证 Bearer Token。
    生产环境模式：验证 JWT 签名。
    开发环境模式：如果未配置公钥，为了方便测试，可能会回退到不安全模式(需谨慎)。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Token")
    
    token = authorization.split(" ")[1]
    payload = None
    
    # -------------------------------------------------------
    # [Real Auth] 生产环境验证逻辑
    # -------------------------------------------------------
    if CLERK_PEM_PUBLIC_KEY:
        try:
            # 验证 Clerk 签发的 JWT
            payload = jwt.decode(token, CLERK_PEM_PUBLIC_KEY, algorithms=["RS256"], options={"verify_aud": False})
            user_id = payload.get("sub")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    else:
        # [Dev Auth] 如果没配公钥，仅提取 user_id (仅限本地开发!)
        # 警告：这不安全，仅用于未配置 Clerk 时的快速调试
        print("⚠️ WARNING: Running in INSECURE AUTH mode (Missing CLERK_PEM_PUBLIC_KEY)")
        try:
            # 不验证签名，仅解码
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub")
        except:
            # 如果连解码都失败，那可能是个假 token
            user_id = token # 回退到 Mock 逻辑: 假设 token 就是 user_id

    # 查库确保用户存在
    profile = get_user_profile(user_id)
    
    # 如果用户不存在数据库，尝试自动创建（处理 webhook 延迟或失败的情况）
    if not profile:
        # 从 JWT payload 中提取用户信息
        email = ""
        username = ""
        avatar_url = ""
        
        if payload:
            # Clerk JWT 中可能包含的字段
            email = payload.get("email", payload.get("primary_email", ""))
            username = payload.get("username", payload.get("name", ""))
            avatar_url = payload.get("image_url", payload.get("picture", ""))
        
        # 创建用户 profile
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

async def require_admin(user: dict = Depends(get_current_user)):
    """管理员权限守卫"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_member(user: dict = Depends(get_current_user)):
    """会员权限守卫（Starter/Pro）"""
    if not is_member(user):
        raise HTTPException(status_code=403, detail="Membership required")
    return user

# ==========================================
# 2. 数据模型 (Models)
# ==========================================
class StoryGenRequest(BaseModel):
    topic: str
    style: Optional[str] = "Children's book illustration"

class ImageGenRequest(BaseModel):
    project_id: str
    prompts: List[str]

class PdfGenRequest(BaseModel):
    project_id: str
    current_hash: str
    image_urls: List[str]
    texts: List[str]

class ProjectUpdate(BaseModel):
    canvas_data: Optional[dict] = None
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    used_listing_ids: Optional[List[str]] = None  # 新增应用的 listing IDs

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
    user_code: str  # 用于验证
    user_email: str  # 用于验证
    target_tier: str  # 'starter' | 'free'
    immediate: bool = False  # True: 立即生效, False: 周期结束后生效
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
    resource_type: str  # 'template' | 'asset'
    price_credits: int = 0
    allowed_tiers: List[str]  # 必填，仅允许 ['free'] / ['starter','pro'] / ['pro']

class MarketplacePurchaseRequest(BaseModel):
    listing_id: str

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
    user_code: str  # 用户唯一标识码，需要与邮箱匹配验证
    payment_intent_id: str
    amount_cents: Optional[int] = None  # None = 全额退款
    reason: str

class AdminCancelSubscriptionRequest(BaseModel):
    user_id: str
    user_code: str  # 用户唯一标识码，需要与邮箱匹配验证
    subscription_id: str
    immediate: bool = False  # True = 立即取消，False = 周期结束取消
    reason: str

# ==========================================
# 3. 接口实现 (Routes)
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
        
        # 检查用户是否已存在（可能已通过 JIT 创建）
        existing_profile = get_user_profile(user_id)
        if existing_profile:
            # 用户已存在（通过 JIT 创建），更新可能缺失的信息
            update_user_profile(user_id, avatar_url=image_url, username=username)
            # 如果 email 为空，单独更新 email
            if not existing_profile.get("email") and email:
                supabase.table("profiles").update({"email": email}).eq("id", user_id).execute()
            print(f"✅ User {user_id} already exists (JIT created), updated profile info")
            return {"status": "updated", "reason": "jit_created"}
        
        # 检查 email 唯一性（防止同一邮箱注册多个账号）
        existing_by_email = search_users(email)
        if existing_by_email:
            print(f"⚠️ User with email {email} already exists, skipping creation")
            return {"status": "skipped", "reason": "email_exists"}
        
        # 创建用户档案
        create_user_profile(user_id, email, username, image_url)
        
        # 记录注册行为
        log_activity(user_id, "user_signup", {
            "email": email,
            "method": "clerk"
        })
    
    elif event_type == "user.updated":
        # 用户更新资料（头像、用户名等）
        user_id = data.get("id")
        new_avatar = data.get("image_url")
        new_username = data.get("username")
        
        # 同步更新到 Supabase
        update_user_profile(user_id, avatar_url=new_avatar, username=new_username)
        
        # 记录更新行为
        log_activity(user_id, "profile_updated", {
            "avatar_changed": new_avatar is not None,
            "username_changed": new_username is not None
        })
        print(f"✅ Updated profile for user {user_id}")
    
    elif event_type == "session.created":
        # 记录登录行为
        user_id = data.get("user_id")
        if user_id:
            log_activity(user_id, "user_login", {
                "client_ip": evt.get("event_attributes", {}).get("http_request", {}).get("client_ip"),
                "user_agent": evt.get("event_attributes", {}).get("http_request", {}).get("user_agent")
            })
    
    elif event_type in ["session.ended", "session.removed", "session.revoked"]:
        # 记录登出行为
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
    
    # 一次性购买完成
    if event_type == 'checkout.session.completed':
        session = event['data']['object']
        uid = session['metadata'].get('user_id')
        plan = session['metadata'].get('plan_type')
        amount_total = session.get('amount_total', 0)  # 以分为单位
        currency = session.get('currency', 'usd').upper()
        
        if uid and plan:
            if plan == 'credits_100':
                # 购买积分：计入 permanent
                add_credits_permanent(uid, 100, "Purchase 100 Credits", "topup_purchase")
                # 记录付款
                log_payment_record(uid, amount_total, currency, "credits_purchase", f"Purchase 100 Credits - ${amount_total/100:.2f}")
                log_activity(uid, "credits_purchase", {"amount": 100, "payment": amount_total})
            elif plan in ['starter', 'pro']:
                # 新订阅：更新 tier + 赠送月度积分
                update_subscription_tier(uid, plan, session.get('customer'), "active")
                amt = 500 if plan == 'starter' else 1000
                add_credits_monthly(uid, amt, f"{plan.capitalize()} Monthly Credits", "sub_grant")
                # 记录订阅付款
                log_payment_record(uid, amount_total, currency, "sub_payment", f"{plan.capitalize()} Plan Subscription - ${amount_total/100:.2f}")
                log_activity(uid, "subscription_started", {"plan": plan, "payment": amount_total})
    
    # 订阅续费成功（月度刷新）
    elif event_type == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        amount_paid = invoice.get('amount_paid', 0)  # 以分为单位
        currency = invoice.get('currency', 'usd').upper()
        billing_reason = invoice.get('billing_reason', '')  # subscription_create, subscription_cycle, etc.
        
        # 查找用户
        if customer_id:
            # 通过 stripe_customer_id 查找用户
            user_res = supabase.table("profiles").select("id, tier")\
                .eq("stripe_customer_id", customer_id).execute()
            
            if user_res.data:
                user = user_res.data[0]
                uid = user['id']
                tier = user['tier']
                
                # 刷新月度积分（重置，不结转）- 只在续费时刷新
                if tier in ['starter', 'pro'] and billing_reason == 'subscription_cycle':
                    refresh_monthly_credits(uid, tier)
                    # 记录续费付款
                    log_payment_record(uid, amount_paid, currency, "sub_renewal", f"{tier.capitalize()} Plan Renewal - ${amount_paid/100:.2f}")
                    log_activity(uid, "monthly_credits_refreshed", {"tier": tier, "payment": amount_paid})
    
    # 订阅取消/过期
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
                    # 降级到 free
                    update_subscription_tier(uid, 'free', subscription_status='inactive')
                    log_activity(uid, "subscription_ended", {"reason": status})
                elif status == 'active':
                    # 订阅恢复
                    plan_id = subscription.get('items', {}).get('data', [{}])[0].get('price', {}).get('id', '')
                    # 根据 price_id 判断 tier（需要配置映射）
                    new_tier = 'starter' if 'starter' in plan_id.lower() else 'pro'
                    update_subscription_tier(uid, new_tier, subscription_status='active')
    
    return {"status": "ok"}

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
    
    # 检查并重置 monthly credits（如果需要）
    # permanent credits 永远不会被重置
    check_and_reset_monthly_credits_if_needed(user_id)
    
    # 重新获取用户信息（可能已更新）
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
    获取用户素材
    
    - Starter用户：只能看到当前项目的素材
    - Pro用户：可以看到所有项目的素材（Cross-Project History）
    - 购买的素材：不受项目限制
    """
    # Pro 用户可以访问所有历史素材
    if scope == "all" and user["tier"] != "pro":
        raise HTTPException(403, "Pro required for cross-project history")
    target_proj = project_id if scope != "all" else None
    return get_assets(user["id"], target_proj)

@app.post("/api/user/assets")
async def upload_asset(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """上传用户素材图片 - 仅 Pro 可用 (PRD v3.2)"""
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
    
    # 验证文件类型
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")
    
    # 验证文件大小 (5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size is 5MB")
    
    # 检查 storage client 是否可用
    if not storage_supabase:
        raise HTTPException(500, "Storage service not configured")
    
    # 生成唯一文件名
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    
    try:
        # 上传文件到 generated-images bucket (复用 image_generator 的客户端)
        storage_supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=contents,
            file_options={"content-type": file.content_type}
        )
        
        # 获取公开 URL
        url = storage_supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        
        # 保存到 assets 表
        save_asset(user["id"], url, "uploaded", project_id)
        
        return {"url": url, "filename": filename}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Failed to upload file: {str(e)}")

@app.delete("/api/user/assets/{asset_id}")
def delete_asset(asset_id: str, user: dict = Depends(get_current_user)):
    """删除用户素材（软删除）"""
    # 验证素材属于当前用户
    asset = supabase.table("assets").select("*").eq("id", asset_id).eq("user_id", user["id"]).single().execute()
    if not asset.data:
        raise HTTPException(404, "Asset not found")
    
    # 软删除
    supabase.table("assets").update({"is_deleted": True}).eq("id", asset_id).execute()
    return {"success": True, "message": "Asset deleted"}

@app.get("/api/user/purchases")
def my_purchases(page: int = 1, limit: int = 50, user: dict = Depends(get_current_user)):
    """获取用户已购买的商品"""
    items = get_user_purchases(user["id"], page, limit)
    return {"items": items, "total": len(items)}

@app.get("/api/user/notifications")
def my_notifications(unread_only: bool = False, user: dict = Depends(get_current_user)):
    """获取用户通知"""
    items = get_user_notifications(user["id"], unread_only)
    return {"items": items}

@app.post("/api/user/notifications/{id}/read")
def mark_read(id: str, user: dict = Depends(get_current_user)):
    """标记通知为已读"""
    mark_notification_read(id, user["id"])
    return {"status": "ok"}

@app.get("/api/resources/stickers")
def get_stickers(user: dict = Depends(get_current_user)):
    """获取贴纸库（根据用户权限过滤）"""
    return get_system_resources("sticker", user["tier"])

# --- Projects ---
@app.get("/api/projects")
def list_projects(
    page: int = 1, 
    limit: int = 6, 
    search: str = None, 
    include_canvas_data: bool = True,  # 新增：是否包含 canvas_data（用于分步加载）
    user: dict = Depends(get_current_user)
):
    """获取用户项目列表，支持分页和搜索
    
    分步加载优化：
    - include_canvas_data=false: 只返回基本信息（快速加载）
    - include_canvas_data=true: 返回完整信息包括 canvas_data（用于渲染预览图）
    """
    print(f"[API] list_projects: page={page}, limit={limit}, search={search}, include_canvas_data={include_canvas_data}, user_id={user['id']}")
    items = get_user_projects(user["id"], page, limit, search, include_canvas_data)
    # 使用 count_user_projects 获取准确的项目总数
    total_count = count_user_projects(user["id"], search)
    print(f"[API] list_projects: items={len(items) if items else 0}, total={total_count}")
    return {"items": items, "total": total_count, "page": page}

class ProjectCreate(BaseModel):
    title: Optional[str] = "My Magic Story"
    canvas_data: Optional[dict] = None

@app.post("/api/projects")
def new_project(req: ProjectCreate = None, user: dict = Depends(get_current_user)):
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
    保存项目（PRD 第12章）
    
    - Save Project 不扣费
    - 保存 canvas_data 与引用关系
    - 必须校验：项目中新增引用的 listing 是否可用（can_access_resource）
    - 使用次数统计：对新产生的 listing 应用写入 listing_usage
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
    
    # 如果有新增的 listing 引用
    if req.used_listing_ids:
        for listing_id in req.used_listing_ids:
            # 获取 listing 信息
            listing = get_marketplace_item(listing_id, user["id"])
            
            if listing:
                # 检查访问权限
                allowed_tiers = listing.get("allowed_tiers", ["free"])
                if not can_access_resource(user, allowed_tiers):
                    locked_elements.append({
                        "listing_id": listing_id,
                        "title": listing.get("title", "Unknown"),
                        "reason": "Upgrade required to access this resource"
                    })
                else:
                    # 记录使用（去重）
                    is_new = record_listing_usage(listing_id, user["id"], id)
                    if is_new:
                        new_usage_recorded.append(listing_id)
    
    # 保存项目
    save_project(id, user["id"], req.canvas_data, req.thumbnail_url, req.title)
    
    # 更新项目的 contains_locked_elements 标记
    if locked_elements:
        supabase.table("projects").update({
            "contains_locked_elements": True
        }).eq("id", id).eq("user_id", user["id"]).execute()
    
    return {
        "status": "saved",
        "locked_elements": locked_elements,
        "usage_recorded": new_usage_recorded
    }

@app.delete("/api/projects/{id}")
def delete_proj(id: str, user: dict = Depends(get_current_user)):
    try:
        soft_delete_project(id, user["id"])
        return {"status": "deleted"}
    except:
        raise HTTPException(404, "Project not found")

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
    """
    blacklist = ["nsfw", "nude", "sex"]
    if any(w in p.lower() for p in req.prompts for w in blacklist):
        raise HTTPException(400, "Safety Violation")
    
    cost = len(req.prompts) * 5
    try:
        result = credit_deduct(user["id"], cost, "generation", f"Gen {len(req.prompts)} images")
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
    
    urls, task_id = await generate_8_images(req.prompts, model=model)
    for url, prompt in zip(urls, req.prompts):
        save_asset(user["id"], url, "ai_generated", req.project_id, prompt)
    
    return {
        "image_urls": urls, 
        "balance": result["total"],
        "balance_monthly": result["balance_monthly"],
        "balance_permanent": result["balance_permanent"],
        "model_used": model  # Return model info for debugging
    }

# [升级] 高级 OCR 接口 - 支持识别表格、文字、图片区域
@app.post("/api/tools/ocr")
@limiter.limit("10/minute")
async def ocr_tool(
    request: Request, 
    file: UploadFile = File(...), 
    project_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """
    高级智能识图 - Pro 可用
    
    识别图片中的：
    - 文字内容（支持多语言）
    - 表格结构
    - 手绘图片区域
    
    返回结构化 JSON，可直接添加到画布
    """
    if user["tier"] != "pro":
        raise HTTPException(status_code=403, detail="Upgrade to Teacher Pro to use Smart Scan")
    
    # 扣费 5 Credits
    try:
        credit_result = credit_deduct(user["id"], 5, "ocr", "Smart Scan")
    except Exception as e:
        if "INSUFFICIENT" in str(e):
            raise HTTPException(402, "Insufficient credits")
        raise
    
    try:
        # 读取文件内容
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        # 上传原始图片到 Supabase Storage
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
        
        # 使用 GPT-4o 进行高级 OCR - 自适应提示词
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
            model="gpt-4o",  # 使用 GPT-4o 获得最佳识别效果
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
        
        # 解析 OCR 结果
        import json
        ocr_result = json.loads(response.choices[0].message.content)
        
        # 转换为画布元素
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
        
        # 保存到 assets 表
        scan_data = {
            "source_image_url": source_image_url,
            "ocr_result": ocr_result,
            "canvas_elements": canvas_elements
        }
        
        # 存储为 scanned 类型的 asset
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

# [新增] 从项目直接生成 PDF（用于 Dashboard）- 免费
@app.get("/api/projects/{project_id}/pdf")
def get_project_pdf(project_id: str, user: dict = Depends(get_current_user)):
    """从保存的项目数据生成 PDF，无需再次传入图片和文字 - 永久免费"""
    proj = get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")
    
    canvas_data = proj.get("canvas_data", {})
    
    # 处理新旧格式
    if isinstance(canvas_data, list):
        # 旧格式: canvas_data 直接是 pages 数组
        pages = canvas_data
        paper_size = "US_LETTER"
    else:
        # 新格式: canvas_data 是 { pages, paperSize }
        pages = canvas_data.get("pages", [])
        paper_size_raw = canvas_data.get("paperSize", "Letter")
        paper_size = "A4" if paper_size_raw == "A4" else "US_LETTER"
    
    # 提取图片 URL 和文字
    image_urls = []
    texts = []
    for page in pages:
        if isinstance(page, dict):
            image_urls.append(page.get("previewImage", "") or "")
            texts.append(page.get("prompt", "") or "")
        else:
            image_urls.append("")
            texts.append("")
    
    # 补齐 8 页
    while len(image_urls) < 8:
        image_urls.append("")
        texts.append("")
    
    # 生成 PDF
    buf = BytesIO()
    create_foldable_book(image_urls, texts, buf, paper_type=paper_size)
    buf.seek(0)
    
    # 生成文件名
    title = proj.get("title", "project").replace(" ", "_")
    
    # 记录下载行为（不扣费）
    log_activity(user["id"], "download_pdf", {"project_id": project_id})
    
    return StreamingResponse(
        buf, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename={title}.pdf"}
    )

# [新增] 预览 PDF 为图片（防止用户绕过下载）
@app.get("/api/projects/{project_id}/preview")
def preview_project_as_image(project_id: str, user: dict = Depends(get_current_user)):
    """生成 PDF 预览图片，防止用户直接下载 PDF"""
    import fitz  # PyMuPDF
    
    proj = get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")
    
    canvas_data = proj.get("canvas_data", {})
    
    # 处理新旧格式
    if isinstance(canvas_data, list):
        pages = canvas_data
        paper_size = "US_LETTER"
    else:
        pages = canvas_data.get("pages", [])
        paper_size_raw = canvas_data.get("paperSize", "Letter")
        paper_size = "A4" if paper_size_raw == "A4" else "US_LETTER"
    
    # 提取图片 URL 和文字
    image_urls = []
    texts = []
    for page in pages:
        if isinstance(page, dict):
            image_urls.append(page.get("previewImage", "") or "")
            texts.append(page.get("prompt", "") or "")
        else:
            image_urls.append("")
            texts.append("")
    
    # 补齐 8 页
    while len(image_urls) < 8:
        image_urls.append("")
        texts.append("")
    
    # 生成 PDF 到内存
    pdf_buffer = BytesIO()
    create_foldable_book(image_urls, texts, pdf_buffer, paper_type=paper_size)
    pdf_buffer.seek(0)
    
    # 将 PDF 转换为图片
    try:
        pdf_doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        page = pdf_doc[0]  # 只有一页
        
        # 设置缩放比例（2x 为高清预览）
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # 转换为 PNG
        img_buffer = BytesIO(pix.tobytes("png"))
        pdf_doc.close()
        
        return StreamingResponse(
            img_buffer, 
            media_type="image/png",
            headers={"Cache-Control": "no-store"}
        )
    except Exception as e:
        print(f"PDF to image conversion error: {e}")
        raise HTTPException(500, "Failed to generate preview")

@app.post("/api/generate/pdf")
def dl_pdf(req: PdfGenRequest, user: dict = Depends(get_current_user)):
    """生成 PDF - 永久免费（根据 PRD v3.0）"""
    # 不再扣费，仅更新 hash 用于缓存/版本识别
    proj = get_project_detail(req.project_id, user["id"])
    if proj and req.current_hash != proj.get("last_downloaded_hash"):
        update_project_hash(req.project_id, req.current_hash)
            
    buf = BytesIO()
    create_foldable_book(req.image_urls, req.texts, buf)
    buf.seek(0)
    log_activity(user["id"], "download_pdf", {"project_id": req.project_id})
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=zine.pdf"})

@app.post("/api/export/zip")
def dl_zip(req: PdfGenRequest, user: dict = Depends(get_current_user)):
    """导出 ZIP - 仅 Pro 可用 (PRD v3.2)"""
    # Normalize tier to lowercase for consistent comparison
    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "ZIP export requires Pro plan. Starter users can export PDF only.")
    buf = BytesIO()
    create_assets_zip(req.image_urls, buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=assets.zip"})

# [新增] 从项目直接导出 ZIP（PDF + 图片）
@app.get("/api/projects/{project_id}/zip")
def get_project_zip(project_id: str, user: dict = Depends(get_current_user)):
    """从保存的项目数据导出 ZIP（包含 PDF 和所有图片）- 仅 Pro 可用 (PRD v3.2)"""
    # 检查权限 - Pro only (PRD v3.2)
    # Normalize tier to lowercase for consistent comparison
    user_tier = (user.get("tier") or "").lower()
    if user_tier != "pro":
        raise HTTPException(403, "ZIP export requires Pro plan. Starter users can export PDF only.")
    
    proj = get_project_detail(project_id, user["id"])
    if not proj:
        raise HTTPException(404, "Project not found")
    
    canvas_data = proj.get("canvas_data", {})
    
    # 处理新旧格式
    if isinstance(canvas_data, list):
        pages = canvas_data
        paper_size = "US_LETTER"
    else:
        pages = canvas_data.get("pages", [])
        paper_size_raw = canvas_data.get("paperSize", "Letter")
        paper_size = "A4" if paper_size_raw == "A4" else "US_LETTER"
    
    # 提取图片 URL 和文字
    image_urls = []
    texts = []
    for page in pages:
        if isinstance(page, dict):
            image_urls.append(page.get("previewImage", "") or "")
            texts.append(page.get("prompt", "") or "")
        else:
            image_urls.append("")
            texts.append("")
    
    # 补齐 8 页
    while len(image_urls) < 8:
        image_urls.append("")
        texts.append("")
    
    title = proj.get("title", "project").replace(" ", "_")
    
    # 创建 ZIP（包含 PDF 和图片）
    import zipfile
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. 生成并添加 PDF
        pdf_buffer = BytesIO()
        create_foldable_book(image_urls, texts, pdf_buffer, paper_type=paper_size)
        pdf_buffer.seek(0)
        zf.writestr(f"{title}.pdf", pdf_buffer.read())
        
        # 2. 添加所有图片
        import requests
        import re
        
        for i, img_url in enumerate(image_urls):
            if not img_url:
                continue
            
            try:
                if img_url.startswith('data:'):
                    # Base64 图片
                    match = re.match(r'data:image/([^;]+);base64,(.+)', img_url)
                    if match:
                        ext = match.group(1)
                        if ext == 'jpeg':
                            ext = 'jpg'
                        img_data = base64.b64decode(match.group(2))
                        zf.writestr(f"Page_{i+1}.{ext}", img_data)
                else:
                    # URL 图片
                    resp = requests.get(img_url, timeout=10)
                    if resp.status_code == 200:
                        # 从 Content-Type 或 URL 推断扩展名
                        content_type = resp.headers.get('content-type', 'image/png')
                        ext = content_type.split('/')[-1].split(';')[0]
                        if ext == 'jpeg':
                            ext = 'jpg'
                        zf.writestr(f"Page_{i+1}.{ext}", resp.content)
            except Exception as e:
                print(f"ZIP: Failed to add image {i+1}: {e}")
    
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename={title}.zip"}
    )

# --- Marketplace ---
@app.get("/api/marketplace/items")
def marketplace_items(
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
    获取市场商品列表（PRD 第13章）
    
    公共列表默认返回: moderation_status='approved' AND is_public=true AND is_deleted=false
    mine=true 时返回本人全状态
    """
    try:
        print(f"[marketplace_items] Request params: resource_type={resource_type}, sort={sort}, tier={tier}, price={price}, mine={mine}, page={page}, limit={limit}")
        print(f"[marketplace_items] User: {user.get('id', 'unknown')}, tier: {user.get('tier', 'unknown')}")
        
        # 调用数据库查询
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
        
        # 为每个商品添加用户可访问性和购买状态
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
                # 设置默认值
                item["is_accessible"] = False
                item["is_owned"] = False
        
        result = {"items": items, "total": len(items), "page": page}
        print(f"[marketplace_items] Returning {len(items)} items")
        return result
    except HTTPException:
        # 重新抛出 HTTPException（保持状态码）
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
    获取单个 listing 详情（PRD 第13章）
    
    公共访问: 仅允许 approved + public + not deleted
    卖家本人: 可看自己的任意状态
    Admin: 可看任意
    """
    item = get_marketplace_item(listing_id, user["id"])
    
    if not item:
        # Admin 可以看任意状态
        if user.get("role") == "admin":
            item = supabase.table("marketplace_listings").select("*, profiles(username, avatar_url)")\
                .eq("id", listing_id).single().execute().data
        
        if not item:
            raise HTTPException(404, "Listing not found")
    
    # 添加权限信息
    allowed_tiers = item.get("allowed_tiers", ["free", "starter", "pro"])
    item["is_accessible"] = can_access_resource(user, allowed_tiers)
    item["is_owned"] = check_user_purchase(user["id"], item["id"])
    
    return item

@app.post("/api/marketplace/publish")
def marketplace_publish(req: MarketplacePublishRequest, user: dict = Depends(require_member)):
    """
    发布商品（提交审核）（PRD 第7/8章）
    
    权限:
    - Free: 拒绝任何发布
    - Starter: 仅允许 resource_type='asset' 且 price_credits=0
    - Pro: 允许 resource_type='asset'|'template' 且 price_credits 在 0..500
    
    提交后 moderation_status='pending'，必须管理员审核通过后才能上架
    """
    # 1. 校验发布权限
    perm = publish_permission(user, req.resource_type, req.price_credits)
    if not perm["allowed"]:
        raise HTTPException(403, perm["reason"])
    
    # 2. 校验 allowed_tiers 白名单
    tiers_validation = validate_allowed_tiers(req.allowed_tiers)
    if not tiers_validation["valid"]:
        raise HTTPException(400, tiers_validation["reason"])
    
    # 3. 创建 listing（自动进入 pending 状态）
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
    下架商品（PRD 第13章）
    
    设置 is_public=false，不改变历史 purchases 与 usage_count
    """
    result = unpublish_listing(req.listing_id, user["id"])
    
    if not result:
        raise HTTPException(404, "Listing not found or not owned by you")
    
    log_activity(user["id"], "marketplace_unpublish", {"listing_id": req.listing_id})
    
    return {"status": "unpublished"}

@app.post("/api/marketplace/purchase")
def marketplace_purchase(req: MarketplacePurchaseRequest, user: dict = Depends(get_current_user)):
    """购买商品"""
    result = execute_purchase(user["id"], req.listing_id)
    
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
    """获取我的上架商品"""
    items = get_seller_listings(user["id"], page, limit)
    return {"items": items, "total": len(items)}

@app.put("/api/marketplace/listings/{listing_id}")
def update_my_listing(listing_id: str, req: ListingUpdateRequest, user: dict = Depends(get_current_user)):
    """更新我的商品"""
    updates = req.dict(exclude_none=True)
    result = update_listing(listing_id, user["id"], updates)
    if not result:
        raise HTTPException(404, "Listing not found or not owned by you")
    return result

@app.get("/api/marketplace/seller/stats")
def seller_stats(user: dict = Depends(get_current_user)):
    """获取卖家统计数据（PRD 第13章）"""
    stats = get_seller_stats(user["id"])
    return stats

@app.get("/api/marketplace/leaderboard")
def marketplace_leaderboard(
    period: str = "monthly",  # 'monthly' | 'all_time'
    type: str = "all",  # 'all' | 'template' | 'asset'
    user: dict = Depends(get_current_user)
):
    """
    获取排行榜（PRD 第9章）
    
    返回 Top 10 listings with usage_count and rank
    仅统计 approved 且 is_public=true 且 is_deleted=false
    """
    leaderboard = get_leaderboard(period=period, board_type=type, limit=10)
    return {"items": leaderboard, "period": period, "type": type}

# --- Pay & Support ---
@app.post("/api/payment/checkout")
def pay(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    # 检查是否有折扣
    discount = get_user_discount(user["id"], req.plan_type)
    discount_percent = discount.get("discount_percent", 0) if discount else 0
    
    url = create_checkout_session(user["id"], req.plan_type, discount_percent)
    return {"url": url, "discount_applied": discount_percent}

@app.post("/api/payment/portal")
def portal(user: dict = Depends(get_current_user)):
    if not user.get("stripe_customer_id"): raise HTTPException(400, "No subscription found")
    return {"url": create_portal_session(user["id"], user.get("stripe_customer_id"))}

@app.post("/api/support/email")
def ticket(req: SupportTicketRequest, user: dict = Depends(get_current_user)):
    # Use provided email or fallback to user's profile email
    email = req.email or user.get("email", "unknown@user.com")
    create_support_ticket(user["id"], email, req.message)
    return {"status": "ok"}

@app.post("/api/contact")
def contact_form(req: ContactFormRequest):
    """
    Public contact form endpoint - no authentication required.
    Used by Contact Us page for both logged in and guest users.
    """
    # Create support ticket with "guest" as user_id for unauthenticated users
    create_support_ticket("guest", req.email, req.message)
    return {"status": "ok"}

@app.post("/api/feedback")
def feedback_with_images(req: FeedbackWithImagesRequest, request: Request):
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
def adm_users(query: str, admin: dict = Depends(require_admin)):
    return search_users(query)

@app.get("/api/admin/user/{uid}")
def adm_audit(uid: str, admin: dict = Depends(require_admin)):
    return get_full_user_audit(uid)

@app.post("/api/admin/credits/adjust")
def adm_adj(req: AdminAdjustRequest, admin: dict = Depends(require_admin)):
    """手动调整用户积分（可指定 bucket）"""
    admin_adjust_credits(req.user_id, req.amount, req.bucket, req.reason)
    log_activity(admin["id"], "admin_credits_adjust", {
        "target_user": req.user_id,
        "amount": req.amount,
        "bucket": req.bucket,
        "reason": req.reason
    })
    return {"status": "ok"}

@app.post("/api/admin/tier/update")
def adm_tier(req: AdminTierRequest, admin: dict = Depends(require_admin)):
    update_subscription_tier(req.user_id, req.tier)
    log_activity(admin["id"], "admin_tier_update", {
        "target_user": req.user_id,
        "new_tier": req.tier
    })
    return {"status": "ok"}

@app.post("/api/admin/discount")
def adm_discount(req: AdminDiscountRequest, admin: dict = Depends(require_admin)):
    """设置用户折扣"""
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
    获取用户的付款历史（用于退款操作）
    
    返回:
    - user_code: 用户唯一标识码（用于验证）
    - user_email: 用户邮箱
    - payments: 付款记录列表，包含可退款金额
    - subscriptions: 订阅记录列表，包含状态信息
    """
    user = get_user_profile(uid)
    if not user:
        raise HTTPException(404, "User not found")
    
    user_code = user.get("user_code")
    user_email = user.get("email")
    
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        return {"user_code": user_code, "user_email": user_email, "payments": [], "subscriptions": []}
    
    # 获取付款历史
    payments = get_customer_payments(customer_id, limit=20)
    payment_list = []
    for pi in payments:
        # 计算已退款金额和可退款金额
        amount_refunded = pi.amount - (pi.amount_received if hasattr(pi, 'amount_received') else pi.amount)
        refundable_amount = pi.amount_received if hasattr(pi, 'amount_received') else pi.amount
        is_fully_refunded = refundable_amount <= 0
        
        payment_list.append({
            "id": pi.id,
            "amount": pi.amount,  # 原始金额
            "amount_refunded": amount_refunded,  # 已退款金额
            "refundable_amount": refundable_amount,  # 可退款金额
            "currency": pi.currency,
            "status": pi.status,
            "created": pi.created,
            "description": pi.description,
            "is_partially_refunded": amount_refunded > 0 and not is_fully_refunded,
            "is_fully_refunded": is_fully_refunded,
        })
    
    # 获取订阅信息
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
def adm_refund(req: AdminRefundRequest, admin: dict = Depends(require_admin)):
    """
    Admin 退款操作
    
    支持全额或部分退款
    
    安全检查:
    1. 验证用户存在
    2. 验证用户ID与邮箱匹配
    3. 验证 PaymentIntent 存在
    4. 验证 PaymentIntent 属于该用户
    5. 验证退款金额不超过可退款金额
    6. 验证 PaymentIntent 未被完全退款
    """
    user = get_user_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # 【安全检查】验证用户ID (user_code) 与用户匹配
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match. Please verify the user code.")
    
    # 获取用户的 Stripe Customer ID
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(400, "User has no Stripe customer ID")
    
    # 获取 PaymentIntent 详情
    pi = get_payment_intent_details(req.payment_intent_id)
    if not pi:
        raise HTTPException(404, "Payment not found")
    
    # 【安全检查1】验证 PaymentIntent 属于该用户
    if pi.customer != customer_id:
        raise HTTPException(403, "Payment does not belong to this user")
    
    # 【安全检查2】验证 PaymentIntent 状态
    if pi.status != 'succeeded':
        raise HTTPException(400, f"Cannot refund payment with status: {pi.status}")
    
    # 【安全检查3】计算可退款金额
    # amount_received 是实际收到的金额，已扣除之前的退款
    refundable_amount = pi.amount_received if hasattr(pi, 'amount_received') else pi.amount
    
    if refundable_amount <= 0:
        raise HTTPException(400, "Payment has already been fully refunded")
    
    # 【安全检查4】验证部分退款金额
    if req.amount_cents is not None:
        if req.amount_cents <= 0:
            raise HTTPException(400, "Refund amount must be positive")
        if req.amount_cents > refundable_amount:
            raise HTTPException(400, f"Refund amount ({req.amount_cents}) exceeds refundable amount ({refundable_amount})")
    
    # 执行退款
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
    
    # 记录退款到用户的交易历史
    log_payment_record(
        req.user_id,
        -refund_amount,  # 负数表示退款
        currency,
        "refund",
        f"Refund - ${refund_amount/100:.2f} | Reason: {req.reason}"
    )
    
    # 记录管理员操作日志
    log_activity(admin["id"], "admin_refund", {
        "target_user": req.user_id,
        "payment_intent_id": req.payment_intent_id,
        "refund_id": refund.id,
        "amount_cents": refund_amount,
        "original_amount": pi.amount,
        "refundable_amount": refundable_amount,
        "reason": req.reason
    })
    
    return {
        "status": "refunded",
        "refund_id": refund.id,
        "amount": refund_amount,
        "currency": currency
    }

@app.post("/api/admin/subscription/cancel")
def adm_cancel_subscription(req: AdminCancelSubscriptionRequest, admin: dict = Depends(require_admin)):
    """
    Admin 取消用户订阅
    
    immediate=True: 立即取消
    immediate=False: 在当前计费周期结束时取消
    
    安全检查:
    1. 验证用户存在
    2. 验证用户ID与邮箱匹配
    3. 验证用户有 Stripe Customer ID
    4. 验证订阅属于该用户
    5. 验证订阅当前状态是活跃的
    6. 验证订阅未被预约取消
    """
    import stripe
    
    user = get_user_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # 【安全检查】验证用户ID (user_code) 与用户匹配
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match. Please verify the user code.")
    
    # 获取用户的 Stripe Customer ID
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(400, "User has no Stripe customer ID")
    
    # 【安全检查1】获取并验证订阅详情
    try:
        subscription_detail = stripe.Subscription.retrieve(req.subscription_id)
    except stripe.error.StripeError as e:
        raise HTTPException(404, f"Subscription not found: {str(e)}")
    
    # 【安全检查2】验证订阅属于该用户
    if subscription_detail.customer != customer_id:
        raise HTTPException(403, "Subscription does not belong to this user")
    
    # 【安全检查3】验证订阅状态
    if subscription_detail.status not in ['active', 'trialing', 'past_due']:
        raise HTTPException(400, f"Cannot cancel subscription with status: {subscription_detail.status}")
    
    # 【安全检查4】验证订阅未被预约取消（如果选择周期结束取消）
    if not req.immediate and subscription_detail.cancel_at_period_end:
        raise HTTPException(400, "Subscription is already scheduled for cancellation")
    
    # 执行取消订阅
    result = cancel_subscription(req.subscription_id, immediate=req.immediate)
    
    if not result["success"]:
        raise HTTPException(400, f"Cancel subscription failed: {result['error']}")
    
    subscription = result["subscription"]
    
    # 获取订阅 plan 名称用于记录
    plan_name = "Unknown"
    if subscription_detail.items.data:
        price_id = subscription_detail.items.data[0].price.id
        if 'starter' in price_id.lower():
            plan_name = "Starter"
        elif 'pro' in price_id.lower():
            plan_name = "Pro"
    
    # 如果是立即取消，更新用户 tier 为 free
    if req.immediate:
        update_subscription_tier(req.user_id, "free", subscription_status="canceled")
        
        # 记录到用户的交易历史
        log_payment_record(
            req.user_id,
            0,
            "USD",
            "sub_canceled",
            f"{plan_name} Subscription Canceled (Immediate) | Reason: {req.reason}"
        )
    else:
        # 记录到用户的交易历史 - 周期结束取消
        log_payment_record(
            req.user_id,
            0,
            "USD",
            "sub_cancel_scheduled",
            f"{plan_name} Subscription Cancel Scheduled | Ends: {subscription.current_period_end} | Reason: {req.reason}"
        )
    
    # 记录管理员操作日志
    log_activity(admin["id"], "admin_cancel_subscription", {
        "target_user": req.user_id,
        "subscription_id": req.subscription_id,
        "plan": plan_name,
        "immediate": req.immediate,
        "reason": req.reason
    })
    
    return {
        "status": "canceled" if req.immediate else "cancel_scheduled",
        "subscription_id": subscription.id,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "current_period_end": subscription.current_period_end
    }

@app.post("/api/admin/subscription/downgrade")
def adm_downgrade_subscription(req: AdminDowngradeRequest, admin: dict = Depends(require_admin)):
    """
    Admin 帮用户降级订阅
    
    支持的降级路径:
    - Pro -> Starter (变更订阅计划)
    - Pro -> Free (取消订阅)
    - Starter -> Free (取消订阅)
    
    immediate=True: 立即生效
    immediate=False: 周期结束后生效
    
    安全检查:
    1. 验证用户存在
    2. 验证用户ID与邮箱匹配
    3. 验证目标等级低于当前等级
    4. 验证 Stripe 订阅状态
    """
    import stripe
    
    user = get_user_profile(req.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # 【安全检查1】验证用户ID (user_code)
    stored_user_code = user.get("user_code")
    if not stored_user_code:
        raise HTTPException(400, "User has no user code assigned")
    if stored_user_code != req.user_code:
        raise HTTPException(403, "User code does not match")
    
    # 【安全检查2】验证邮箱
    if user.get("email") != req.user_email:
        raise HTTPException(403, "User email does not match")
    
    current_tier = user.get("tier", "free")
    target_tier = req.target_tier.lower()
    
    # 【安全检查3】验证等级降级路径
    tier_levels = {"free": 0, "starter": 1, "pro": 2}
    if tier_levels.get(target_tier, -1) >= tier_levels.get(current_tier, 0):
        raise HTTPException(400, f"Cannot downgrade from {current_tier} to {target_tier}")
    
    if target_tier not in ["free", "starter"]:
        raise HTTPException(400, "Invalid target tier. Must be 'free' or 'starter'")
    
    customer_id = user.get("stripe_customer_id")
    
    # 情况1: 降级到 Free (取消订阅)
    if target_tier == "free":
        if not customer_id:
            # 没有 Stripe 订阅，直接更新数据库
            update_subscription_tier(req.user_id, "free", subscription_status="inactive")
            
            # 清零月度积分
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
        
        # 有 Stripe 订阅，需要取消
        subscriptions = get_customer_subscriptions(customer_id)
        active_sub = None
        for sub in subscriptions:
            if sub.status in ['active', 'trialing']:
                active_sub = sub
                break
        
        if not active_sub:
            # 没有活跃订阅，直接更新
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
        
        # 取消订阅
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
    
    # 情况2: Pro -> Starter (变更订阅计划)
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
        
        # 获取 Starter 价格 ID
        starter_price_id = os.environ.get("STRIPE_STARTER_MONTHLY_PRICE_ID")
        if not starter_price_id:
            raise HTTPException(500, "Starter price ID not configured")
        
        try:
            # 修改订阅计划
            # proration_behavior: 
            # - 'create_prorations': 按比例退款差额
            # - 'none': 不退款，立即生效
            # - 'always_invoice': 立即开发票
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
                # 立即更新用户等级
                update_subscription_tier(req.user_id, "starter", subscription_status="active")
                
                # 调整月度积分为 Starter 额度 (500)
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
def adm_broadcast(req: AdminBroadcastRequest, admin: dict = Depends(require_admin)):
    """群发系统通知"""
    notification = create_broadcast(req.title, req.content, req.target_group)
    log_activity(admin["id"], "admin_broadcast", {
        "target_group": req.target_group,
        "title": req.title
    })
    return notification

@app.post("/api/admin/projects/{project_id}/restore")
def adm_restore_project(project_id: str, admin: dict = Depends(require_admin)):
    """恢复被删除的项目"""
    project = restore_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    log_activity(admin["id"], "admin_project_restore", {"project_id": project_id})
    return project

@app.get("/api/admin/projects/feed")
def adm_projects_feed(page: int = 1, limit: int = 50, admin: dict = Depends(require_admin)):
    """获取全站项目流"""
    items = get_all_projects_feed(page, limit)
    return {"items": items, "total": len(items), "page": page}

# --- Admin Marketplace Moderation (PRD 第16章) ---
@app.get("/api/admin/marketplace/moderation/list")
def adm_moderation_list(
    status: Optional[str] = None,  # 'pending' | 'approved' | 'rejected' | 'all'
    type: Optional[str] = None,  # 'template' | 'asset'
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    """
    获取审核列表（PRD 第16章）
    
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
    获取审核详情（PRD 第16章）
    
    预览: thumbnail + resource_url
    元信息: title/description/allowed_tiers/price_credits
    """
    item = admin_get_moderation_detail(listing_id)
    if not item:
        raise HTTPException(404, "Listing not found")
    return item

@app.post("/api/admin/marketplace/moderation/{listing_id}/approve")
def adm_moderation_approve(listing_id: str, admin: dict = Depends(require_admin)):
    """
    批准 listing（PRD 第16章）
    
    pending -> approved
    """
    result = admin_approve_listing(listing_id, admin["id"])
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_approve", {"listing_id": listing_id})
    return {"status": "approved", "listing_id": listing_id}

@app.post("/api/admin/marketplace/moderation/{listing_id}/reject")
def adm_moderation_reject(
    listing_id: str, 
    req: AdminModerationRejectRequest,
    admin: dict = Depends(require_admin)
):
    """
    拒绝 listing（PRD 第16章）
    
    pending -> rejected（必须附原因）
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
    return {"status": "rejected", "listing_id": listing_id, "reason": req.reason}

@app.post("/api/admin/marketplace/moderation/{listing_id}/delete")
def adm_moderation_delete(listing_id: str, admin: dict = Depends(require_admin)):
    """
    软删除 listing（PRD 第16章）
    
    设置 is_deleted=true
    """
    result = admin_delete_listing(listing_id)
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_delete", {"listing_id": listing_id})
    return {"status": "deleted", "listing_id": listing_id}

@app.post("/api/admin/marketplace/moderation/{listing_id}/unpublish")
def adm_moderation_unpublish(listing_id: str, admin: dict = Depends(require_admin)):
    """
    强制下架 listing（PRD 第16章）
    
    设置 is_public=false
    """
    result = admin_unpublish_listing(listing_id)
    if not result:
        raise HTTPException(404, "Listing not found")
    
    log_activity(admin["id"], "admin_moderation_unpublish", {"listing_id": listing_id})
    return {"status": "unpublished", "listing_id": listing_id}
