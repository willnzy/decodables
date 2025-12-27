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
app = FastAPI(title="MagicZine AI API v2.3 (Production)")
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
    canvas_data: dict
    thumbnail_url: Optional[str] = None

class CheckoutRequest(BaseModel):
    plan_type: str  # 'credits_100', 'starter', or 'pro'

class SupportTicketRequest(BaseModel):
    email: Optional[str] = None  # Optional - will use user's email if not provided
    message: str

class AdminAdjustRequest(BaseModel):
    user_id: str
    amount: int
    reason: str

class AdminTierRequest(BaseModel):
    user_id: str
    tier: str

# ==========================================
# 3. 接口实现 (Routes)
# ==========================================

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.3"}

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
        # 创建用户档案
        create_user_profile(
            data["id"], 
            data["email_addresses"][0]["email_address"], 
            data.get("username"), 
            data.get("image_url")
        )
        # 记录注册行为
        log_activity(data["id"], "user_signup", {
            "email": data["email_addresses"][0]["email_address"],
            "method": "clerk"
        })
    
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
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        uid = session['metadata'].get('user_id')
        plan = session['metadata'].get('plan_type')
        if uid and plan:
            if plan == 'credits_100':
                add_credits(uid, 100, "Purchase 100 Credits")
            elif plan in ['starter', 'pro']:
                update_subscription_tier(uid, plan, session.get('customer'))
                amt = 500 if plan == 'starter' else 1000
                add_credits(uid, amt, f"{plan} Sub Grant", "sub_grant")
    return {"status": "ok"}

# --- User ---
@app.get("/api/user/me")
def get_me(user: dict = Depends(get_current_user)):
    return user

@app.get("/api/user/history")
def get_history(page: int = 1, limit: int = 20, user: dict = Depends(get_current_user)):
    items = get_credit_history(user["id"], page, limit)
    return {"items": items, "total": len(items), "page": page}

@app.get("/api/user/assets")
def my_assets(project_id: Optional[str]=None, scope: Optional[str]=None, user: dict = Depends(get_current_user)):
    if scope == "all" and user["tier"] == "free":
        raise HTTPException(403, "Pro required for history")
    target_proj = project_id if scope != "all" else None
    return get_assets(user["id"], target_proj)

@app.get("/api/resources/stickers")
def get_stickers(user: dict = Depends(get_current_user)):
    is_pro = user["tier"] in ["starter", "pro"]
    return get_system_resources("sticker", is_pro)

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
    save_project(id, user["id"], req.canvas_data, req.thumbnail_url)
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
        deduct_credits_atomic(user["id"], cost, "generation", f"Gen {len(req.prompts)}")
    except Exception:
        raise HTTPException(402, "Insufficient credits")
        
    urls, task_id = await generate_8_images(req.prompts)
    for url, prompt in zip(urls, req.prompts):
        save_asset(user["id"], url, "ai_generated", req.project_id, prompt)
    return {"image_urls": urls, "balance": user["credits"] - cost}

# [修复] 真实 OCR 接口
@app.post("/api/tools/ocr")
@limiter.limit("10/minute")
async def ocr_tool(request: Request, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """智能识图"""
    # [修复] 严格限制仅 Pro 用户可用 (根据 PRD Starter 也不可用)
    if user["tier"] != "pro":
        raise HTTPException(status_code=403, detail="Upgrade to Teacher Pro to use Smart Scan")
    
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
        return {"text": description}
    except Exception as e:
        print(f"OCR Error: {e}")
        raise HTTPException(500, "OCR Failed")

# --- Export ---
@app.post("/api/generate/pdf")
def dl_pdf(req: PdfGenRequest, user: dict = Depends(get_current_user)):
    proj = get_project_detail(req.project_id, user["id"])
    if req.current_hash != proj.get("last_downloaded_hash"):
        try:
            deduct_credits_atomic(user["id"], 50, "download_pdf", "PDF Export")
            # [修复] 调用 db_service 中的 Hash 更新函数
            update_project_hash(req.project_id, req.current_hash)
        except:
            raise HTTPException(402, "Insufficient credits")
            
    buf = BytesIO()
    create_foldable_book(req.image_urls, req.texts, buf)
    buf.seek(0)
    log_activity(user["id"], "download_pdf")
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=zine.pdf"})

@app.post("/api/export/zip")
def dl_zip(req: PdfGenRequest, user: dict = Depends(get_current_user)):
    if user["tier"] == "free":
        raise HTTPException(403, "Upgrade required")
    buf = BytesIO()
    create_assets_zip(req.image_urls, buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=assets.zip"})

# --- Pay & Support ---
@app.post("/api/payment/checkout")
def pay(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    return {"url": create_checkout_session(user["id"], req.plan_type)}

@app.post("/api/payment/portal")
def portal(user: dict = Depends(get_current_user)):
    if not user.get("stripe_customer_id"): raise HTTPException(400, "No sub")
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
    # [修复] 调用 db_service 的聚合函数，而不是直接操作 DB
    return get_full_user_audit(uid)

@app.post("/api/admin/credits/adjust")
def adm_adj(req: AdminAdjustRequest, admin: dict = Depends(require_admin)):
    if req.amount > 0:
        add_credits(req.user_id, req.amount, req.reason, "admin_adj")
    else:
        deduct_credits_atomic(req.user_id, abs(req.amount), "admin_adj", req.reason)
    return {"status": "ok"}

@app.post("/api/admin/tier/update")
def adm_tier(req: AdminTierRequest, admin: dict = Depends(require_admin)):
    update_subscription_tier(req.user_id, req.tier)
    return {"status": "ok"}