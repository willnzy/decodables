import os
import jwt # 需安装 pyjwt
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Header, Depends, UploadFile, File
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
from db_service import *
from payment_service import create_checkout_session, create_portal_session, construct_event
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",                      # 👈 关键！允许本地开发环境
        "https://make-decodables.vercel.app",         # 您的 Vercel 生产环境域名
        "https://decodables-production.up.railway.app" # 允许 Swagger UI 自身调用
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

class CheckoutRequest(BaseModel):
    plan_type: str  # 'credits_100', 'starter', or 'pro'

class SupportTicketRequest(BaseModel):
    email: Optional[str] = None  # Optional - will use user's email if not provided
    message: str

class AdminAdjustRequest(BaseModel):
    user_id: str
    amount: int
    bucket: Optional[str] = "permanent"  # 'monthly' | 'permanent'
    reason: str

class AdminTierRequest(BaseModel):
    user_id: str
    tier: str

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
    resource_type: str  # 'template', 'sticker', 'image'
    price_credits: int = 0
    allowed_tiers: Optional[List[str]] = None

class MarketplacePurchaseRequest(BaseModel):
    listing_id: str

class ListingUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price_credits: Optional[int] = None
    is_public: Optional[bool] = None
    allowed_tiers: Optional[List[str]] = None

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
        # 检查 email 唯一性
        email = data["email_addresses"][0]["email_address"]
        existing = search_users(email)
        if existing:
            print(f"⚠️ User with email {email} already exists, skipping creation")
            return {"status": "skipped", "reason": "email_exists"}
        
        # 创建用户档案
        create_user_profile(
            data["id"], 
            email, 
            data.get("username"), 
            data.get("image_url")
        )
        # 记录注册行为
        log_activity(data["id"], "user_signup", {
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
        
        if uid and plan:
            if plan == 'credits_100':
                # 购买积分：计入 permanent
                add_credits_permanent(uid, 100, "Purchase 100 Credits", "topup_purchase")
                log_activity(uid, "credits_purchase", {"amount": 100})
            elif plan in ['starter', 'pro']:
                # 新订阅：更新 tier + 赠送月度积分
                update_subscription_tier(uid, plan, session.get('customer'), "active")
                amt = 500 if plan == 'starter' else 1000
                add_credits_monthly(uid, amt, f"{plan.capitalize()} Monthly Credits", "sub_grant")
                log_activity(uid, "subscription_started", {"plan": plan})
    
    # 订阅续费成功（月度刷新）
    elif event_type == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        
        # 查找用户
        if customer_id:
            # 通过 stripe_customer_id 查找用户
            user_res = supabase.table("profiles").select("id, tier")\
                .eq("stripe_customer_id", customer_id).execute()
            
            if user_res.data:
                user = user_res.data[0]
                uid = user['id']
                tier = user['tier']
                
                # 刷新月度积分（重置，不结转）
                if tier in ['starter', 'pro']:
                    refresh_monthly_credits(uid, tier)
                    log_activity(uid, "monthly_credits_refreshed", {"tier": tier})
    
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
    # 返回用户信息，包括两类积分
    return {
        **user,
        "credits_total": user.get("credits_monthly", 0) + user.get("credits_permanent", 0),
        "is_member": is_member(user)
    }

@app.get("/api/user/history")
def get_history(page: int = 1, limit: int = 20, user: dict = Depends(get_current_user)):
    items = get_credit_history(user["id"], page, limit)
    return {"items": items, "total": len(items), "page": page}

@app.get("/api/user/assets")
def my_assets(project_id: Optional[str]=None, scope: Optional[str]=None, user: dict = Depends(get_current_user)):
    # Pro 用户可以访问所有历史素材
    if scope == "all" and user["tier"] != "pro":
        raise HTTPException(403, "Pro required for cross-project history")
    target_proj = project_id if scope != "all" else None
    return get_assets(user["id"], target_proj)

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
def list_projects(page: int=1, limit: int=20, user: dict = Depends(get_current_user)):
    items = get_user_projects(user["id"], page, limit)
    return {"items": items, "total": len(items), "page": page}

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
    return p

@app.put("/api/projects/{id}")
def save_proj(id: str, req: ProjectUpdate, user: dict = Depends(get_current_user)):
    save_project(id, user["id"], req.canvas_data, req.thumbnail_url, req.title)
    return {"status": "saved"}

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
        
    urls, task_id = await generate_8_images(req.prompts)
    for url, prompt in zip(urls, req.prompts):
        save_asset(user["id"], url, "ai_generated", req.project_id, prompt)
    
    return {
        "image_urls": urls, 
        "balance": result["total"],
        "balance_monthly": result["balance_monthly"],
        "balance_permanent": result["balance_permanent"]
    }

# [修复] 真实 OCR 接口
@app.post("/api/tools/ocr")
@limiter.limit("10/minute")
async def ocr_tool(request: Request, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """智能识图 - Pro 或 Trial 可用"""
    # Pro 用户可无限使用，其他用户需要 Trial 逻辑（这里简化为仅 Pro）
    if user["tier"] != "pro":
        raise HTTPException(status_code=403, detail="Upgrade to Teacher Pro to use Smart Scan")
    
    # 扣费 5 Credits
    try:
        result = credit_deduct(user["id"], 5, "ocr", "Smart Scan")
    except Exception as e:
        if "INSUFFICIENT" in str(e):
            raise HTTPException(402, "Insufficient credits")
        raise
    
    try:
        # 读取文件内容并转 Base64
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        # 调用 OpenAI Vision
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini", # 或 gpt-4o
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this sketch for a children's book illustration prompt. Keep it short."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ],
            max_tokens=100
        )
        description = response.choices[0].message.content
        return {"text": description, "balance": result["total"]}
    except Exception as e:
        print(f"OCR Error: {e}")
        raise HTTPException(500, "OCR Failed")

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
    """导出 ZIP - 仅 Starter/Pro 可用，永久免费"""
    if user["tier"] == "free":
        raise HTTPException(403, "Upgrade to Starter or Pro to export ZIP")
    buf = BytesIO()
    create_assets_zip(req.image_urls, buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=assets.zip"})

# [新增] 从项目直接导出 ZIP（PDF + 图片）
@app.get("/api/projects/{project_id}/zip")
def get_project_zip(project_id: str, user: dict = Depends(get_current_user)):
    """从保存的项目数据导出 ZIP（包含 PDF 和所有图片）"""
    # 检查权限
    if user["tier"] == "free":
        raise HTTPException(403, "Upgrade to Starter or Pro to export ZIP")
    
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
    page: int = 1, 
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """获取市场商品列表"""
    items = get_marketplace_listings(featured, resource_type, page, limit)
    
    # 为每个商品添加用户可访问性和购买状态
    for item in items:
        allowed_tiers = item.get("allowed_tiers", ["free", "starter", "pro"])
        item["is_accessible"] = can_access_resource(user, allowed_tiers)
        item["is_owned"] = check_user_purchase(user["id"], item["id"])
    
    return {"items": items, "total": len(items), "page": page}

@app.post("/api/marketplace/publish")
def marketplace_publish(req: MarketplacePublishRequest, user: dict = Depends(get_current_user)):
    """上架商品"""
    listing = create_listing(
        seller_id=user["id"],
        title=req.title,
        description=req.description,
        thumbnail_url=req.thumbnail_url,
        resource_url=req.resource_url,
        resource_type=req.resource_type,
        price_credits=req.price_credits,
        allowed_tiers=req.allowed_tiers
    )
    log_activity(user["id"], "marketplace_publish", {"listing_id": listing["id"]})
    return listing

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
    """获取卖家统计数据"""
    stats = get_seller_stats(user["id"])
    return stats

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
